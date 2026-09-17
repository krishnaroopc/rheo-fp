"""Zimm/Rouse/reptation model bank for polymer-solution regime identification.

Canonical source: solution_identifier.ipynb. Its embedded _maxwell_sum was a
byte-for-byte duplicate of rheofp.models.maxwell.maxwell_spectrum (confirmed
by diff) and is not migrated - all forward models here call the canonical
version instead.
"""
from __future__ import annotations

import numpy as np

from rheofp.models.maxwell import maxwell_spectrum


def _rouse_spectrum(N, tau1, exponent):
    """Generalized bead-spring spectrum.
      tau_p = tau1 / p**exponent
      exponent = 2   -> Rouse
      exponent = 3*nu (good solvent ~1.8) -> Zimm
    Equal modulus weight per mode (g_p = const, normalized later by Ge/N).
    Returns (g, tau) for p = 1..N.
    """
    p = np.arange(1, N + 1)
    tau = tau1 / p**exponent
    g = np.ones_like(tau)
    return g, tau


def model_zimm(w, theta):
    """params: Gscale(log), tau1(log), N(int via round) ; HI exponent fixed 1.8"""
    Gs, tau1, N = theta
    Gs = 10.0**Gs
    tau1 = 10.0**tau1
    N = max(2, int(round(N)))
    g, tau = _rouse_spectrum(N, tau1, exponent=1.8)
    g = g * (Gs / g.sum())
    return maxwell_spectrum(w, g, tau)


ZIMM_P0 = [2.0, 0.0, 20]
ZIMM_BNDS = [(-2, 8), (-4, 4), (2, 200)]


def model_rouse(w, theta):
    """params: Gscale(log), tau1(log), N ; Rouse exponent 2"""
    Gs, tau1, N = theta
    Gs = 10.0**Gs
    tau1 = 10.0**tau1
    N = max(2, int(round(N)))
    g, tau = _rouse_spectrum(N, tau1, exponent=2.0)
    g = g * (Gs / g.sum())
    return maxwell_spectrum(w, g, tau)


ROUSE_P0 = [2.0, 0.0, 20]
ROUSE_BNDS = [(-2, 8), (-4, 4), (2, 200)]


# Milner-McLeish contour-length-fluctuation prefactor: the fraction of the
# tube that survives CLF and must relax by reptation proper is
# mu = 1 - C_CLF/sqrt(Z). 1.3 is the standard coefficient (Milner & McLeish
# 1998; Likhtman & McLeish 2002 eq 12 uses the same 1/sqrt(Z) form).
C_CLF = 1.3
# Floor on mu, so a weakly-entangled chain cannot drive the reptation
# amplitude to zero (mu would go negative below Z = 1.69).
MU_FLOOR = 0.05
# The high-frequency Rouse ladder stops once a mode's tau sits this many
# decades below the window's fastest time - it then contributes w*tau << 1 to
# both moduli, i.e. nothing measurable. Mirrors star.MODE_TAU_FLOOR_DECADES.
REPT_MODE_TAU_FLOOR_DECADES = 2.0
REPT_MODE_COUNT_CAP = 4000


