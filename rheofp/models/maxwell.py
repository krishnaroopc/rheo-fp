"""Maxwell / Prony-series family of linear-rheology forward models.

Canonical `maxwell_spectrum` unifies what were four separate but numerically
identical implementations across the original notebooks (batch1's
maxwell_spectrum, solution_identifier's _maxwell_sum, xpp_pompom's
maxwell_Gstar, and batch2's inline sum inside branched_spectrum) - all compute
Gp = sum(g * wt^2 / (1+wt^2)), Gpp = sum(g * wt / (1+wt^2)) over modes.

branched_spectrum and bsw_spectrum live here (not in tube.py) because their
output representation is a Prony/Maxwell sum over a constructed mode ladder,
even though they model entangled / long-chain-branched melts.

Two branched-melt forwards, kept for different jobs:
  * branched_spectrum - 3-param hierarchical double-reptation. Cheap, and the
    right shape for a moderately broadened linear/LCB spectrum. It CANNOT
    represent real LDPE: fitting it to Pivokonsky (2006) E and B bottoms out
    at ~0.28-0.32 decades RMS whatever sigma is allowed (a 10-mode Maxwell
    reaches ~0.02). Retained for the tube-model context and its tests.
  * bsw_spectrum - 5-param Baumgartel-Schausberger-Winter relaxation spectrum
    (two power-law wedges: a broad terminal wedge tau^n_e and a high-frequency
    wedge tau^-n_g below a crossover time). This is the branched class's
    forward model in the classifier: it fits Pivokonsky E and B to ~0.06-0.07
    decades RMS, and its intrinsically broad spectrum cannot fake a sharp
    reptation terminal, so AICc still separates it from the linear-melt class.
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


def bsw_spectrum(omega, G_N, tau_max, tau_c, n_e, n_g, n_modes=120):
    """Baumgartel-Schausberger-Winter relaxation spectrum -> (G', G'').

    H(tau) = n_e G_N [ (tau/tau_max)^{n_e}
                       + (tau/tau_c)^{-n_g} * 1(tau < tau_c) ]   for tau <= tau_max

    Two power-law wedges: a broad TERMINAL wedge (exponent n_e, ~0.2-0.7) that
    a single-power-law ladder cannot make wide enough, and a high-frequency
    GLASSY/Rouse wedge (exponent n_g, ~0.4-0.7) that switches on below the
    crossover time tau_c. Discretized onto a log-tau ladder (g_i = H_i * dln tau)
    then fed to the canonical Maxwell sum.

    Parameters:
      G_N     spectrum amplitude scale [Pa]. Equals the plateau modulus only
              when the window actually reaches the plateau; on a terminal-zone
              sweep it acts as an overall amplitude and should not be read as a
              measured G_N^0.
      tau_max longest relaxation time [s] (sets the terminal region).
      tau_c   crossover time [s] below which the glassy wedge dominates.
      n_e     terminal-wedge exponent.
      n_g     glassy-wedge exponent.
    """
    tau_max = float(tau_max)
    tau_c = float(tau_c)
    tau_lo = min(tau_c, tau_max) * 1e-4
    log_tau = np.linspace(np.log(tau_lo), np.log(tau_max), n_modes)
    tau = np.exp(log_tau)
    dln = log_tau[1] - log_tau[0]
    H = n_e * G_N * (tau / tau_max) ** n_e
    glassy = tau < tau_c
    H[glassy] += n_e * G_N * (tau[glassy] / tau_c) ** (-n_g)
    return maxwell_spectrum(omega, H * dln, tau)


# BSW parameter bounds (log10 for the moduli/times). n_e, n_g are linear.
BSW_N_E_BOUNDS = (0.05, 0.90)
BSW_N_G_BOUNDS = (0.20, 1.00)


def fit_bsw(omega, Gp_data, Gpp_data, n_restarts=48, seed=0):
    """Fit the BSW spectrum. Params [logG_N, logtau_max, logtau_c, n_e, n_g]."""
    omega = np.asarray(omega, float)
    yp = np.log(np.asarray(Gp_data, float))
    ypp = np.log(np.asarray(Gpp_data, float))
    Gscale = np.median(np.concatenate([Gp_data, Gpp_data]))
    w_lo, w_hi = omega.min(), omega.max()
    bGN = (np.log(Gscale) - np.log(10), np.log(Gscale) + 4 * np.log(10))
    btmax = (np.log(1 / w_hi), np.log(1 / w_lo) + 4 * np.log(10))
    btc = (np.log(1 / w_hi) - 4 * np.log(10), np.log(1 / w_lo))
    bounds = [bGN, btmax, btc, BSW_N_E_BOUNDS, BSW_N_G_BOUNDS]

    def objective(p):
        Gp, Gpp = bsw_spectrum(omega, np.exp(p[0]), np.exp(p[1]), np.exp(p[2]),
                               p[3], p[4])
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                             np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    return dict(G_N=float(np.exp(best.x[0])), tau_max=float(np.exp(best.x[1])),
                tau_c=float(np.exp(best.x[2])), n_e=float(best.x[3]),
                n_g=float(best.x[4]), cost=float(best.fun),
                success=bool(best.success))


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


def model_branched(w, theta):
    """params: G_N(log10), tau_max(log10), tau_c(log10), n_e, n_g.

    The branched / long-chain-branched melt class (e.g. LDPE), as a BSW
    spectrum. Same (forward, p0, bounds, k) shape as the solution and network
    banks so rheofp.fitting.identify can merge it in.
    """
    lGN, ltmax, ltc, n_e, n_g = theta
    return bsw_spectrum(w, 10.0**lGN, 10.0**ltmax, 10.0**ltc, n_e, n_g)


BRANCHED_P0 = [3.0, 1.0, -1.0, 0.3, 0.55]
# Bounds are absolute (not data-scaled) so the merged identify() bank can use a
# single static registry. They must enclose the synthetic population's ranges
# in rheofp.data.synth (there is a test): G_N ~ 3 Pa - 1 MPa; tau_max 1 ms -
# 1e4 s; tau_c from 7 decades below to just above 1 s (tau_max's synth ceiling
# is 1e3 s, drawn at least 0.2 decades above tau_c); exponents per BSW_N_*.
BRANCHED_BNDS = [(0.5, 6.0), (-3.0, 4.0), (-7.0, 2.9),
                list(BSW_N_E_BOUNDS), list(BSW_N_G_BOUNDS)]

# registry: name -> (forward, p0, bounds, k_params), same shape as
# rheofp.models.solutions.MODELS and network.NETWORK_MODELS.
BRANCHED_MODELS = {
    "branched": (model_branched, BRANCHED_P0, BRANCHED_BNDS, 5),
}


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
