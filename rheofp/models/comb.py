"""Comb / H-polymer melts: the McLeish et al. (1999) linear tube theory.

Reference: T. C. B. McLeish, J. Allgaier, D. K. Bick, G. Bishko, P. Biswas,
R. Blackwell, B. Blottiere, N. Clarke, B. Gibbs, D. J. Groves, A. Hakiki,
R. K. Heenan, J. M. Johnson, R. Kant, D. J. Read & R. N. Young, "Dynamics of
Entangled H-Polymers: Theory, Rheology, and Neutron-Scattering",
Macromolecules 1999, 32, 6734-6758. Source PDF: originals/ma990323j.pdf.
Equation numbers below are that paper's (section 2.1 and Appendix A).

>>> WHY THIS IS NOT McLEISH & LARSON 1998, WHICH IS THE OBVIOUS CHOICE <<<
An earlier version of this module was written against McLeish & Larson 1998
(the pom-pom paper, originals/mcleish_larson1998_pompom.pdf) and had to be
thrown away. Record so it is not re-attempted:

  ML1998 eq 8 is    G(t) = G_0 [ phi_b e^(-t/tau_b)
                               + (1-phi_b) Int e^(-t/tau_a(x)) dx ]^2

A SQUARED bracket is not a Prony series, so it cannot go through
`maxwell_spectrum`, and evaluating G*(omega) needs a numerical Fourier
transform. That transform ALIASES: log-spaced trapezoid quadrature of an
oscillatory sin(wt) kernel cannot converge once dt at large t exceeds the
period 1/w. Measured - the identical machinery reproduces an analytic single
Maxwell mode to 4 decimals on a narrow grid and fails by a factor of 114 on the
16-decade grid the model needs, improving only to 16 at 80000 points and not
even monotonically. It is not fixable by adding points.

ML1998's own authors superseded it. Its backbone carries "a single relaxation
time" by explicit admission, because it was built to feed a NONLINEAR
constitutive model. ML1999 section 2.1 gives the backbone a full spectrum and
writes the modulus as a SUM of two weighted integrals (eqs 22-24), which is a
mode ladder and hands straight to the validated `maxwell_spectrum` - exactly
the shape `star.py` already uses for its eq 26. The aliasing problem does not
need solving; it needs not creating.

THE ARCHITECTURE. An H-polymer is a linear "cross-bar" (backbone) terminated at
each end by a branch point carrying q = 2 dangling arms. A comb is the same
hierarchy with arms distributed along the backbone; a pom-pom is the same with
q > 2. LVE integrates over where the arms sit, so this one model serves all
three and the class is named `comb`. See "what this class cannot say" below.

RELAXATION IS HIERARCHICAL (paper section 2.1, its Figure 3), and the hierarchy
is the whole signature - a shoulder in G'' from the arms, then a weak maximum
at lower frequency from the cross-bar:

  (i)   Early: path-length fluctuation in the dangling arms, Rouse-fast at the
        very ends. The branch points are pinned, so NO backbone relaxation.
  (ii)  Deeper arm retraction becomes activated - exponentially slow - against
        an effective potential. The tube dilates self-consistently as relaxed
        arm material becomes solvent; the cross-bars stay immobile.
  (iii) Once the arms have fully retracted, the branch points may hop. The
        cross-bar now moves in a tube defined ONLY by other cross-bars. All the
        effective friction is concentrated at the branch points - the rapidly
        fluctuating arms outweigh the monomeric drag along the cross-bar.
  (iv)  The cross-bar relaxes as a "two-arm star" by fluctuation, cut off by
        reptation of its central portion. This is the slowest process.

THE MODULUS (eqs 22-24). Two weighted integrals over arc coordinates, x_a
running along an arm from free end (0) to branch point (1), x_b from branch
point (0) to the middle of the cross-bar (1):

    G*(w) = G_0 (R+1) [ Int_0^1 dx_a phi_a (1 - phi_a x_a)^R   K(w tau_a(x_a))
                      + Int_0^1 dx_b phi_b^(R+1) (1 - x_b)^R   K(w tau_b(x_b)) ]

with K the standard Maxwell kernel. The bracketed weights are the effective
concentration of unrelaxed entangling network at the moment that segment
relaxes - dynamic dilution. phi_a and phi_b are the arm and cross-bar volume
fractions, phi_a + phi_b = 1.

TWO CONSTANTS THAT THE LITERATURE DOES NOT AGREE ON. Both are module-level and
both are deliberately NOT fitted; see the notes on each:
  * R, the dilution exponent. ML1999 Appendix A eq 26 states R = 4/3
    (Colby-Rubinstein, as star.py uses). Kapnistos et al. 2005
    (originals/ma050644x.pdf, Macromolecules 38, 7852) chose R = 1 after
    testing and say outright "the dilution is not a fully resolved issue".
    4/3 is the default here because this module follows ML1999.
  * p^2, the branch-point diffusion constant (eq 32). ML1999 finds p^2 = 1/6
    "accounts well for the materials in this study"; Kapnistos 2005 Table 2
    uses 1/12. A factor of two between two papers on the same quantity is the
    argument for FIXING it rather than fitting it - a free p^2 would absorb
    exactly the spectral width that s_a and s_b are supposed to determine.

PARAMETERS (k = 5 for AICc): (G_0, s_a, s_b, phi_b, tau_e).
  G_0    plateau modulus [Pa], a pure vertical amplitude.
  s_a    entanglements per ARM, M_a/M_e.
  s_b    entanglements along the CROSS-BAR, M_b/M_e.
  phi_b  cross-bar volume fraction; phi_a = 1 - phi_b.
  tau_e  Rouse time of one entanglement segment [s], a pure horizontal scale.
Note phi_b is NOT independent of s_a, s_b and q in a real molecule - it is
s_b / (s_b + 2 q s_a) by construction (ML1998 eq 10). It is carried as a free
parameter anyway because polydispersity and the comb-vs-H ambiguity break that
identity, and because ML1999's own Table 2 fits phi_b separately from the
synthesis value. `phi_b_from_architecture` computes the ideal value so tests
and callers can check consistency.

>>> THE NUMBER OF G'' MAXIMA IS NOT FIXED FOR THIS CLASS. <<<
Measured 2026-09-14 over phi_b at fixed s_a = 6, s_b = 30: **two** resolved
maxima at phi_b <= 0.40, **three** at phi_b >= 0.50. The cause is physical, not
numerical - at low phi_b the cross-bar ladder ends where the arm ladder begins
and the two features MERGE into one peak, while at higher phi_b a distinct
low-frequency cross-bar maximum separates out. The third feature, near
w ~ 1/tau_e, is where the entangled description terminates at its floor.

Consequence, and it is the same trap star.py records for its own two-peak split
past Z ~ 40: **any feature or pre-filter rule that assumes a single (or a
fixed) number of loss peaks will misread a comb.** Spectrum width must not be
measured from "the" G'' peak, and a rule keyed on peak count will flip
behaviour across phi_b ~ 0.45 for reasons that have nothing to do with the
sample being a comb. Note also that the merged low-phi_b peak is LARGER than
either separated feature, so peak HEIGHT is not a monotone function of phi_b
either, even though the cross-bar contribution alone is (verified separately -
see test_the_cross_bar_peak_strengthens_and_slows_with_the_cross_bar).

WHAT THIS CLASS CANNOT SAY:
  - **It cannot count the arms.** q enters only through the branch-point
    diffusion constant (eq 32, Db ~ p^2 a^2 / (2 q tau_a(1))), perfectly
    degenerate with tau_e and with p^2. Same situation star.py documents for
    star arm number, same reason. q is FIXED at 2 and the degeneracy is pinned
    by a test.
  - **It cannot separate a comb from an H from a pom-pom.** The hierarchy is
    identical; only arm placement differs, and LVE integrates over that.
  - **s_a, s_b and phi_b are not independently well determined on real data.**
    ML1999's own Table 2 compares synthesis against fit: H110B52A comes out
    phi_b 0.13 (chemistry) vs 0.63 (fit), H200B65A s_a 27 vs 16. The paper is
    candid that arm polydispersity matters exponentially and that its fits
    adjusted M_a, M_b AND two polydispersity indices. Treat any recovered
    parameter as suspect until measured here - see tests.

NOT WIRED INTO identify()'s BANK. `ALL_MODELS` is untouched and a test asserts
`"comb" not in ALL_MODELS`, to be deleted only in the commit that records a
passing cannibalisation check (n=30/class planted, identical seeds, per-class
before/after, real data must hold 6/6). The risk is concrete, not theoretical:
this is a broad-spectrum model at k=5 going onto a ballot that already has BSW
(`branched`) at k=5, and BSW was silently absorbing 25/30 planted stars before
`star` existed.
"""
from __future__ import annotations

