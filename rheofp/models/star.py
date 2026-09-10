"""Star-polymer melts: the Milner-McLeish (1997) arm-retraction theory.

Reference: S. T. Milner & T. C. B. McLeish, "Parameter-Free Theory for Stress
Relaxation in Star Polymer Melts", Macromolecules 1997, 30, 2159-2166.
Source PDF: originals/milner_mcleish1997_star.pdf.
Equation numbers in the comments below are that paper's.

A star polymer cannot reptate - the branch point pins the molecule - so stress
relaxes by ARM RETRACTION: the free end retreats a fractional distance s back
along its tube against an entropic potential, then pokes out in a new
direction. The barrier is exponential in s, which is why star melts relax over
a spectrum many decades wide and why their viscosity is exponential in arm
molecular weight but independent of the number of arms.

Two ingredients make the bare Pearson-Helfand picture quantitative, and both
are implemented here:

  DYNAMIC DILUTION.  On the timescale at which segment s relaxes, everything
  outside it (s' < s) has long since relaxed and acts as solvent. The
  surviving network is diluted to volume fraction phi = 1 - s, so the
  entanglement length dilates as Ne(phi) = Ne * phi^-alpha (eq 23). Milner-
  McLeish adopt the Colby-Rubinstein exponent alpha = 4/3, measured on
  semidilute theta solutions, rather than the naive binary-contact alpha = 1.
  Integrating the hierarchical retraction relation (eq 7) with that exponent
  gives the effective potential

      Ueff(s) = (15 N / 4 Ne) * [1 - (1-s)^(1+a) (1 + (1+a) s)]
                              / [(1+a)(2+a)]                        (eq 24)

  which at alpha = 1 collapses to the Ball-McLeish form 15N(s - 2s^3/3)/8Ne
  (eq 8). The paper is explicit that the spectrum WIDTH is very sensitive to
  alpha: at alpha = 1 you need an unphysically large Me to fit the same data.

  EARLY FAST DIFFUSION.  For s below s* ~ (Ne/N)^(1/2) the barrier is under
  kBT and the free end is not activated at all - it moves as the end of a Rouse
  chain, faster than diffusively (eq 12), giving tau_e(s) ~ tau_R s^4 (eq 13).
  Without this the theoretical G'' has a spuriously sharp peak near
  omega tau_e = 1; including it broadens the peak to match data (their Figs 3
  vs 5).

The two regimes are joined by the paper's own crossover, eq 22:

    tau(s) = tau_early(s) / (1 + tau_early(s)/tau_activated(s))

with tau_activated from eq 29 - the first-passage-time result carrying its
prefactor, including the s(1-s)^2a term that keeps the barrier-top behaviour
finite and the Gamma(1/(1+a)) factor from the non-quadratic maximum at s = 1.

The modulus integral also carries the dilution exponent (eq 26):

    G*(omega) = (alpha+1) G_N Int_0^1 ds (1-s)^alpha [ i w tau(s)
                                                       / (1 + i w tau(s)) ]

NOTE the sign convention. The paper writes the bracket as -i w tau/(1 - i w
tau) under a exp(-i w t) Fourier convention; under this project's exp(+i w t)
convention (used throughout maxwell.py) that is the same complex modulus with
the conjugate sign, i.e. the standard Maxwell kernel (w tau)^2/(1+(w tau)^2)
for G' and (w tau)/(1+(w tau)^2) for G''. We evaluate it by discretizing s and
handing the resulting mode ladder to `maxwell_spectrum`, so the whole family
shares one summation routine with the Prony/BSW models.

WHAT THIS MODEL CAN AND CANNOT TELL YOU - read before reporting a result.
The number of arms f does NOT appear in G*(omega) at all. This is a real
physical prediction of the theory, not an implementation shortcut: relaxation
depends on the ARM length Na/Ne and on nothing else about the architecture, so
Pearson-Helfand's observed independence of viscosity from arm count is
reproduced. Consequently this class can identify a material as a STAR, but it
can never report how many arms it has. Do not add an `f` parameter to make it
look more informative.

Scope, stated the same way pompom.py states its own: this is the LVE
(SAOS) prediction only. The paper validates against G'(omega)/G''(omega) of
12-arm polybutadiene and 3-arm polyisoprene stars, agreeing in SHAPE over
about five decades and within factors of ~1.6 in modulus and ~2 in time when
fed literature values of G_N, Ne and zeta. Those residual factors are the
paper's own open question (its section V), so a fit here that lands within a
factor of two on the time scale is behaving exactly as published.

STATUS: wired into `fitting/identify.py`'s bank as `star` (2026-09-09) after
the cannibalisation check against `branched` (BSW) - which found BSW silently
absorbing 25/30 planted star melts before this class existed. `synth.py`
generates the class too. Real-data validation is PARTIAL: `identify()` returns
`star` for 5 of the 7 MM1998 four-arm PI stars (the two misses, the highest-Z
arms, go to `branched`), but Z is not quantitatively recoverable - see the two
corrections below.

VERIFIED SO FAR against the paper's own analytic statements and figures:
  - eq 24 reduces to eq 8 (Ball-McLeish) at alpha = 1, to machine precision;
  - Ueff(1)/U_PearsonHelfand(1) = 0.257 at alpha = 4/3, against ~0.26 read off
    their Figure 2, and exactly 1/3 at alpha = 1, matching the text's "Ueff(1)
    is reduced by a factor of 3";
  - the Pearson-Helfand barrier reproduces the paper's quoted
    log(tau(1)/tau_0) = 13.8 for the Figure 1 system (Z = 17);
  - dUeff/ds matches central differences to 1e-10; Ueff is monotone in s;
  - the eq-22 crossover hands off from the early to the activated branch at
    s ~ 0.18, i.e. 1 - s of order (Ne/N)^(1/2) as the text requires;
  - G' ~ w^2 and G'' ~ w^1 in the terminal zone, to 1e-3 in the exponent;
  - G' recovers 0.96 G_N on a wide window (eq 25's weight integrates to 1);
  - G_N is a pure amplitude and tau_e a pure time scale (rigid shift in log w);
  - G''(w) spans ~5.9 decades for the Figure 1 system, against the paper's
    "excellent agreement over five decades".

FOUND WHILE BUILDING THE FITTER, worth knowing before this class goes on the
ballot: past Z ~ 40 the model predicts TWO G'' maxima, not one. The eq-22
crossover separates the early Rouse branch from the activated one, and once
the barrier is tall enough the terminal time is pushed so far from the Rouse
time that the single broad loss peak resolves into a fast peak (near the
crossover frequency) and a slow one (near 1/tau(1)). Verified numerically
converged - peak positions identical for n_s from 400 to 64000 - so it is
physics, not quadrature. Two consequences: any feature that assumes "one loss
peak" will misread a high-Z star, and spectrum width must not be measured from
the global G'' peak, which jumps between the two branches around Z ~ 40.

TWO CORRECTIONS MADE 2026-09-09 AGAINST REAL DATA (the seven monodisperse
four-arm PI stars of Milner & McLeish 1998, data/mm1998.npz - the theory's
OWN validation set, where the authors report excellent agreement with no
adjustable parameters). Both were found by fitting known-Z data and finding Z
wrong by a median 44%:

  1. THE EQ-29 PREFACTOR WAS 2x TOO LARGE. This is the authors' own erratum,
     printed in MM1998's Appendix under its eq 10: "This is eq 29 of ref 1
     with an additional factor of 1/2, which was mistakenly omitted in the
     earlier paper." This module was transcribed from the 1997 paper, so it
     inherited the error. Small effect on its own (a constant prefactor is a
     ~0.3 decade rigid shift, which tau_e absorbs) but it is a real bug.

  2. THE ARM'S OWN ROUSE MODES WERE MISSING - the larger effect. MM scope eq
     26 to "the terminal region up to the start of the high-frequency Rouse
     regime [the minimum in G''(omega)]" (section IV, comment 1); above that
     minimum their Figure 5 shows the data rising away from the theory. A real
     SAOS window usually extends into that region, and without a term there
     the fitter widens the spectrum - i.e. inflates Z - to cover it. Added as
     `_arm_rouse_modes` (Likhtman-McLeish eq-19 bookkeeping, reusing the form
     already validated in tube.py), switchable off via `arm_rouse=False` to
     recover the paper's bare result.

  Measured effect on Z recovery, the five samples with Z above Z_BOUNDS'
  floor: median |error| 44% -> 30%, every residual improved, and the fitted
  G_N moved from 440-490 kPa toward 366-436 kPa against polyisoprene's true
  ~400 kPa plateau. The systematic high-frequency G'' deficit at known Z
  (-0.21 to -0.37 decades in the top band) is gone.

  CONSEQUENCE FOR G_N, worth knowing before reporting one: with the Rouse
  modes on, G' rises ABOVE G_N at high frequency (~2.4x on a very wide
  window). G_N is the plateau LEVEL, not the maximum of the curve. A test
  pins this.

Z IS STILL BIASED HIGH by 17-84% on that set and is NOT a quantitative output.
Two separate reasons, both real: the mid-Z samples (Z ~ 7-9) do not have
enough barrier for the retraction picture to dominate - the terminal peak and
the Rouse regime sit about a decade apart, with no window between them - and
`Z_BOUNDS` starts at 4, so genuinely weakly-entangled arms (the Ma 17k and
11.4k samples, true Z 3.4 and 2.2) cannot be fitted correctly at all. Report
"star", not "Z = ...", until this is resolved.

KNOWN LIMIT, not yet resolved: the terminal time moves only ~0.16 decades
between alpha = 1 and alpha = 4/3, where Ueff(1) alone would imply ~1.03. The
cause is eq 22 itself - at s -> 1 the early and activated branches sit within
~0.3 decades of each other for this Z, so the harmonic-style blend pulls the
result toward the faster branch instead of switching cleanly. This is the
paper's own "simple crossover function", not a coding error, but it does mean
the alpha sensitivity the paper emphasises is damped here. Quantify it against
real star data before reporting any alpha-dependent claim.
"""
from __future__ import annotations

