"""Stack-level melt-vs-network resolution across a temperature stack.

The single-curve pipeline abstains on the melt-vs-rubber ambiguity because no
statistic on one curve can settle it. These tests exercise the evidence a
stack adds: terminal relaxation appearing at some temperature, and the
spectrum shifting along the frequency axis as the sample is heated.
"""
import numpy as np
import pytest

from rheofp.models.maxwell import (
    maxwell_spectrum, arrhenius_shift, sticky_maxwell_stack,
)
from rheofp.models.network import chasset_thirion_spectrum
from rheofp.fitting.identify import (
    identify, identify_stack, resolve_melt_vs_network, shift_factor,
    SHIFT_DECADES_MIN,
)

T_LIST = [278.15, 288.15, 298.15, 308.15, 318.15]
T_REF = 298.15


def _stack(w, curves, temps=T_LIST):
    return [dict(omega=w, Gp=gp, Gpp=gpp, T_K=t)
            for (gp, gpp), t in zip(curves, temps)]


def _network_stack(w, T=T_LIST):
    """Permanent network: entropic elasticity scales the moduli with absolute
    temperature, but nothing moves along the frequency axis."""
    return _stack(w, [chasset_thirion_spectrum(w, 1.0e6 * (t / T_REF),
                                               2.0e4 * (t / T_REF), 0.20)
                      for t in T], T)


def _hidden_terminal_melt_stack(w, Ea=80e3, T=T_LIST):
    """High-Mw entangled melt whose terminal relaxation sits below the window.

    A broad mode ladder gives a plateau plus a rising Rouse wing - the shape
    that impersonates a crosslinked network in a single curve.
    """
    tau0 = np.logspace(-5, 2, 60)
    g = np.full(60, 1.0e5 / 60)
    return _stack(w, [maxwell_spectrum(w, g, arrhenius_shift(tau0, Ea, t, T_REF))
                      for t in T], T)


# --- shift_factor ------------------------------------------------------------

def test_shift_factor_recovers_a_planted_horizontal_shift():
    w = np.logspace(-2, 3, 60)
    tau = np.logspace(-3, 1, 30)
    g = np.full(30, 1.0e4 / 30)
    ref = (w,) + maxwell_spectrum(w, g, tau)
    planted = 0.8  # decades
    cur = (w,) + maxwell_spectrum(w, g, tau * 10**planted)
    # shifting `cur` back onto `ref` undoes the planted slowdown
    s, cost = shift_factor(ref, cur)
    assert abs(s - planted) < 0.05
    assert cost < 1e-3


def test_shift_factor_is_zero_for_identical_curves():
    w = np.logspace(-2, 3, 60)
    spec = (w,) + chasset_thirion_spectrum(w, 1.0e6, 2.0e4, 0.2)
    s, _ = shift_factor(spec, spec)
    assert abs(s) < 1e-6


def test_shift_factor_ignores_a_pure_vertical_rescaling():
    """tan(delta) is a modulus ratio, so b_T cancels and no shift is reported."""
    w = np.logspace(-2, 3, 60)
    Gp, Gpp = chasset_thirion_spectrum(w, 1.0e6, 2.0e4, 0.2)
    s, _ = shift_factor((w, Gp, Gpp), (w, 3.0 * Gp, 3.0 * Gpp))
    assert abs(s) < 1e-6


# --- resolve_melt_vs_network -------------------------------------------------

def test_terminal_relaxation_at_any_temperature_settles_it_as_melt():
    w = np.logspace(-2, 3, 60)
    curves = sticky_maxwell_stack(w, [5000.0], [1.0], 60e3, T_LIST, T_REF)
    out = resolve_melt_vs_network(_stack(w, curves))
    assert out["verdict"] == "melt"
    assert "terminal" in out["reason"]
    assert out["terminal_at"]


def test_shifting_spectrum_reveals_a_melt_with_no_terminal_in_window():
    """The case the resolver exists for - nothing in any single curve flows."""
    w = np.logspace(1.5, 3, 40)
    curves = sticky_maxwell_stack(w, [5000.0], [1.0], 60e3, T_LIST, T_REF)
    stack = _stack(w, curves)
    assert not any(resolve_melt_vs_network([s])["terminal_at"] for s in stack)

    out = resolve_melt_vs_network(stack)
    assert out["verdict"] == "melt"
    assert out["shift_decades"] >= SHIFT_DECADES_MIN


def test_temperature_invariant_plateau_resolves_as_network():
    w = np.logspace(-3, 4, 60)
    out = resolve_melt_vs_network(_network_stack(w))
    assert out["verdict"] == "network"
    assert out["shift_decades"] < SHIFT_DECADES_MIN


