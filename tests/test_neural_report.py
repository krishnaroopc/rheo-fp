"""The neural head as report.py's second column, and the agreement signal.

The claim being tested is the one the module exists for: two mathematically
independent methods landing on the same class is better evidence than either
one's own confidence, and their DISAGREEMENT is the only signal available here
that neither self-confidence can produce.

Most of these tests need the trained checkpoint, which is gitignored and does
NOT travel between machines - so they skip rather than fail when it is absent,
and the pure-logic tests below run everywhere.
"""
import os

import numpy as np
import pytest

from rheofp.fitting.identify import identify
from rheofp.io.data import load_npz
from rheofp.neural_report import (
    DEFAULT_CHECKPOINT, agreement, neural_column, load_checkpoint,
    explain_with_neural, format_neural, ABSTAIN_HIGH,
)

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")

_HAVE_CKPT = os.path.exists(DEFAULT_CHECKPOINT)
needs_ckpt = pytest.mark.skipif(
    not _HAVE_CKPT,
    reason=f"{DEFAULT_CHECKPOINT} not present (gitignored; retrain to create)")

CLASSES = ["zimm", "rouse_screened", "reptation", "sticky_rouse",
           "sticky_reptation", "cured_elastomer", "critical_gel",
           "wormlike_micelle", "branched", "star"]


def _probs(**kw):
    """A probability vector with the named classes at exactly the given
    values and the rest sharing what is left - so `star=0.5` really is 0.5,
    not 0.5 renormalised back up to ~0.98."""
    p = np.zeros(len(CLASSES))
    for name, v in kw.items():
        p[CLASSES.index(name)] = v
    rest = p == 0
    p[rest] = max(0.0, 1.0 - p.sum()) / rest.sum()
    return p


# ── the agreement logic itself (no checkpoint, no torch) ──────────────────

def test_same_class_from_both_methods_reads_as_corroboration():
    n = neural_column(_probs(branched=0.9), CLASSES, 0.02)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0}])
    assert a["kind"] == "agree"
    assert "BOTH" in a["text"]
    # and it must NOT overclaim: shared taxonomy can fool both at once
    assert "not proof" in a["text"]


def test_a_split_across_a_known_degenerate_pair_is_not_a_real_disagreement():
    """Zimm vs Rouse differ only in a mode-spacing exponent and are known to
    be inseparable from a cropped noisy SAOS window. Reporting that split with
    the same alarm as a genuine one would cry wolf on the taxonomy's own
    documented blind spot."""
    n = neural_column(_probs(rouse_screened=0.8), CLASSES, 0.05)
    a = agreement("zimm", n, [{"name": "zimm", "delta": 0.0},
                              {"name": "rouse_screened", "delta": 0.4}])
    assert a["kind"] == "agree_degenerate"
    assert a["degeneracy_note"]
    assert "inseparable" in a["text"]


def test_a_disagreement_inside_the_live_short_list_is_marked_as_the_mild_kind():
    n = neural_column(_probs(zimm=0.7), CLASSES, 0.1)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0},
                                  {"name": "zimm", "delta": 3.0}])
    assert a["kind"] == "disagree_ranked"
    assert a["neural_delta_aicc"] == 3.0
    assert "DISAGREE" in a["text"]


def test_a_disagreement_outside_the_short_list_is_marked_as_the_sharp_kind():
    """The case that matters most: the two methods reach classes that the
    other does not even rank. This is also what out-of-taxonomy material
    tends to produce, since each side falls back on its own least-bad class
    and they need not agree on which."""
    n = neural_column(_probs(cured_elastomer=0.8), CLASSES, 0.1)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0},
                                  {"name": "cured_elastomer", "delta": 300.0}])
    assert a["kind"] == "disagree"
    assert "sharply" in a["text"]
    assert "OUTSIDE the taxonomy" in a["text"]


def test_a_class_the_prefilter_struck_is_reported_as_never_ranked():
    """The network can name a class identify() never fitted; the text must not
    imply a delta that does not exist."""
    n = neural_column(_probs(reptation=0.9), CLASSES, 0.1)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0}])
    assert a["kind"] == "disagree"
    assert a["neural_delta_aicc"] is None
    assert "never even put on the ballot" in a["text"]


def test_neural_confidence_bands_are_ordered():
    assert neural_column(_probs(star=0.95), CLASSES, 0.0)["confidence"] == "confident"
    assert neural_column(_probs(star=0.5), CLASSES, 0.0)["confidence"] == "leaning"
    assert neural_column(_probs(star=0.2), CLASSES, 0.0)["confidence"] == "unsure"