import numpy as np
from scipy.special import gamma as _gamma

from rheofp.fitting.optimize import multi_restart_fit
from rheofp.models.maxwell import maxwell_spectrum

# --- config -----------------------------------------------------------------

# Colby-Rubinstein dilution exponent (eq 23). alpha = 1 is the older naive
# binary-contact value and is retained only so tests can exercise the eq-8
# limit; do not change this default - the paper shows the spectrum width is
# very sensitive to it, and alpha = 1 forces an unphysical Me to fit data.
ALPHA_CR = 4.0 / 3.0

# Quadrature resolution in s. The integrand is smooth but tau(s) spans many
# decades, so the mode ladder is built on a grid dense enough that adjacent
# modes are well under a decade apart for realistic Z.
#
# Converged well below this: G'' peak positions are identical for n_s from 400
# to 64000. Do NOT reach for this as a speed dial - measured 2026-09-09,
# dropping it 8x (400 -> 50) saves only ~0.5 s of a 2.4 s fit, because the
# cost sits in multi_restart_fit's restarts, not in building the ladder.
N_S = 400

# s is kept strictly inside (0, 1): both endpoints are integrable but
# degenerate - tau(0) = 0 and the (1-s)^alpha weight vanishes at s = 1.
S_EPS = 1e-6