import numpy as np

from rheofp.fitting.optimize import multi_restart_fit
from rheofp.models.maxwell import maxwell_spectrum

# --- config -----------------------------------------------------------------

# Dilution exponent. 4/3 per ML1999 Appendix A eq 26; Kapnistos 2005 uses 1 and
# calls the question open. See the module docstring - do not change this
# silently, and if you do, re-run the cannibalisation check.
R_DILUTION = 4.0 / 3.0

# Branch-point diffusion constant (eq 32). ML1999: 1/6. Kapnistos 2005: 1/12.
# NOT fitted - see the module docstring.
P_SQUARED = 1.0 / 6.0

# Arms per branch point (eq 32's q). Fixed at the H-polymer value; exactly
# degenerate with tau_e in the linear theory.
Q_FIXED = 2.0

# Pearson-Helfand barrier coefficients for a fixed network, before dilution:
# eq 25 U(x_a) = (15/8) s_a x_a^2 for an ARM, eq 35 U(x_b) = (15/16) s_b x_b^2
# for the cross-bar (half, because the cross-bar is treated as a two-arm star
# of arm length N_b/2).
ARM_BARRIER_COEFF = 15.0 / 8.0
BACKBONE_BARRIER_COEFF = 15.0 / 16.0

# Early-time Rouse prefactor, eq 3: tau_e(x) = (2253/256) s_a^2 tau_R x^4.
EARLY_ROUSE_COEFF = 2253.0 / 256.0

