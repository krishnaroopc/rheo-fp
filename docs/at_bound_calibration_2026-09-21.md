# At-bound check: calibration, and the `branched` finding it produced

**Plan A, step 1 (the at-bound check). Measured 2026-09-21.**
Module `rheofp/plausibility.py`, wired into `report.py` only, 20 tests in
`tests/test_plausibility.py`. **Reporting only** — `identify()`'s ranking and
contract are untouched, and the dependency runs `plausibility -> report`,
never back.

Calibration followed the precedent set by `branched_vitrimer_contradiction()`:
a report-only warning must fire on the known bad cases and stay quiet on the
known good ones, or it is noise that trains users to ignore it.

---

## 1. Known-bad: it fires where the failure was diagnosed by hand

Nine real Kapnistos curves through `fit_comb` (the class is not in the bank,
so this is against `COMB_BNDS` directly). `s_b` pins at its ceiling of 120 on
**8 of 9**, and two also drive `s_a` to its floor:

| sample | rms | pinned |
|---|---|---|
| **c6bb-PS** (linear control) | 0.1258 | **none** |
| c612-PS | 0.2420 | s_b @ upper |
| c622-PS | 0.3938 | s_b @ upper |
| c632-PS | 0.3686 | s_b @ upper |
| c642-PS | 0.3210 | s_a @ lower, s_b @ upper |
| c652-PS | 0.0725 | s_a @ lower, s_b @ upper |
| lc3-PBd | 0.3352 | s_b @ upper |
| lc1-PBd | 0.3231 | s_b @ upper |
| lc2-PBd | 0.2850 | s_b @ upper |

**This reproduces `docs/comb_reparameterisation_diagnosis.md` mechanically,**
which is the point: that diagnosis took a human reading parameter vectors, and
so did the `tdd` rejection (`M*/Me` pinned at 60 while Z error blew to
+50-60%). The check now does it on every call.

**>>> BUT READ THE LIMIT HONESTLY. <<<** The one curve where nothing pins is
**c6bb-PS, the linear control — the curve `comb` wrongly WINS.** So the check
catches the bad *fits*, not the bad *win*. It is a parameter-usability test,
not a wrong-class detector, and it must not be described as the latter. (This
is consistent with the diagnosis: `comb` wins the linear chain from a
comfortably interior vector, via its star limit. Nothing is at a bound because
nothing needs to be.)

## 2. Known-good: two "false alarms" on the 6/6 benchmark — which turned out to be REAL

| sample | winner | truth | rms | at-bound |
|---|---|---|---|---|
| SY184_10-1 | cured_elastomer | ✓ | 0.0114 | quiet |
| Solaris_1-1 | cured_elastomer | ✓ | 0.0196 | quiet |
| EF0030_1-1 | cured_elastomer | ✓ | 0.0173 | quiet |
| Tixier2004_gel | critical_gel | ✓ | 0.0108 | quiet |
| **Pivokonsky E** | branched | ✓ | 0.0624 | **n_e @ upper (0.90)** |
| **Pivokonsky B** | branched | ✓ | 0.0557 | **n_e @ upper (0.90)** |

Two fires on correct, well-fitted answers. Before treating that as a
calibration failure and loosening the tolerance, the alarm was **checked**:

**It is not a false alarm. `n_e` chases every ceiling it is given.**
Refitting the two LDPE curves with the `n_e` ceiling widened
(40 restarts, seed 0, everything else fixed):

| ceiling | E: fitted n_e | E: rms | B: fitted n_e | B: rms |
|---|---|---|---|---|
| 0.90 (shipped) | 0.9000 ← at | 0.06187 | 0.9000 ← at | 0.05567 |
| 0.95 | 0.9500 ← at | 0.06054 | 0.9500 ← at | 0.05566 |
| 0.99 | 0.9900 ← at | 0.06081 | 0.9452 | 0.05512 |
| 1.20 | 1.2000 ← at | 0.05634 | 1.2000 ← at | 0.05276 |
| 2.00 | 2.0000 ← at | 0.04574 | 2.0000 ← at | 0.04202 |

rms improves monotonically out to `n_e` = 2.0 — **more than double BSW's own
stated physical range.** `bsw_spectrum`'s docstring says the terminal wedge
exponent is "~0.2-0.7"; `synth.py` plants it in (0.15, 0.75). So on **these
two curves** the shipped bound is the only thing keeping `n_e` inside physics,
and the fit would leave that range entirely if allowed.

**>>> QUALIFIED 2026-09-21 by a second, independent LDPE — do not read this as
"real LDPE always violates the range". <<<** On BASF Lupolen 1810H (Verbeeten
2001 Table III, an exact 6-mode Prony spectrum, no digitizing) `n_e` fits to
**0.63 — comfortably inside both the bound and the literature range**, and the
check stays quiet. So the pinning is a property of the Pivokonsky curves, not
of branched melts generally. The over-flexibility itself still reproduces
there (`n_e` rises to 1.08 then 2.00 as the ceiling lifts, rms improving), but
the shipped bound does not catch it. Full measurement:
`docs/second_ldpe_lupolen_2026-09-21.md`.