# Default optimizer settings; override per-call, not by editing these.
N_RESTARTS = 32
SEED = 0

# Arm-Rouse mode ladder truncation (see `_arm_rouse_modes`). A mode whose
# tau_p sits this many decades below the window's fastest time contributes
# w tau << 1 to both moduli, i.e. nothing measurable, so the sum stops there.
# 2.0 is already generous: convergence measured at 1.0/2.0/3.0/4.0 decades.
MODE_TAU_FLOOR_DECADES = 2.0
# Hard ceiling on the number of transverse modes, so no parameter vector the
# optimizer explores can make one forward call pathologically slow.
MODE_COUNT_CAP = 4000

# Entanglements per arm. The lower end is where "star melt" stops meaning
# anything - below ~4 entanglements there is no barrier to speak of and the
# arm is effectively Rouse. The upper end is set by what SAOS can carry: at
# Z ~ 60 the terminal time is already ~13 decades above tau_e, so the terminal
# zone leaves any realistic window and Z stops being measurable from the
# spectrum shape. Kept linear (not log10) because the barrier is linear in Z.
Z_BOUNDS = (4.0, 60.0)

# Decades of headroom on the modulus and time-scale bounds, mirroring the
# convention in maxwell.fit_bsw / network._log_bounds.
G_DECADES_UP = 3.0
G_DECADES_DOWN = 2.0
TAU_E_DECADES = 4.0


