"""Maxwell / Prony-series family of linear-rheology forward models.

Canonical `maxwell_spectrum` unifies what were four separate but numerically
identical implementations across the original notebooks (batch1's
maxwell_spectrum, solution_identifier's _maxwell_sum, xpp_pompom's
maxwell_Gstar, and batch2's inline sum inside branched_spectrum) - all compute
Gp = sum(g * wt^2 / (1+wt^2)), Gpp = sum(g * wt / (1+wt^2)) over modes.

branched_spectrum lives here (not in tube.py) because its output
representation is a Prony/Maxwell sum over a hierarchically constructed mode
ladder, even though it models entangled/LCB melts.
"""
from __future__ import annotations

import numpy as np

from rheofp.fitting.optimize import multi_restart_fit

R_GAS = 8.314462618  # J / (mol K)

# Default optimizer settings; override per-call, not by editing these.
N_RESTARTS = 12
SEED = 0


def maxwell_spectrum(omega, G, tau):
    """Generalized Maxwell / Prony series -> (G', G'')."""
    omega = np.atleast_1d(np.asarray(omega, float))
    G = np.atleast_1d(np.asarray(G, float))
    tau = np.atleast_1d(np.asarray(tau, float))
    wt = np.outer(omega, tau)
    denom = 1.0 + wt**2
    Gp = (G * wt**2 / denom).sum(axis=1)
    Gpp = (G * wt / denom).sum(axis=1)
    return Gp, Gpp


def wlm_spectrum(omega, G0, tau_rep, tau_br, beta=1.0):
    """Practical wormlike-micelle model. Dominant tau = sqrt(tau_rep*tau_br)."""
    omega = np.atleast_1d(np.asarray(omega, float))
    tau = np.sqrt(tau_rep * tau_br)
    wt = omega * tau
    denom = 1.0 + wt**2
    Gp = G0 * wt**2 / denom
    Gpp = G0 * wt / denom
    x = omega * tau_br
    corr = beta * G0 * np.sqrt(x) / (1.0 + 1.0 / np.maximum(x, 1e-300))
    return Gp, Gpp + corr


def arrhenius_shift(tau_ref, Ea, T, T_ref):
    """tau(T) = tau_ref * exp[(Ea/R)(1/T - 1/T_ref)], T in Kelvin."""
    return np.asarray(tau_ref, float) * np.exp((Ea / R_GAS) * (1.0 / T - 1.0 / T_ref))


def sticky_maxwell_stack(omega, G, tau_ref, Ea, T_list, T_ref):
    """Temperature stack: G assumed T-independent, tau Arrhenius-shifted.
    Returns list of (G', G'') tuples, one per temperature."""
    out = []
    for T in np.atleast_1d(T_list):
        tau_T = arrhenius_shift(tau_ref, Ea, T, T_ref)
        out.append(maxwell_spectrum(omega, G, tau_T))
    return out


def branched_spectrum(omega, Ge, tau_b, sigma, n_modes=60, p_tail=2.0):
    """Hierarchical double-reptation broadened tube spectrum (branched/LCB).
    Ge: plateau [Pa]; tau_b: longest time [s]; sigma: breadth [decades].
    Builds a mode ladder then reuses the canonical Maxwell sum."""
    log_tau = np.linspace(np.log10(tau_b) - sigma, np.log10(tau_b), n_modes)
    tau = 10**log_tau
    w = (tau / tau_b) ** (1.0 / (p_tail * sigma))
    w /= w.sum()
    inv = 1.0 / (2 * tau)
    tau_ij = 1.0 / (inv[:, None] + inv[None, :])
    g_ij = Ge * np.outer(w, w)
    return maxwell_spectrum(omega, g_ij.ravel(), tau_ij.ravel())


def fit_maxwell(omega, Gp_data, Gpp_data, n_modes=1, n_restarts=None,
                 seed=None, log_tau_bounds=None, log_G_bounds=None):
    """Fit n-mode Maxwell/Prony in log space. Params [logG..., logtau...]."""
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    yp, ypp = np.log(np.asarray(Gp_data, float)), np.log(np.asarray(Gpp_data, float))
    w_lo, w_hi = omega.min(), omega.max()
    if log_tau_bounds is None:
        log_tau_bounds = (np.log(1 / w_hi) - 2 * np.log(10), np.log(1 / w_lo) + 2 * np.log(10))
    Gscale = np.median(np.concatenate([Gp_data, Gpp_data]))
    if log_G_bounds is None:
        log_G_bounds = (np.log(Gscale) - 6 * np.log(10), np.log(Gscale) + 4 * np.log(10))

    def objective(p):
        Gp, Gpp = maxwell_spectrum(omega, np.exp(p[:n_modes]), np.exp(p[n_modes:]))
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                             np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    bounds = [log_G_bounds] * n_modes + [log_tau_bounds] * n_modes

    def sampler(rng):
        g0 = rng.uniform(*log_G_bounds, n_modes)
        t0 = np.sort(rng.uniform(*log_tau_bounds, n_modes))
        return np.concatenate([g0, t0])

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed, sampler=sampler)
    G, tau = np.exp(best.x[:n_modes]), np.exp(best.x[n_modes:])
    o = np.argsort(tau)
    return dict(G=G[o], tau=tau[o], cost=float(best.fun), success=bool(best.success))