def test_a_high_abstention_is_flagged():
    lo = neural_column(_probs(star=0.9), CLASSES, 0.01)
    hi = neural_column(_probs(star=0.9), CLASSES, ABSTAIN_HIGH + 0.1)
    assert not lo["abstain_high"] and hi["abstain_high"]


def test_report_stays_importable_without_torch():
    """rheofp.report must not acquire a torch dependency through this module.

    The AICc pipeline has to keep working on a machine with no checkpoint and
    no torch - that is why DEGENERATE_PAIRS is duplicated rather than imported
    from ml/evaluate.py, and the dependency direction must stay that way.
    """
    import ast
    src = open("rheofp/report.py", encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in node.names]
            assert "torch" not in mod and not any(
                n.startswith("torch") for n in names), \
                "report.py must not import torch"
            assert "neural_report" not in mod, \
                "dependency direction is neural_report -> report, not back"


# ── against the real data, with the trained checkpoint ────────────────────

@needs_ckpt
def test_both_brains_agree_on_the_real_benchmark_curves():
    """On the literature curves both sides already get right, the agreement
    verdict has to actually say so - otherwise the signal is useless."""
    model, norm, classes = load_checkpoint()
    for path, sample, expect in (("data/tixier2004.npz", None, "critical_gel"),
                                 ("data/pivo2006.npz", "E", "branched"),
                                 ("data/pivo2006.npz", "B", "branched")):
        d = load_npz(path)
        name = sample or next(iter(d))
        s = d[name]
        w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
        out = identify(w, gp, gpp)
        curves = [dict(omega=w, Gp=gp, Gpp=gpp,
                       T_K=float(s.get("T_K", float("nan"))))]
        rep = explain_with_neural(out, curves, model, norm, classes)
        assert rep["winner"] == expect
        assert rep["neural"]["winner"] == expect
        assert rep["agreement"]["kind"] == "agree", (
            f"{name}: {rep['agreement']['kind']}")


@needs_ckpt
def test_the_agreement_signal_separates_the_star_hits_from_the_star_misses():
    """The measured payoff, and the reason this column was built.

    On Milner-McLeish 1998's seven-star set the AICc side is 5/7: it calls
    `branched` on Ma95k and Ma105k, whose windows never reach terminal flow
    (next-actions, step 4). The network reads BOTH of those as `star`.

    So on exactly the two curves where the physics side is wrong, the two
    brains disagree - and on all five where it is right, they agree. Neither
    side's own confidence score does this: AICc reports delta 57 and 103 for
    the misses, i.e. decisive, and the network is at 0.99 on both. Only the
    comparison between them carries the warning.
    """
    model, norm, classes = load_checkpoint()
    d = load_npz("data/mm1998.npz")
    agree_kinds = {}
    for name, s in d.items():
        w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
        out = identify(w, gp, gpp)
        curves = [dict(omega=w, Gp=gp, Gpp=gpp,
                       T_K=float(s.get("T_K", float("nan"))))]
        rep = explain_with_neural(out, curves, model, norm, classes)
        agree_kinds[name] = (rep["winner"], rep["neural"]["winner"],
                             rep["agreement"]["kind"])

    # every one of these is a true star (four-arm polyisoprene, Z from Ma/Me)
    for name, (phys, neur, kind) in agree_kinds.items():
        if phys == "star":
            assert kind == "agree", f"{name} should corroborate: {kind}"
        else:
            # the physics side missed it; the disagreement is the warning
            assert kind.startswith("disagree"), f"{name}: {kind}"
            assert neur == "star", f"{name}: network said {neur}"

    n_phys_right = sum(1 for p, _, _ in agree_kinds.values() if p == "star")
    assert n_phys_right == 5, f"expected the known 5/7, got {n_phys_right}"


@needs_ckpt
def test_the_linear_control_that_fools_the_fitter_is_flagged_by_disagreement():
    """Santangelo L176 is a LINEAR PIB control that identify() returns as
    `star`, at weight 1.000, a 0.043-decade fit and NO alternative inside
    delta 10 - nothing in the AICc report expresses doubt. The network does
    not say `star`, so the agreement verdict does."""
    model, norm, classes = load_checkpoint()
    s = load_npz("data/santangelo1999.npz")["L176"]
    w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
    out = identify(w, gp, gpp)
    curves = [dict(omega=w, Gp=gp, Gpp=gpp,
                   T_K=float(s.get("T_K", float("nan"))))]
    rep = explain_with_neural(out, curves, model, norm, classes)

    assert rep["winner"] == "star"                    # the known false positive
    assert all(r["delta"] > 10 for r in out["ranking"][1:])   # unopposed
    assert rep["neural"]["winner"] != "star"
    assert rep["agreement"]["kind"].startswith("disagree")


