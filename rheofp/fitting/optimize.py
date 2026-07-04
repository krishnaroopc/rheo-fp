"""Shared multi-restart local optimization core.

Extracted from the repeated pattern across fit_maxwell, fit_wlm,
fit_sticky_stack, fit_branched, fit_model: random-restart L-BFGS-B in log
space, keeping the best of n_restarts local optima. Not a migration of any
single notebook function - a generalization of a pattern duplicated six times.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def multi_restart_fit(objective, bounds, n_restarts, seed=0, x0_first=None, sampler=None):
    """Random-restart L-BFGS-B, returning the best-of-n_restarts OptimizeResult.

    objective(x) -> scalar cost.
    bounds: list of (lo, hi) pairs, one per parameter.
    x0_first: optional exact starting point tried on the first restart
        (falls back to a random draw for restart 0 if omitted).
    sampler(rng) -> initial-guess array; defaults to independent uniform draws
        within each bound. Pass a custom sampler when parameters need
        structure at init time (e.g. sorted tau values for multi-mode fits).
    """
    rng = np.random.default_rng(seed)

    def default_sampler(rng):
        return np.array([rng.uniform(lo, hi) for lo, hi in bounds])

    draw = sampler if sampler is not None else default_sampler

    best = None
    for i in range(n_restarts):
        if i == 0 and x0_first is not None:
            x0 = np.asarray(x0_first, float)
        else:
            x0 = draw(rng)
        res = minimize(objective, x0, method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    return best