# Quadrature resolution along each arc coordinate. The integrands are smooth
# but the relaxation times span many decades, so the ladders must be dense
# enough that adjacent modes sit well under a decade apart. Convergence is
# checked by a test; this is NOT a speed dial (same lesson as star.N_S).
N_X = 200

# Arc coordinates are kept strictly inside (0, 1): tau(0) -> the Rouse limit
# and the (1-x)^R weight vanishes at x = 1.
X_EPS = 1e-9

# Inner quadrature for the first-passage double integral (eqs 29, 38). The
# asymptotic forms (eqs 30, 39) are used by default instead - see
# `_first_passage_asymptotic` and the `exact_fpt` switch on the spectrum.
N_S_INNER = 120

# Self-consistent solve for the retraction/reptation crossover x_c (eq 43).
XC_TOL = 1e-6
XC_MAX_ITER = 60

# Default optimizer settings; override per-call, not by editing these.
#
# 24 IS A MEASURED FLOOR, NOT A ROUND NUMBER - do not reduce it. At k=5 this is
# the widest parameter space in the bank, and 12 restarts is demonstrably not
# enough: a planted (s_a=6, s_b=20, phi_b=0.40, tau_e=1e-5) curve recovers
# EXACTLY at seed 2 and fails at seed 1 with the same 12 restarts, landing at
# rms 0.053 with s_a 20.2 against a true 6.0. The global minimum is not in
# doubt - cost at the true vector is 2.6e-29 against 3.4e-01 at the point 12
# restarts found, thirteen orders of magnitude better - so this is purely
# insufficient sampling of the basin. Every configuration at 24 and 48 restarts
# recovered every case tested. Pinned by
# test_twelve_restarts_is_not_enough_for_this_parameter_space.
N_RESTARTS = 24
SEED = 0

# Fit bounds. s_a and s_b are entanglement counts, kept LINEAR because the
# barriers are linear in them (same convention as star.Z_BOUNDS). The s_a floor
# mirrors star.py's Z floor of 4 and rests on the same measurement: below ~4
# entanglements the retraction barrier is under a couple of kBT and there is no
# architecture-specific shape left to fit.
S_A_BOUNDS = (2.0, 40.0)
S_B_BOUNDS = (4.0, 120.0)
PHI_B_BOUNDS = (0.05, 0.95)
# The cross-bar must be entangled with OTHER cross-bars for the dilated-tube
# reptation picture (eqs 41-42) to mean anything. ML1999 calls s_b*phi_b ~ 15
# the well-separated case. Enforced as a penalty, since it couples parameters.
S_B_PHI_MIN = 1.0