@needs_ckpt
def test_the_neural_column_renders_and_hedges_the_abstention_number():
    model, norm, classes = load_checkpoint()
    s = list(load_npz("data/tixier2004.npz").values())[0]
    w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
    out = identify(w, gp, gpp)
    rep = explain_with_neural(out, [dict(omega=w, Gp=gp, Gpp=gpp)],
                              model, norm, classes)
    text = format_neural(rep)
    assert "SECOND OPINION" in text
    assert "DO THE TWO BRAINS AGREE?" in text
    # the abstention number must never be presented as a reliability score
    assert "SYNTHETIC distribution only" in text
    assert "not evidence the answer is right" in text


@needs_ckpt
def test_explain_with_neural_leaves_the_existing_report_intact():
    """The neural column is ADDITIVE. Every key explain() returned must
    survive unchanged, because scripts and tests already read them."""
    from rheofp.report import explain
    model, norm, classes = load_checkpoint()
    s = list(load_npz("data/tixier2004.npz").values())[0]
    w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
    out = identify(w, gp, gpp)
    plain = explain(out, w=w, Gp=gp, Gpp=gpp)
    withn = explain_with_neural(out, [dict(omega=w, Gp=gp, Gpp=gpp)],
                                model, norm, classes)
    assert set(plain) <= set(withn)
    for k in plain:
        if k in ("challenge",):          # list of dicts, compare by kind
            assert [c["kind"] for c in plain[k]] == [c["kind"] for c in withn[k]]
        else:
            assert plain[k] == withn[k], f"{k} changed"


@needs_ckpt
def test_a_temperature_stack_goes_through_the_same_path_as_one_curve():
    """N=1 is the degenerate case of the set model, not a separate code path -
    that is what the masked attention pool is for."""
    model, norm, classes = load_checkpoint()
    d = load_npz("data/darby2022.npz")
    curves = [dict(omega=s["omega"], Gp=s["Gp"], Gpp=s["Gpp"],
                   T_K=float(s.get("T_K", float("nan"))))
              for s in d.values()]
    from rheofp.neural_report import predict
    p_stack, _ = predict(model, norm, classes, curves)
    p_one, _ = predict(model, norm, classes, curves[:1])
    assert p_stack.shape == p_one.shape == (len(classes),)
    assert np.isclose(p_stack.sum(), 1.0) and np.isclose(p_one.sum(), 1.0)


# ── what the PAIR is worth, as distinct from either label ────────────────

def test_a_disagreement_offers_the_two_labels_as_a_shortlist():
    """The most robust thing the n=200 measurement produced, and it was not
    the thing being measured: one of the two labels is right ~89% of the time
    on disagreements, where each method ALONE is right 39-50%. So the pair is
    worth much more than the argument about which of them wins, and the report
    has to hand it over as a shortlist rather than a winner plus a dissent."""
    n = neural_column(_probs(cured_elastomer=0.8), CLASSES, 0.1)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0},
                                  {"name": "cured_elastomer", "delta": 300.0}])
    assert a["pair"] == ["branched", "cured_elastomer"]      # sorted, both named
    assert a["pair_note"] and "TAKE THE TWO TOGETHER" in a["pair_note"]


def test_agreement_on_one_class_offers_no_pair():
    """There is no shortlist when both methods named the same class."""
    n = neural_column(_probs(branched=0.9), CLASSES, 0.02)
    a = agreement("branched", n, [{"name": "branched", "delta": 0.0}])
    assert a["pair"] is None
    assert a["pair_note"] is None


def test_the_degenerate_pair_gets_its_own_stronger_shortlist_claim():
    """On the known-degenerate split the pair is stronger than either member
    (~97% of planted cases against 40-58% each) and the actionable advice is
    different: outside knowledge (solvent quality, whether it was crosslinked)
    settles it.

    The note must ALSO warn that which member is the better bet is unstable -
    the two measurement runs reversed on exactly this group (physics 0.364 /
    neural 0.636 at n=200; 0.576 / 0.394 at n=600), so any advice to prefer
    one side of this pair would have been fitted to noise.
    """
    n = neural_column(_probs(rouse_screened=0.8), CLASSES, 0.05)
    a = agreement("zimm", n, [{"name": "zimm", "delta": 0.0},
                              {"name": "rouse_screened", "delta": 0.4}])
    assert a["pair"] == ["rouse_screened", "zimm"]
    assert "97%" in a["pair_note"]
    assert "not even stable" in a["pair_note"]


