# Plan A step 2 (literature ranges) and Plan B (optional user fields)

Built 2026-09-21, after Plan A step 1 (`docs/at_bound_calibration_2026-09-21.md`).
Both are **reporting only**: `identify()`'s ranking and contract are untouched,
neither imports torch, and the dependency runs
`ranges -> report` / `user_fields -> report` and never back.

* `rheofp/ranges.py` + 21 tests (`tests/test_ranges.py`)
* `rheofp/user_fields.py` + 22 tests (`tests/test_user_fields.py`)

---

# Plan A step 2 — literature ranges

## What it adds over step 1

Step 1 asks "did the fit hit a wall?". That is blind, **by construction**, to a
value that is comfortably interior and still physically absurd, because the
bounds it compares against were chosen permissive enough to fit the synthetic
population.

`n_e` is the proof. Step 1 caught it only because BSW's bound happens to sit at
0.90; had the bound been 2.0, `n_e = 1.4` would have passed silently while
being twice BSW's own stated range. The range check catches it on the **value**,
so widening a bound can never hide it. Pinned by
`test_the_branched_n_e_finding_is_what_this_catches_independently_of_bounds`.

## Grounding: literature, not `synth.py`

Per the user's instruction, ranges come from literature and physical reasoning
rather than the generator's sampling ranges, so this is an **independent**
check rather than a circular one. Re-deriving from `synth.py` could only ever
confirm "this fit looks like the training data" — which is exactly the failure
mode the project keeps finding. A test asserts the `n_e` range is not a copy of
`synth.BRANCHED_N_E`.

**Plateau moduli** — Fetters et al. (1994) Tables 1 (413 K, 25 polymers) and 2
(298 K, ~40 polymers), `originals/fetters1994_plateau_modulus_table.pdf`.
Measured G_N⁰ spans 0.015 MPa (PAPHM) to 2.6 MPa (PE). Values relevant to
`data/`: 1,4-PBd 1.15 MPa, 1,4-PI 0.35, PIB 0.32, PDMS 0.20, PS 0.20.
Corroborated independently by the project's own recoveries — `star` returns
366–436 kPa on polyisoprene (true ~400) and recovers Pryke's stated 0.765 MPa
to +1.4%/−4.4%.

**How wide is "plausible"** — Liu et al. (2006) §6 and §5.3,
`originals/liu2006_plateau_modulus_methods.pdf`, read directly:

* monodisperse, long-chain (M_w/M_n < 1.1, Z > 20–30): methods agree "within
  an error margin of 5–10% close to the experimental uncertainty";
* polydisperse: "within an error margin of 15% could be achieved as a result
  of careful measurements and the correct use of the methods";
* in practice far worse — their Table 9 records published G_N for bisphenol-A
  polycarbonate spanning **1.2 to 4.1 MPa**, a factor of 3.4 for one polymer.

So the bands are deliberately generous (1 kPa–10 MPa for a plateau). A tighter
band would fire on correct answers, which is the standard
`branched_vitrimer_contradiction` and step 1 were both held to.

## Two things the tests caught in my own table

**1. BSW's `G_N` must NOT be ranged.** CLAUDE.md is explicit that for
`branched` it is "a window-limited amplitude scale, not a measured plateau
modulus", so Fetters' plateau values do not apply. The real Pivokonsky melts
fit 635 Pa and 1108 Pa — the softer one sits *below* a 1 kPa plateau floor
while being a **correct** `branched` call on real LDPE. Ranging it produced a
permanent false alarm on the project's own branched benchmark. Removed, pinned
by `test_branched_G_N_is_deliberately_unranged`.

**2. Three candidate entries were dead code.** Where a parameter's BOUNDS are
already stricter than any honest literature band, a range entry implies a
check that is not happening. Measured and removed:

| entry | bounds | literature band | verdict |
|---|---|---|---|
| `branched` n_g | (0.2, 1.0) | ~0.15–1.0 | bound binds first |
| `reptation` Z | (2, 200) | 2–500 | bound binds first |
| `star` Z | (4, 60) | 1–100 | bound binds first; Z non-reportable anyway |

`test_every_shipped_range_is_actually_reachable` now stops inert entries being
added or returning.

## Shipped table — six live checks

