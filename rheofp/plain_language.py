"""Plain-language translation of the ten class labels - the "what does that
word mean?" layer.

WHY THIS EXISTS. The end users are rheologists and materials scientists, not
ML people. `rouse_screened` is an internal label: it names a mode-spacing
exponent and a screening assumption, which is how the forward model is
parameterised, not how a person describes a sample. This module maps each
class to (a) a phrase a rheologist would actually use, and (b) the dynamic
regime it sits in.

>>> THE ONE THING THIS MODULE MUST NOT DO, and the reason it is written this
way. <<<

The obvious design - and the one the user asked about - is to report the
CONCENTRATION regime: dilute / semidilute / concentrated. That is how
Rubinstein-Colby organises the subject and it is how a rheologist thinks.
**It is not reportable from a single curve, and this module does not claim
it.**

Concentration is not in the forward models at all. `model_zimm` and
`model_rouse` take (Gscale, tau1, N) - an amplitude, a time, a mode count -
and differ ONLY in the spectral exponent (1.8 vs 2.0). Concentration acts on a
spectrum by scaling the amplitude and shifting the time axis, i.e. it MOVES a
curve without changing its shape, and those shifts are degenerate with
molecular weight, solvent viscosity and temperature. A dilute solution of long
chains and a more concentrated solution of short chains can land on the same
G'/G'' curve. So "what concentration is this" has no unique answer from one
curve, and a layer that printed one would be inventing information.

What IS in the curve is the DYNAMIC regime - unscreened-hydrodynamics vs
screened-unentangled vs entangled - because that is a shape question. That is
what `regime_note()` reports, and it is careful to say that the dynamic regime
IMPLIES a concentration regime only given facts the curve does not carry
(solvent quality, c*, Me).

The concentration axis becomes identifiable from a CONCENTRATION STACK, where
the trend across c is visible. The scaling layer for that is already validated
(CLAUDE.md Batch 3: exponents against Colby 2010 and Dobrynin-Colby-Rubinstein
1995) and the polyelectrolyte discriminator is the working precedent - it
reads whether the relaxation time falls with c (unentangled) or is
c-independent (entangled). `stack_hint()` says so, and says what to measure.

SCOPE. Reporting only. This module imports nothing from the fitting side and
changes no contract; `report.py` may call it, never the reverse. Same rule
`neural_report -> report` already follows.
"""
from __future__ import annotations

# ── config ────────────────────────────────────────────────────────────────

# The three dynamic regimes that ARE readable off a single curve's shape.
# Keyed by the internal class label. `None` means the class is not a solution
# or melt chain-dynamics class at all, so the axis does not apply to it.
UNSCREENED = "unscreened"      # hydrodynamic interaction intact - dilute
SCREENED = "screened"          # HI screened, chains not yet entangled
ENTANGLED = "entangled"        # topological constraints dominate

# Plain-language name, then a one-line gloss in a rheologist's terms.
# The gloss says what the MODEL asserts about the material, not what the
# fitting machinery did.
PLAIN_NAMES = {
    "zimm": (
        "dilute polymer solution (Zimm dynamics)",
        "An unentangled chain whose hydrodynamic interaction is UNSCREENED - "
        "the coil drags solvent with it. This is the dilute regime, below the "
        "overlap concentration c*.",
    ),
    "rouse_screened": (
        "unentangled polymer, screened hydrodynamics (Rouse dynamics)",
        "An unentangled chain whose hydrodynamic interaction is SCREENED by "
        "neighbouring chains. Covers semidilute-unentangled solutions AND "
        "melts below the entanglement molecular weight Me.",
    ),
    "reptation": (
        "entangled linear polymer",
        "A linear chain long enough to be topologically constrained, relaxing "
        "by reptation with contour-length fluctuation and constraint release. "
        "Covers both entangled solutions and entangled melts - the mechanism "
        "is the same.",
    ),
    "sticky_rouse": (
        "unentangled associating polymer (sticky Rouse)",
        "An unentangled chain carrying reversible stickers - ionic groups, "
        "hydrogen bonds, or dynamic covalent bonds. Relaxation waits on the "
        "sticker lifetime.",
    ),
    "sticky_reptation": (
        "entangled associating polymer (sticky reptation)",
        "An entangled chain carrying reversible stickers, so both "
        "entanglement and bond exchange gate the relaxation.",
    ),
    "cured_elastomer": (
        "permanently crosslinked elastomer",
        "A covalent network that cannot flow at any temperature. Its "
        "equilibrium modulus stays finite as frequency goes to zero.",
    ),
    "critical_gel": (
        "critical gel (at the gel point)",
        "A network exactly at its percolation threshold, with a power-law "
        "relaxation spectrum and a frequency-INDEPENDENT loss tangent - the "
        "Winter-Chambon signature.",
    ),
    "wormlike_micelle": (
        "wormlike micellar solution",
        "Self-assembled surfactant threads that break and recombine. Reptation "
        "plus reversible breaking gives a near-single-Maxwell response.",
    ),
    "branched": (
        "long-chain-branched melt",
        "A broad relaxation spectrum consistent with long-chain branching, as "
        "in LDPE. Fitted with a Baumgaertel-Schausberger-Winter spectrum.",
    ),
    "star": (
        "star polymer melt",
        "A branched architecture relaxing by ARM RETRACTION rather than "
        "reptation. Linear viscoelasticity depends on arm LENGTH only, so this "
        "cannot report how many arms the molecule has.",
    ),
}