def model_reptation(w, theta, clf=True, hf_rouse=True):
    """Doi-Edwards reptation + contour-length fluctuation + Rouse modes.

    params: Ge(log10 Pa), tau_d(log10 s), Z(entanglements)

    Three contributions, all reaching maxwell_spectrum as one mode ladder:

      1. reptation proper - odd modes 8/(pi^2 p^2) at tau_d/p^2, carrying only
         the fraction `mu` of the plateau that survives CLF;
      2. contour-length fluctuation - the remaining (1 - mu), relaxing on a
         Rouse ladder between tau_e and the Rouse time tau_R = tau_d/(3Z);
      3. the chain's own Rouse motion above 1/tau_R - the longitudinal modes
         (weight Ge/5Z) and the transverse/high-frequency modes (weight Ge/Z,
         tau_R/2p^2), which is Likhtman-McLeish eq 19's 2nd and 3rd sums in the
         form already validated in tube.py.

    >>> WHY 2 AND 3 EXIST: THE BUG THEY FIX, MEASURED 2026-09-16 <<<

    The original version had neither. It carried the full plateau on the
    reptation modes (no CLF) and truncated its Rouse ladder at q = Z, using
    tau_e = tau_d/Z^3 - so the spectrum simply STOPPED at 1/tau_e, while a real
    sweep continues past it. On Katzarova et al. (2018)'s three monodisperse
    polystyrene melts - textbook entangled linear chains, exactly this class's
    target - the model's G'' fell a factor of ~9 below the data at the top of
    the window and it fit at rms 0.18-0.22 decades, losing to `branched` (BSW)
    by dAICc 518 and 8-9x on residual. It was never returned for any of the
    three; `identify()` called all of them `branched`.

    That is the SAME defect, with the same signature, that was found and fixed
    in star.py on 2026-09-09: "the arm's own Rouse modes were missing - MM
    scope eq 26 to end at the G'' minimum, a real window goes past it, so the
    fitter inflated Z to cover the gap." Here the compensation ran the other
    way: Z was driven DOWN (7.5 / 5.5 / 3.5 against a true 29.5 / 15.5 / 7.9)
    because in the old model Z's only job was to set where the ladder stopped.

    Effect of the fix on those three curves, at the bank's 12 restarts:

        rms        0.220 / 0.210 / 0.176  ->  0.115 / 0.083 / 0.044
        fitted Ge  1.9-2.1e5 Pa, i.e. ON polystyrene's true ~2e5 plateau
                   (the old model also landed near it, but only by distorting Z)

    Ablation, so the two terms are separately justified - PS392 / PS206 / PS105:
        neither term:  0.788 / 0.600 / 0.457   (Z runs to the bound, 130-186)
        + Rouse only:  0.152 / 0.125 / 0.076
        + CLF + Rouse: 0.115 / 0.083 / 0.044

    CONTEXT FOR READING THOSE NUMBERS: a FREE 12-mode Prony ladder - 12 free
    amplitudes, no physics - reaches only 0.029 / 0.039 / 0.047 on the same
    curves, so ~0.03-0.05 is the digitization floor here, not zero. This
    3-parameter model is now within ~2x of an unconstrained fit on PS392 and
    at the floor on PS105.

    Z IS STILL BIASED LOW (14.9 / 7.8 / 4.8 against 29.5 / 15.5 / 7.9) and is
    NOT a reportable output - report "reptation", never "Z = ...". The same
    caveat star.py carries for its own Z, for the same reason: LVE constrains
    the SHAPE, and Z enters mainly through where the Rouse ladder begins.

    The full Likhtman-McLeish forward (tube.Gstar, with CLF, constraint release
    and the Sturm-sequence machinery) reaches rms 0.049-0.086 with Ge 2.1-2.5e5
    and Z 20 / 12.7 / 6.8 - better on both counts, as it should be. It is NOT
    wired in here because a single fit costs 175-420 s against this model's
    ~1 s, which would dominate identify(). tube.py remains the reference
    implementation; this is the bank's fast surrogate.

    A constraint-release term was tried and REJECTED: adding a Rouse ladder of
    weight CR_FRAC*Ge*mu at tau_d/k^2 improved PS392 monotonically from 0.114
    to 0.057, but with no interior optimum - the improvement was still rising
    at CR_FRAC = 1.0, i.e. the term wanted to duplicate the ENTIRE reptation
    amplitude as a second free smear. That is flexibility absorbing residual,
    not constraint release, so it was not kept.

    `clf` and `hf_rouse` are switchable off to recover the bare Doi-Edwards
    result; tests use them to pin the ablation above.
    """
    lGe, ltau_d, Z = theta
    Ge = 10.0**lGe
    tau_d = 10.0**ltau_d
    Z = float(np.clip(Z, 2.0, 200.0))
    Zi = max(2, int(round(Z)))
    tau_R = tau_d / (3.0 * Z)   # Doi-Edwards: tau_d = 3 Z tau_R

    mu = max(MU_FLOOR, 1.0 - C_CLF / np.sqrt(Z)) if clf else 1.0

    p = np.arange(1, 31, 2)
    g = [Ge * mu * 8.0 / (np.pi**2 * p**2)]
    tau = [tau_d / p**2]

    if clf and mu < 1.0:
        q = np.arange(1, Zi)
        if len(q):
            g.append(np.full(len(q), Ge * (1.0 - mu) / len(q)))
            tau.append(tau_R / q**2)

    if hf_rouse:
        q2 = np.arange(1, Zi)
        if len(q2):
            g.append(np.full(len(q2), Ge / (5.0 * Z)))
            tau.append(tau_R / q2**2)
        wmax = float(np.max(w))
        p_max = int(np.sqrt(tau_R * wmax
                            / (2 * 10.0**-REPT_MODE_TAU_FLOOR_DECADES))) + 1
        p_max = min(max(p_max, Zi), REPT_MODE_COUNT_CAP)
        p_hf = np.arange(Zi, p_max + 1)
        if len(p_hf):
            g.append(np.full(len(p_hf), Ge / Z))
            tau.append(tau_R / (2.0 * p_hf**2))

    return maxwell_spectrum(w, np.concatenate(g), np.concatenate(tau))