G_DECADES_UP = 3.0
G_DECADES_DOWN = 2.0
# tau_e bounds, in decades either side of 1/omega_max (see fit_comb for why the
# anchor is the window's fastest frequency and not its median). Deliberately
# ASYMMETRIC: tau_e can sit many decades below a window that only catches the
# terminal zone, but a tau_e far ABOVE the fastest measured frequency would
# mean the entire entangled spectrum lies outside the sweep, which is not a
# fittable situation.
TAU_E_DECADES_BELOW = 6.0
TAU_E_DECADES_ABOVE = 2.0


def phi_b_from_architecture(s_a, s_b, q=Q_FIXED):
    """Ideal cross-bar volume fraction, phi_b = s_b / (s_b + 2 q s_a).

    The geometric identity for a monodisperse H/pom-pom (ML1998 eq 10). The
    fitter does NOT impose it - see the module docstring - but it is the right
    consistency check against a synthesis-characterised sample.
    """
    return float(s_b) / (float(s_b) + 2.0 * float(q) * float(s_a))


# --- arm relaxation: eqs 25-31 ----------------------------------------------

def arm_potential(x_a, s_a, phi_a, R=R_DILUTION):
    """Effective arm retraction potential U_a,eff(x_a), eq 28, in kBT.

        U = (15 s_a / 4) [1 - (1-phi_a x_a)^(R+1) (1 + (1+R) phi_a x_a)]
                        / [(1+R)(2+R) phi_a^2]

    x_a runs from the FREE END (x_a = 0, zero barrier) to the BRANCH POINT
    (x_a = 1, full barrier). That is the same orientation as star.py's s, and
    the opposite of ML1998's x - the 1998 paper measures from the branch point
    outward. Getting this backwards inverts the whole spectrum, so it is pinned
    by `test_arm_potential_is_zero_at_the_free_end_and_maximal_at_the_branch`.

    Note the barrier depends on phi_a: cross-bar material acts as a PERMANENT
    network throughout arm relaxation, so an arm on an H-polymer relaxes
    exponentially slower than the same arm on a pure star. That is the paper's
    explanation (section 4.1) of Roovers' viscosity-enhancement observation,
    and it is why phi_a appears here at all.
    """
    x_a = np.asarray(x_a, float)
    s_a = float(s_a)
    phi_a = float(phi_a)
    u = phi_a * x_a
    num = 1.0 - (1.0 - u) ** (R + 1.0) * (1.0 + (1.0 + R) * u)
    return (15.0 * s_a / 4.0) * num / ((1.0 + R) * (2.0 + R) * phi_a**2)


def _arm_potential_slope(x_a, s_a, phi_a, R=R_DILUTION):
    """dU_a,eff/dx_a, stated under eq 30 as (15/4) s_a x_a (1 - phi_a x_a)^R."""
    x_a = np.asarray(x_a, float)
    return (15.0 / 4.0) * float(s_a) * x_a * (1.0 - float(phi_a) * x_a) ** R


def _tau_arm_early(x_a, s_a, tau_e):
    """Early Rouse fluctuation of the free end, eq 3.

        tau_e(x_a) = (2253/256) s_a^2 tau_R x_a^4,  tau_R = s_a^2 tau_e

    The x^4 is the sub-Fickian s ~ t^(1/4) end motion inverted; it is NOT a
    typo for x^2 (that is the CROSS-BAR's early form, eq 34, because the
    branch-point friction is localized rather than distributed).
    """
    x_a = np.asarray(x_a, float)
    tau_R = float(s_a) ** 2 * float(tau_e)
    return EARLY_ROUSE_COEFF * float(s_a) ** 2 * tau_R * x_a**4


def _first_passage_asymptotic(U, dU, U0, prefactor):
    """Mean first-passage time, the eqs 30 / 39 asymptotic form.

        tau = prefactor * exp(U) / dU * sqrt(pi / (2 U0))

    Valid where the barrier is large and the slope finite, which is everywhere
    except x -> 0 (handled by the crossover to the early branch) and, for the
    arm, x -> 1 where dU -> 0 if phi_a = 1. Guarded below.
    """
    dU = np.clip(np.asarray(dU, float), 1e-300, None)
    return prefactor * np.exp(np.asarray(U, float)) / dU * np.sqrt(
        np.pi / (2.0 * max(float(U0), 1e-300)))