def ueff(s, Z, alpha=ALPHA_CR):
    """Effective arm-retraction potential Ueff(s), in units of kBT (eq 24).

    Z = Na/Ne is the number of entanglements per arm. With alpha = 1 this
    reduces to the Ball-McLeish eq 8, 15 Z (s - 2 s^3 / 3) / 8.
    """
    s = np.asarray(s, float)
    pref = 15.0 * Z / 4.0
    num = 1.0 - (1.0 - s) ** (1.0 + alpha) * (1.0 + (1.0 + alpha) * s)
    return pref * num / ((1.0 + alpha) * (2.0 + alpha))


def dueff_ds(s, Z, alpha=ALPHA_CR):
    """dUeff/ds. Differentiating eq 24 collapses to a single power term."""
    s = np.asarray(s, float)
    pref = 15.0 * Z / 4.0
    # d/ds of the bracket is (1+a)(2+a) s (1-s)^a, cancelling the denominator.
    return pref * s * (1.0 - s) ** alpha


def _tau_early(s, Z, tau_e):
    """Unactivated Rouse-like retraction of the free end, eq 13.

    tau(s) = (225 pi^3 / 256) Z^2 tau_R s^4, with tau_R = tau_e Z^2, so the
    Z dependence is Z^4 overall. Valid for s << s* = (Ne/N)^(1/2).

    The Z^4 is not a transcription slip - it follows from eq 12 independently.
    Setting l = sL in <l^2(t)> = (4R^2/3pi^{3/2})(t/tau_R)^{1/2} and solving
    for t gives t(s) = (9 pi^3/16)(L/R)^4 tau_R s^4, and with L = R^2/a,
    a^2 = (4/5) Ne b^2, R^2 = N b^2 one has (L/R)^4 = (5Z/4)^2, which lands
    exactly on the printed 225 pi^3 Z^2 tau_R / 256. Reaching s = 1 means
    retracting the whole primitive path L, longer than R by sqrt(Z), and
    Rouse-like motion over that extra distance genuinely costs (L/R)^4 in
    time. So this branch is expected to be enormous at s ~ 1: it is an
    s << s* asymptote and is never meant to be evaluated there on its own.
    """
    s = np.asarray(s, float)
    tau_R = tau_e * Z**2
    return (225.0 * np.pi**3 / 256.0) * Z**2 * tau_R * s**4


def _tau_activated(s, Z, tau_e, alpha=ALPHA_CR):
    """First-passage retraction time with prefactor, eq 29.

    Eq 29 is eq 24 substituted into eq 21 with Deff = 2 DR, written out as

        tau_a(s) = A(Z) exp[Ueff(s)] / [ s^2 (1-s)^(2a) + K^-2 ]^(1/2)

        A(Z) = (L^2/Deff) (4/(15 Z)) sqrt(pi / (2 Ueff''(0)))
             = sqrt(30) pi^(5/2) / 30 * Z^(3/2) tau_e     (~13.2 Z^(3/2) tau_e)

        K = (15 Z / 4)^(a/(a+1)) (1+a)^(-(2a+1)/(a+1)) Gamma(1/(a+1))

    On the prefactor, which is the easiest thing in this paper to get wrong.
    Eq 19 reads tau ~ (L^2/Deff) exp[Ueff]/U'eff(s) * sqrt(pi/(2 Ueff''(0))).
    Eq 29 rewrites the U'eff(s) division into the square-root denominator,
    pulling the CONSTANT part (15Z/4) of U'eff(s) = (15Z/4) s (1-s)^a out of
    it - which is why the denominator holds a bare s^2 (1-s)^(2a) rather than
    (U'eff)^2. That extracted 15Z/4 must therefore be divided out here, in
    A(Z); leaving it in gives Z^(5/2) and puts tau_a about a decade high.

    The resulting Z^(3/2) is checkable three ways, and all three agree:
      - MM's own scaling remark under eq 19, "tau(s) ~ tau_e (N/Ne)^(3/2)
        exp[Ueff(s)]";
      - their statement in the same sentence that the prefactor "depends more
        weakly on N/Ne than the Rouse time tau_R" - and tau_R/tau_e = Z^2,
        so any exponent >= 2 (such as the Z^(5/2) above) contradicts the text;
      - the L^2/Deff group assembled from L = R^2/a, a^2 = (4/5) Ne b^2,
        R^2 = N b^2, Deff = 2 DR, DR = kT/(N zeta), which gives
        (15 pi^2/8) Z^3 tau_e and lands on Z^(3/2) once 4/(15Z) and the
        Z^(-1/2) from sqrt(pi/(2 Ueff''(0))) are applied.

    Ball & McLeish (1989), MM's ref 2, is the sanity anchor at the other end:
    their eq 8 writes the same activated time as t(s) = t_0 exp[U(s)] with t_0
    stated to be "the Rouse time for an entanglement length", i.e. tau_e. MM's
    refinement is precisely to replace that O(1) t_0 with this computed
    Z^(3/2) prefactor, so a prefactor far above tau_e * Z^2 cannot be right.

    Two further details of the printed eq 29. K carries the exponent a/(a+1)
    on the 15N/4Ne group, and it enters the sum under the root as K^-2 (not
    K^+2): it is the eq-20 barrier-top branch written as a reciprocal, so a
    LARGER K means a smaller additive floor. That additive term regularizes
    s -> 1, where Ueff has a non-quadratic maximum (eq 24 flattens as
    (1-s)^(1+a)) and the bare 1/U'eff would diverge.
    """
    s = np.asarray(s, float)
    # The factor 1/2 is the AUTHORS' OWN ERRATUM to eq 29, published in the
    # follow-up paper: Milner & McLeish (1998), Macromolecules 31, 7479,
    # Appendix, under its eq 10 - "This is eq 29 of ref 1 with an additional
    # factor of 1/2, which was mistakenly omitted in the earlier paper."
    # originals/ma980060d.pdf. Without it the activated branch is 2x too slow
    # at any given Z, the spectrum is correspondingly too wide, and fitting
    # real data recovers Z high by ~1.4-2.2x (measured on the seven MM1998
    # four-arm PI stars, 2026-09-09 - see scripts/validate_star_real.py).
    pref = 0.5 * tau_e * np.sqrt(30.0) * np.pi**2.5 / 30.0 * Z**1.5

    K = ((15.0 * Z / 4.0) ** (alpha / (alpha + 1.0))
         * (1.0 + alpha) ** (-(2.0 * alpha + 1.0) / (1.0 + alpha))
         * _gamma(1.0 / (1.0 + alpha)))

    denom = np.sqrt(s**2 * (1.0 - s) ** (2.0 * alpha) + K ** (-2.0))
    return pref * np.exp(ueff(s, Z, alpha)) / denom


