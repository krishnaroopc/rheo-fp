"""Literature ranges for fitted parameters — Plan A step 2.

REPORTING ONLY, like `plausibility.py` and `plain_language.py`. Nothing here
feeds into `identify()`'s ranking; the dependency runs `ranges -> report` and
never back. No torch.

>>> WHY THIS IS SEPARATE FROM THE AT-BOUND CHECK <<<
`plausibility.at_bound_warning` asks "did the fit hit a wall?". That catches
a parameter the optimiser was still pushing, but it is blind to a value that
is comfortably interior and *still physically absurd* — and it is blind by
construction, because the bounds it compares against were chosen to be
permissive enough to fit the synthetic population. This module asks the
different question: **is this number what real materials of this kind
actually show?**

The `branched`/`n_e` finding is the case in point. `n_e` was caught by the
at-bound check only because its bound happens to sit at 0.90; had the bound
been 2.0, `n_e = 1.4` would have passed silently while being twice BSW's own
stated physical range. A literature range catches it either way.

>>> GROUNDING: LITERATURE, NOT `synth.py` <<<
The user's explicit instruction (2026-09-21) was to source these from
literature and physical reasoning rather than reusing the generator's own
sampling ranges, so that this is an INDEPENDENT check rather than a circular
one. Re-deriving the ranges from `synth.py` would only ever confirm that a
fit looks like the training data — which is exactly the failure this project
keeps finding (a good fit of the wrong class, drawn from a distribution that
cannot represent the real material).

>>> HOW WIDE IS "PLAUSIBLE"? Measured, from Liu et al. (2006). <<<
`originals/liu2006_plateau_modulus_methods.pdf`, §6 (Conclusions) and §5.3,
compares every published method for determining the plateau modulus:

  * Monodisperse, long-chain (M_w/M_n < 1.1, Z > 20-30): methods agree
    "within an error margin of 5-10% close to the experimental uncertainty".
  * Polydisperse: "agreement within an error margin of 15% could be achieved
    as a result of careful measurements and the correct use of the methods",
    and polydispersity "introduces a large uncertainty".
  * Worse in practice for real resins: Liu's Table 9 records published G_N
    for bisphenol-A polycarbonate ranging over **1.2 to 4.1 MPa** — a factor
    of 3.4 for ONE polymer. PE likewise spans 1.05-2.73 MPa across sources.

So a "plausible" band must be generous: a factor of ~2 either side of the
literature spread, not 15%. A tighter band would fire constantly on correct
answers, which is the calibration standard `branched_vitrimer_contradiction`
and the at-bound check were both held to. **These ranges are deliberately
wide enough that firing means something is genuinely odd.**

>>> SCOPE: five classes, not ten. <<<
Per the plan, only the classes with a documented real-data failure get a
range: `branched`, `star`, `reptation`, `cured_elastomer`, `critical_gel`.
The remaining five have no real-data failure to calibrate against, and
inventing a range for them would be guessing dressed as physics.

>>> REDUNDANT-RANGE NOTE: three candidate entries were REMOVED because they
could never fire. <<<
Measured 2026-09-21 by comparing each range against the bound it sits behind.
Where a parameter's BOUNDS are already stricter than any honest literature
band, a range entry is dead code that implies a check is happening when none
is. Removed on that basis:

  * `branched` n_g  - bounds (0.2, 1.0) sit inside the ~0.15-1.0 band.
  * `reptation` Z   - bounds (2, 200) are stricter than the 2-500 band; real
                      monodisperse melts run Z ~ 8-30 (Katzarova 2018) and
                      ultra-high-MW PE reaches ~3000, so the bound binds first.
  * `star` Z        - bounds (4, 60) are stricter than 1-100, and `star`'s Z
                      is non-reportable anyway (biased +17-84%).

`Z_ENTANGLEMENTS`, `Z_STAR_ARM` and `BSW_N_G` are kept as documented
constants because they record the literature reading, and because a future
change to those bounds would make the corresponding range live again. A test
asserts every SHIPPED entry is actually reachable, so this cannot silently
regress.
"""
import numpy as np