REP_P0 = [3.0, 1.0, 10.0]
REP_BNDS = [(0, 8), (-3, 5), (2, 200)]


# --- Likhtman-McLeish reptation: the SHIPPING linear-melt candidate ---------
#
# `model_reptation` above is a hand-rolled approximation to the same physics.
# It is retained for tests, for ablation, and because the synthetic generator
# has always used it - but it is NOT what `identify()` fits. The bank entry
# "reptation" is `model_reptation_lm` below, which calls the verbatim
# Likhtman-McLeish (2002) implementation in tube.py.
#
# WHY (user decision 2026-09-16): the approximation cannot be defended in
# review. A rheologist asks "which model?" and the answer has to be a named,
# published one, not "a three-parameter form we wrote". The approximation was
# also measurably wrong on real monodisperse polystyrene (Katzarova 2018):
# rms 0.220/0.210/0.176 decades before its CLF + Rouse-ladder repair, against
# a ~0.03-0.05 digitization floor set by a free 12-mode Prony fit.
#
# PARAMETERIZATION. The bank's vector stays (log10 Ge, log10 tau_d, Z) so k=3
# is unchanged and AICc stays comparable to every other candidate. tube.py's
# native parameter is tau_e, recovered exactly via its own eq 4,
# tau_d0 = 3 Z^3 tau_e, so no new physics or fitted parameter is introduced.
# c_nu is FIXED at 1.0 because the paper fixes it (tube.C_NU_DEFAULT); making
# it free would be a 4th parameter and a different model.
#
# DETERMINISM. tube.R_of_t Monte-Carlo averages constraint release over
# `nchains` sampled chains. A fresh default_rng(LM_RNG_SEED) is passed on every
# call, so the objective is a deterministic function of theta - required, or
# L-BFGS-B's finite-difference gradients would be differencing sampling noise.
LM_NCHAINS = 20
LM_RNG_SEED = 0
LM_Z_MIN = 2.0


def model_reptation_lm(w, theta, nchains=LM_NCHAINS):
    """Likhtman-McLeish (2002) linear entangled melt, eq 19, via tube.Gstar.

    params: Ge(log10 Pa), tau_d(log10 s), Z(entanglements)

    Thin adapter only - all physics lives in rheofp.models.tube, which was
    validated in Batch 2 against the paper's own figures. Converts the bank's
    (Ge, tau_d, Z) to tube.py's (Z, tau_e, Ge) by inverting eq 4.
    """
    from . import tube

    lGe, ltau_d, Z = theta
    Ge = 10.0**lGe
    tau_d = 10.0**ltau_d
    Z = float(np.clip(Z, LM_Z_MIN, 200.0))
    tau_e = tau_d / (3.0 * Z**3)          # eq 4 inverted
    rng = np.random.default_rng(LM_RNG_SEED)
    Gp, Gpp = tube.Gstar(np.atleast_1d(w), Z, tau_e, Ge, tube.C_NU_DEFAULT,
                         nchains=nchains, rng=rng)
    return Gp, Gpp