def tau_of_s(s, Z, tau_e, alpha=ALPHA_CR):
    """Retraction time for arm segment s, joining eqs 13 and 29 via eq 22.

    tau = tau_early / (1 + tau_early / tau_activated) - a harmonic-style
    crossover that follows whichever branch is FASTER, since an arm end that
    can move freely does not wait for the activated route.
    """
    te = _tau_early(s, Z, tau_e)
    ta = _tau_activated(s, Z, tau_e, alpha)
    return te / (1.0 + te / ta)


def _arm_rouse_modes(omega, G_N, Z, tau_e):
    """Longitudinal + transverse Rouse modes of the ARM, above the G'' minimum.

    WHY THIS IS HERE AND WHY IT IS SEPARATE FROM EQ 26. Milner-McLeish scope
    their own result explicitly (1997, section IV, comment 1): the theory
    agrees with data "from the terminal region up to the start of the
    high-frequency Rouse regime [the minimum in G''(omega)]". Above that
    minimum the arm's own internal Rouse modes carry the stress, eq 26 does
    not describe them, and their Figure 5 shows the data rising away above the
    theory curve exactly there. So this term is NOT part of the paper's star
    theory - it is the standard tube-model high-frequency bookkeeping, added so
    a fit over a window that extends past the G'' minimum is not forced to
    distort Z to cover a region the retraction integral cannot reach.

    Measured before adding it (2026-09-09, the seven MM1998 four-arm PI stars
    in data/mm1998.npz): at the KNOWN Z, eq 26 alone under-predicts G'' in the
    top frequency band by 0.21-0.37 decades (1.6-2.3x too low) while
    over-predicting mid-window, and `fit_star` inflates Z by a median 44% to
    compensate. That is the failure this corrects.

    The form is Likhtman-McLeish (2002) eq 19's second and third sums, the same
    expressions already implemented and validated in `tube.py`
    (`_Gstar_long_modes`, `_Gstar_hf_rouse`) for linear melts - a Rouse mode
    ladder tau_p = tau_R / p^2 with tau_R = Z^2 tau_e:

      longitudinal, p = 1 .. Z-1 : weight G_N / (5 Z) per mode
      transverse,   p = Z .. p_max: weight G_N / Z     per mode

    The 1/5 on the longitudinal branch and the p >= Z switch to transverse are
    that paper's, not fitted here. For a star the ladder is built on the ARM
    (Z = entanglements per arm), because the branch point pins one end and the
    arm's internal modes are what relax at these frequencies - the same reason
    the retraction picture uses the arm and not the whole molecule.

    TRUNCATION, and it matters for speed as well as sense. Modes whose tau_p
    lies far BELOW the window's fastest point contribute nothing measurable -
    each adds w tau << 1, i.e. essentially zero to both moduli. The sum is
    therefore cut at the p whose tau_p is MODE_TAU_FLOOR_DECADES decades below
    1/w_max, not at some fixed p. Bounding it by tau_e instead (the obvious
    first way to write it) makes p_max scale as sqrt(tau_e w_max): at the top
    of `fit_star`'s tau_e bound that reached ~3.7 MILLION modes and a 60 x 3.7M
    temporary per call, which made a single fit take minutes. Measured
    2026-09-09. The cap below keeps it in the hundreds regardless of tau_e.
    """
    omega = np.atleast_1d(np.asarray(omega, float))
    Zi = max(1, int(round(float(Z))))
    tR = float(tau_e) * float(Z) ** 2

    # Longitudinal modes: p below Z, weight G_N/(5Z).
    p_long = np.arange(1, max(2, Zi))
    tau_long = tR / p_long ** 2
    wt = omega[:, None] * tau_long[None, :]
    denom = 1.0 + wt ** 2
    Gp = (G_N / (5.0 * Z)) * (wt ** 2 / denom).sum(axis=1)
    Gpp = (G_N / (5.0 * Z)) * (wt / denom).sum(axis=1)

    # Transverse (high-frequency) modes: p from Z up to where tau_p has fallen
    # MODE_TAU_FLOOR_DECADES below the window's fastest time. Solving
    # tR/(2 p^2) = tau_floor for p gives the bound.
    w_max = omega.max()
    tau_floor = (1.0 / w_max) * 10.0 ** (-MODE_TAU_FLOOR_DECADES)
    p_needed = int(np.sqrt(tR / (2.0 * tau_floor))) + 1
    p_max = min(max(Zi, p_needed), Zi + MODE_COUNT_CAP)
    p_hf = np.arange(Zi, p_max + 1)
    tau_hf = tR / (2.0 * p_hf ** 2)
    wt = omega[:, None] * tau_hf[None, :]
    denom = 1.0 + wt ** 2
    Gp = Gp + (G_N / Z) * (wt ** 2 / denom).sum(axis=1)
    Gpp = Gpp + (G_N / Z) * (wt / denom).sum(axis=1)
    return Gp, Gpp