# --- plateau modulus, from Fetters et al. (1994) Tables 1 and 2 ------------
# originals/fetters1994_plateau_modulus_table.pdf. Table 1 (413 K, 25
# polymers) and Table 2 (298 K, ~40 polymers) give measured G_N^0 spanning
# 0.015 MPa (PAPHM, a compact liquid-crystalline polymer) to 2.6 MPa (PE).
# Representative measured values relevant to the datasets in data/:
#   1,4-PBd  1.15 MPa (298 K)      PS      0.20 MPa (413 K)
#   1,4-PI   0.35 MPa (298 K)      PIB     0.32 MPa (298 K)
#   PDMS     0.20 MPa (298 K)      PE      2.60 MPa (413 K)
# The project's own real-data recoveries land in the same place, which is the
# independent corroboration this table needed: `star` recovers 366-436 kPa on
# polyisoprene against PI's true ~400 kPa, and recovers Pryke's stated
# 0.765 MPa for 1,2-polybutadiene to +1.4%/-4.4%.
#
# Band: 1 kPa to 10 MPa. The floor sits ~15x below the softest entry in
# Fetters (0.015 MPa) and the ceiling ~4x above the stiffest (2.6 MPa),
# because a real sample can be a melt measured off its plateau, a solution,
# or a filled compound. Firing here means "this is not an entangled polymer
# plateau at all", not "this disagrees with Fetters".
G_PLATEAU_PA = (1.0e3, 1.0e7)

# A network's equilibrium modulus is NOT a plateau modulus and the two must
# not share a band: a lightly crosslinked elastomer sits far below any
# entanglement plateau. Darby's cured silicones and Tixier's PDMS gels are
# the project's real anchors here, both well under 1 MPa.
G_NETWORK_PA = (1.0e0, 1.0e7)

# --- exponents -------------------------------------------------------------
# BSW terminal-wedge exponent n_e. rheofp/models/maxwell.py's own docstring
# states ~0.2-0.7 for this wedge (Baumgaertel-Schausberger-Winter 1990;
# Baumgaertel-Winter 1992); synth.py plants (0.15, 0.75). The band below is
# the union, widened slightly. >>> BOTH real LDPE melts VIOLATE it (measured
# n_e = 0.90, pinned at the bound, and chasing 2.0 when freed) - that is the
# open BSW item, and this range is what makes it visible without relying on
# where the bound happens to sit. See docs/at_bound_calibration_2026-09-21.md.
BSW_N_E = (0.10, 0.80)
# High-frequency (glassy/Rouse) wedge. Same sources, ~0.4-0.7.
BSW_N_G = (0.15, 1.00)

# Winter-Chambon critical-gel exponent. u must lie strictly in (0, 1) by
# construction. Real gels cluster mid-range: Tixier et al. (2004) measure
# u = 0.69-0.75 on PDMS near the sol-gel threshold, and Winter-Chambon's own
# stoichiometric gel sits at 0.5. Values very near 0 or 1 are not gels, they
# are an elastic solid or a viscous liquid.
GEL_U = (0.05, 0.95)

# Chasset-Thirion exponent m for a cured network. Small by nature - the
# modulus is nearly flat - and tied to crosslink density (Curro & Pincus
# 1983). Real cured elastomers sit at a few hundredths to ~0.3.
CURED_M = (0.005, 0.60)

# --- entanglement counts ---------------------------------------------------
# Z from a rheological fit. The lower end is set by physics, not by data: a
# chain needs a handful of entanglements before a tube description means
# anything, and below Z ~ 4 the star retraction barrier is 1-2 k_BT (measured
# in star.py). The upper end is generous - Katzarova's longest monodisperse PS
# is Z = 29.5, Liu's ultra-high-MW PE reaches Z ~ 3000 - so this band flags
# only the absurd.
Z_ENTANGLEMENTS = (2.0, 500.0)

# Z per ARM for a star. Same floor logic; arms are shorter than whole chains,
# and MM1998's seven real PI stars span Z = 2.2-21.
Z_STAR_ARM = (1.0, 100.0)


