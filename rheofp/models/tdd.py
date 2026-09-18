"""des Cloizeaux time-dependent diffusion (TDD) reptation, under double
reptation (DR), for monodisperse linear entangled melts.

Sources, transcribed verbatim:
  - van Ruymbeke & Keunings (2002), Macromolecules 35, 2689. Table 1 eq 4
    (the TDD kernel and its g(y)), eqs 1 and 5 (the double-reptation mixing
    rule). This is the paper that COMPARES the kernels and concludes TDD+DR
    is the best of the three for well-entangled chains (section V).
  - Chaudhuri & Lele (2020), J. Rheol. 64, 1. Its eqs 1-5 restate the same
    kernel; eq 5 is the polydisperse form, of which this module implements
    only the monodisperse special case.
  - des Cloizeaux (1990), Macromolecules 23, 4678; (1992), 25, 835.

WHY THIS EXISTS ALONGSIDE `tube.py`. `tube.py` (Likhtman-McLeish 2002) is
also a validated linear-melt model and is NOT being deleted. TDD's advantages
are specific and were measured before this module was written (see
`docs/tdd_preregistration.md`):

  1. It is CLOSED FORM. `tube.Gstar` costs ~10.7 ms/call and accounted for
     94.2% of `identify()`'s total runtime; this costs ~0.05 ms/call.
  2. It does NOT SAMPLE. `tube.R_of_t` Monte-Carlo averages constraint release
     over 20 chains, whose ~1.3e-2 decade noise exceeds AICc margins the bank
     decides on - the defect that forced the PS105 withdrawal on 2026-09-18.
     Nothing here draws a random number, so the objective is exactly
     reproducible.

THE PHYSICS. Two effects are folded in that plain Doi-Edwards omits:

  - Time-dependent diffusion (the `g(y)/H` term in U(t)). Immediately after a
    step strain the curvilinear diffusion coefficient is singular, because
    fast Rouse motions are not yet hampered by the tube; it decays to the
    constant DE value at long times. This is what lets the model cover the
    intermediate region between reptation and Rouse relaxation, which van
    Ruymbeke section V singles out as the reason to prefer it.
  - Double reptation (the `**beta` in eq 5). An entanglement is a BINARY
    event: it disappears when EITHER chain's end passes it, so constraint
    release enters as a power of the single-chain survival function rather
    than as a separate sampled process.

FIXED CONSTANTS - deliberately not fitted, see the pre-registration:
  - `beta = 2.25`, not the naive 2. van Ruymbeke fit this consistently across
    all their PS samples (section IV) and attribute the excess to
    entanglements involving more than two chains (p.2698).
  - `MSTAR_OVER_ME = 8.7`, their best-fit value FOR POLYSTYRENE (p.2698),
    justified by their own statement that "the quality of the fit is not very
    sensitive to the exact value of M*". It is chemistry-dependent - they
    report 20 for PC (Me 2500) and 47 for PE (Me 1500), rising as Me falls -
    so this is a PS-calibrated constant, recorded as a known limit.

KNOWN LIMIT, from the paper and NOT patched here. van Ruymbeke p.2694
("Relaxation of Short Chains") show TDD-DR relaxes chains below ~4 Me too
fast, and repair it with an admittedly empirical tau_rep -> tau_rep/beta
rescale below that threshold. That correction is NOT implemented: it is
empirical, it was never validated here, and every melt in this project's
benchmark sits above 4 Me. A melt with Z < 4 is outside this module's
validated envelope.
"""
from __future__ import annotations

import numpy as np

from rheofp.models.maxwell import maxwell_spectrum

# --- fixed constants (see module docstring; none of these are fitted) -------
BETA_DR = 2.25          # double-reptation exponent, vR2002 section IV
MSTAR_OVER_ME = 8.7     # PS best fit, vR2002 p.2698
N_ODD_MODES = 101       # odd p in the eq-4 sum, p = 1,3,...,N_ODD_MODES
# Ladder settings. MEASURED against the quadrature referee (see
# `_prony_from_Gt` and test_tdd.py), not guessed: N_PRONY = 80 over this span
# reproduces exact quadrature to 1.6e-4 decades, two orders below the ~1e-2
# noise floor the bank's AICc margins live on, at 1.26 ms/call. Raising it to
# 120 buys 1.6e-4 -> 1e-5 decades for 3x the cost, which buys nothing real.
N_PRONY = 80            # modes in the G(t) -> G*(w) ladder
N_TFIT = 400            # G(t) samples the ladder is fitted against
PRONY_DECADES_BELOW = 12.0  # ladder span below tau_rep
PRONY_DECADES_ABOVE = 4.0   # ... and above