def star_spectrum(omega, G_N, Z, tau_e, alpha=ALPHA_CR, n_s=N_S,
                  arm_rouse=True):
    """Milner-McLeish star-melt dynamic modulus -> (G', G'').

    Evaluates eq 26 by discretizing the arm coordinate s and summing the
    resulting Maxwell modes, so the final summation is the same
    `maxwell_spectrum` used by the Prony and BSW models.

    Parameters:
      G_N    plateau modulus [Pa]. Unlike BSW's amplitude scale this IS the
             physical plateau whenever the window reaches it, because the
             (alpha+1) Int (1-s)^alpha ds weight is normalized to 1.
      Z      entanglements per arm, Na/Ne. The single shape parameter: it sets
             the barrier height and hence the spectrum WIDTH. Note the number
             of arms does not enter - see the module docstring.
      tau_e  Rouse time of one entanglement segment [s]. Pure time scale.
      alpha  dilution exponent; 4/3 (Colby-Rubinstein) by default.
      arm_rouse  add the arm's own Rouse modes above the G'' minimum, which
             eq 26 does not describe (see `_arm_rouse_modes`). True by
             default because a real SAOS window usually extends into that
             region and without it Z absorbs the shortfall. Set False to get
             the paper's bare eq-26 result - which is what the analytic
             checks against MM's published statements must use.
    """
    s = np.linspace(S_EPS, 1.0 - S_EPS, int(n_s))
    ds = s[1] - s[0]
    tau = tau_of_s(s, float(Z), float(tau_e), alpha)
    # Weight from eq 26: (alpha+1)(1-s)^alpha ds, which integrates to 1 over
    # [0,1], so the mode weights sum to G_N and the plateau is recovered.
    g = float(G_N) * (alpha + 1.0) * (1.0 - s) ** alpha * ds
    Gp, Gpp = maxwell_spectrum(omega, g, tau)
    if arm_rouse:
        Gp_r, Gpp_r = _arm_rouse_modes(omega, float(G_N), float(Z),
                                       float(tau_e))
        Gp, Gpp = Gp + Gp_r, Gpp + Gpp_r
    return Gp, Gpp