# Per-class expectations, keyed by class then by the parameter's index in the
# fitted vector - the same (class, index) keying `plausibility` uses, so the
# two modules stay aligned and a test can check the indices agree.
#
# Each entry: (range, is_log10, short human label, why this range).
# `is_log10` matters because most moduli and times are fitted as log10.
EXPECTED = {
    "branched": {
        # >>> NO RANGE ON BSW's G_N, DELIBERATELY. <<<
        # CLAUDE.md is explicit that for this class "G_N is a window-limited
        # amplitude scale, not a measured plateau modulus", so Fetters'
        # PLATEAU values simply do not apply to it. Caught by a test: the real
        # Pivokonsky melts fit G_N = 635 Pa and 1108 Pa, i.e. the softer one
        # sits BELOW a 1 kPa plateau floor while being a correct `branched`
        # call on real LDPE. Ranging it would have produced a permanent false
        # alarm on the project's own branched benchmark - which is exactly the
        # mistake this table exists to avoid making about other people's fits.
        3: (BSW_N_E, False, "terminal wedge exponent n_e",
            "the BSW terminal wedge is ~0.2-0.7 in the papers the model comes "
            "from (Baumgaertel-Schausberger-Winter 1990/1992)"),
        # n_g is NOT ranged: its bounds (0.2, 1.0) already sit inside any
        # honest literature band, so an entry here could never fire. See the
        # REDUNDANT-RANGE note below.
    },
    "star": {
        0: (G_PLATEAU_PA, True, "plateau modulus G_N",
            "an entangled melt plateau; polyisoprene's is ~0.35-0.4 MPa "
            "(Fetters et al. 1994), which this class recovers to within ~10% "
            "on real star melts"),
        # Z per arm is NOT ranged: STAR_BNDS already clips it to (4, 60),
        # stricter than any literature band, and `star`'s Z is non-reportable
        # anyway (biased +17-84%). See the REDUNDANT-RANGE note below.
    },
    "reptation": {
        0: (G_PLATEAU_PA, True, "plateau modulus Ge",
            "an entangled linear melt plateau; Fetters et al. (1994) measure "
            "0.015-2.6 MPa across real polymers"),
        # Z is NOT ranged: its bounds (2, 200) are already stricter than any
        # literature band. See the REDUNDANT-RANGE note below.
    },
    "cured_elastomer": {
        0: (G_NETWORK_PA, True, "equilibrium modulus G_inf",
            "a crosslinked network's equilibrium modulus, which sits well "
            "below an entanglement plateau for a lightly cured elastomer"),
        2: (CURED_M, False, "Chasset-Thirion exponent m",
            "m is small for a cured network - the modulus is nearly flat - "
            "and is tied to crosslink density (Curro & Pincus 1983)"),
    },
    "critical_gel": {
        1: (GEL_U, False, "critical-gel exponent u",
            "Winter-Chambon confine u to 0 < u < 1; real gels cluster "
            "mid-range (Tixier et al. 2004 measure 0.69-0.75 on PDMS, and a "
            "stoichiometric gel sits near 0.5)"),
    },
}


def out_of_range_parameters(name, params):
    """Which of the winner's fitted parameters fall outside literature ranges?

    Returns a list of dicts, one per offending parameter, in fitted order.
    Classes without an `EXPECTED` entry return [] - absence of a range is not
    evidence of a problem, and five of the ten classes deliberately have none.
    """
    out = []
    spec = EXPECTED.get(name)
    if spec is None or params is None:
        return out
    values = np.asarray(params, float)
    for i, (rng, is_log10, label, why) in sorted(spec.items()):
        if i >= len(values):
            continue
        raw = float(values[i])
        value = 10.0**raw if is_log10 else raw
        if not np.isfinite(value):
            continue
        lo, hi = rng
        if lo <= value <= hi:
            continue
        out.append({
            "index": i,
            "param": label,
            "value": value,
            "low": lo,
            "high": hi,
            "side": "below" if value < lo else "above",
            "is_log10": is_log10,
            "why": why,
        })
    return out


def _fmt(value, is_log10):
    """Moduli read better in kPa/MPa than in scientific notation."""
    if not is_log10:
        return f"{value:.4g}"
    if value >= 1e6:
        return f"{value / 1e6:.3g} MPa"
    if value >= 1e3:
        return f"{value / 1e3:.3g} kPa"
    return f"{value:.3g} Pa"


def out_of_range_warning(name, params):
    """Report-ready warning for a winner with unphysical values, else None."""
    bad = out_of_range_parameters(name, params)
    if not bad:
        return None

    parts = []
    for b in bad:
        parts.append(
            f"{b['param']} came out at {_fmt(b['value'], b['is_log10'])}, "
            f"{b['side']} the {_fmt(b['low'], b['is_log10'])} to "
            f"{_fmt(b['high'], b['is_log10'])} range real materials show "
            f"({b['why']})")
    joined = parts[0] if len(parts) == 1 else (
        "; ".join(parts[:-1]) + "; and " + parts[-1])

    return {
        "kind": "out_of_range",
        "offenders": bad,
        "text": (
            f"FITTED VALUES OUTSIDE THE RANGE REAL MATERIALS SHOW. The "
            f"`{name}` fit reproduces your curve, but {joined}. A model can "
            "match a curve's shape using numbers that do not describe any "
            "real material of that type - that is the most common way this "
            "tool goes wrong, and fit quality alone never reveals it. Either "
            "the class is wrong, or your sample sits outside what this model "
            "was built for. Note the ranges above are deliberately wide: "
            "published plateau moduli for a single polymer can differ by a "
            "factor of three between methods (Liu et al. 2006), so landing "
            "outside them is a strong signal rather than a quibble."),
    }