def tau_arm(x_a, s_a, phi_a, tau_e, R=R_DILUTION):
    """Arm relaxation spectrum tau_a(x_a), eq 31's harmonic crossover.

        tau_a = tau_early e^U / (1 + tau_early e^U / tau_late)

    which follows whichever branch is faster, exactly as star.py's eq-22
    crossover does.

    FLOORED AT tau_e, AND THAT FLOOR IS LOAD-BEARING. Eq 3 is an x_a -> 0
    ASYMPTOTE (tau ~ x_a^4), so taken literally it sends the fastest arm mode
    to zero - at s_a = 8 it reaches 2.5e-37 s, some 30 decades below anything
    physical. The paper bounds it explicitly: section 2.1 describes free Rouse
    modes within the tube giving G'' ~ w^(1/2) at high frequency with the G''
    MINIMUM at w ~ tau_e^-1 (its section 4.1), and calls tau_e "the Rouse time
    of an entanglement length". The entangled description simply stops there;
    below tau_e the arm's own unentangled Rouse modes carry the stress, and
    ML1999 says outright that its theory "does not capture the high-frequency
    unentangled Rouse relaxations".

    star.py records the identical trap for the analogous eq 13 ("it looks
    absurd at s = 1 because it is an s << s* asymptote"), and needed the same
    correction via `_arm_rouse_modes`. Without this floor the arm ladder spans
    37 decades instead of ~7, interleaves with the cross-bar ladder, and the
    two-feature H-polymer signature disappears entirely - measured, see
    test_the_arm_and_crossbar_relaxations_separate.
    """
    x_a = np.asarray(x_a, float)
    U = arm_potential(x_a, s_a, phi_a, R)
    dU = _arm_potential_slope(x_a, s_a, phi_a, R)
    U0 = arm_potential(1.0, s_a, phi_a, R)

    # L_a^2 / D_a,eff = (15^2/8) s_a tau_R, stated under eq 29.
    tau_R = float(s_a) ** 2 * float(tau_e)
    prefactor = (15.0**2 / 8.0) * float(s_a) * tau_R

    early = _tau_arm_early(x_a, s_a, tau_e)
    late = _first_passage_asymptotic(U, dU, U0, prefactor)
    activated = early * np.exp(U)
    tau = activated / (1.0 + activated / np.clip(late, 1e-300, None))
    return np.maximum(tau, float(tau_e))


# --- backbone relaxation: eqs 32-43 -----------------------------------------

def backbone_potential(x_b, s_b, phi_b, R=R_DILUTION):
    """Effective cross-bar retraction potential U_b,eff(x_b), eq 37, in kBT.

        U = (15 s_b phi_b^R / 8) [1 - (1-x_b)^(R+1)(1 + (1+R) x_b)]
                                / [(1+R)(2+R)]

    x_b runs from the BRANCH POINT (0) to the middle of the cross-bar (1). The
    s_b phi_b^R combination is the dilated entanglement count - the cross-bar
    only feels other cross-bars. Coefficient is 15/8 not 15/4 because the
    cross-bar is treated as a two-arm star of arm length N_b/2 (eq 35).
    """
    x_b = np.asarray(x_b, float)
    num = 1.0 - (1.0 - x_b) ** (R + 1.0) * (1.0 + (1.0 + R) * x_b)
    return (15.0 * float(s_b) * float(phi_b) ** R / 8.0) * num / (
        (1.0 + R) * (2.0 + R))


def _backbone_potential_slope(x_b, s_b, phi_b, R=R_DILUTION):
    """dU_b,eff/dx_b, stated under eq 39 as (15/8) s_b phi_b^R x_b (1-x_b)^R."""
    x_b = np.asarray(x_b, float)
    return (15.0 / 8.0) * float(s_b) * float(phi_b) ** R * x_b * (
        1.0 - x_b) ** R