# Which dynamic regime each class asserts. Classes whose physics is not a
# chain-dynamics regime question map to None and are simply not given a
# regime line.
CLASS_REGIME = {
    "zimm": UNSCREENED,
    "rouse_screened": SCREENED,
    "reptation": ENTANGLED,
    "sticky_rouse": SCREENED,
    "sticky_reptation": ENTANGLED,
    "wormlike_micelle": ENTANGLED,
    "branched": ENTANGLED,
    "star": ENTANGLED,
    "cured_elastomer": None,
    "critical_gel": None,
}

# What the dynamic regime does and does NOT tell you about concentration.
# Each entry is deliberately phrased as an implication with its premise
# stated, because the premise is exactly what a single curve does not carry.
_REGIME_NOTES = {
    UNSCREENED: (
        "Dynamic regime: hydrodynamically UNSCREENED (dilute). "
        "Unscreened hydrodynamics is what 'dilute' means dynamically, so this "
        "does imply a concentration below c* - but c* itself depends on "
        "molecular weight and solvent quality, which this curve does not "
        "carry. The curve gives the regime, not the concentration."
    ),
    SCREENED: (
        "Dynamic regime: SCREENED but UNENTANGLED. "
        "This is consistent with a semidilute-unentangled solution AND with a "
        "melt below Me - the two are dynamically the same thing and a single "
        "curve does not separate them. If you know whether there is solvent "
        "present, you know which."
    ),
    ENTANGLED: (
        "Dynamic regime: ENTANGLED. "
        "Consistent with an entangled solution above c_e AND with an entangled "
        "melt; the relaxation mechanism is identical, so the curve alone does "
        "not say which. Whether the sample contains solvent settles it."
    ),
}

# The honest statement about the concentration axis, printed whenever a
# concentration-regime reading might be expected. Wording matters here: the
# failure mode this guards against is a user reading "screened" as "semidilute"
# and taking a concentration away from a measurement that never contained one.
CONCENTRATION_CAVEAT = (
    "Concentration regime (dilute / semidilute / concentrated) is NOT "
    "reported, because it is not recoverable from one curve. Concentration "
    "scales a spectrum's amplitude and shifts its time axis without changing "
    "its shape, and those shifts are degenerate with molecular weight, solvent "
    "viscosity and temperature."
)

# What to measure to make the concentration axis identifiable. This is the
# constructive half - the same shape as report.py's what_would_settle_it.
CONCENTRATION_STACK_HINT = (
    "To place the sample on the concentration axis, measure a CONCENTRATION "
    "STACK: the same polymer in the same solvent at 3+ concentrations, with c "
    "recorded. The trend across c is the discriminator - in the unentangled "
    "regime the relaxation time falls as c rises, while in the entangled "
    "regime it becomes c-independent. A single curve cannot show a trend."
)


# ── api ───────────────────────────────────────────────────────────────────

def plain_name(class_name):
    """Rheologist-facing name for an internal class label.

    Unknown labels are returned unchanged rather than raising: this is a
    display helper, and a missing translation must never break a report.
    """
    entry = PLAIN_NAMES.get(class_name)
    return entry[0] if entry else class_name


def plain_gloss(class_name):
    """One-line physical description, or None if the label is unknown."""
    entry = PLAIN_NAMES.get(class_name)
    return entry[1] if entry else None


def dynamic_regime(class_name):
    """The dynamic regime a class asserts, or None where the axis does not
    apply (the two network classes)."""
    return CLASS_REGIME.get(class_name)


def regime_note(class_name):
    """The regime statement for a class, with its concentration implication
    spelled out including the premise it needs.

    Returns None for classes with no regime (networks), so a caller can simply
    skip the line rather than printing an empty heading.
    """
    return _REGIME_NOTES.get(CLASS_REGIME.get(class_name))


def stack_hint(class_name):
    """The 'measure a c-stack' suggestion, for classes where the concentration
    axis is meaningful.

    Deliberately NOT offered for the network classes: a cured elastomer or a
    critical gel is not placed on a dilute/semidilute axis, so suggesting a
    concentration series there would be noise.
    """
    if CLASS_REGIME.get(class_name) is None:
        return None
    return CONCENTRATION_STACK_HINT


def describe_class(class_name):
    """Everything this module knows about one label, as a dict.

    Structured rather than pre-formatted so a UI, a notebook and the text
    report can each render it their own way - the same contract report.py's
    explain() keeps.
    """
    return {
        "class": class_name,
        "plain_name": plain_name(class_name),
        "gloss": plain_gloss(class_name),
        "regime": dynamic_regime(class_name),
        "regime_note": regime_note(class_name),
        "concentration_caveat": (
            CONCENTRATION_CAVEAT if dynamic_regime(class_name) else None),
        "stack_hint": stack_hint(class_name),
    }
