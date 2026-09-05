"""Synthetic training-set generator.

The generator's job is to produce labelled spectra the trained model can learn
from, so what matters is that the physics is real (every class evaluates to a
finite positive spectrum), the labels are planted rather than fitted, stacks
are physically coherent, and the population round-trips through the identifier
we already trust.
"""
import numpy as np
import pytest

from rheofp.data.synth import (
    make_example, generate, to_npz_dataset, class_counts, sample_params,
    forward, ALL_CLASSES, FINE_CLASSES, MODEL_ONLY_CLASSES, CLASS_REGIME,
    T_REF, N_OMEGA, N_OMEGA_RANGE,
)
from rheofp.fitting.identify import identify
from rheofp.io.data import save_npz, load_npz


@pytest.mark.parametrize("name", ALL_CLASSES)
def test_every_class_produces_a_finite_positive_spectrum(name):
    rng = np.random.default_rng(0)
    for _ in range(8):
        ex = make_example(rng, name, n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        assert N_OMEGA_RANGE[0] <= len(w) <= N_OMEGA_RANGE[1]
        assert len(Gp) == len(w) and len(Gpp) == len(w)
        assert np.all(np.isfinite(Gp)) and np.all(np.isfinite(Gpp))
        assert np.all(Gp > 0) and np.all(Gpp > 0)


@pytest.mark.parametrize("name", ALL_CLASSES)
def test_sampled_parameters_stay_inside_the_fitters_search_space(name):
    """Generated population and fitting bounds must not drift apart."""
    from rheofp.models.solutions import MODELS
    from rheofp.models.maxwell import BRANCHED_MODELS, WLM_MODELS
    banks = {**MODELS, **BRANCHED_MODELS, **WLM_MODELS}
    if name not in banks:
        pytest.skip("network classes use their own ranges (see test_network)")
    rng = np.random.default_rng(1)
    bounds = banks[name][2]
    for _ in range(20):
        theta = sample_params(rng, name)
        for v, (lo, hi) in zip(theta, bounds):
            assert lo <= v <= hi


def test_every_generated_class_has_a_candidate_in_the_identifier_bank():
    """The generator and the AICc bank must cover the same classes.

    A class the generator can produce but the bank cannot emit is not merely
    hard for the identifier - it is unanswerable, and it silently corrupts any
    accuracy measured against that identifier. wormlike_micelle was in exactly
    that state: generated, learnable by the neural head, and absent from the
    bank, so the published physics baseline was scored partly on questions it
    could not answer. Keep this assertion pointed at ALL_CLASSES, not at the
    fine classes - model-only classes are scored too.
    """
    from rheofp.fitting.identify import ALL_MODELS
    missing = set(ALL_CLASSES) - set(ALL_MODELS)
    assert not missing, (
        f"generated but unreachable by identify(): {sorted(missing)} - "
        "register a (forward, p0, bounds, k) entry or stop generating it")


def test_labels_and_regimes_are_consistent():
    rng = np.random.default_rng(2)
    for name in ALL_CLASSES:
        ex = make_example(rng, name, n_curves=1)
        assert ex["label"] == name
        assert ex["regime"] == CLASS_REGIME[name]
    assert set(FINE_CLASSES).isdisjoint(MODEL_ONLY_CLASSES)


# --- stack coherence ---------------------------------------------------------

def test_temperature_stack_shares_one_parameter_set():
    """Curves in a stack are one material at several temperatures, not
    independent draws - otherwise the classifier learns a false correlation."""
    rng = np.random.default_rng(3)
    ex = make_example(rng, "reptation", n_curves=4)
    assert len(ex["curves"]) == 4
    temps = [c[3] for c in ex["curves"]]
    assert all(np.isfinite(temps))
    assert temps == sorted(temps)
    assert np.isfinite(ex["Ea"]) and ex["Ea"] > 0
    # One window shared across the stack - same instrument, same material.
    # The point COUNT is redrawn per curve (each temperature is its own
    # sweep), so compare the window's endpoints, not the arrays.
    w0 = ex["curves"][0][0]
    for c in ex["curves"][1:]:
        np.testing.assert_allclose(c[0][0], w0[0])
        np.testing.assert_allclose(c[0][-1], w0[-1])


def test_a_melt_stack_actually_shifts_with_temperature():
    from rheofp.fitting.identify import shift_factor
    rng = np.random.default_rng(4)
    ex = make_example(rng, "reptation", n_curves=5)
    cold = ex["curves"][0][:3]
    hot = ex["curves"][-1][:3]
    s, _ = shift_factor(cold, hot)
    assert np.isfinite(s) and abs(s) > 0.1


def test_a_cured_elastomer_stack_does_not_shift_with_temperature():
    """A permanent network's plateau stays put; only the moduli scale with T."""
    from rheofp.fitting.identify import shift_factor
    rng = np.random.default_rng(5)
    ex = make_example(rng, "cured_elastomer", n_curves=4)
    assert ex["Ea"] == 0.0
    s, _ = shift_factor(ex["curves"][0][:3], ex["curves"][-1][:3])
    assert abs(s) < 0.1
    # entropic elasticity still lifts the moduli with absolute temperature
    assert ex["curves"][-1][1].mean() > ex["curves"][0][1].mean()


def test_a_critical_gel_stack_is_honestly_unalignable():
    """A gel's loss tangent is frequency-independent, so there is no feature to
    measure a shift against. The resolver must say so rather than report a
    meaningless number - the objective is flat, not minimised at zero."""
    from rheofp.fitting.identify import shift_factor, resolve_melt_vs_network
    rng = np.random.default_rng(5)
    ex = make_example(rng, "critical_gel", n_curves=4)
    assert ex["Ea"] == 0.0
    s, _ = shift_factor(ex["curves"][0][:3], ex["curves"][-1][:3])
    assert np.isnan(s)

    stack = [dict(omega=w, Gp=gp, Gpp=gpp, T_K=T) for w, gp, gpp, T in ex["curves"]]
    out = resolve_melt_vs_network(stack)
    assert out["verdict"] == "ambiguous"
    assert "frequency-independent" in out["reason"]


def test_single_curve_examples_carry_no_temperature():
    rng = np.random.default_rng(6)
    ex = make_example(rng, "zimm", n_curves=1)
    assert len(ex["curves"]) == 1
    assert np.isnan(ex["curves"][0][3])


# --- dataset assembly --------------------------------------------------------

def test_generate_is_balanced_and_deterministic():
    a = generate(45, seed=11, progress=False)
    b = generate(45, seed=11, progress=False)
    assert [e["label"] for e in a] == [e["label"] for e in b]
    counts = class_counts(a)
    assert set(counts) == set(ALL_CLASSES)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_npz_roundtrip_preserves_labels_and_stack_grouping(tmp_path):
    examples = generate(18, seed=12, progress=False)
    dataset = to_npz_dataset(examples)
    path = tmp_path / "synth.npz"
    save_npz(path, dataset)
    loaded = load_npz(path)

    assert len(loaded) == sum(len(e["curves"]) for e in examples)
    # every curve knows its label, regime and which stack it belongs to
    by_stack = {}
    for fields in loaded.values():
        sid = int(fields["stack_id"])
        by_stack.setdefault(sid, []).append(str(fields["label"]))
    assert len(by_stack) == len(examples)
    for sid, labels in by_stack.items():
        assert len(set(labels)) == 1                       # one label per stack
        assert labels[0] == examples[sid]["label"]
        assert len(labels) == len(examples[sid]["curves"])


def test_generated_population_round_trips_through_the_identifier():
    """A cheap separability check: the physics we already trust should mostly
    recover the planted label from a single cropped, noisy curve.

    Not 100% by design - Zimm and Rouse differ only in exponent, and the gel
    and elastomer models are nested. Those confusions are the ambiguity the
    trained classifier has to learn, not a generator defect.
    """
    rng = np.random.default_rng(13)
    hits = total = 0
    for name in FINE_CLASSES:
        for _ in range(4):
            ex = make_example(rng, name, n_curves=1)
            w, Gp, Gpp, _ = ex["curves"][0]
            hits += identify(w, Gp, Gpp, n_restarts=6)["best"] == name
            total += 1
    assert hits / total > 0.6


def test_synthetic_branched_population_is_identified_as_branched():
    """The model-only branched class must route to `branched` through the
    identifier bank often enough that the ML model has a clean signal - the
    old 3-param branched_spectrum could not, which is why LDPE failed."""
    rng = np.random.default_rng(21)
    hits = total = 0
    for _ in range(10):
        ex = make_example(rng, "branched", n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        hits += identify(w, Gp, Gpp, n_restarts=6)["best"] == "branched"
        total += 1
    assert hits / total > 0.6


def test_noise_is_applied_and_is_small():
    rng = np.random.default_rng(14)
    theta = sample_params(rng, "critical_gel")
    w = np.logspace(-1, 2, N_OMEGA)
    clean_p, clean_pp = forward("critical_gel", w, theta)
    ex = make_example(np.random.default_rng(14), "critical_gel", n_curves=1)
    wn, Gp, _, _ = ex["curves"][0]
    ref_p, _ = forward("critical_gel", wn, theta)
    resid = np.abs(np.log10(Gp) - np.log10(ref_p))
    assert resid.max() > 0            # noise really was applied
    assert np.median(resid) < 0.1     # ...and stayed small