**This is the BSW over-flexibility fault showing up in a third, independent
way** — alongside beating verbatim Likhtman-McLeish on Katzarova's three
monodisperse linear melts, and absorbing 25/30 planted stars before `star`
existed. Here it is visible on *correct* `branched` calls.

### A correction this produced: `synth.py`'s quoted Pivokonsky n_e is not the optimum

`rheofp/data/synth.py`'s comment states that `fit_bsw` on Pivokonsky E and B
lands at `n_e ~ 0.55-0.68`, and `BRANCHED_N_E = (0.15, 0.75)` was chosen to
bracket that. Measured:

* `fit_bsw` does return `n_e` = 0.547 (E) and 0.680 (B) — interior, healthy.
* `identify()`'s bank fit on the same curves returns **0.900 (pinned) for
  both**, at **better** rms.
* Evaluating the bank's own objective at both vectors: the pinned vector wins
  on both curves (E 0.06395 vs 0.06795; B 0.05567 vs 0.05920).

So **`fit_bsw` is finding a worse local optimum**, and the `0.55-0.68` figure
in `synth.py` describes that local optimum rather than the model's best fit to
the data. The two fitters differ in bounds (`fit_bsw` scales `tau_max`/`tau_c`
to the measured window; the bank uses fixed absolute bounds) and in restart
budget (48 vs `N_RESTARTS` = 12) — but no `tau` bound is active in either
case, and the recovered times agree closely (E: 92.3 s vs 85.2 s; B: 52.8 s
vs 52.6 s). The natural-log vs log10 objective is only a constant factor and
cannot move an optimum.

**Not changed, deliberately.** Widening `BRANCHED_N_E` or re-tuning `fit_bsw`
would alter the training distribution and the `branched` class's behaviour,
which is a pre-registered, cannibalisation-checked change under this
project's rules — not a drive-by edit inside a reporting task. Recorded here
and in `next-actions.md` as an open item. Note the likely direction: letting
`n_e` reach 2.0 would make BSW *more* flexible, which is the opposite of what
the active BSW fault needs.

## 3. What the check does about a bound that is itself physics

Three bounds are legitimately reachable by an ordinary sample, so a bare
"parameter at its limit!" would be wrong there. `SOFT_BOUND_NOTES` marks them
and they are reported **without** the distrust language (`n_hard` = 0):

* **`star`'s Z floor of 4** — below Z ≈ 4 the retraction barrier is 1-2 k_BT
  and the cost is FLAT in Z, so Z is unidentifiable there whatever the bound.
  Refitting at floors 4/3/2/1 left two weakly entangled arms at Z = 9.12 and
  6.66, unmoved. The floor asserts the identifiability limit rather than
  causing it, and `star`'s Z is non-reportable anyway.
* **`critical_gel`'s u in (0.01, 0.99)** — Winter-Chambon confines the
  exponent to 0 < u < 1. An edge value means "barely a gel", not a numerical
  wall.
* **`cured_elastomer`'s m** — same shape; a small m is the ordinary reading
  for a well-cured network.

`n_e` is deliberately **not** on that list: §2 shows its ceiling is a real
wall the fit wants to cross, so it must keep raising a hard warning.

## 4. A gap found while reviewing the check itself: rounded mode counts

Several forward models **round or clip** their integer-like parameters:
`model_zimm`/`model_rouse` do `N = max(2, int(round(N)))`, the sticky models
do the same for their mode counts, and the reptation family clips `Z` with
`max(2.0, Z)`. So **the float the fitter reports is not the value the model
used.** A fitted `N = 2.4` against a floor of 2 is a model running at its
floor, but `AT_BOUND_FRAC` on a `(2, 200)` span is only 0.198 — well inside
that half-unit band, so such cases were being missed entirely.

Fixed by widening the tolerance to a half unit **for those parameters only**
(`INTEGER_ROUNDED`, keyed `(class, index)` exactly like `SOFT_BOUND_NOTES` so
it cannot drift onto the wrong parameter; a test asserts every entry names a
parameter whose declared unit is `count`). The half-unit band must not leak
onto continuous parameters — on `n_e`, whose whole span is 0.85, it would
report "at bound" everywhere. Also pinned by a test.

**Re-ran the calibration afterwards: unchanged.** Still 2/6 on the benchmark
(the same two real `n_e` defects), still quiet on the four network/gel curves
— the widening introduced no new fires.

## Status

* Fires on 8/9 real combs (the diagnosed case) — mechanically reproducing two
  verdicts previously reached by hand.
* Fires on 2/6 of the benchmark, and **both were investigated and are real
  defects**, not noise. Nothing was loosened to silence them.
* Does not fire on the 4 network/gel benchmark curves.
* Does not detect a wrong-class win from an interior vector (c6bb-PS) — stated
  as a limit, not papered over.
* `identify()` untouched; 20 tests; no torch import.

**Not done in this step:** Plan A's second half, the literature range table
(`fetters1994_plateau_modulus_table.pdf` and
`liu2006_plateau_modulus_methods.pdf` are in `originals/` for it). The
`branched`/`n_e` finding above is an argument for building it: a range table
would have flagged `n_e` = 0.9 as outside BSW's stated 0.2-0.7 without needing
the bound to be hit at all.