def fit_wlm(omega, Gp_data, Gpp_data, n_restarts=None, seed=None):
    """Fit practical WLM: params [logG0, logtau_rep, logtau_br, logbeta]."""
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    yp, ypp = np.log(np.asarray(Gp_data, float)), np.log(np.asarray(Gpp_data, float))
    w_lo, w_hi = omega.min(), omega.max()
    Gscale = np.median(np.concatenate([Gp_data, Gpp_data]))
    bG = (np.log(Gscale) - 4 * np.log(10), np.log(Gscale) + 3 * np.log(10))
    btau = (np.log(1 / w_hi) - 3 * np.log(10), np.log(1 / w_lo) + 3 * np.log(10))
    bbeta = (np.log(1e-3), np.log(5.0))
    bounds = [bG, btau, btau, bbeta]

    def objective(p):
        Gp, Gpp = wlm_spectrum(omega, *np.exp(p))
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                             np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    G0, tr, tb, beta = np.exp(best.x)
    return dict(G0=G0, tau_rep=tr, tau_br=tb, beta=beta, tau=np.sqrt(tr * tb),
                cost=float(best.fun), success=bool(best.success))


def fit_sticky_stack(omega, stack_Gp, stack_Gpp, T_list, T_ref,
                      n_modes=1, n_restarts=None, seed=None):
    """Joint T-stack fit: one Ea ties all temperatures.
    Params [logG..., logtau_ref..., Ea] at T_ref."""
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    T_list = np.atleast_1d(np.asarray(T_list, float))
    logGp = [np.log(np.asarray(g, float)) for g in stack_Gp]
    logGpp = [np.log(np.asarray(g, float)) for g in stack_Gpp]
    w_lo, w_hi = omega.min(), omega.max()
    Gscale = np.median(np.concatenate([np.exp(logGp[0]), np.exp(logGpp[0])]))
    bG = (np.log(Gscale) - 5 * np.log(10), np.log(Gscale) + 4 * np.log(10))
    btau = (np.log(1 / w_hi) - 3 * np.log(10), np.log(1 / w_lo) + 3 * np.log(10))
    bEa = (1e3, 400e3)
    bounds = [bG] * n_modes + [btau] * n_modes + [bEa]

    def objective(p):
        G = np.exp(p[:n_modes])
        tau_ref = np.exp(p[n_modes:2 * n_modes])
        Ea = p[-1]
        total = 0.0
        for k, T in enumerate(T_list):
            Gp, Gpp = maxwell_spectrum(omega, G, arrhenius_shift(tau_ref, Ea, T, T_ref))
            r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - logGp[k],
                                 np.log(np.maximum(Gpp, 1e-300)) - logGpp[k]])
            total += np.dot(r, r)
        return 0.5 * total

    def sampler(rng):
        g0 = rng.uniform(*bG, n_modes)
        t0 = np.sort(rng.uniform(*btau, n_modes))
        return np.concatenate([g0, t0, [rng.uniform(*bEa)]])

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed, sampler=sampler)
    G = np.exp(best.x[:n_modes])
    tau_ref = np.exp(best.x[n_modes:2 * n_modes])
    Ea = best.x[-1]
    o = np.argsort(tau_ref)
    return dict(G=G[o], tau_ref=tau_ref[o], Ea=float(Ea),
                cost=float(best.fun), success=bool(best.success))


def fit_branched(omega, Gp_data, Gpp_data, n_restarts=16, seed=0):
    """Fit branched spectrum: params [logGe, logtau_b, sigma]."""
    omega = np.asarray(omega, float)
    yp = np.log(np.asarray(Gp_data, float))
    ypp = np.log(np.asarray(Gpp_data, float))
    Gscale = np.median(np.concatenate([Gp_data, Gpp_data]))
    w_lo, w_hi = omega.min(), omega.max()
    bGe = (np.log(Gscale) - 2 * np.log(10), np.log(Gscale) + 3 * np.log(10))
    btau = (np.log(1 / w_hi), np.log(1 / w_lo) + 3 * np.log(10))
    bsig = (0.5, 5.0)
    bounds = [bGe, btau, bsig]

    def objective(p):
        Gp, Gpp = branched_spectrum(omega, np.exp(p[0]), np.exp(p[1]), p[2])
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                             np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    return dict(Ge=np.exp(best.x[0]), tau_b=np.exp(best.x[1]), sigma=best.x[2],
                cost=float(best.fun), success=bool(best.success))
