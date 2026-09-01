"""Validation script for the stack-level melt-vs-network resolver.

The single-curve pipeline abstains on the melt-vs-rubber ambiguity because no
statistic on one curve can settle it (a melt's absent terminal relaxation is
missing evidence, not evidence of absence). A temperature stack adds two
pieces of evidence that a single curve cannot carry:

  1. Terminal relaxation appearing at ANY temperature. A permanent network
     cannot flow at any temperature, so one observation settles it.
  2. How far the spectrum SHIFTS along the frequency axis across the stack.
     Heating walks a melt's relaxation spectrum; a crosslinked network's
     plateau stays put.

Alignment is done on tan(delta) rather than the moduli, so the vertical shift
factor b_T cancels exactly and only the horizontal shift has to be fitted.

Three planted cases, each with a known truth:
  A. Melt, terminal visible          -> caught by evidence 1
  B. Melt, terminal hidden           -> caught by evidence 2 (the hard case)
  C. Permanent network, G_inf ~ T    -> stays a network despite moduli rising

Plus the adversarial case the whole feature exists for: an entangled melt that
a single curve confidently misclassifies as a network class, which the stack
then overturns.

Run directly: python scripts/validate_stack.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.maxwell import (
    maxwell_spectrum, arrhenius_shift, sticky_maxwell_stack,
)
from rheofp.models.network import chasset_thirion_spectrum
from rheofp.fitting.identify import (
    identify, identify_stack, resolve_melt_vs_network, SHIFT_DECADES_MIN,
)

T_LIST = [278.15, 288.15, 298.15, 308.15, 318.15]
T_REF = 298.15
EA_MELT = 80e3        # J/mol, a typical melt activation energy
N_MODES = 60


def _stack(w, curves, temps=T_LIST):
    return [dict(omega=w, Gp=gp, Gpp=gpp, T_K=t)
            for (gp, gpp), t in zip(curves, temps)]


def network_stack(w):
    """Entropic rubber elasticity: moduli scale with absolute T, nothing shifts."""
    return _stack(w, [chasset_thirion_spectrum(w, 1.0e6 * (t / T_REF),
                                               2.0e4 * (t / T_REF), 0.20)
                      for t in T_LIST])


def disguised_melt_stack(w, Ea=EA_MELT):
    """High-Mw entangled melt with the terminal region below the window."""
    tau0 = np.logspace(-5, 2, N_MODES)
    g = np.full(N_MODES, 1.0e5 / N_MODES)
    return _stack(w, [maxwell_spectrum(w, g, arrhenius_shift(tau0, Ea, t, T_REF))
                      for t in T_LIST])


def _report(label, stack, expect):
    out = resolve_melt_vs_network(stack)
    ok = out["verdict"] == expect
    shift = out["shift_decades"]
    shift_s = "n/a" if not np.isfinite(shift) else f"{shift:.2f} dec"
    print(f"{'PASS' if ok else 'FAIL'} {label:<38s} -> {out['verdict']:<9s} "
          f"shift {shift_s:>8s}   {out['reason']}")
    return ok, out


def main():
    all_pass = True
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6))

    print("=== Resolver verdicts (planted truth) ===")

    # A. melt, terminal visible
    wA = np.logspace(-2, 3, 60)
    stackA = _stack(wA, sticky_maxwell_stack(wA, [5000.0], [1.0], 60e3, T_LIST, T_REF))
    ok, _ = _report("A  melt, terminal in window", stackA, "melt"); all_pass &= ok

    # B. melt, terminal hidden - only the shift betrays it
    wB = np.logspace(1.5, 3, 40)
    stackB = _stack(wB, sticky_maxwell_stack(wB, [5000.0], [1.0], 60e3, T_LIST, T_REF))
    ok, outB = _report("B  melt, terminal hidden", stackB, "melt"); all_pass &= ok

    # C. genuine network
    wC = np.logspace(-3, 4, 60)
    stackC = network_stack(wC)
    ok, outC = _report("C  permanent network, G_inf ~ T", stackC, "network"); all_pass &= ok

    # D. single curve cannot resolve
    ok, _ = _report("D  single curve", stackC[:1], "ambiguous"); all_pass &= ok

    # E. Ea = 0 - a melt frozen in place is honestly unresolvable
    wE = np.logspace(-1, 2, 40)
    ok, _ = _report("E  melt with Ea = 0 (no shift)", disguised_melt_stack(wE, Ea=0.0),
                    "network"); all_pass &= ok
    print("     ^ expected: with no temperature dependence there is nothing to see.")

    # --- the adversarial case ---
    print("\n=== Adversarial: melt that a single curve calls a network ===")
    stackD = disguised_melt_stack(wE)
    alone = identify(stackD[0]["omega"], stackD[0]["Gp"], stackD[0]["Gpp"])
    joint = identify_stack(stackD)
    print(f"  single curve : best={alone['best']:<16s} abstain={alone['abstain']}")
    print(f"  with stack   : best={joint['best']:<16s} abstain={joint['abstain']}")
    print(f"                 {joint['abstain_reason']}")
    ok = (alone["best"] in {"cured_elastomer", "critical_gel"}
          and not alone["abstain"] and joint["abstain"])
    all_pass &= ok
    print(f"  {'PASS' if ok else 'FAIL'} - stack overturns a confidently wrong network call")

    print("\n=== Abstention lifted on a genuine network ===")
    aloneC = identify(stackC[0]["omega"], stackC[0]["Gp"], stackC[0]["Gpp"])
    jointC = identify_stack(stackC)
    print(f"  single curve : best={aloneC['best']:<16s} abstain={aloneC['abstain']}")
    print(f"  with stack   : best={jointC['best']:<16s} abstain={jointC['abstain']}")
    ok = aloneC["abstain"] and not jointC["abstain"]
    all_pass &= ok
    print(f"  {'PASS' if ok else 'FAIL'} - stack lifts an abstention it can justify")

    # --- plots ---
    for ax, (stack, title) in zip(axes, [
            (stackB, "Melt, terminal hidden"),
            (stackC, "Permanent network"),
            (stackD, "Melt disguised as network")]):
        cmap = plt.get_cmap("coolwarm")
        for k, s in enumerate(stack):
            col = cmap(k / max(1, len(stack) - 1))
            ax.loglog(s["omega"], s["Gp"], "-", color=col, lw=1.6)
            ax.loglog(s["omega"], s["Gpp"], "--", color=col, lw=1.1)
        ax.set_xlabel(r"$\omega$ (rad/s)")
        ax.set_ylabel("G', G'' (Pa)")
        ax.set_title(title, fontsize=10)
        ax.grid(True, which="both", ls=":", alpha=0.4)

    axes[0].text(0.03, 0.05, f"shift {outB['shift_decades']:.2f} dec\n-> melt",
                 transform=axes[0].transAxes, fontsize=9, va="bottom")
    axes[1].text(0.03, 0.05, f"shift {outC['shift_decades']:.2f} dec\n-> network",
                 transform=axes[1].transAxes, fontsize=9, va="bottom")
    axes[2].text(0.03, 0.05, f"shift {joint['stack']['shift_decades']:.2f} dec\n-> melt",
                 transform=axes[2].transAxes, fontsize=9, va="bottom")

    print(f"\n{'ALL PASS' if all_pass else 'SOME FAIL'} - stack resolver "
          f"(threshold {SHIFT_DECADES_MIN} decades)")
    print("Solid = G', dashed = G''; blue -> red is cold -> hot.")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