| class | parameter | plausible range |
|---|---|---|
| branched | terminal wedge exponent n_e | 0.10–0.80 |
| critical_gel | critical-gel exponent u | 0.05–0.95 |
| cured_elastomer | equilibrium modulus G_inf | 1 Pa – 10 MPa |
| cured_elastomer | Chasset-Thirion exponent m | 0.005–0.60 |
| reptation | plateau modulus Ge | 1 kPa – 10 MPa |
| star | plateau modulus G_N | 1 kPa – 10 MPa |

Scope is the five classes with a documented real-data failure, per the plan.
The other five have no real failure to calibrate against and inventing a range
would be guessing dressed as physics.

## Calibration on real data

Quiet on all four correct network/gel benchmark curves (Darby ×3, Tixier).
Fires on both Pivokonsky LDPE melts — the known `n_e` defect, now caught on
the value rather than on the bound.

---

# Plan B — optional user-supplied fields

Mandatory input is unchanged: frequency, G′, G″, temperature. These four
fields are optional additions, used **only** at report time.

## >>> The zero case is the normal case. <<<

Most uploads supply nothing. `user_note()` returns None when nothing is given,
and `explain(..., user=None)` produces a **byte-identical** report — verified
end-to-end. This is load-bearing: the measured 0.923 accuracy is on bare
curves, and that must remain exactly what a bare upload does. Pinned by
`test_the_zero_case_is_silent`.

## 1. `mw_g_per_mol` — the strongest of the four

`tube.Z_of_sample(Mw, Ge)` turns a fitted plateau modulus plus a known
molecular weight into an expected entanglement count. That machinery has been
in `tube.py` all along but only ran in the other direction (forcing Mw into
validation curves); it was never a user-facing cross-check.

**Validated on Katzarova 2018's three monodisperse polystyrenes**, the one
dataset where Z is known independently from M_w/M_e — and where `tube.py`'s
defaults (ρ = 959 kg/m³, T = 453.15 K) *are* the right chemistry:

| sample | true Z | fitted Z | Mw-implied Z | ratio |
|---|---|---|---|---|
| PS105 | 7.9 | 9.40 | 9.28 | 1.01 |
| PS206 | 15.5 | 16.07 | 14.49 | 1.11 |
| PS392 | 29.5 | 28.94 | 26.64 | 1.09 |

Both independent routes land within 1–11% of each other and near the truth.
That is a genuine consistency check, because the fit never saw the Mw.

**Tolerance is a factor of 2**, deliberately loose: Z is linear in 1/Ge, so it
inherits the full plateau-modulus method spread above, and `tube.py`'s ρ/T
defaults are polystyrene-specific. The note says so explicitly whenever the
defaults are used, since applying them silently to another chemistry would be
a quiet error.

Only `reptation`, `sticky_reptation` and `star` support this — asking a
critical gel for an entanglement count is meaningless.

## 2. `flows` — a direct observation beats a threshold

`terminal_reached` is one of only two hard discards the project trusts, and it
is already documented missing a visibly flowing sample: **Pryke's Ma38k
measures 1.39 against a 1.4 cutoff while plainly flowing** (raw terminal slopes
1.87/0.85, G″/G′ = 33 at the lowest point).

Both directions are handled, and they are not symmetric. If the user says it
flows and a **network class won**, that is a real refutation — a permanent
network cannot flow at any temperature, which is the project's own grounding
for the discard. If `terminal_reached` was False for a non-network winner, the
likely reading is a terminal zone below the measured window.

## 3. `solvent_present` — aimed at the biggest error source

Zimm vs Rouse-screened is 58% of all remaining classifier error and is
essentially "good solvent or screened", currently inferred from spectral shape
alone. Reported against the winner: solvent + a melt class is a real
disagreement; solvent + a solution class flags that the choice between the two
turns on concentration, which one curve cannot measure.

## 4. `suspected_class` — deliberately NOT a model input

A claimed architecture is shown **beside** the independent answer and never
fed into classification. Blending it in would teach the model to defer to a
claim that may be wrong, destroying the only thing that makes the comparison
worth printing — that the two were reached independently. Framed as a
two-item shortlist, exactly as `neural_report.pair_note()` does for a
two-brain disagreement, and never as one answer overruling the other.

## What is NOT built

Promoting `flows` / `solvent_present` into **trained network inputs**. That
needs a presence-flag per field, training with fields randomly blanked
(feature dropout) so the network cannot lean on a usually-absent field, and an
ablation showing that accuracy with zero fields reproduces 0.923 unchanged.
That is a retraining experiment, and per the plan it is only worth doing if
this report-time version proves useful first.