def _tau_backbone_early(x_b, s_a, s_b, phi_b, tau_e, q=Q_FIXED, R=R_DILUTION):
    """Early branch-point fluctuation of the cross-bar, eq 34.

        tau_b,e(x_b) = (75/32) q s_b^2 phi_b^(2R) tau_a(1) x_b^2

    x_b^2, NOT x_b^4: the friction is concentrated at the branch points rather
    than distributed along the chain, so this is not the free-end Rouse form.
    Note it carries tau_a(1) - the SLOWEST arm time - because a branch point
    can only hop once its arms have fully retracted. This is what makes the
    backbone's terminal time exponential in ARM length.
    """
    x_b = np.asarray(x_b, float)
    ta1 = tau_arm(1.0 - X_EPS, s_a, 1.0 - float(phi_b), tau_e, R)
    return ((75.0 / 32.0) * float(q) * float(s_b) ** 2
            * float(phi_b) ** (2.0 * R) * float(ta1) * x_b**2)


def _tau_reptation(x_c, s_a, s_b, phi_b, tau_e, q=Q_FIXED, R=R_DILUTION,
                   p2=P_SQUARED):
    """Cross-bar reptation time in the dilated tube, eq 42.

        tau_rep = (75/2) (1-x_c)^2 s_b^2 phi_b^(2R) tau_a(1) q / p^2

    The (1-x_c)^2 is the shortening from retraction having already relaxed the
    outer part of the contour. p^2 is the branch-point diffusion constant of
    eq 32 - see the module docstring on why it is fixed.
    """
    ta1 = tau_arm(1.0 - X_EPS, s_a, 1.0 - float(phi_b), tau_e, R)
    return ((75.0 / 2.0) * (1.0 - float(x_c)) ** 2 * float(s_b) ** 2
            * float(phi_b) ** (2.0 * R) * float(ta1) * float(q) / float(p2))


def _tau_backbone_retraction(x_b, s_a, s_b, phi_b, tau_e, q=Q_FIXED,
                             R=R_DILUTION, p2=P_SQUARED):
    """Cross-bar retraction spectrum tau_b,ret(x_b), eq 40's crossover."""
    x_b = np.asarray(x_b, float)
    U = backbone_potential(x_b, s_b, phi_b, R)
    dU = _backbone_potential_slope(x_b, s_b, phi_b, R)
    U0 = backbone_potential(1.0, s_b, phi_b, R)

    early = _tau_backbone_early(x_b, s_a, s_b, phi_b, tau_e, q, R)
    # L_b^2 / (4 D_b,eff): the eq-38 prefactor, assembled from eq 33's
    # tau_b,e = (x_b L_b,eff/2)^2 / (2 D_b,eff) evaluated at x_b = 1.
    prefactor = _tau_backbone_early(1.0, s_a, s_b, phi_b, tau_e, q, R)
    late = _first_passage_asymptotic(U, dU, U0, prefactor)
    activated = early * np.exp(U)
    return activated / (1.0 + activated / np.clip(late, 1e-300, None))


def solve_xc(s_a, s_b, phi_b, tau_e, q=Q_FIXED, R=R_DILUTION, p2=P_SQUARED):
    """Retraction/reptation crossover x_c, eq 43: tau_rep(x_c) = tau_b,ret(x_c).

    Self-consistent because tau_rep itself depends on x_c through eq 42's
    (1-x_c)^2 shortening. Solved by bisection on

        f(x) = log tau_b,ret(x) - log tau_rep(x)

    which is monotonically increasing: retraction slows with x while reptation
    speeds up. If f has no sign change the cross-bar never reaches reptation
    within the contour (a weakly entangled backbone), and x_c = 1 is returned -
    i.e. the whole cross-bar relaxes by retraction, which is the correct
    physical limit, not a failure.
    """
    def f(x):
        ret = _tau_backbone_retraction(x, s_a, s_b, phi_b, tau_e, q, R, p2)
        rep = _tau_reptation(x, s_a, s_b, phi_b, tau_e, q, R, p2)
        return np.log(max(float(ret), 1e-300)) - np.log(max(float(rep), 1e-300))

    lo, hi = X_EPS, 1.0 - X_EPS
    f_lo, f_hi = f(lo), f(hi)
    if f_lo > 0.0:
        # Reptation is already slower than retraction at the branch point:
        # reptation never takes over anywhere.
        return 1.0
    if f_hi < 0.0:
        # Retraction never becomes slower than reptation: reptation dominates
        # from the middle outward, x_c at the far end.
        return 1.0
    for _ in range(XC_MAX_ITER):
        mid = 0.5 * (lo + hi)
        if f(mid) < 0.0:
            lo = mid
        else:
            hi = mid
        if hi - lo < XC_TOL:
            break
    return 0.5 * (lo + hi)