def model_sticky_rouse(w, theta):
    """Unentangled associating chain (sticky Rouse).
    Two well-separated relaxations:
      - fast: bare Rouse modes of the strands BETWEEN stickers (time tau_R),
        carrying the transient network plateau Gs;
      - slow: terminal relaxation gated by the sticker lifetime tau_s >> tau_R,
        carrying the same plateau Gs (network renewal).
    A G'' dip sits between tau_R and tau_s -> sticker shoulder.
    params: Gs(log) plateau, tau_s(log) sticker/terminal time,
            tau_R(log) strand Rouse time (< tau_s), Nst Rouse modes per strand
    """
    Gs, tau_s, tau_R, Nst = theta
    Gs = 10.0**Gs
    tau_s = 10.0**tau_s
    tau_R = 10.0 ** min(tau_R, np.log10(tau_s) - 0.5)  # enforce tau_R < tau_s
    Nst = max(2, int(round(Nst)))
    p_f = np.arange(1, Nst + 1)
    tau_f = tau_R / p_f**2
    g_f = np.full_like(p_f, Gs / Nst, dtype=float)
    tau_sl = np.array([tau_s])
    g_sl = np.array([Gs])
    g = np.concatenate([g_sl, g_f])
    tau = np.concatenate([tau_sl, tau_f])
    return maxwell_spectrum(w, g, tau)


SR_P0 = [3.0, 2.0, -1.0, 15]
SR_BNDS = [(0, 7), (0, 5), (-5, 1), (2, 150)]


def model_sticky_reptation(w, theta):
    """Entangled associating system (sticky reptation).
    Three features:
      - entanglement plateau Ge (Rouse modes between tau_e and tau_d give the
        high-w wing and set the plateau);
      - sticker shoulder: G'' bump from the sticker lifetime tau_s;
      - slow terminal at the sticky-reptation time tau_st (>> tau_s) where the
        tube is renewed only as fast as stickers permit.
    params: Ge(log) plateau, tau_st(log) terminal, Z entanglements,
            tau_s(log) sticker time (tau_e < tau_s < tau_st)
    """
    Ge, tau_st, Z, tau_s = theta
    Ge = 10.0**Ge
    tau_st = 10.0**tau_st
    Z = max(2.0, Z)
    tau_s = 10.0 ** min(tau_s, np.log10(tau_st) - 0.5)  # tau_s < tau_st
    p = np.arange(1, 31, 2)
    g_rep = Ge * 8.0 / (np.pi**2 * p**2)
    tau_rep = tau_st / p**2
    g_s = np.array([0.5 * Ge])
    tau_s_m = np.array([tau_s])
    tau_e = tau_s / Z**2
    q = np.arange(1, int(round(Z)) + 1)
    g_rouse = np.full_like(q, Ge / Z, dtype=float)
    tau_rouse = tau_s / q**2
    g = np.concatenate([g_rep, g_s, g_rouse])
    tau = np.concatenate([tau_rep, tau_s_m, tau_rouse])
    return maxwell_spectrum(w, g, tau)


SREP_P0 = [3.0, 3.0, 10.0, 1.0]
SREP_BNDS = [(0, 8), (1, 6), (2, 200), (-2, 4)]

# registry: name -> (forward, p0, bounds, k_params)
MODELS = {
    "zimm": (model_zimm, ZIMM_P0, ZIMM_BNDS, 3),
    "rouse_screened": (model_rouse, ROUSE_P0, ROUSE_BNDS, 3),
    # The shipping linear-melt candidate is the verbatim Likhtman-McLeish
    # tube model, NOT the model_reptation approximation above. See the long
    # note at model_reptation_lm. Same (Ge, tau_d, Z) vector and same k=3, so
    # AICc stays comparable across the bank.
    "reptation": (model_reptation_lm, REP_P0, REP_BNDS, 3),
    "sticky_rouse": (model_sticky_rouse, SR_P0, SR_BNDS, 4),
    "sticky_reptation": (model_sticky_reptation, SREP_P0, SREP_BNDS, 4),
}
