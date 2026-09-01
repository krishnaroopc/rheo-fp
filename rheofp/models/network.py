"""Crosslinked-network family: cured elastomers and critical gels.

Forward model is the fractional Kelvin-Voigt element - a Hookean spring
(G_inf) in parallel with a springpot (c, m) - which is the frequency-domain
form of Chasset-Thirion power-law relaxation. Springpot G*(w) = c (i w)^m
expands to c w^m [cos(pi m/2) + i sin(pi m/2)], so in parallel with the spring

    G'(w)  = G_inf + c w^m cos(pi m / 2)
    G''(w) =         c w^m sin(pi m / 2)

Three parameters, no mode ladder - hence a separate module from the
Prony/Maxwell family in maxwell.py rather than another entry there.

Two DISTINCT fine classes share this functional family (user decision,
2026-07-04 - they are labeled and scored separately, never merged):

  cured elastomer  G_inf dominates; tan(delta) << 1; weak m ~ 0.1-0.3.
  critical gel     G_inf -> 0; G' ~ G'' ~ w^u with tan(delta) frequency-
                   independent at tan(pi u / 2).

For the critical gel the spring vanishes and the model collapses to the bare
springpot, so `critical_gel_spectrum` is a genuine 2-parameter model, not a
3-parameter fit that happens to drive G_inf small. Keeping it 2-parameter is
what lets AICc adjudicate between the two classes on parameter count.

Scope note on the gel exponent: u is NOT universally 1/2. Winter-Chambon's
n = 1/2 is the balanced-stoichiometry, entanglement-free special case; Tixier
et al. (2004, J. Rheol. 48, 39) measure u = 0.69-0.75 on end-linked PDMS.
GEL_U_RANGE below therefore spans ~0.5-0.75 and must not be narrowed to 0.5.

Both fits are planted-parameter validated in tests/test_network.py; real-data
validation against digitized EPDM (Martin 2008) and Tixier (2004) figures is
pending those xlsx files. See docs/elastomer_litreview.md sections 5-6.
"""
from __future__ import annotations

import numpy as np

from rheofp.fitting.optimize import multi_restart_fit

# Default optimizer settings; override per-call, not by editing these.
N_RESTARTS = 16
SEED = 0

# Physical bounds on the springpot exponent. m -> 0 is a pure spring, m -> 1 a
# pure dashpot; both endpoints are excluded so the fit stays in the fractional
# interior where the model is identifiable.
M_BOUNDS = (0.01, 0.99)

# Exponent window in which a power-law spectrum is called a critical gel.
# Spans Winter-Chambon (0.5) through Tixier's end-linked PDMS (0.75); a little
# slack on each side absorbs fit scatter. Do NOT narrow this to 0.5.
GEL_U_RANGE = (0.40, 0.85)

# Decades of headroom given to the modulus bounds around the data's median.
G_DECADES_UP = 3.0
G_DECADES_DOWN = 4.0
# G_inf is allowed to fall this far below the data to represent "no plateau".
G_INF_DECADES_DOWN = 10.0


def chasset_thirion_spectrum(omega, G_inf, c, m):
    """Fractional Kelvin-Voigt (frequency-domain Chasset-Thirion) -> (G', G'').

    G_inf: equilibrium/plateau modulus [Pa]; c: springpot quasi-modulus
    [Pa s^m]; m: power-law exponent in (0, 1).
    """
    omega = np.atleast_1d(np.asarray(omega, float))
    springpot = c * omega**m
    Gp = G_inf + springpot * np.cos(np.pi * m / 2.0)
    Gpp = springpot * np.sin(np.pi * m / 2.0)
    return Gp, Gpp


def critical_gel_spectrum(omega, c, u):
    """Bare springpot: the G_inf = 0 limit, as a 2-parameter model.

    This is the Winter-Chambon critical gel - G' and G'' are parallel power
    laws in w and tan(delta) = tan(pi u / 2) is frequency-independent.
    """
    return chasset_thirion_spectrum(omega, 0.0, c, u)