def fit_star(omega, Gp_data, Gpp_data, n_restarts=None, seed=None,
             alpha=ALPHA_CR, n_s=N_S):
    """Fit the star-melt spectrum. Params [logG_N, Z, logtau_e].

    Three parameters, and they are cleanly separated in what they do to the
    curve, which is what makes this identifiable at all:
      G_N    pure vertical scale,
      tau_e  pure horizontal scale (a rigid shift in log omega),
      Z      the only SHAPE parameter - it sets the barrier height and hence
             the spectrum width, which grows monotonically from ~2.9 decades
             at Z = 5 to ~7.4 at Z = 40 (and tan(delta) at its minimum falls
             monotonically over the same range). Because width is a shape
             property no amount of shifting can fake, Z does not trade off
             against tau_e the way a pure time constant would.

    Note the fitted Z is the number of entanglements per ARM. The number of
    arms is NOT a parameter and cannot be recovered from LVE data - see the
    module docstring.
    """
    n_restarts = N_RESTARTS if n_restarts is None else n_restarts
    seed = SEED if seed is None else seed
    omega = np.asarray(omega, float)
    yp = np.log(np.asarray(Gp_data, float))
    ypp = np.log(np.asarray(Gpp_data, float))

    Gscale = np.median(np.concatenate([np.asarray(Gp_data, float),
                                       np.asarray(Gpp_data, float)]))
    w_lo, w_hi = omega.min(), omega.max()

    bG = (np.log(Gscale) - G_DECADES_DOWN * np.log(10),
          np.log(Gscale) + G_DECADES_UP * np.log(10))
    # tau_e is the FAST end of the spectrum (a single entanglement segment),
    # so it belongs at or below the shortest time the window resolves. The
    # terminal time sits many decades ABOVE it, carried by exp[Ueff]; bounding
    # tau_e near 1/w_hi and letting Z supply that span is what keeps the two
    # from trading off.
    btau = (np.log(1.0 / w_hi) - TAU_E_DECADES * np.log(10),
            np.log(1.0 / w_lo))
    bounds = [bG, Z_BOUNDS, btau]

    def objective(p):
        Gp, Gpp = star_spectrum(omega, np.exp(p[0]), p[1], np.exp(p[2]),
                                alpha=alpha, n_s=n_s)
        r = np.concatenate([np.log(np.maximum(Gp, 1e-300)) - yp,
                            np.log(np.maximum(Gpp, 1e-300)) - ypp])
        return 0.5 * np.dot(r, r)

    best = multi_restart_fit(objective, bounds, n_restarts, seed=seed)
    return dict(G_N=float(np.exp(best.x[0])), Z=float(best.x[1]),
                tau_e=float(np.exp(best.x[2])), cost=float(best.fun),
                success=bool(best.success))


def model_star(w, theta):
    """params: G_N(log10), Z, tau_e(log10) ; the 3-parameter MM star melt."""
    G_N, Z, tau_e = theta
    return star_spectrum(w, 10.0**G_N, Z, 10.0**tau_e)


STAR_P0 = [5.5, 15.0, -5.0]
# log10 G_N, Z, log10 tau_e. The tau_e floor of -10 is deliberately generous:
# synth.py places the terminal time near the window and back-computes tau_e,
# and at the top of STAR_Z (~55) that lands tau_e ~9.4 decades below 1 s
# (measured over 2000 draws: -9.38 .. -0.27, none outside). If STAR_Z's upper
# end is ever raised, widen this floor to match - a planted vector on the
# bound is a silent fit failure.
STAR_BNDS = [(-4, 9), Z_BOUNDS, (-10, 2)]

# registry: name -> (forward, p0, bounds, k_params), same shape as
# rheofp.models.solutions.MODELS and network.NETWORK_MODELS so the banks can be
# merged by identify(). NOT yet merged into ALL_MODELS - the cannibalisation
# check against `branched` has to run first (next-actions, star task step 3).
STAR_MODELS = {
    "star": (model_star, STAR_P0, STAR_BNDS, 3),
}
