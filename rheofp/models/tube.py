"""Likhtman-McLeish (2002) tube model for linear entangled melts.

Canonical source: batch2_tube_models.ipynb. figure10_likhtman_mcleish_fit.ipynb
contained a byte-for-byte identical copy of this physics (confirmed by diff)
and is not migrated separately - CLAUDE.md itself notes this code was "reused
unchanged from the validated Figure-10 notebook."

Sample chemistry constants (density, temperature) are passed as arguments
with defaults rather than module-level globals, since they vary per sample
(e.g. RHO=959.0/TEMP=453.15 for PS at 180C, RHO=896.0 for PB) - a real
per-sample config, not a fixed constant for the whole module.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize, nnls

# eq 12 coefficients (best fit, Z = 2..100)
C1, C2, C3, C4, C5 = 1.69, 4.17, -1.55, 2.0, -1.24
C_MU = 1.5  # eq 11 early-time plateau

RGAS = 8.314  # J / (mol K)

# Default sample chemistry - override per call, not by editing these.
RHO_DEFAULT = 959.0    # kg/m^3 (PS)
TEMP_DEFAULT = 453.15  # K (180 C)

# Default constraint-release settings.
C_NU_DEFAULT = 1.0     # paper fixes c_nu = 1
NCHAINS_DEFAULT = 60


def Gtilde(Z):  # eq 12
    return 1 - C1 / np.sqrt(Z) + C4 / Z + C5 / Z**1.5


def taudf_ratio(Z):  # tau_df / tau_d0, eq 12
    return 1 - 2 * C1 / np.sqrt(Z) + C2 / Z + C3 / Z**1.5


def tau_d0(Z, te):  # eq 4
    return 3.0 * Z**3 * te


def tau_R(Z, te):  # Rouse time = tau_d0/(3Z) = Z^2 te
    return Z**2 * te


def _pstar_odd(Z):
    pmax = int(np.floor(max(1.0, np.sqrt(Z) / 10.0)))  # p* = sqrt(Z)/10
    odd = [p for p in range(1, pmax + 1) if p % 2 == 1]
    return odd if odd else [1]


def eps_star(Z, te):  # eq 14
    Gt = Gtilde(Z)
    S = sum(1.0 / p**2 for p in _pstar_odd(Z))
    den = 1 - 8 * Gt / np.pi**2 * S
    return (1.0 / (te * Z**4)) * (4 * 0.306 / den)**4


def mu_of_t(t, Z, te):
    """Single-chain tube-survival fraction mu(t), eq 13."""
    t = np.atleast_1d(t).astype(float)
    Gt = Gtilde(Z)
    tdf = taudf_ratio(Z) * tau_d0(Z, te)
    rep = np.zeros_like(t)
    for p in _pstar_odd(Z):
        rep += (1.0 / p**2) * np.exp(-t * p**2 / tdf)
    rep *= 8 * Gt / np.pi**2
    es = eps_star(Z, te)
    epsg = np.logspace(np.log10(es), np.log10(es) + 13, 4000)
    w = 0.306 / (Z * te**0.25) * epsg**(-1.25)
    early = np.array([np.trapezoid(w * np.exp(-epsg * tt), epsg) for tt in t])
    return rep + early


def _sample_mobilities(Z, te, nseg, rng):
    """Draw nseg tube-segment mobilities (rates) from P(eps) = inverse Laplace of mu(t)."""
    Gt = Gtilde(Z)
    tdf = taudf_ratio(Z) * tau_d0(Z, te)
    odd = _pstar_odd(Z)
    eps_p = np.array([p**2 / tdf for p in odd])
    a_p = np.array([8 * Gt / np.pi**2 / p**2 for p in odd])
    es = eps_star(Z, te)
    W_cont = 0.306 / (Z * te**0.25) * 4 * es**(-0.25)
    weights = np.concatenate([a_p, [W_cont]])
    weights = weights / weights.sum()
    choice = rng.choice(len(weights), size=nseg, p=weights)
    out = np.empty(nseg)
    cont_idx = len(eps_p)
    for k in range(nseg):
        c = choice[k]
        if c < cont_idx:
            out[k] = eps_p[c]
        else:
            u = rng.random()
            out[k] = es * (1 - u)**(-4)
    return out


def _Mcount_vectorized(epsgrid, gammas):
    """Sturm-sequence mode count for all eps in epsgrid simultaneously.
    Returns array of shape (n_eps,) = number of modes slower than each eps.
    Vectorized over eps; loop is over the Z chain segments only."""
    TINY = 1e-300
    Z = len(gammas)
    s = gammas[0] + (gammas[1] if Z >= 2 else 0.0) - epsgrid
    s = np.where(s == 0.0, TINY, s)
    neg = (s < 0).astype(np.float64)
    for i in range(1, Z):
        gi = gammas[i]
        gip = gammas[i + 1] if i + 1 < Z else 0.0
        s = gi + gip - epsgrid - gi * gi / s
        s = np.where(s == 0.0, TINY, s)
        neg += (s < 0)
    return neg


def R_of_t(t, Z, te, cnu, nchains=60, rng=None):
    """Constraint-release relaxation R(t,cnu), eq 15. Normalized so R(0)=1.
    Vectorized Sturm sequence: loop is over nchains, not over (nchains x n_eps x Z)."""
    if rng is None:
        rng = np.random.default_rng(0)
    t = np.atleast_1d(t).astype(float)
    if cnu <= 0:
        return np.ones_like(t)
    Zi = int(round(Z))
    if Zi < 2:
        return np.ones_like(t)
    epsgrid = np.logspace(-13, 3, 500)
    emid = np.sqrt(epsgrid[:-1] * epsgrid[1:])
    decay = np.exp(-cnu * emid[None, :] * t[:, None])
    acc = np.zeros(len(t))
    for _ in range(nchains):
        gammas = _sample_mobilities(Z, te, Zi, rng)
        Mvals = _Mcount_vectorized(epsgrid, gammas)
        dM = np.diff(Mvals)
        acc += decay @ dM
    R = acc / nchains
    return R / R[0] if R[0] > 0 else R


def _Gstar_hf_rouse(omega, Z, te, Ge):
    """High-frequency Rouse contribution (3rd sum of eq 19), computed analytically."""
    omega = np.atleast_1d(omega)
    Zi = int(round(Z))
    tR = tau_R(Z, te)
    wmax = omega.max()
    p_max = int(np.sqrt(tR * wmax / (2 * 1e-4))) + 1
    p_max = max(p_max, Zi)
    p_hf = np.arange(Zi, p_max + 1)
    tau_p = tR / (2.0 * p_hf**2)
    wt = omega[:, None] * tau_p[None, :]
    Gp = (Ge / Z) * (wt**2 / (1 + wt**2)).sum(axis=1)
    Gpp = (Ge / Z) * (wt / (1 + wt**2)).sum(axis=1)
    return Gp, Gpp


def _Gstar_long_modes(omega, Z, te, Ge):
    """Longitudinal modes contribution (2nd sum of eq 19)."""
    omega = np.atleast_1d(omega)
    Zi = int(round(Z))
    tR = tau_R(Z, te)
    p_long = np.arange(1, max(2, Zi))
    tau_p = tR / p_long**2
    wt = omega[:, None] * tau_p[None, :]
    Gp = (Ge / (5 * Z)) * (wt**2 / (1 + wt**2)).sum(axis=1)
    Gpp = (Ge / (5 * Z)) * (wt / (1 + wt**2)).sum(axis=1)
    return Gp, Gpp


def _prony_modes(Z, te, Ge, cnu, nchains=60, rng=None, n_prony=60):
    """Fit 4/5 * mu(t)*R(t) to a non-negative Prony series on a log-time grid.
    Returns list of (weight*Ge, tau_k) pairs."""
    Zi = int(round(Z))
    tmax = 30.0 * tau_d0(Z, te) * Zi**2
    tg = np.logspace(np.log10(1e-3 * te), np.log10(tmax), 400)
    F = 0.8 * mu_of_t(tg, Z, te) * R_of_t(tg, Z, te, cnu, nchains=nchains, rng=rng)
    tauk = np.logspace(np.log10(tg[1]), np.log10(tmax), n_prony)
    A = np.exp(-tg[:, None] / tauk[None, :])
    wk, _ = nnls(A, F)
    return [(wk[k] * Ge, tauk[k]) for k in range(len(tauk)) if wk[k] > 1e-6]


def _Gstar_from_prony(omega, modes):
    """Analytic G', G'' from a list of (g_i, tau_i) Prony modes."""
    omega = np.atleast_1d(omega)
    Gp = np.zeros_like(omega)
    Gpp = np.zeros_like(omega)
    for gi, ti in modes:
        wt = omega * ti
        Gp += gi * wt**2 / (1 + wt**2)
        Gpp += gi * wt / (1 + wt**2)
    return Gp, Gpp