# Rouse ladder truncation (see `_rouse_modes`).
ROUSE_TAU_FLOOR_DECADES = 2.0   # keep modes to 2 decades below 1/w_max
ROUSE_P_CAP = 4000              # hard cap; guards against a huge tau_R/w_max

_P_ODD = np.arange(1, N_ODD_MODES + 1, 2)


def g_dc(y):
    """des Cloizeaux fluctuation function, vR2002 Table 1 eq 4 'simplified'.

        g(y) = -y + y^0.5 [y + (pi y)^0.5 + pi]^0.5

    This is the closed-form stand-in for the exact series
    g(y) = sum_n (1 - exp(-n^2 y)) / n^2, which the paper gives directly
    above it. `test_tdd.py` checks the two agree.
    """
    y = np.asarray(y, float)
    return -y + np.sqrt(y) * np.sqrt(y + np.sqrt(np.pi * y) + np.pi)


def g_dc_series(y, n_terms=4000):
    """Exact series form of g(y), for validating `g_dc`. Slow; tests only."""
    y = np.atleast_1d(np.asarray(y, float))[:, None]
    n = np.arange(1, n_terms + 1)[None, :]
    return np.sum((1.0 - np.exp(-(n**2) * y)) / n**2, axis=1)


def U_of_t(t, Z, tau_rep):
    """vR2002 Table 1 eq 4: U(t) = t/tau_rep + (1/H) g(H t / tau_rep).

    H = M/M* is the number of entanglements per chain rescaled by the TDD
    material parameter, so with M/Me = Z it is H = Z / (M*/Me) - derived from
    Z, introducing no extra fitted parameter.
    """
    t = np.asarray(t, float)
    H = Z / MSTAR_OVER_ME
    return t / tau_rep + g_dc(H * t / tau_rep) / H


def F_tdd(t, Z, tau_rep):
    """Single-chain TDD relaxation function, vR2002 Table 1 eq 4:

        F_TDD(t) = (8/pi^2) sum_{p odd} p^-2 exp(-p^2 U(t))
    """
    U = np.atleast_1d(U_of_t(t, Z, tau_rep))[:, None]
    terms = np.exp(-(_P_ODD**2) * U) / _P_ODD**2
    return (8.0 / np.pi**2) * terms.sum(axis=1)


def G_of_t(t, Z, tau_rep, Ge):
    """Relaxation modulus under double reptation, vR2002 eqs 1 + 5 in the
    monodisperse limit: G(t) = G_N * F_TDD(t)^beta."""
    F = np.clip(F_tdd(t, Z, tau_rep), 0.0, None)
    return Ge * F**BETA_DR


def _prony_from_Gt(Z, tau_rep, Ge):
    """Represent G(t) as a non-negative Prony series by NNLS.

    G(t) here is NOT a Prony series in closed form: U(t) is nonlinear in t, so
    F_TDD's exponentials do not have constant rates, and G = Ge * F^2.25 is a
    non-integer power on top of that. Some t -> w route is therefore
    unavoidable. This one solves

        min_g || sum_i g_i exp(-t/tau_i) - G(t) ||,  g_i >= 0

    on a fixed log ladder of tau_i, then hands (g, tau) to the validated
    `maxwell_spectrum` so that G*(w) is evaluated ANALYTICALLY. Non-negativity
    is imposed because a negative Maxwell weight is unphysical and lets the
    fit oscillate.

    WHY NNLS AND NOT A FINITE DIFFERENCE. The obvious cheaper route -
    g_i = G(tau_i) - G(tau_{i+1}), the drop across each interval - was tried
    first and IS WRONG. It conserves total mass exactly but misplaces it, and
    it does not converge: refining the ladder from N=96 to N=1536 moved G' by
    0.09 decades and kept drifting. Against a referee of direct oscillatory
    quadrature of the exact definition G'(w) = w int G(t) sin(wt) dt, the
    finite-difference route was off by 0.12-0.30 decades across the window
    while NNLS matched to < 1e-4 decades at every frequency tested. Placing a
    mode at the geometric midpoint of its interval did not help (identical
    0.80-decade error on a single-exponential control).

    This is the same aliasing hazard that forced `comb.py` onto ML1999 rather
    than ML1998, caught here by having a referee rather than by eyeballing.
    """
    from scipy.optimize import nnls

    lo = np.log10(tau_rep) - PRONY_DECADES_BELOW
    hi = np.log10(tau_rep) + PRONY_DECADES_ABOVE
    tau = np.logspace(lo, hi, N_PRONY)
    t = np.logspace(lo - 0.5, hi + 0.5, N_TFIT)
    A = np.exp(-t[:, None] / tau[None, :])
    g, _ = nnls(A, G_of_t(t, Z, tau_rep, Ge))
    return g, tau