def test_flat_loss_tangent_is_reported_as_unalignable_not_as_zero_shift():
    """A critical gel has a frequency-independent tan(delta), so the alignment
    objective is flat - every shift fits equally well. Reporting the grid's
    arbitrary minimum as a measurement would be worse than admitting the
    stack cannot answer, so the resolver must return "ambiguous"."""
    from rheofp.models.network import critical_gel_spectrum
    w = np.logspace(-1, 2, 40)
    stack = _stack(w, [critical_gel_spectrum(w, 300.0 * (t / T_REF), 0.70)
                       for t in T_LIST])
    s, _ = shift_factor(stack[0]["spectrum"] if "spectrum" in stack[0]
                        else (stack[0]["omega"], stack[0]["Gp"], stack[0]["Gpp"]),
                        (stack[-1]["omega"], stack[-1]["Gp"], stack[-1]["Gpp"]))
    assert np.isnan(s)

    out = resolve_melt_vs_network(stack)
    assert out["verdict"] == "ambiguous"
    assert "frequency-independent" in out["reason"]


def test_single_curve_cannot_resolve_and_says_so():
    w = np.logspace(-3, 4, 60)
    out = resolve_melt_vs_network(_network_stack(w)[:1])
    assert out["verdict"] == "ambiguous"
    assert "temperatures" in out["reason"]


def test_entropic_modulus_growth_alone_is_not_read_as_movement():
    """G_inf ~ T lifts every curve vertically; that must not look like a shift."""
    w = np.logspace(-3, 4, 60)
    out = resolve_melt_vs_network(_network_stack(w))
    assert out["shift_decades"] < 0.05


# --- identify_stack ----------------------------------------------------------

def test_stack_lifts_the_abstention_on_a_genuine_network():
    w = np.logspace(-3, 4, 60)
    stack = _network_stack(w)
    alone = identify(stack[0]["omega"], stack[0]["Gp"], stack[0]["Gpp"])
    assert alone["best"] == "cured_elastomer"
    assert alone["abstain"] is True          # one curve cannot commit

    out = identify_stack(stack)
    assert out["best"] == "cured_elastomer"
    assert out["abstain"] is False           # the stack can
    assert out["stack"]["verdict"] == "network"


def test_stack_confirms_a_broad_melt_identified_as_branched():
    """A single curve of this broad entangled melt now routes to `branched`
    (the BSW spectrum in the bank), not to a network class - it is a melt and
    is identified as one. The stack agrees: the spectrum walks along the
    frequency axis on heating. Nothing to overturn, and Head 1 must NOT
    spuriously abstain on a melt it got right.
    """
    w = np.logspace(-1, 2, 40)
    stack = _hidden_terminal_melt_stack(w)

    alone = identify(stack[0]["omega"], stack[0]["Gp"], stack[0]["Gpp"])
    assert alone["best"] == "branched"
    assert alone["abstain"] is False

    out = identify_stack(stack)
    assert out["stack"]["verdict"] == "melt"
    assert out["stack"]["shift_decades"] >= SHIFT_DECADES_MIN
    assert out["best"] == "branched"
    assert out["abstain"] is False


def _disguised_network_melt_stack(w):
    """Residual disguised-melt case: a dominant slow mode (the plateau) plus a
    faint fast ladder (the wing), terminal well below the window. The
    single-curve fit calls this cured_elastomer, not branched - it is flat and
    loss-poor enough to pass for a crosslinked network."""
    tau0 = np.concatenate([[50.0], np.logspace(-4, -1, 20)])
    g = np.concatenate([[1.0e5], np.full(20, 1.0e5 / 400)])
    return _stack(w, [maxwell_spectrum(w, g, arrhenius_shift(tau0, 90e3, t, T_REF))
                      for t in T_LIST])


def test_stack_overturns_a_network_call_on_a_disguised_melt():
    """The stack overturn logic still guards the residual case: a melt the
    single-curve fit calls cured_elastomer. With the stack present,
    identify_stack passes n_temperatures>=2, which would normally LIFT the
    melt-vs-rubber abstention - but the stack shows the spectrum shifting with
    temperature, which no permanent network does, so the abstention must be
    re-imposed rather than lifted.
    """
    w = np.logspace(-1, 2, 40)
    stack = _disguised_network_melt_stack(w)

    alone = identify(stack[0]["omega"], stack[0]["Gp"], stack[0]["Gpp"])
    assert alone["best"] == "cured_elastomer"

    # a genuine network at the same n_temperatures would have its abstention lifted
    net = identify_stack(_network_stack(w))
    assert net["abstain"] is False

    out = identify_stack(stack)
    assert out["stack"]["verdict"] == "melt"
    assert out["stack"]["shift_decades"] >= SHIFT_DECADES_MIN
    assert out["abstain"] is True
    assert "contradicts" in out["abstain_reason"]


def test_identify_stack_still_emits_a_model_when_head_one_abstains():
    """Head 2 never abstains, per the frozen two-head architecture."""
    w = np.logspace(-1, 2, 40)
    out = identify_stack(_disguised_network_melt_stack(w))
    assert out["abstain"] is True
    assert out["best"] in {r["name"] for r in out["ranking"]}
    assert out["best_weight"] > 0


@pytest.mark.parametrize("Ea,expected", [(80e3, "melt"), (0.0, "network")])
def test_activation_energy_controls_the_verdict(Ea, expected):
    """Ea = 0 freezes the spectrum in place, making the melt indistinguishable
    from a network - the resolver reports what it can see, not what is true."""
    w = np.logspace(-1, 2, 40)
    out = resolve_melt_vs_network(_hidden_terminal_melt_stack(w, Ea=Ea))
    assert out["verdict"] == expected