def _log_bounds(Gp_data, Gpp_data):
    """Modulus bounds (natural log) scaled to the data's median magnitude."""
    Gscale = np.median(np.concatenate([np.asarray(Gp_data, float),
                                       np.asarray(Gpp_data, float)]))
    lo = np.log(Gscale) - G_DECADES_DOWN * np.log(10)
    hi = np.log(Gscale) + G_DECADES_UP * np.log(10)
    return Gscale, (lo, hi)


def _log_residual_objective(omega, Gp_data, Gpp_data, forward):
    """Sum-of-squares of log-space residuals, the house fitting objective."""
    yp = np.log(np.asarray(Gp_data, float))
    ypp = np.log(np.asarray(Gpp_data, float))

    def objective(p):
        Gp, Gpp = forward(p)
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                            np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    return objective


def fit_chasset_thirion(omega, Gp_data, Gpp_data, n_restarts=None, seed=None):
    """Fit the cured-elastomer model. Params [logG_inf, logc, m]."""
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    Gscale, bG = _log_bounds(Gp_data, Gpp_data)
    # G_inf gets a much deeper floor than c: a nearly-uncrosslinked sample must
    # be able to push the plateau to effectively zero without hitting a bound.
    bG_inf = (np.log(Gscale) - G_INF_DECADES_DOWN * np.log(10), bG[1])
    bounds = [bG_inf, bG, M_BOUNDS]

    forward = lambda p: chasset_thirion_spectrum(omega, np.exp(p[0]), np.exp(p[1]), p[2])
    objective = _log_residual_objective(omega, Gp_data, Gpp_data, forward)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    return dict(G_inf=float(np.exp(best.x[0])), c=float(np.exp(best.x[1])),
                m=float(best.x[2]), cost=float(best.fun), success=bool(best.success))


def fit_critical_gel(omega, Gp_data, Gpp_data, n_restarts=None, seed=None):
    """Fit the 2-parameter critical gel. Params [logc, u]."""
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    _, bG = _log_bounds(Gp_data, Gpp_data)
    bounds = [bG, M_BOUNDS]

    forward = lambda p: critical_gel_spectrum(omega, np.exp(p[0]), p[1])
    objective = _log_residual_objective(omega, Gp_data, Gpp_data, forward)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    return dict(c=float(np.exp(best.x[0])), u=float(best.x[1]),
                cost=float(best.fun), success=bool(best.success))


def model_cured_elastomer(w, theta):
    """params: G_inf(log10), c(log10), m ; the full 3-parameter element."""
    G_inf, c, m = theta
    return chasset_thirion_spectrum(w, 10.0**G_inf, 10.0**c, m)


CURED_P0 = [5.0, 3.5, 0.2]
CURED_BNDS = [(-4, 9), (-4, 9), M_BOUNDS]


def model_critical_gel(w, theta):
    """params: c(log10), u ; the 2-parameter bare springpot."""
    c, u = theta
    return critical_gel_spectrum(w, 10.0**c, u)


GEL_P0 = [3.0, 0.6]
GEL_BNDS = [(-4, 9), M_BOUNDS]

# registry: name -> (forward, p0, bounds, k_params), same shape as
# rheofp.models.solutions.MODELS so both banks can be merged by identify().
NETWORK_MODELS = {
    "cured_elastomer": (model_cured_elastomer, CURED_P0, CURED_BNDS, 3),
    "critical_gel": (model_critical_gel, GEL_P0, GEL_BNDS, 2),
}


def tan_delta_spread(omega, Gp, Gpp):
    """Peak-to-peak spread of log10 tan(delta) across the window, in decades.

    The critical-gel signature is a frequency-INDEPENDENT loss tangent, so this
    is the discriminating statistic: ~0 for a gel, large for anything with a
    characteristic time inside the window.
    """
    tan_d = np.asarray(Gpp, float) / np.clip(np.asarray(Gp, float), 1e-30, None)
    ltd = np.log10(np.clip(tan_d, 1e-30, None))
    return float(ltd.max() - ltd.min())