def _rouse_modes(omega, Z, tau_rep, Ge):
    """Rouse modes of the chain, vR2002 Table 2 eq 8 (entangled melt).

    WHY THIS IS SEPARATE FROM THE TDD KERNEL. van Ruymbeke add Rouse relaxation
    to the reptation contribution themselves, by an explicit linear mixing rule
    (p.2692: "The Rouse contribution to the relaxation modulus, G_Rouse, is
    simply added to the reptation contribution expressed by eq 1, using a
    linear mixing rule"). The TDD kernel alone does NOT contain it.

    It is not optional cosmetics. Measured here before adding it: the bare TDD
    kernel gives G'' DECAYING as w^-0.23 at high frequency, where `tube.py`
    turns up into a Rouse rise and shows a G'' minimum. Over a real window that
    extends past the minimum, a fitter with no Rouse term must distort Z to
    cover the gap - precisely the failure diagnosed and fixed in `star.py`
    (median |Z error| 44% -> 30% when its arm-Rouse modes were added).

    Table 2 eq 8 splits the ladder at p = N = Z, because a subchain shorter
    than Me relaxes like an unentangled chain while longer ones feel the tube
    and keep only their LONGITUDINAL modes (hence the 1/3):

        G_Rouse(t) = Ge sum_{p=N}^{N_tot} exp(-p^2 t/tau_R)          [free]
                   + (Ge/3) sum_{p=1}^{N-1} exp(-p^2 t/tau_R)        [longitudinal]

    with per-mode weight Ge/Z. tau_R = tau_rep / (3 Z) is the Rouse time, from
    the standard tau_rep = 3 Z tau_R; no new parameter is introduced.
    """
    Zi = max(1, int(round(Z)))
    tau_R = tau_rep / (3.0 * Z)

    # Truncate where modes stop contributing: tau_p far below 1/w_max adds
    # nothing (w tau << 1). Same reasoning and the same hazard as star.py's
    # MODE_TAU_FLOOR_DECADES - an untruncated ladder is unbounded work.
    w_max = float(np.max(np.atleast_1d(omega)))
    p_need = int(np.ceil(np.sqrt(tau_R * w_max * 10.0**ROUSE_TAU_FLOOR_DECADES)))
    p_max = int(np.clip(p_need, Zi, ROUSE_P_CAP))

    p_long = np.arange(1, Zi)                    # longitudinal, p < Z
    p_free = np.arange(Zi, p_max + 1)            # free Rouse, p >= Z
    g = np.concatenate([np.full(p_long.size, Ge / (3.0 * Z)),
                        np.full(p_free.size, Ge / Z)])
    tau = np.concatenate([tau_R / p_long**2, tau_R / p_free**2])
    return maxwell_spectrum(np.atleast_1d(omega), g, tau)


def Gstar(omega, Z, tau_rep, Ge, rouse=True):
    """G'(w), G''(w) for a monodisperse linear entangled melt via TDD-DR.

    Parameters
    ----------
    omega : array, rad/s
    Z : entanglements per chain, M/Me
    tau_rep : reptation time, s (vR2002 eq 3: tau_rep = K M^3)
    Ge : plateau modulus G_N^0, Pa
    rouse : add the Rouse contribution by vR2002's own linear mixing rule
        (Table 2 eq 8). True by default; set False to recover the bare TDD
        kernel, which is what the paper's Figure 4 curves show.

    Deterministic: no sampling anywhere, unlike `tube.Gstar`.
    """
    Z = float(Z)
    tau_rep = float(tau_rep)
    Ge = float(Ge)
    g, tau = _prony_from_Gt(Z, tau_rep, Ge)
    Gp, Gpp = maxwell_spectrum(np.atleast_1d(omega), g, tau)
    if rouse:
        rGp, rGpp = _rouse_modes(omega, Z, tau_rep, Ge)
        Gp = Gp + rGp
        Gpp = Gpp + rGpp
    return Gp, Gpp