def tau_backbone(x_b, s_a, s_b, phi_b, tau_e, q=Q_FIXED, R=R_DILUTION,
                 p2=P_SQUARED, x_c=None):
    """Full cross-bar relaxation spectrum: retraction, cut off by reptation.

    Beyond x_c retraction is slower than reptation, so those segments relax at
    tau_rep instead (the paper's "final crossover", under eq 43).

    FLOORED AT tau_a(1), AND THAT FLOOR IS THE HIERARCHY ITSELF. Eq 34's
    early branch goes as x_b^2, so at x_b -> 0 it sends the fastest cross-bar
    mode to zero. That is physically impossible here: section 2.1 step (iii)
    is explicit that only "when the path length of the dangling arms
    eventually fluctuates to zero... the branch point may make a diffusive
    hop", and eq 32 puts tau_a(1) in the branch-point diffusion constant for
    exactly that reason. So tau_a(1) is a FLOOR on the cross-bar ladder, not
    merely a scale factor multiplying it.

    Without this the backbone ladder started 15.8 decades BELOW where the arm
    ladder ended (measured), inverting the hierarchy, interleaving the two
    ladders, and destroying the two-feature signature the class exists to
    detect.
    """
    x_b = np.asarray(x_b, float)
    if x_c is None:
        x_c = solve_xc(s_a, s_b, phi_b, tau_e, q, R, p2)
    ret = _tau_backbone_retraction(x_b, s_a, s_b, phi_b, tau_e, q, R, p2)
    rep = _tau_reptation(x_c, s_a, s_b, phi_b, tau_e, q, R, p2)
    tau = np.where(x_b <= x_c, ret, rep)
    ta1 = float(tau_arm(1.0 - X_EPS, s_a, 1.0 - float(phi_b), tau_e, R))
    return np.maximum(tau, ta1)


# --- the modulus: eqs 22-24 -------------------------------------------------

def comb_spectrum(omega, G_0, s_a, s_b, phi_b, tau_e, q=Q_FIXED, R=R_DILUTION,
                  p2=P_SQUARED, n_x=N_X):
    """Comb / H-polymer dynamic modulus -> (G', G''). Eqs 22-24.

        G*(w) = G_0 (R+1) [ Int dx_a phi_a (1-phi_a x_a)^R K(w tau_a)
                          + Int dx_b phi_b^(R+1) (1-x_b)^R K(w tau_b) ]

    Both integrals are discretized into Maxwell mode ladders and summed by the
    shared `maxwell_spectrum`, so this model uses the same validated summation
    routine as the Prony, BSW and star models. No numerical Fourier transform
    is involved - see the module docstring for why that matters.

    Parameters are as the module docstring. phi_a = 1 - phi_b throughout.
    """
    omega = np.atleast_1d(np.asarray(omega, float))
    phi_b = float(phi_b)
    phi_a = 1.0 - phi_b

    x_a = np.linspace(X_EPS, 1.0 - X_EPS, int(n_x))
    x_b = np.linspace(X_EPS, 1.0 - X_EPS, int(n_x))
    dx = x_a[1] - x_a[0]

    ta = tau_arm(x_a, s_a, phi_a, tau_e, R)
    x_c = solve_xc(s_a, s_b, phi_b, tau_e, q, R, p2)
    tb = tau_backbone(x_b, s_a, s_b, phi_b, tau_e, q, R, p2, x_c=x_c)

    scale = float(G_0) * (R + 1.0) * dx
    g_a = scale * phi_a * (1.0 - phi_a * x_a) ** R
    g_b = scale * phi_b ** (R + 1.0) * (1.0 - x_b) ** R

    g = np.concatenate([g_a, g_b])
    tau = np.concatenate([np.asarray(ta, float), np.asarray(tb, float)])
    ok = np.isfinite(tau) & (tau > 0.0) & np.isfinite(g)
    return maxwell_spectrum(omega, g[ok], tau[ok])


# --- inverse -----------------------------------------------------------------