def test_no_text_claims_agreement_beats_the_other_confidence_scores():
    """The n=200 measurement REFUTED that claim (0.940 vs 0.934 at matched
    coverage, +0.006, inside sampling error), and an earlier draft of this
    module asserted it in two places. The honest framing is that agreement is
    INDEPENDENT of both and so fails differently - never that it is better."""
    from rheofp.neural_report import _agreement_text
    for kind in ("agree", "agree_degenerate", "disagree_ranked", "disagree"):
        n = neural_column(_probs(star=0.8), CLASSES, 0.1)
        txt = _agreement_text(kind, "branched", n, 5.0).lower()
        assert "worth more than either" not in txt
        assert "stronger evidence than either" not in txt


def test_the_quoted_accuracies_match_the_committed_measurement():
    """The user-facing text quotes measured numbers, so they must not drift
    from the run they came from. Pins them against the committed output of
    scripts/measure_agreement.py rather than against a copy of the numbers.

    Points at the n=600 run (seed 11), which supersedes the n=200 one (seed 7)
    because that had only 18 curves in the disagree arm. Both files stay
    committed; this asserts the constants track whichever the module says it
    is quoting.
    """
    import re
    from rheofp import neural_report as nr

    path = "docs/agreement_measurement_n600_2026-09-10.txt"
    text = open(path, encoding="utf-8").read()

    m = re.search(r"^(\d+) planted curves", text, re.M)
    assert m and int(m.group(1)) == nr.AGREE_N

    def row(label):
        m = re.search(
            rf"^{re.escape(label)}\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
            text, re.M)
        assert m, f"row {label!r} not found in {path}"
        return float(m.group(2)), float(m.group(3)), float(m.group(4))

    phys_a, neur_a, either_a = row("agree (any kind)")
    phys_d, neur_d, either_d = row("disagree (any)")
    assert phys_a == nr.AGREE_ACC_PHYS
    assert neur_a == nr.AGREE_ACC_NEURAL
    assert phys_d == nr.DISAGREE_ACC_PHYS
    assert neur_d == nr.DISAGREE_ACC_NEURAL
    assert either_d == nr.EITHER_RIGHT_DISAGREE
    assert either_a == nr.EITHER_RIGHT_AGREE

    m = re.search(r"keep top \d+% by network p\s*:\s*neural acc ([\d.]+)", text)
    assert m and float(m.group(1)) == nr.AGREE_ACC_GATE_BASELINE


def test_the_pair_beats_either_member_which_is_what_the_shortlist_rests_on():
    """The claim the shortlist is built on, asserted against the constants so
    it cannot quietly stop being true if they are ever re-measured.

    This held across both runs and got STRONGER at the larger n, unlike the
    gate comparison - which is why it, not the gate, is the headline.
    """
    from rheofp import neural_report as nr
    assert nr.EITHER_RIGHT_DISAGREE > nr.DISAGREE_ACC_PHYS + 0.3
    assert nr.EITHER_RIGHT_DISAGREE > nr.DISAGREE_ACC_NEURAL + 0.3
    assert nr.EITHER_RIGHT_AGREE > nr.AGREE_ACC_PHYS


def test_the_gate_margin_is_not_overstated():
    """The n=200 run put this margin at +0.006 (refuted); n=600 puts it at
    +0.019 against an SE of ~0.011, i.e. ~1.7 SE - real enough to stop calling
    it refuted, NOT enough to call it established. The wording must stay at
    "comparable, possibly a little better" until a run settles it."""
    from rheofp.neural_report import (
        AGREE_ACC_NEURAL, AGREE_ACC_GATE_BASELINE, _agreement_text,
    )
    margin = AGREE_ACC_NEURAL - AGREE_ACC_GATE_BASELINE
    assert 0.0 < margin < 0.05, (
        "if the margin has moved out of this band, re-read the wording in "
        "_agreement_text before changing this test")
    n = neural_column(_probs(branched=0.9), CLASSES, 0.02)
    txt = _agreement_text("agree", "branched", n, 0.0)
    assert "not decisively so" in txt
