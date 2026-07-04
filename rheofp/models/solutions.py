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


def model_reptation(w, theta):
    """Doi-Edwards reptation: plateau Ge, disengagement tau_d, odd modes.
    Plus higher Rouse modes between tau_e and tau_d for the high-w rise.
    params: Ge(log), tau_d(log), Z(entanglements)
    """
    Ge, tau_d, Z = theta
    Ge = 10.0**Ge
    tau_d = 10.0**tau_d
    Z = max(2.0, Z)
    p = np.arange(1, 31, 2)
    g_rep = Ge * 8.0 / (np.pi**2 * p**2)
    tau_rep = tau_d / p**2
    tau_e = tau_d / Z**3  # approx tau_e ~ tau_d / Z^3
    q = np.arange(1, int(round(Z)) + 1)
    g_rouse = np.full_like(q, Ge / Z, dtype=float)
    tau_rouse = tau_e / q**2
    g = np.concatenate([g_rep, g_rouse])
    tau = np.concatenate([tau_rep, tau_rouse])
    return maxwell_spectrum(w, g, tau)


REP_P0 = [3.0, 1.0, 10.0]
REP_BNDS = [(0, 8), (-3, 5), (2, 200)]


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
    "reptation": (model_reptation, REP_P0, REP_BNDS, 3),
    "sticky_rouse": (model_sticky_rouse, SR_P0, SR_BNDS, 4),
    "sticky_reptation": (model_sticky_reptation, SREP_P0, SREP_BNDS, 4),
}
