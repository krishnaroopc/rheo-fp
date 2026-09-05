"""ML pipeline: dataset contracts, masking, and a short end-to-end train.

The tests that matter here are the ones guarding leakage and masking - the
two failure modes that silently inflate results instead of raising an error.
Training itself is exercised only briefly; this is a correctness suite, not a
benchmark.
"""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from rheofp.data.synth import generate
from rheofp.ml.dataset import (
    SpectraStacks, collate_stacks, fit_normalisation, split_records,
    examples_to_records, npz_to_records, curve_tensor, CLASSES, CLASS_TO_IDX,
    N_CHANNELS, N_SUMMARY, N_GRID,
)
from rheofp.ml.model import RheoNet, count_parameters
from rheofp.ml.train import train, make_loaders, compute_loss, evaluate, _auc
from rheofp.ml.evaluate import (
    confusion_matrix, abstention_curve, accuracy_by_stack_size, predict,
    summarise, physics_baseline_accuracy,
)
from rheofp.io.data import save_npz


@pytest.fixture(scope="module")
def records():
    return examples_to_records(generate(180, seed=3, progress=False))


# --- dataset contracts -------------------------------------------------------

def test_curve_tensor_shape_and_channels():
    w = np.logspace(-2, 2, 40)
    x = curve_tensor(w, np.full(40, 100.0), np.full(40, 10.0))
    assert x.shape == (N_GRID, N_CHANNELS)
    assert np.isfinite(x).all()
    # log-frequency channel is centred, so window POSITION is carried by the
    # summary vector rather than leaking into the sequence
    assert abs(x[:, 0].mean()) < 1e-5


@pytest.mark.parametrize("n", [5, 11, 16, 40, 60, 90, 200])
def test_curve_tensor_accepts_any_point_count(n):
    """An upload carries whatever density it carries; the tensor is fixed."""
    w = np.logspace(-1, 2, n)
    x = curve_tensor(w, 100.0 * w ** 0.5, 10.0 * w ** 0.5)
    assert x.shape == (N_GRID, N_CHANNELS)
    assert np.isfinite(x).all()


def test_curve_tensor_is_invariant_to_sampling_density():
    """Same spectrum, same window, different densities -> same tensor.

    This is the property that was missing: the model was trained only at 60
    points and keyed on density, so every real curve (11-90 points) was
    misclassified until it was resampled by hand.
    """
    power = lambda w: (100.0 * w ** 0.5, 10.0 * w ** 0.5)   # exact in log-log
    sparse = np.logspace(-1, 2, 13)
    dense = np.logspace(-1, 2, 97)
    x_sparse = curve_tensor(sparse, *power(sparse))
    x_dense = curve_tensor(dense, *power(dense))
    assert np.allclose(x_sparse, x_dense, atol=1e-5)


def test_curve_tensor_still_distinguishes_different_windows():
    """Density invariance must not flatten away the window itself."""
    a = np.logspace(-2, 0, 30)
    b = np.logspace(1, 3, 30)
    xa = curve_tensor(a, 100.0 * a ** 0.5, 10.0 * a ** 0.5)
    xb = curve_tensor(b, 100.0 * b ** 0.5, 10.0 * b ** 0.5)
    assert not np.allclose(xa[:, 1], xb[:, 1])


def test_curve_tensor_handles_unsorted_frequencies():
    w = np.logspace(-1, 2, 25)
    perm = np.random.default_rng(0).permutation(len(w))
    ordered = curve_tensor(w, 100.0 * w ** 0.5, 10.0 * w ** 0.5)
    shuffled = curve_tensor(w[perm], (100.0 * w ** 0.5)[perm],
                            (10.0 * w ** 0.5)[perm])
    assert np.allclose(ordered, shuffled, atol=1e-6)


def test_collate_accepts_stacks_whose_curves_had_different_densities():
    """A stack's curves are separate sweeps and need not share a density."""
    rng = np.random.default_rng(0)
    curves = []
    for n in (11, 47, 90):
        w = np.logspace(-1, 2, n)
        curves.append((w, 100.0 * w ** 0.5, 10.0 * w ** 0.5, 300.0))
    rec = {"curves": curves, "label": CLASSES[0],
           "regime": "terminal", "params": np.zeros(2)}
    batch = collate_stacks([SpectraStacks([rec])[0]])
    assert batch["x"].shape[1:3] == (3, N_GRID)
    assert batch["mask"].all()


def test_split_is_by_stack_not_by_curve(records):
    train_rec, val_rec, test_rec = split_records(records, seed=0)
    assert len(train_rec) + len(val_rec) + len(test_rec) == len(records)
    # a record object must appear in exactly one split
    ids = [{id(r) for r in part} for part in (train_rec, val_rec, test_rec)]
    assert ids[0].isdisjoint(ids[1])
    assert ids[0].isdisjoint(ids[2])
    assert ids[1].isdisjoint(ids[2])