def G_of_t(t, Z, te, Ge, cnu, nchains=60, rng=None):
    """Full G(t) in Pa, eq 19 (time-domain, for inspection/plotting)."""
    t = np.atleast_1d(t).astype(float)
    Zi = int(round(Z))
    tR = tau_R(Z, te)
    mu = mu_of_t(t, Z, te)
    R = R_of_t(t, Z, te, cnu, nchains=nchains, rng=rng)
    term1 = 0.8 * mu * R
    p_long = np.arange(1, max(2, Zi))
    term2 = (1.0 / (5 * Z)) * np.exp(-np.outer(t, p_long**2) / tR).sum(axis=1)
    N = Zi * max(2, Zi)
    p_hf = np.arange(Zi, N + 1)
    term3 = (1.0 / Z) * np.exp(-2 * np.outer(t, p_hf**2) / tR).sum(axis=1) if len(p_hf) else np.zeros_like(t)
    return Ge * (term1 + term2 + term3)


def Gstar(omega, Z, te, Ge, cnu, nchains=60, rng=None, _prony_modes_cache=None):
    """G'(w), G''(w) for a single sample.

    Pass _prony_modes_cache (a list) to reuse already-computed Prony modes across
    frequency evaluations - critical for fitting speed. If None, modes are recomputed."""
    omega = np.atleast_1d(omega).astype(float)
    if _prony_modes_cache is None:
        modes = _prony_modes(Z, te, Ge, cnu, nchains=nchains, rng=rng)
    else:
        modes = _prony_modes_cache
    Gp, Gpp = _Gstar_from_prony(omega, modes)
    Gp2, Gpp2 = _Gstar_long_modes(omega, Z, te, Ge)
    Gp3, Gpp3 = _Gstar_hf_rouse(omega, Z, te, Ge)
    return Gp + Gp2 + Gp3, Gpp + Gpp2 + Gpp3