def fit_comb(omega, Gp_data, Gpp_data, n_restarts=None, seed=None, q=Q_FIXED,
             R=R_DILUTION, p2=P_SQUARED, n_x=N_X):
    """Fit the comb/H spectrum. Params [logG_0, s_a, s_b, phi_b, logtau_e].

    Five fitted parameters, k = 5 for AICc - G_0 and tau_e are pure vertical
    and horizontal scales but they are still fitted degrees of freedom and AICc
    counts them.

    q, R and p2 are NOT fitted. q is exactly degenerate with tau_e; R and p2
    disagree between the two source papers and a free p2 would absorb the
    spectral width that s_a and s_b exist to determine.
    """
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed

    omega = np.asarray(omega, float)
    Gp_data = np.asarray(Gp_data, float)
    Gpp_data = np.asarray(Gpp_data, float)

    Gscale = np.median(np.concatenate([Gp_data, Gpp_data]))
    lGs = np.log10(Gscale)
    # tau_e is anchored to the window's HIGHEST frequency, not its median.
    # tau_e is the FASTEST time in the model - every ladder is floored at it
    # (see tau_arm) - so 1/omega_max is the scale it lives near, and a window
    # that resolves the arm shoulder sits above it. Keying off the median put
    # the lower bound at 1/median(omega) / 10^4, which for a logspace(-4, 4)
    # sweep is 9.88e-05: a planted tau_e of 7e-6 was then OUTSIDE the box and
    # the fit pinned on the bound, returning +1311% error with the true value
    # unreachable. star.py's STAR_BNDS comment records the same trap - "a
    # planted vector on the bound is a silent fit failure". Asymmetric because
    # tau_e may sit well below the window (a melt measured only in its
    # terminal zone) but rarely far above it.
    ltau_fast = -np.log10(np.max(omega))
    bounds = [
        (lGs - G_DECADES_DOWN, lGs + G_DECADES_UP),
        S_A_BOUNDS,
        S_B_BOUNDS,
        PHI_B_BOUNDS,
        (ltau_fast - TAU_E_DECADES_BELOW, ltau_fast + TAU_E_DECADES_ABOVE),
    ]

    lp = np.log10(np.clip(Gp_data, 1e-30, None))
    lpp = np.log10(np.clip(Gpp_data, 1e-30, None))

    def objective(theta):
        lG, s_a, s_b, phi_b, ltau = theta
        if s_b * phi_b < S_B_PHI_MIN:
            return 1e6
        try:
            mp, mpp = comb_spectrum(omega, 10.0**lG, s_a, s_b, phi_b,
                                    10.0**ltau, q, R, p2, n_x)
        except Exception:
            return 1e6
        mp = np.clip(mp, 1e-30, None)
        mpp = np.clip(mpp, 1e-30, None)
        r = np.concatenate([np.log10(mp) - lp, np.log10(mpp) - lpp])
        if not np.all(np.isfinite(r)):
            return 1e6
        return float(np.sum(r * r))

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    lG, s_a, s_b, phi_b, ltau = best.x
    n = 2 * len(omega)
    return dict(G_0=float(10.0**lG), s_a=float(s_a), s_b=float(s_b),
                phi_b=float(phi_b), tau_e=float(10.0**ltau),
                x_c=float(solve_xc(s_a, s_b, phi_b, 10.0**ltau, q, R, p2)),
                cost=float(best.fun),
                rms_decades=float(np.sqrt(best.fun / n)),
                success=bool(best.success))


def model_comb(w, theta):
    """params: G_0(log10), s_a, s_b, phi_b, tau_e(log10)."""
    lG, s_a, s_b, phi_b, ltau = theta
    return comb_spectrum(w, 10.0**lG, s_a, s_b, phi_b, 10.0**ltau)


COMB_P0 = [5.7, 8.0, 30.0, 0.30, -5.0]
COMB_BNDS = [(-4, 9), S_A_BOUNDS, S_B_BOUNDS, PHI_B_BOUNDS, (-10, 2)]

# registry: name -> (forward, p0, bounds, k_params), the same shape as
# solutions.MODELS, network.NETWORK_MODELS and star.STAR_MODELS.
#
# NOT MERGED INTO ALL_MODELS. See the module docstring - the cannibalisation
# check has not been run, and tests/test_comb.py asserts this class is absent
# from identify()'s bank until it has.
COMB_MODELS = {
    "comb": (model_comb, COMB_P0, COMB_BNDS, 5),
}