def test_split_is_deterministic_for_a_seed(records):
    a = split_records(records, seed=5)[0]
    b = split_records(records, seed=5)[0]
    assert [id(r) for r in a] == [id(r) for r in b]


def test_normalisation_is_fitted_on_training_data_only(records):
    """Leakage guard: stats from the train split must differ from stats over
    everything, or the fit is silently seeing val/test."""
    train_rec, _, _ = split_records(records, seed=0)
    n_train = fit_normalisation(train_rec)
    n_all = fit_normalisation(records)
    assert not np.allclose(n_train["x_mean"], n_all["x_mean"])


def test_collate_pads_and_masks_ragged_stacks(records):
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(16)])
    B, n_max = batch["mask"].shape
    assert batch["x"].shape[:2] == (B, n_max)
    assert batch["summary"].shape == (B, n_max, N_SUMMARY)
    # every example has at least one real curve, and the mask is a prefix
    counts = batch["mask"].sum(dim=1)
    assert (counts >= 1).all()
    for i in range(B):
        n = int(counts[i])
        assert batch["mask"][i, :n].all()
        assert not batch["mask"][i, n:].any()


# --- masking correctness -----------------------------------------------------

def test_padding_cannot_influence_the_output(records):
    """The central masking guarantee: garbage in padded slots changes nothing."""
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(24)])
    assert (~batch["mask"]).any(), "need at least one padded slot to test"

    model = RheoNet().eval()
    poisoned = {k: (v.clone() if torch.is_tensor(v) else v)
                for k, v in batch.items()}
    poisoned["x"][~poisoned["mask"]] = 1e3
    poisoned["summary"][~poisoned["mask"]] = 1e3

    with torch.no_grad():
        a = model(batch["x"], batch["summary"], batch["mask"])
        b = model(poisoned["x"], poisoned["summary"], poisoned["mask"])
    torch.testing.assert_close(a["class_logits"], b["class_logits"])
    torch.testing.assert_close(a["params"], b["params"])


def test_attention_weights_are_normalised_and_ignore_padding(records):
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(24)])
    model = RheoNet().eval()
    with torch.no_grad():
        out = model(batch["x"], batch["summary"], batch["mask"])
    attn = out["attention"]
    torch.testing.assert_close(attn.sum(dim=1), torch.ones(attn.shape[0]),
                               rtol=1e-4, atol=1e-4)
    assert float(attn[~batch["mask"]].abs().max()) == 0.0


def test_single_curve_stacks_are_handled(records):
    """N=1 is the degenerate case of the set architecture, not a special path."""
    singles = [r for r in records if len(r["curves"]) == 1][:8]
    assert singles
    ds = SpectraStacks(singles, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(len(singles))])
    assert batch["mask"].shape[1] == 1
    model = RheoNet().eval()
    with torch.no_grad():
        out = model(batch["x"], batch["summary"], batch["mask"])
    assert out["class_logits"].shape == (len(singles), len(CLASSES))
    assert torch.isfinite(out["class_logits"]).all()


# --- model -------------------------------------------------------------------

def test_model_emits_both_heads_with_correct_shapes(records):
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(8)])
    out = RheoNet()(batch["x"], batch["summary"], batch["mask"])
    assert out["class_logits"].shape == (8, len(CLASSES))
    assert out["abstain_logit"].shape == (8,)
    assert out["params"].shape[0] == 8
    assert count_parameters(RheoNet()) > 0


def test_gradients_reach_every_parameter(records):
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(8)])
    model = RheoNet()
    out = model(batch["x"], batch["summary"], batch["mask"])
    loss, parts = compute_loss(out, batch)
    loss.backward()
    dead = [n for n, p in model.named_parameters()
            if p.requires_grad and (p.grad is None or torch.all(p.grad == 0))]
    # the pooling query can legitimately receive a zero grad on a tiny batch
    assert not [d for d in dead if "query" not in d], f"no gradient: {dead}"
    assert set(parts) == {"ce", "regime", "abstain", "params"}


# --- evaluation --------------------------------------------------------------

def test_confusion_matrix_counts_correctly():
    cm = confusion_matrix(np.array([0, 1, 1, 2]), np.array([0, 1, 2, 2]),
                          n=len(CLASSES))
    assert cm[0, 0] == 1 and cm[1, 1] == 1 and cm[2, 1] == 1 and cm[2, 2] == 1
    assert cm.sum() == 4