def Me_from_Ge(Ge, rho=RHO_DEFAULT, temp=TEMP_DEFAULT, rgas=RGAS):
    """eq 3: Ge = rho R T / Me. Returns Me in kg/mol."""
    return rho * rgas * temp / Ge


def Z_of_sample(Mw, Ge, rho=RHO_DEFAULT, temp=TEMP_DEFAULT, rgas=RGAS):
    Me_g = Me_from_Ge(Ge, rho=rho, temp=temp, rgas=rgas) * 1000.0  # kg/mol -> g/mol
    return Mw / Me_g


def linear_melt_forward(omega, Ge, te, Mw, cnu=None, nchains=None, rng=None,
                         rho=RHO_DEFAULT, temp=TEMP_DEFAULT):
    """Linear-melt G'(w), G''(w) via the L-M Gstar. Z derived from Ge, Mw."""
    cnu = C_NU_DEFAULT if cnu is None else cnu
    nchains = NCHAINS_DEFAULT if nchains is None else nchains
    Z = Z_of_sample(Mw, Ge, rho=rho, temp=temp)
    return Gstar(np.atleast_1d(omega), Z, te, Ge, cnu, nchains=nchains, rng=rng)


def valid_window(Ge, te, Mw, pad_lo=30.0, rho=RHO_DEFAULT, temp=TEMP_DEFAULT):
    """Trustworthy omega range [1/(pad_lo*tau_d), 1/tau_R] for a linear melt.
    The generator should keep synthetic linear curves inside this band."""
    Z = Z_of_sample(Mw, Ge, rho=rho, temp=temp)
    tau_d = tau_d0(Z, te)
    tau_Rouse = tau_R(Z, te)
    return 1.0 / (pad_lo * tau_d), 1.0 / tau_Rouse


def fit_linear_melt(samples, Mw_map, cnu=None, nchains=30, seed=7,
                     rho=RHO_DEFAULT, temp=TEMP_DEFAULT):
    """Shared-(Ge, te) fit across samples. samples: {label:(w,Gp,Gpp)}."""
    cnu = C_NU_DEFAULT if cnu is None else cnu

    def resid(params):
        Ge, te = params
        if Ge <= 0 or te <= 0:
            return 1e6
        rloc = np.random.default_rng(seed)
        tot = 0.0
        n = 0
        for label, (w, Gp_e, Gpp_e) in samples.items():
            Mw = Mw_map.get(label)
            if Mw is None:
                continue
            Z = Z_of_sample(Mw, Ge, rho=rho, temp=temp)
            modes = _prony_modes(Z, te, Ge, cnu, nchains=nchains, rng=rloc)
            Gp_m, Gpp_m = Gstar(w, Z, te, Ge, cnu, _prony_modes_cache=modes)
            ok = (Gp_m > 0) & (Gpp_m > 0) & (Gp_e > 0) & (Gpp_e > 0)
            tot += np.sum((np.log10(Gp_m[ok]) - np.log10(Gp_e[ok]))**2)
            tot += np.sum((np.log10(Gpp_m[ok]) - np.log10(Gpp_e[ok]))**2)
            n += 2 * np.sum(ok)
        return tot / max(n, 1)

    all_w = np.concatenate([s[0] for s in samples.values()])
    all_gp = np.concatenate([s[1] for s in samples.values()])
    Ge0 = float(np.median(all_gp[all_w > np.percentile(all_w, 90)]))
    lab_lo = min(Mw_map, key=Mw_map.get)
    w_lo, _, gpp_lo = samples[lab_lo]
    w_peak = float(w_lo[np.argmax(gpp_lo)])
    te0 = 1.0 / w_peak / (3.0 * (Mw_map[lab_lo] / Me_from_Ge(Ge0, rho=rho, temp=temp) / 1000)**3)
    res = minimize(lambda u: resid([10**u[0], 10**u[1]]), np.log10([Ge0, te0]),
                   method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-4, "maxiter": 200})
    Ge_fit, te_fit = 10**res.x
    return dict(Ge=Ge_fit, te=te_fit, Me=Me_from_Ge(Ge_fit, rho=rho, temp=temp) * 1000, cost=float(res.fun))