def test_abstention_curve_improves_accuracy_on_a_perfect_signal():
    true = np.array([0, 0, 1, 1, 2, 2])
    pred = np.array([0, 9, 1, 9, 2, 9])          # every other one wrong
    score = np.array([0.0, 1.0, 0.0, 1.0, 0.0, 1.0])   # perfectly flags errors
    curve = abstention_curve(pred, true, score, fractions=[0.0, 0.5])
    assert curve[0]["accuracy"] == 0.5
    assert curve[1]["accuracy"] == 1.0


def test_auc_is_half_for_a_useless_signal_and_one_for_a_perfect_one():
    wrong = np.array([True, True, False, False])
    assert _auc(np.array([1.0, 1.0, 1.0, 1.0]), wrong) == pytest.approx(0.5)
    assert _auc(np.array([0.9, 0.8, 0.2, 0.1]), wrong) == pytest.approx(1.0)


def test_accuracy_by_stack_size_groups_correctly():
    rows = accuracy_by_stack_size(np.array([0, 0, 1, 1]), np.array([0, 1, 1, 1]),
                                  np.array([1, 1, 3, 3]))
    by_n = {r["n_curves"]: r for r in rows}
    assert by_n[1]["accuracy"] == 0.5
    assert by_n[3]["accuracy"] == 1.0


# --- end to end --------------------------------------------------------------

@pytest.mark.slow
def test_short_training_run_learns_something(records):
    """Two epochs on a small set: not a benchmark, just proof the loop runs,
    the loss is finite, and accuracy clears chance (1/9)."""
    model, history, test, norm = train(records, epochs=2, batch_size=16,
                                       seed=0, device=torch.device("cpu"),
                                       verbose=False)
    assert len(history) == 2
    assert np.isfinite(history[-1]["train_loss"])
    assert test["accuracy"] > 1.0 / len(CLASSES)
    assert set(norm) == {"x_mean", "x_std", "s_mean", "s_std"}


def test_param_targets_are_padded_and_masked(records):
    """A 2-parameter critical gel must not train the two unused output slots."""
    from rheofp.ml.dataset import N_PARAMS, _param_target
    gel = [r for r in records if r["label"] == "critical_gel"][:1]
    assert gel
    vec, has = _param_target(gel[0]["params"])
    assert has and vec.shape == (N_PARAMS,)
    assert np.count_nonzero(vec[2:]) == 0        # padded tail is zero

    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(8)])
    assert batch["params"].shape == (8, N_PARAMS)
    assert batch["params_mask"].dtype == torch.bool


def test_head_two_receives_gradient_from_the_parameter_loss(records):
    """Regression guard: head 2 was once silently untrained because the loss
    never saw a target. It must get a non-zero gradient."""
    ds = SpectraStacks(records, norm=fit_normalisation(records))
    batch = collate_stacks([ds[i] for i in range(16)])
    model = RheoNet()
    loss, parts = compute_loss(model(batch["x"], batch["summary"],
                                     batch["mask"]), batch)
    loss.backward()
    grads = [p.grad.abs().sum().item() for n, p in model.named_parameters()
             if n.startswith("head_params") and p.grad is not None]
    assert grads and max(grads) > 0
    assert parts["params"] > 0


def test_physics_baseline_is_scored_only_on_classes_its_bank_can_emit():
    """The baseline must not be charged for questions it cannot answer.

    It used to filter its pool by the NEURAL head's class list, which is a
    no-op, so every wormlike_micelle example counted as a miss for a bank that
    had no micelle candidate - about 1/9 of the pool, dragging the published
    baseline down by roughly a tenth. The filter now follows the bank, and
    reports what it dropped instead of absorbing it into the score.
    """
    from rheofp.fitting.identify import ALL_MODELS
    from rheofp.data.synth import ALL_CLASSES

    # the invariant the fix restores: nothing generated is unanswerable
    assert not set(ALL_CLASSES) - set(ALL_MODELS)

    recs = generate(4, classes=["critical_gel"], seed=4, progress=False)
    out = physics_baseline_accuracy(recs, n_max=4, n_restarts=4)
    assert out["skipped"] == 0 and out["n"] == 4

    # an unregistered class is dropped and reported, never scored as a miss
    orphan = [{**recs[0], "label": "not_in_any_bank"}] + recs
    out2 = physics_baseline_accuracy(orphan, n_max=4, n_restarts=4)
    assert out2["skipped"] == 1
    assert out2["accuracy"] == out["accuracy"]


def test_npz_roundtrip_reproduces_records(tmp_path):
    from rheofp.data.synth import to_npz_dataset
    examples = generate(12, seed=9, progress=False)
    path = tmp_path / "ml.npz"
    save_npz(path, to_npz_dataset(examples))
    recs = npz_to_records(path)
    assert len(recs) == len(examples)
    for a, b in zip(recs, examples):
        assert a["label"] == b["label"]
        assert len(a["curves"]) == len(b["curves"])
