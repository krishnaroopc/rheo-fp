# Next actions (handoff across PCs)

Claude: read this at the start of work. It is the live "what to do next" list,
kept in git so it syncs between the user's home and office PCs. When the user
says something like "let's continue" / "do the next thing" / "pick up where we
left off", this is where to look. Update + commit this file as items complete.

Last updated: **2026-09-09 (OFFICE PC, end of session).**

# >>> START HERE ON ANY PC <<<

**On arrival, in order:** `git pull` → `uv sync` → `uv run pytest -m "not slow"`.
Expect **229 passed, 2 skipped**. **Runtime is UNSTABLE on the office PC and
the cause is UNKNOWN — see below before reading anything into a slow run.**

### >>> OPEN: the suite runs at either ~15 min or ~76 min, nondeterministically

Measured on the office PC (Core Ultra 9 285) on 2026-09-11, same machine, same
command, same 228/229-test suite:

| run | wall | note |
|---|---|---|
| bare `-q` | **1:15:51** | other work running concurrently |
| `-q --durations=40` | **15:10** | idle |
| bare `-q` | **1:15:38** | **idle — nothing else running** |

**Two explanations were proposed and BOTH are refuted. Do not re-propose
them:**
1. *"Contention from concurrent work in the repo."* Refuted — the third run
   was deliberately idle and still took 1:15:38.
2. *"The `--durations` flag somehow changes it."* Refuted — A/B on
   `tests/test_stack.py`: **32s without, 31s with**. No effect.

**The one hard clue: CPU time is ~992 s in BOTH slow runs, against ~4540 s of
wall-clock — a ~22% CPU ratio.** A single-threaded SciPy workload should sit
near 100%. So the slow runs are not computing more; they are *waiting*, and
the fast run did the same work in a fifth of the wall time. Something is
blocking (IO, an antivirus/Defender scan of `.venv`, a filesystem or OneDrive
hook, power/thermal state) — unidentified as of this session.

**What this means practically:** a slow run is NOT evidence of a regression,
and the 13:34/2026-09-09 figure is consistent with the FAST path. Time the
suite more than once before believing any timing claim. **No code was changed**
and none should be until the blocking cause is identified.

**NARROWED 2026-09-11, not solved. Three more candidates ruled out:**
- *Per-test variance / bimodality.* Ruled out. One expensive test
  (`test_stack_overturns_a_network_call_on_a_disguised_melt`) run 4x
  back-to-back: **10.87 / 10.89 / 11.04 / 10.23 s**. Rock steady. Whatever
  blocks only appears over a long full-suite run, not in any single test.
- *CPU throttling / power plan.* Ruled out despite looking guilty. The plan is
  "HP Optimized (Modern Standby)" and `CurrentClockSpeed` reports 2500 MHz,
  but **Maximum processor state is 100% (0x64) on BOTH AC and DC** — the 2500
  figure is the nameplate base clock WMI always reports, not a cap.
- *A conftest / pytest plugin.* There is no `conftest.py` at all, and
  `[tool.pytest.ini_options]` defines only the `slow` marker.

**The one candidate left and NOT yet tested: Windows Defender.** Real-time
monitoring is ON (`DisableRealtimeMonitoring = False`) and the exclusion list
could not be read — `Get-MpPreference` requires **admin**, which this session
did not have. A Defender scan of `.venv` / the 10-model SciPy import graph
fits the evidence exactly: ~22% CPU, no per-test penalty, cost proportional to
total process-spawn and file-touch volume over a long run.

**NEXT STEP (needs an elevated shell):**
```
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
Add-MpPreference -ExclusionPath "C:\Users\krish\rheo-fp"
```
then re-time the suite twice. If that fixes it, record it in environment.md as
a per-machine setup step (it is machine-local, like `.venv`, and will need
doing on the laptop and home PC too).

Profile (2026-09-11, `--durations=40`, the FAST run): three tests are 38% of
the total — `test_contradiction_has_zero_false_positives_on_a_mixed_population`
189s, `test_generated_population_round_trips_through_the_identifier` 106s,
`test_the_agreement_signal_separates_the_star_hits_from_the_star_misses` 60s.
All three loop real or planted curves through the 10-model bank, and all three
are the evidence behind a user-facing claim. **Do not mark them `slow` to buy
time** — that removes exactly the checks this project's honesty rests on from
the default run.
Everything through `uv run`; there is no usable system Python (on the laptop
`python` is a 0-byte Microsoft Store stub). On a fresh Windows PC also run
**`gh auth setup-git`** or `git push` will hang forever with no error —
see environment.md.

## ~~The ONE unverified thing~~ — VERIFIED 2026-09-09 (office PC)

The laptop's unconfirmed commit was run against the full non-slow suite on the
office PC and is green. The suite has since grown by the 17 tests added this
session (3 in `test_report.py`, 14 in the new `test_neural_report.py`) — see
the count at the bottom of the office-PC session entry.

## What the state actually is

- **Star class: COMPLETE through step 4** (forward physics → inverse recovery
  → cannibalisation → wired into the bank → generator → real-data validation
  → reported limits). Nothing outstanding on it.
- **Two brains, both current.** The 10-model AICc bank and a freshly trained
  10-class checkpoint. `checkpoints/` is **gitignored, so it does NOT travel** —
  whichever PC you are on, if `checkpoints/rheonet.pt` is absent you must
  retrain before doing anything neural:
  `uv run python scripts/train_classifier.py -n 16000 --epochs 55`
  (~20 s/epoch on the laptop; the AICc baseline afterwards is the long pole).
- **Accuracy, and how to quote it honestly.** Seed 1 (office): 0.923 / merged
  0.968 / regime 0.999 / baseline 0.907. Seed 0 (laptop): 0.922 / 0.963 /
  0.999 / baseline 0.860. The NETWORK is seed-stable to 0.001. The **baseline
  is not** — n=150 gives it ~±0.027 sampling error, which is larger than the
  published "+0.016 margin". **Do not quote +0.016 as a result.** Say the
  network is at least as good as the physics baseline and the gap is not
  resolvable at n=150.
- Real data: **6/6** benchmark; `star` 5/7 on MM1998 (5/5 restricted to curves
  that reach terminal flow).

## >>> ~~THE NEXT TASK~~ — BOTH ITEMS BUILT 2026-09-09 (office PC) <<<

**The neural head IS report.py's second column now** (`rheofp/neural_report.py`,
`tests/test_neural_report.py`, `--neural` on `scripts/explain.py`), and the
discard/unopposed-winner link IS built (`unopposed_after_discard` in
`challenge()`). Details and the measured payoff are in `sessions.md` under the
office-PC entry; read that before extending either.

---

# >>> ~~THE ACTIVE TASK: star-polybutadiene validation~~ — DONE 2026-09-11 <<<

**COMPLETE.** User digitized Figure 2's two well-entangled panels;
`data/pryke2002.npz` is committed and 7 tests pin the result. Full scoring in
`docs/pryke2001_preregistration.md`'s OUTCOME section; narrative in
`sessions.md`. Headline:

| sample | Z_true | winner | dAICc | fitted G_N | fitted Z |
|---|---|---|---|---|---|
| PBD3_Ma38k | 10.96 | **star** | 170 | **0.776 MPa** | 13.6 (+24%) |
| PBD3_Ma78k | 22.14 | **star** | 87 | **0.731 MPa** | 31.5 (+42%) |

`star` **transfers to a third chemistry**, and a free fit recovered the paper's
own G_0 = 0.765 MPa to within 1.4% / 4.4%. P1, P3, P5 held; P2 untested.

**ITEM 2 — `terminal_reached` threshold: WATCH-AND-WAIT, trigger written down
2026-09-11 so it is not re-litigated from scratch.** The feature is
`(slope_Gp_lo > 1.4) and (slope_Gpp_lo > 0.7)`; Pryke's Ma38k measures
**1.39 / 0.625** and reads False while plainly flowing. **Deliberately NOT
changed**, for three reasons worth keeping: n=2; the threshold gates a
*sound* positive-observation discard (observed flow rules out permanent
networks, which is the one discard this project defends); and moving a
threshold to accommodate two curves is the exact failure the
pre-registration habit exists to prevent.

**THE TRIGGER:** act when a *third independent dataset* shows a curve that
visibly flows (G″/G′ > 1 at the low end, or raw terminal slopes approaching
2/1) and still reads `terminal_reached` False. At that point it is a
systematic threshold problem, not a coincidence.

**WHEN IT TRIGGERS, the change is NOT "lower the threshold".** That would
weaken the network-class discard, which rests on it. The candidate fixes, in
the order I would try them: (a) compute the slopes on the RAW trace rather
than the interpolated common grid — Ma38k's raw slopes are 1.87/0.85 against
1.39/0.625 after interpolation, so the smoothing is doing real damage and
this may be the whole bug; (b) add G″/G′ > 1 at the lowest point as an
alternative sufficient condition; (c) only then consider the numbers.
**Any change needs the full cannibalisation protocol** (n=30/class planted,
identical seeds, before/after per class, real data must hold) because this
feature feeds the pre-filter on every single `identify()` call.

**>>> THE ONE THING TO CARRY FORWARD: P4's PREMISE IS WRONG AS STATED. <<<**
`terminal_reached` read **False on both** samples and `star` was **right on
both** — against the 1/5 rate this file and CLAUDE.md both quote. The cause is
a hard threshold, `slope_Gp_lo > 1.4 and slope_Gpp_lo > 0.7`; Ma38k measures
**1.39 / 0.625**, missing the G′ cut by **0.01** while plainly flowing (raw
slopes 1.87/0.85, G″/G′ = 33 at the lowest point). So **stop quoting
"5/5 where flow is observed, 1/5 where it is not" as the class's envelope** —
it is a threshold artefact at least as much as a physical boundary.
**Nothing was changed** (n=2; the feature gates a sound positive-observation
discard) and nothing should be until a third dataset says so. Pinned by
`test_terminal_reached_is_a_sharp_threshold_that_a_flowing_melt_can_miss`.

Knock-on, unresolved: `challenge()`'s star window caveat fires on both curves —
**2 false alarms / 2** — on correct calls with G_N within 4% of the paper's.
Whether to condition it on something better than this threshold is now a real
open question, not a hypothetical.

**P6 also failed:** both curves are sharp two-brain disagreements (network:
`branched` p=0.983, `cured_elastomer` p=0.986; both confident, abstain_p ≈ 0).
Physics was right here, knowable only from the recovered G_0 — do NOT
generalise that into trusting physics on a split.

Unpredicted, flagged not acted on: fitted `tau_e` 2.78e-5 / 3.66e-5 s vs the
paper's 1.02e-5 (factors 2.7 / 3.6), just outside the factor-of-2 band
`star.py` cites, while the modulus sits well inside. Revisit on the next star
dataset.

### The original brief, kept as the record

**Status was: BLOCKED ON DIGITIZING. The paper is in hand; the data is not.**
`originals/ma010350l.pdf` — Pryke, Blackwell, McLeish & Young, *Macromolecules*
**35**, 467-472 (2002), DOI `10.1021/ma010350l`. Checked page by page
2026-09-10: it is the right paper and it is worth the effort.

**Why this one.** It closes the standing gap that `star` has never been tested
on a star MELT of independent chemistry. All existing star validation is
polyisoprene (MM1998) and polyisobutylene (Santangelo). Three further reasons
it is a strong test rather than just another dataset:
  1. **Z is known independently**, exactly as for MM1998 — the paper gives both
     the arm molecular weights and M_e, so Z = M_a/M_e is not fitted.
  2. It is **a direct Milner-McLeish test run by McLeish himself**, with the
     same three parameters this module implements (G_0, tau_e, s = M_a/M_e).
  3. **It independently corroborates a limit measured here.** The paper says
     its low-M_a samples "show the largest deviation from the data curves...
     marginal degree of entanglement, with s = 3.2" — the same Z ~ 4 floor this
     project found from the flat-cost-in-Z analysis (§ STEP 4 RESOLVED). Two
     independent routes to the same boundary.

**The numbers, transcribed from the PDF so nobody needs to reopen it:**

Table 1 — four symmetric THREE-ARM 1,2-polybutadiene stars:

| arm M_w | star M_w | PD | Z = M_a/M_e |
|---|---|---|---|
| 11 300 | 30 600 | 1.01 | **3.2** |
| 24 100 | 60 800 | 1.01 | **6.8** |
| 38 900 | 97 600 | 1.02 | **11.0** |
| 78 600 | 203 300 | 1.04 | **22.1** |

Table 2 — parameters at **333 K** (the master-curve reference temperature):

| species | M_e (g/mol) | G_0 (MPa) | tau_e (s) |
|---|---|---|---|
| 1,2-polybutadiene | 3550 | 0.765 | 1.02e-5 |
| poly(1-butene) (hydrogenated) | 6100 | 0.510 | 2.04e-5 |

Note the hydrogenated set has a DIFFERENT M_e, so its Z values differ: 1.9,
4.0, 6.4, 12.9. The paper fitted that M_e rather than taking it from
literature, and flags it as well below Fetters' 9536 — treat hydrogenated Z as
less certain than the parent's.

**WHAT IS ACTUALLY NEEDED — the data is in FIGURES, not tables.** There are no
numeric G'/G'' values anywhere in the PDF. Figures 2 (parent 1,2-PBD) and 3
(hydrogenated) are log-log master curves at 333 K spanning **1e-3 to 1e6 s^-1**
(~9 decades), four panels each, G' and G'' per panel. Same situation as every
other dataset here: Darby, Tixier, Pivokonsky, MM1998 and Santangelo all
reached `data/` only because the USER digitized them first.

**RECOMMENDED SCOPE, smallest useful first** — do NOT digitize all 16 curves:
  * Start with **Figure 2 only** (the unsaturated parents — their M_e is a
    literature value, not a fitted one, so Z is firmer).
  * Within it, the two well-entangled panels: **M_a = 38.9K (Z ~ 11)** and
    **M_a = 78.6K (Z ~ 22)**. These are where the class should work, and they
    are the cleanest panels to trace.
  * The two low-Z panels (3.2, 6.8) are a BONUS test of the known failure mode,
    not the main event. Expect Z to come back wrong there and do not treat that
    as a regression — it is the documented flat-cost-in-Z region.

**>>> THE PREDICTIONS ARE ALREADY PRE-REGISTERED — READ THEM FIRST <<<**
`docs/pryke2001_preregistration.md`, committed 2026-09-11 **before any curve
was digitized or fitted**. Six numbered predictions (P1-P6) plus an explicit
"what would count as a genuine problem" / "what would NOT" split, so a bad
result cannot be over- or under-read after the fact. **Do not edit anything
above its OUTCOME section**; record results underneath and let the diff show
what was wrong. Headline: `star` expected on the two well-entangled samples
(Z 11.0, 22.1); sample A (Z 3.2) expected to fail and that is NOT a
regression; misses expected to land on `branched`; Z expected to be biased
high and still non-reportable.

**Then, once `originals/pryke2001.xlsx` (or .ods) exists:**
  1. Write `scripts/prep_pryke2001.py` on the established pattern (see
     `prep_mm1998.py` / `prep_santangelo.py`) -> commit `data/pryke2001.npz`
     so tests run without `originals/`. Record T_K = 333.
  2. Run `identify()` per curve and score against the pre-registration.
     **Check `features["terminal_reached"]` and the low-frequency slopes
     BEFORE scoring any curve as a miss** — these are TTS master curves over
     ~9 decades, so how much terminal zone survives depends on where the
     digitizing stopped. A truncated trace is a digitizing artefact, not a
     class failure (prediction P4).
  3. Do NOT report Z as an output, and do NOT tune anything to improve Z on
     this dataset — that would be fitting the bound to the test set (P3).
  4. Add tests alongside `tests/test_star.py`'s real-data section.

---

**READ BOTH MEASUREMENTS, NOT JUST THE PRETTY ONE.** On MM1998's seven-star set
the agreement signal separates the AICc hits from the AICc misses PERFECTLY —
agree on all 5 AICc gets right, disagree on both it gets wrong (Ma95k/Ma105k,
true stars called `branched` at delta 56.5 and 102.6, where AICc is decisive
and the abstention head reads 0.00, so neither self-confidence flags them).

**Then it was measured on synthetic data THREE TIMES (seeds 7, 11, 23; 1400
curves total, all three outputs committed under `docs/`). Quote the POOLED
numbers — the constants in `neural_report.py` are pooled and a test recomputes
them from all three files.**

| | agree (n=1231) | disagree (n=169) |
|---|---|---|
| physics | 0.945 ± 0.007 | **0.438 ± 0.038** |
| neural | 0.937 | **0.426** |
| either right | 0.975 | **0.864** |

- **A disagreement roughly HALVES both methods** (ratio 0.46). "More than
  halves", written after seed 7, was an artefact of its 18-curve disagree arm.
- **The gate margin is small but consistently positive: +0.006 / +0.019 /
  +0.012 → pooled +0.014 at 2.0 SE.** No single run reaches significance;
  only the pooled agree arm does. **Wording is "comparable, probably a shade
  better; not a reason to prefer it" — do not upgrade it.** See §2 for the
  pre-registered rule this was judged against.
- **WHICH brain degrades more on a disagreement is NOT stable** — network
  worse at seed 11, fitter worse at seed 23. **Never advise trusting one side
  over the other on a split**; that is the whole argument for the shortlist.
- **`agree_degenerate` swings** (physics 0.364 / 0.576 / 0.575) on ~5-7% of
  curves. Only its `either right` (0.97-1.00) is quotable, and the report says
  outright that which member to prefer is not stable.
- **A SHARP disagreement is the pair's BETTER case** — pooled either-right
  **0.93** (n=112) against **0.75** for the milder `disagree_ranked` kind
  (n=51). Held in all three runs, though seed 23 narrowed the gap
  (1.00 / 0.98 / 0.85).
- **`star -> branched` shows up 10x (seed 11) and 3x (seed 23) with the
  PHYSICS side right** — the opposite direction from MM1998. **The real-data
  n=7 pattern does not generalise**; quote it as a striking observation, not
  as the general behaviour.

**A next-actions claim was found WRONG and corrected — do not re-propagate
it.** This file said the L176 false positive arose because "the pre-filter
struck `reptation`, so the plausibly correct class was never on the ballot".
It does not reproduce: on L176 all ten classes are allowed, and `reptation`
was fitted and lost on merit (delta 429.8, rms 0.256 vs star's 0.043). L176 is
a forward-model overlap, not a pre-filter deletion. (The `unopposed_after_
discard` link is still right and still useful — it fires on Pivokonsky E and
MM1998 Ma36k, where a real absence-grounded discard really does coincide with
an uncontested winner.)

### What is genuinely next, in the order I would take it

1. ~~Measure the agreement signal on synthetic data~~ — **DONE TWICE.**
   n=200 (seed 7) 2026-09-09, then **n=600 (60/class, seed 11) 2026-09-10**,
   which supersedes it: 75 curves in the disagree arm instead of 18. Output
   committed as `docs/agreement_measurement_n600_2026-09-10.txt`. **The
   n=200 verdict was WITHDRAWN by the larger run — see the summary at the
   top of this file, and do not quote the n=200 numbers as current.**
2. ~~Third seed~~ — **RUN 2026-09-10, seed 23. VERDICT: AMBIGUOUS by the
   pre-registered rule; SMALL BUT REAL when the three runs are pooled.**
   Output: `docs/agreement_measurement_seed23_2026-09-10.txt`.

   The rule was committed (`9b51840`) BEFORE the numbers existed: CONFIRM at
   margin ≥ +0.015, REFUTE at ≤ +0.005, else AMBIGUOUS. **Seed 23 came in at
   +0.012 — inside the ambiguous band, so no side was picked.** The rule was
   not renegotiated after the fact and must not be.

   | run | n | gate margin | |
   |---|---|---|---|
   | seed 7 | 200 | **+0.006** | 0.3 SE — read at the time as "refuted" |
   | seed 11 | 600 | **+0.019** | 1.8 SE — read at the time as "suggestive" |
   | seed 23 | 600 | **+0.012** | 1.1 SE — AMBIGUOUS |
   | **POOLED** | **1400** | **+0.014** | **2.0 SE** |

   **The honest conclusion, and it is now stable enough to stop re-measuring:**
   the margin was POSITIVE in all three runs and never flipped sign, but no
   single run reaches significance — only the pooled 1231-curve agree arm
   does, at 2.0 SE. So the effect is **consistent and small**. Wording
   everywhere is "comparable, probably a shade better; not a reason to prefer
   it", pinned by `test_the_gate_margin_is_not_overstated`.

   **Still do NOT wire agreement into `identify()`.** A ~1.4-point gain on one
   gate does not justify changing a contract the tests, validation scripts and
   ML baseline all depend on (DECISION 2). A fourth seed is NOT worth running:
   three runs already bracket the effect, and the remaining uncertainty is
   about size, not existence.

   **What the three runs settled that the single runs got wrong:**
   - "More than halves the fitting side" was seed 7's 18-curve artefact.
     Pooled over 169 disagree-arm curves: **0.945 ± 0.007 (agree) vs
     0.438 ± 0.038 (disagree), ratio 0.46.** "Roughly halves" is right.
   - **WHICH brain degrades more on a disagreement is NOT stable** — the
     network fell further at seed 11 (0.413 vs 0.493), the fitter at seed 23
     (0.395 vs 0.421). Never advise trusting one side over the other on a
     split.
   - `agree_degenerate` swings (physics 0.364 / 0.576 / 0.575) on ~5-7% of
     curves. Only its `either right` (0.97-1.00) is quotable.
3. ~~Report both labels as a shortlist~~ — **DONE 2026-09-10.** `pair_note()`
   in `neural_report.py`; the renderer prints `YOUR SHORTLIST: A or B` on any
   disagreement, with the measured worth of the pair (96% agree / 89% disagree
   / 100% degenerate, against 0.875-0.900 for either method alone). Framed as
   a two-item list to settle with outside knowledge, never as a winner with a
   dissent, and never averaged — averaging would destroy the one robust
   result here. 5 tests, one of which **pins the quoted constants against
   `docs/agreement_measurement_2026-09-09.txt`** so user-facing numbers cannot
   drift from the run they came from, and one of which asserts no text ever
   re-acquires the refuted "better than either confidence score" claim.
4. The star caveat and the `unopposed_after_discard` link are both prose in
   `challenge()`. Neither has been read by a rheologist other than the user.

---

**>>> ~~ACTIVE TASK FOR THE LAPTOP~~ — BOOTSTRAP + STEP 4 BOTH DONE 2026-09-09 <<<**

**Laptop bootstrap COMPLETE** (i7-10750H, 32 GB, GTX 1660 Ti). Installed uv
0.12.12 via winget; git + GitHub CLI + VS Code were already present; set the
global git identity; `uv sync` reproduced the env first try (Python 3.12.14,
`torch 2.13.0+cpu` as designed on Windows). **`uv run pytest -m "not slow"` ->
185 passed, 2 skipped in 14:31.** Note the repo lives at
`C:\Users\krish\repos\rheo-fp` on this machine, not the `C:\Users\krish\rheo-fp`
the bootstrap section assumes — harmless, but absolute paths in notes will be
off by one directory here. `originals/` junction NOT set up (optional; nothing
is blocked by it).

**STEP 4 IS NOW CLOSED — see "STEP 4 RESOLVED" below for the numbers.** Both
open questions turned out to have answers that contradicted the guesses in
this file, so read that section rather than the brief that follows it.

The original brief, kept because its items 1-3 are the record:

1. **CANNIBALISATION CHECK — DONE, PASSED.** Matched before/after, identical
   seed 11 and n=20/class, 12 restarts, the OLD forward model reproduced
   exactly (`arm_rouse=False` + 2x prefactor restored via monkeypatch):

   | | OLD star model | NEW star model |
   |---|---|---|
   | overall | 0.845 | **0.855** |
   | `star` self-recovery | 18/20 | **20/20** |
   | all 8 other classes | — | **byte-identical** |

   The star fix cost nothing and gained 2 on star's own recovery; the per-class
   diff is one line. NOTE this n=20/seed-11 run is NOT comparable to the
   published 0.885 (n=30, different seeds) — it is an internal before/after
   only. If you want a headline number, re-run at n=30 with the standard seeds.
2. **Run the full suite** — **DONE on the laptop: 185 passed, 2 skipped, 14:31
   at bootstrap; 194 passed, 2 skipped, 12:15 after the 9 step-4 tests below.**
   `tests/test_star.py` is now **40** (was 31), running in 54 s.
3. **Real data held 6/6** at session end; MM1998 was 5/7 on `identify()`.
   Both reconfirmed on the laptop.
4. ~~Decide about the two misses and `Z_BOUNDS`~~ — **RESOLVED, see below.**
5. ~~Update CLAUDE.md~~ — **DONE.**

### STEP 4 RESOLVED 2026-09-09 (laptop) — both answers contradicted the guess

**(a) `Z_BOUNDS`' floor of 4 is NOT what binds the weakly-entangled arms, and
this file's claim that it makes them "unfittable by construction" was WRONG.**
Measured by refitting at floors 4 / 3 / 2 / 1:

| sample | Z_true | flr=4 | flr=3 | flr=2 | flr=1 |
|---|---|---|---|---|---|
| PI4_Ma17k | 3.40 | 9.12 | 9.12 | 9.12 | 9.12 |
| PI4_Ma11k | 2.20 | 6.66 | 6.66 | 6.66 | 2.45 |

Neither fit ever sits ON the floor, so nothing is being clamped. The real
cause is that **below Z ~ 4 the cost is FLAT in Z**: `Ueff(1)` is 1.9 kBT at
Z = 4 and 1.1 kBT at Z = 2.3, and the activated terminal time sits only
1.1 / 0.75 decades above the arm's own Rouse time `Z^2 tau_e`, so there is no
star-specific shape left to measure. (Ma11k's jump to 2.45 at floor 1 is a
second, equally-good minimum — rms 0.0311 vs 0.0313 — that happens to land
near truth for one of two samples. Luck, not recovery.) **Decision: leave the
floor at 4.** It was asserting exactly the right thing. Pinned by
`test_lowering_the_Z_bounds_floor_does_not_rescue_weakly_entangled_arms`, and
`identify()` returns `star` for both samples anyway — only Z is wrong, and Z
is already non-reportable.

**(b) The two misses are DECISIVE losses, not ties — and the real predictor is
`terminal_reached`, not Z.** Full rankings:

| sample | Z_true | terminal? | winner | star's dAICc | star rms | branched rms |
|---|---|---|---|---|---|---|
| Ma11k | 2.20 | yes | **star** | 0.00 | 0.0307 | 0.0308 (d 4.8) |
| Ma17k | 3.40 | yes | **star** | 0.00 | 0.0242 | 0.0551 (d 202) |
| Ma36k | 7.20 | yes | **star** | 0.00 | 0.0246 | 0.0616 (d 225) |
| Ma44k | 8.80 | yes | **star** | 0.00 | 0.0334 | 0.0735 (d 194) |
| Ma47k | 9.40 | yes | **star** | 0.00 | 0.0407 | 0.0590 (d 93) |
| Ma95k | 19.0 | **no** | branched | **56.6** | 0.0986 | 0.0765 |
| Ma105k | 21.0 | **no** | branched | **102.6** | 0.1282 | 0.0822 |

Not the zimm-style exact tie: star's rms is 20-55% worse on the two misses.
Cause is truncation of the terminal zone — star has 3 parameters and cannot
bend to a cropped terminal, BSW's two free power-law wedges can. Windows are
NOT too narrow (104-211% of the model's own predicted spectrum width at the
true Z); it is specifically the low-frequency asymptote that is missing
(Ma105k's terminal slopes are 1.40 / 0.70 against the 2.0 / 1.0 limit).

**The unified finding, and the useful one: `terminal_reached` predicts the
class's correctness on real data almost perfectly.**

| terminal_reached | correct | wrong |
|---|---|---|
| True (5 curves) | **5/5** | 0 |
| False (5 curves) | 1/5 | **4** |

All four real-data failures across BOTH datasets sit in the False row — the
two MM1998 misses, Santangelo's S490, and (the one that matters most)
Santangelo's **LINEAR control returned as `star`**. So a non-terminal window
makes the class fail in both directions.

**DO NOT turn that into a pre-filter discard.** `if not terminal_reached:
allowed -= {star}` would be the `has_shoulder` fallacy a fourth time — an
unobserved terminal zone is missing evidence, not evidence against a star, and
it would delete the class on exactly the curves where a real star is hardest
to see. It belongs in the REPORT. n=10 curves, so state it as a strong
indication, not a law.

**~~OPEN~~ — DECIDED AND BUILT 2026-09-09 (user: yes, "in rheology friendly
language").** `challenge()` now emits a second `window` item when the winner
is `star` AND `terminal_reached` is False. It explains the physics rather than
the statistics: arm retraction along the tube, retraction time exponential in
arm length so the spectrum is broad and its characteristic shape lives in the
TERMINAL zone, the measured low-frequency slopes quoted against the 2 and 1 of
a melt in flow, the note that what is left (the high-frequency wing) looks much
the same for a broad linear or LCB melt, and the fix a rheologist would
actually use — extend the low-frequency end, or measure warmer and shift by
time-temperature superposition until the G'/G" crossover and the 2/1 onset are
in the window.

**What made the case, and it is worth looking at before ever softening this:**
run `challenge()` on Santangelo L176 (a LINEAR PIB control that comes back as
`star`). The ordinary report shows weight **1.000**, a **0.036-decade** fit
called "a genuinely good fit", and **no alternative inside dAICc 10 at all** —
so the alternatives section is EMPTY. Nothing in the standard output signals
any doubt whatsoever. Two tests pin it, including a counterpart on MM1998
Ma36k asserting the caveat does NOT fire when flow was reached, so it cannot
quietly become unconditional.

**Second thing that run exposed — ADDRESSED 2026-09-09 (office PC), but the
diagnosis above was WRONG and is corrected here.** The claim was that on L176
the pre-filter struck `reptation`, leaving the plausibly correct class off the
ballot. **That does not reproduce.** `signature_features` allows all ten
classes on L176; `reptation` was fitted and lost badly on merit (delta 429.8,
rms 0.256 against star's 0.043). So L176 is a forward-model overlap — the star
model genuinely fits a linear PIB better than the reptation model does — not a
pre-filter deletion, and the fix for it is the `star`+no-terminal-flow caveat
already built, plus the neural disagreement that now also flags it.

The general "discarded class AND uncontested winner" link WAS still worth
building and is built (`unopposed_after_discard` in `challenge()`, 3 tests).
It fires where the reasoning actually applies — Pivokonsky E and MM1998 Ma36k,
where `reptation` really is struck for want of a plateau and the winner really
does run with no alternative inside delta 10 — and deliberately does NOT fire
on discards grounded in a positive observation (`terminal_reached` striking the
network classes), because a settled comparison is not a missing one.

**`Z` IS NOT A REPORTABLE OUTPUT** and that has not changed: still biased
+17-84% on mm1998. The class says "star", never "Z = ...".

The preceding 2026-09-07 session (home PC, RTX A1000) closed the model-only
tier, fixed a latent NaN in the AICc ranking, fixed the `has_shoulder`
pre-filter bug, built the whole explanation layer (`rheofp/report.py`),
validated the temperature stack against TWO real vitrimer datasets for the
first time, and diagnosed why the sticky models fail on real vitrimer data.

**`originals/` note (setup changed 2026-09-09):** `originals/` is now a
**junction** into OneDrive
(`C:\Users\krish\OneDrive - UCB-O365\CUB\ML\rheo_fingerprinting\originals\`,
same path on every Windows PC — one copy, no more per-machine redundancy). Set
up per `.claude-notes/environment.md` on a fresh Windows PC (`mklink /J`, no
admin needed). Files are FLAT in `originals/` now — the nested
`originals/rheo_fingerprinting/` layout is retired. Paper PDFs were renamed to
`firstauthor+year` form and outdated material moved to `originals/archive/`
(2026-09-09; see that dir's README). Still gitignored; derived `data/*.npz`
stay committed so tests don't need it. All three star-polymer papers are
present (`milner_mcleish1997_star.pdf`, `ball_mcleish1989.pdf`,
`pearson_helfand1984.pdf`).

## 0. First, on any PC at session start
- Confirm the env exists: run `uv run pytest -m "not slow"` (should be **180
  passing, 2 skipped**, ~17 min). If uv or the venv is missing, bootstrap per
  `.claude-notes/environment.md` (install uv, then `uv sync`). Python is
  pinned to 3.12 — do not change.
  NOTE: the suite is now noticeably slower than earlier sessions recorded —
  first the 5-param BSW candidate, then the 2026-09-07 `has_shoulder` removal
  put two more k=4 models on every ballot, then 2026-09-09 added `star` as a
  tenth candidate (~3 min -> ~4.5 -> ~10 -> **~17 min**). All are expected
  costs of correctness fixes, not a hang.
  MEASURED per-candidate cost (12 restarts, one 60-pt curve, 2026-09-09), so
  nobody optimises the wrong thing: `branched` 3.36 s, `sticky_reptation`
  2.61, `star` 2.36, `reptation` 1.55, then everything else <= 0.32
  (wormlike_micelle 0.32, cured_elastomer 0.30, sticky_rouse 0.20, zimm 0.16,
  rouse_screened 0.14, critical_gel 0.10). Total ~11 s/curve.
  **`star` is NOT the bottleneck** — the two broad-spectrum mode-ladder models
  above it are, and `branched` sits on every ballot. Note also that `N_S` in
  star.py is a poor dial: dropping it 8x (400 -> 50) saves only ~0.5 s
  (2.35 -> 1.83), because the cost is in `multi_restart_fit`'s restarts, not
  the ladder. If the suite ever needs to be faster, reduce restarts on the
  expensive candidates or mark more tests slow — do not shrink N_S expecting
  a win.
- Skim `.claude-notes/sessions.md` (newest entries) for what changed since.
- **`originals/` is a OneDrive junction now (2026-09-09).** On a Windows PC it
  points at `C:\Users\krish\OneDrive - UCB-O365\CUB\ML\rheo_fingerprinting\originals\`
  — one shared copy, files flat (no nested `rheo_fingerprinting/`). Set it up
  per `.claude-notes/environment.md` if `ls originals/` is empty (`mklink /J`,
  no admin). Still gitignored; derived `data/*.npz` are committed so tests /
  planted-parameter validation run without it — only re-digitizing or a
  `prep_*.py` rerun needs the raw files.
  **Cleaned + renamed 2026-09-09:** paper PDFs now have legible names
  (`milner_mcleish1997_star.pdf`, `tixier2004_pdms_gel.pdf`, `curro_pincus1983.pdf`,
  …); the digitized-data xlsx keep their npz-matching names (`pivo2006.xlsx`,
  `edera2024.xlsx`, `ricarte2023.xlsx`, `likhtman_mcleish2002.xlsx`). Outdated
  material (dropped-XPP papers, notebook-era artifacts, `garbage/`) moved to
  `originals/archive/` with a README explaining each. All three star-polymer
  papers ARE present (earlier note that they were missing was wrong).
  Still absent on this PC: the Darby 2022 digitize inputs (`darby.ods/.xlsx`,
  `darby2022-*.txt`) and `tixier.xlsx` — pre-existing gap, `data/darby2022.npz`
  + `data/tixier2004.npz` are committed so nothing is blocked.

## ACTIVE TASK — star-polymer (Milner-McLeish) class

**UNBLOCKED 2026-09-09. Steps 1 and 2 DONE; step 3 (cannibalisation) is next.**

The user supplied all three papers into `originals/` (renamed 2026-09-09):
`milner_mcleish1997_star.pdf` (Milner-McLeish 1997), `ball_mcleish1989.pdf`
(Ball-McLeish 1989, ref 2), `pearson_helfand1984.pdf` (Pearson-Helfand 1984,
ref 1).

**Built:** `rheofp/models/star.py` (forward + `fit_star` + `STAR_MODELS`
registry, k=3), `tests/test_star.py` (27 tests, ~10 s),
`scripts/validate_star.py`. **NOT wired into `identify()`** - `ALL_MODELS` is
untouched and a test asserts `"star" not in ALL_MODELS`, to be deleted in the
same commit that does step 3.

**Parameters are (G_N, Z, tau_e), k=3** - G_N a pure amplitude, tau_e a pure
time scale, and Z = entanglements per arm the ONLY shape parameter. The number
of arms f does not enter G*(omega) at all; that is a real prediction of the
theory (it reproduces Pearson-Helfand's observed arm-number independence of
viscosity), so the class can say "star" but never "how many arms". Do not add
an `f` parameter to make it look more informative.

**Recovery measured:** planted round-trip exact (rms 0.0000 dec) on four
parameter sets; under 2% log-normal noise Z comes back to within 0.4% at
Z = 8/17/30. Z is genuinely identifiable, not degenerate with the tau_e shift -
the profile cost with G_N and tau_e re-optimised is 5.9e-29 at the true Z = 17
against 1.6e-02 one unit away.

**Two limits found while building, both pinned by tests:**
  - *Low Z + cropped plateau loses Z.* At Z = 8 with the high-frequency end
    cut off, the G'' peak sits at the window edge and 2% noise moves the
    fitted Z by ~20% (the profile minimum is still correct). So Z must not be
    reported from a terminal-only sweep.
  - *Past Z ~ 40 the model predicts TWO G'' maxima, not one.* The eq-22
    crossover separates the Rouse and activated relaxations far enough that
    the loss peak splits - fast peak near the crossover frequency, slow peak
    near 1/tau(1). Numerically converged (identical for n_s 400..64000), so it
    is physics. **Any feature or pre-filter rule that assumes a single loss
    peak will misread a high-Z star**, and spectrum width must not be measured
    from the global G'' peak, which jumps between branches around Z ~ 40.

**Three transcription traps in the 1997 paper, all hit and all now documented
in the module docstrings** - record them so nobody re-derives them the hard way:
  1. *Eq 8 is printed across two lines* so it reads `(s - 2s^3/3)`; it is
     actually `(s^2 - 2s^3/3)`. The wrong version makes the barrier turn over.
  2. *Eq 29's prefactor.* Eq 29 rewrites eq 19's `1/U'eff(s)` division into the
     square-root denominator, pulling the CONSTANT `15Z/4` out of
     `U'eff(s) = (15Z/4) s (1-s)^a` - which is why the denominator holds a bare
     `s^2(1-s)^{2a}`. That `15Z/4` must therefore be divided out of the
     prefactor, giving `A(Z) = sqrt(30) pi^{5/2} Z^{3/2} tau_e / 30`. Leaving
     it in gives `Z^{5/2}`, about a decade too slow, and then **the eq-22
     crossover never fires at all**: the terminal time stays Rouse-like and the
     entire alpha dependence collapses (measured: 0.00 decades between
     alpha = 1 and 4/3, where Ueff(1) alone demands 1.03). Three independent
     checks fix the exponent at 3/2 - the paper's scaling remark under eq 19,
     its statement that the prefactor "depends more weakly on N/Ne than tau_R"
     (= Z^2 tau_e, so anything >= 2 contradicts the text), and assembling
     L^2/Deff from L = R^2/a, a^2 = (4/5)Ne b^2, Deff = 2DR, DR = kT/(N zeta).
     **Ball-McLeish eq 8 is the anchor at the other end**: they write the same
     activated time as `t(s) = t_0 exp[U(s)]` with t_0 stated to be "the Rouse
     time for an entanglement length", i.e. tau_e, so a prefactor far above
     tau_e Z^2 cannot be right.
  3. *Eq 13's `(N/Ne)^2 tau_R` really is Z^4 overall*, not Z^2. Deriving it
     from eq 12 gives `(9pi^3/16)(L/R)^4 tau_R s^4` with `(L/R)^4 = (5Z/4)^2`,
     landing exactly on the printed coefficient. It looks absurd at s = 1
     because it is an `s << s*` asymptote, and it is the ONLY reading under
     which the eq-22 crossover fires (at s ~ 0.18, matching the text's
     "1-s of order (Ne/N)^{1/2}"). The Z^2 reading never hands off.

**Remaining honest gap:** terminal time moves only ~0.16 decades between
alpha = 1 and 4/3 where Ueff(1) implies ~1.03, because at s -> 1 the two eq-22
branches sit within ~0.3 decades for Z ~ 17 and the harmonic blend pulls toward
the faster one. That is the paper's own "simple crossover function", not a
coding error, but it damps the alpha sensitivity the paper emphasises.
Quantify against real star data before making any alpha-dependent claim.

**STEP 3 DONE 2026-09-09 - checked, reported, and WIRED IN.**
`scripts/check_star_cannibalisation.py` (kept, re-runnable) ran the standard
pre-registered protocol: n=30 planted single cropped noisy curves per class,
identical seeds through both banks, 12 restarts.

| class | before | after |
|---|---|---|
| zimm | 23/30 | **21/30** (both to `star`) |
| all 8 others | — | **identical** |
| overall | 244/270 (0.904) | 242/270 (0.896) |
| real data | **6/6** | **6/6** |
| `star` self-recovery | (unreachable) | **29/30** |

**Why the class earns its place:** with the 9-model bank, `branched` (BSW)
absorbed **25/30 planted star melts** silently and confidently, with
sticky_reptation taking 3 more. That is the "good fit of the WRONG class"
failure mode already documented for vitrimers (§2b), now confirmed for a
second molecular architecture and previously invisible. `branched` itself lost
nothing (30/30 both ways), so BSW's real melts are safe - real data confirms
it at 6/6.

**The -2 on zimm was investigated before wiring, and both are EXACT TIES:**
  - curve 14 (4.56 dec window, 79 pts): zimm rms 0.0182, star rms 0.0182,
    **dAICc 0.07**, rouse_screened at 0.11.
  - curve 17 (2.77 dec window, 23 pts): zimm rms 0.0187, star rms 0.0187,
    **dAICc 0.00**, rouse_screened also 0.00 - a three-way tie.
  Identical fit to four decimals at identical k=3, so AICc has no parsimony
  lever and the winner is decided by float noise. By the Burnham-Anderson rule
  the report itself prints (delta < 2 = substantial support), these are ties,
  not losses. **`star` has joined the known Zimm<->Rouse degenerate cluster**
  rather than displacing anything.

**Two hypotheses tested and REJECTED along the way, recorded so they are not
re-tried:**
  1. *"star cannot impersonate zimm"* - FALSE as stated. On clean full-window
     zimm the star model fits badly (median 0.41 dec, 1/6 under FLOOR_CHI2),
     but on the generator's cropped noisy population it fits **11/30 under
     FLOOR_CHI2**, median 0.18 dec. The fit-quality overlap is much larger
     than the classification damage, because ties do not move the winner.
  2. *"cropping causes the overlap"* - FALSE. Correlation between window width
     and star-fit rms is **+0.06** (nil), and the well-fit curves have a
     slightly NARROWER median window (3.52 vs 3.93 dec). The overlap is just
     two broad-spectrum models being similar, not a window artifact.

**STEP 3b DONE 2026-09-09 - `synth.py` now generates `star`.** The reverse
bank/generator gap is closed: `STAR_LOG_GN` / `STAR_Z` /
`STAR_TERMINAL_OFFSET_DECADES` ranges, a `sample_params` branch, a `forward`
branch, `CLASS_REGIME["star"] = "terminal"`, and `star` appended to
`FINE_CLASSES`. `ml/dataset.py` needed NO change - `CLASSES` derives from
`ALL_CLASSES`, and `N_PARAMS = 5` still holds because star is k=3 (branched
remains the widest class).

**Design choice worth understanding before touching the ranges: `tau_e` is
DERIVED, not drawn.** A star's spectrum spans ~23-24 decades from tau_e up to
the terminal tau(1), while a sweep window is ~3-5 decades. An independent draw
would drop the visible slice essentially anywhere, usually somewhere
featureless. Instead the TERMINAL time is placed relative to the window (the
physically meaningful anchor - it is what a real experiment is set up to catch)
and tau_e is back-computed via `_star_terminal_decades(Z)`, since tau(1)/tau_e
is a fixed function of Z alone. Same pattern as `BRANCHED_TAU_C_OFFSET_DECADES`
deriving tau_c from tau_max.

**A bug was caught here and it is the kind that would have been learned as
physics.** The first offset range, (-1, 3), gave **terminal_reached = 0%** over
60 planted curves: the sign convention meant positive offsets pushed the
terminal BELOW the window, so no planted star ever flowed. Training on that
population would have taught the classifier that stars never reach terminal
flow, making `terminal_reached` a spurious star-vs-melt discriminator - the
same shape of defect as the fixed-60-point density bug in §1f. Range is now
(-3, 1), **measured at 51% terminal_reached (n=120)**. Re-measure that fraction
if the range is ever touched.

Verified: 8/8 planted stars self-recover through `identify()`; temperature
stacks shift rigidly and monotonically in log omega with density redrawn per
curve; Z uniform on (5, 55) as declared (median 30.4).

**`star` was deliberately NOT added to `AMBIGUOUS_PAIRS`** (ml/evaluate.py),
despite the tie evidence - reasoning is in a comment there. Short version:
zimm<->rouse and cured<->gel are clean two-way nestings differing by one
parameter; the star/zimm overlap is three-way (rouse_screened tied alongside),
window-dependent, and cost only 2/30. Collapsing star into zimm for
`merged_pair_accuracy` would HIDE genuine star-vs-linear-melt errors, which is
the distinction the class exists to make. Revisit once a trained checkpoint
shows where the network's star errors actually land.

## >>> ~~ACTIVE TASK FOR THE OFFICE PC~~ — RETRAIN DONE 2026-09-09 <<<

**COMPLETE.** Retrained on the office PC (RTX A1000) the same day it was set.
Results below; CLAUDE.md's "Current state" now carries them as 10-class numbers.

| | 9-class (old) | **10-class (new)** |
|---|---|---|
| accuracy | 0.917 | **0.923** |
| merged-pair | 0.963 | **0.968** |
| regime | 0.999 | **0.999** |
| physics baseline | ~0.82 standalone (n=90) | **0.907, SAME split** (n=150) |
| margin | +0.10 (not comparable) | **+0.016** |
| real data (neural) | 6/6 | **6/6**, raw == resampled |

Accuracy went UP despite a harder 10-class problem. Answers to the four things
this retrain was set up to check:
1. **No collision** - `star` did not depress anything.
2. **`star` = 0.996 (239/240)**, its one error to `wormlike_micelle`. NEITHER
   hypothesis held: not zimm/rouse (so the AICc three-way tie does not
   reproduce in the network), and not `branched` (so the two brains do NOT
   disagree about what absorbs stars). **`star` stays OUT of
   `AMBIGUOUS_PAIRS`** - decision recorded in the comment in `ml/evaluate.py`.
   Asymmetry worth keeping: 2 zimm -> star, but 0 star -> zimm.
3. **`rouse_screened` 0.737 on seed 1** - no collapse this time; merged-pair
   0.968 confirms nothing broke.
4. **Baseline paired on the same split - §1h is CLOSED.** `skipped` = 0, so the
   bank genuinely covers all ten generated classes.
   **Read the +0.016 correctly:** the baseline rose ~0.82 -> 0.907 because the
   BANK was fixed (wormlike_micelle, then star), not because the network got
   worse. The network is now measured against a much stronger physics side.
   The two still are not strictly comparable - baseline sees ONE curve.

Unchanged and still true: 58% of all error is Zimm<->Rouse; cured/gel is zero.

**Environment note that cost time here - read before debugging a "stuck" run.**
On Windows `torch` resolves to **`2.13.0+cpu`** from the shared lock (CUDA
extras carry `sys_platform == 'linux'` markers), so `torch.cuda.is_available()`
is False **even on the A1000 box** and `nvidia-smi` shows no process during
training. That is INTENDED - see environment.md, "must not be fixed with a
per-PC torch variant". Measured this run: **7.4-10.9 s/epoch on CPU**, matching
the ~9 s/epoch already recorded. The genuine long pole is the **AICc baseline
after training** (150 stacks x 10 SciPy candidates, single-threaded), not the
55 epochs. Also: the suite ran in **5:07 here**, not the ~17 min §0 predicts -
that estimate is home-PC-specific.

### original brief (kept for reference)

**RETRAIN THE CLASSIFIER. The shipped checkpoint is STALE.** The training
distribution now has a tenth class (`star`), so every accuracy number currently
in this file and in CLAUDE.md was measured on a 9-class population and does not
describe the current code. `checkpoints/` is gitignored and reproducible.

    uv run python scripts/train_classifier.py -n 16000 --epochs 55

(~12 min on a GTX 1660 Ti; the home PC's RTX A1000 did the last one. Seed 1 was
used for the runs quoted below.)

**What to check, and what would be a red flag:**
1. **Overall accuracy vs the 0.917 from the 9-class run.** Adding a tenth class
   makes the problem strictly harder, so a small drop is expected and fine. A
   LARGE drop means star is colliding with something - look at
   `pair_confusions`.
2. **Where star's errors land.** The AICc side ties star against
   zimm/rouse_screened (see step 3 above). If the network's star confusion is
   also mostly zimm/rouse, that CONFIRMS a genuine three-way degeneracy and
   `AMBIGUOUS_PAIRS` should probably gain star at that point. If star instead
   collides with `branched`, that is the more interesting result - it would
   mean the two brains disagree about which class absorbs stars, since on the
   AICc side `branched` was the one absorbing them 25/30 before star existed.
3. **`rouse_screened` per-class accuracy is known seed-unstable** (0.20 on
   seed 0, 0.71 on seed 1) - check `merged_pair_accuracy` (~0.96 historically)
   before concluding anything is broken.
4. **Re-measure the physics baseline in the SAME run** - §1h left that pairing
   outstanding, and the standalone ~0.82 (n=90) is not from the same split as
   the 0.917. This retrain is the natural chance to fix that.
5. Then update the "Current state" paragraph in CLAUDE.md and §1e/§1g here with
   the new numbers, and say plainly that they are 10-class numbers.

**Real-data eval also wants a rerun after the retrain**
(`scripts/eval_real_data.py`) - it uses the checkpoint, and the 6/6 currently
quoted for the NEURAL head is a 9-class result. The AICc side's 6/6 was
re-confirmed with the 10-model bank on 2026-09-09 and is current.

**NEXT after that - step 4, real-data validation of the star class.** BLOCKED
on the user supplying star melt data; sources already identified below
(Roovers' star polybutadienes, the four-arm polyisoprene MM validation set,
Santangelo & Roland star PIB - the last has a free PDF at
http://polymerphysics.net/pdf/Macromolecules_32_1972_99.pdf).
  - ~~**`has_shoulder` wording overstates its case**~~ — **FIXED 2026-09-09
    (user decision: state it neutrally, drop the causal claim).**
    report.py:240 used to read "a sticker / bond-exchange shoulder,
    characteristic of a reversibly associating network". Measured on 60
    planted curves per class, a second G" maximum fires on 92% of stars (the
    Z >~ 35 two-peak split), but also **72% of `branched` and 75% of
    `reptation`**, which have no exchangeable bonds at all — and only **62% of
    `sticky_rouse`**, the class it was meant to mark. So it pointed AWAY from
    the sticker classes at least as often as toward them, and the wording was
    a causal claim the evidence did not support. It now reports the
    observation and names the alternatives (broad-spectrum melts, star
    polymers) without attributing it. The `not has_shoulder` branches were
    already correctly hedged and kept, except report.py:503's "its signature
    is a second G\" maximum", softened to "it would show as ... though that
    alone is not specific to stickers".
    **General lesson, third instance of the same shape:** `has_shoulder` was
    already the subject of the 2026-09-07 pre-filter fix (missing-evidence
    reasoning) and is now also a reporting overstatement. The feature itself is
    weak; the discard is gone and the prose is neutral, but if it ever gets
    used as evidence again, measure its per-class rates FIRST.

### 2b-bis. `has_shoulder` measured properly — DO NOT RE-INVESTIGATE 2026-09-09
Investigated at the user's request, then **user decided: LEAVE THE DETECTOR
ALONE.** No code changed in `signature_features`. Recorded so the ground is not
covered twice — the numbers below are the whole answer.

**The detector fires on NOISE, not on spectrum shape.** Same planted
population, noise on vs off (n=60/class):

| class | noisy (2%) | clean |
|---|---|---|
| zimm | 65% | **0%** |
| rouse_screened | 67% | **0%** |
| reptation | 63% | **0%** |
| sticky_rouse | 67% | **3%** |
| sticky_reptation | 92% | **10%** |
| cured_elastomer | 85% | **0%** |
| critical_gel | 72% | **0%** |
| wormlike_micelle | 65% | **0%** |
| branched | 68% | **0%** |
| star | 95% | **15%** |

At 2% scatter every class sits at 63-95%, i.e. the feature carries no class
information at all. `cured_elastomer` - a flat plateau with NO second G" peak
by construction - trips it 85% of the time. Cause: `has_shoulder` counts raw
sign changes in G" with no smoothing and no prominence threshold
(identify.py ~line 153), and 2% multiplicative scatter (~0.0086 decades)
manufactures local maxima freely.

**But the detector's LOGIC is sound - the shoulder is genuinely absent.** On
clean curves a dip exists in only **3% of `sticky_rouse` and 10% of
`sticky_reptation`**; when one IS present it is unmistakable (0.5-0.73 decades
deep) and the detector finds it. So the generator's random window cropping puts
the bond-exchange time outside the sweep ~90% of the time. Two separate facts,
easy to conflate: a noise-blind detector AND an almost-always-absent signal.

**A prominence threshold was swept and does NOT rescue it** (require the
interior dip to exceed N decades):

| threshold | sticker mean | others mean | why unusable |
|---|---|---|---|
| 0.02 | 72% | 61% | `cured_elastomer` 83% > `sticky_rouse` 57% |
| 0.05 | 31% | 24% | `cured_elastomer` 48% ties `sticky_reptation` |
| 0.10 | 3% | 0% | zero false positives, but feature is dead |
| 0.20 | 2% | 0% | dead |

There is no operating point where the sticker classes separate, because there
is barely any true signal in the population to recover. 0.10 dec would give a
rare-but-trustworthy feature (0% false positives on all seven non-sticker
classes); the user judged that not worth changing `signature_features`, which
feeds the pre-filter and every identify() call.

**This vindicates the 2026-09-07 has_shoulder fix on stronger grounds than were
available then.** The old discard deleted both vitrimer classes whenever no
shoulder was visible — and the shoulder is invisible ~90% of the time even for
genuine vitrimers on CLEAN data. The rule was not merely unsound reasoning; it
would have fired against the correct class in the large majority of cases.

### original brief (kept for reference)

**~~BLOCKED on the user supplying the paper.~~** User asked
"am I forgetting common [molecular] models?" (explicitly NOT macroscopic
material categories — that filter was established 2026-09-04). Audited the
existing taxonomy plus `docs/rheology_models.md` (which is mostly macroscopic
categories, rightly out of scope) and found **star polymers are missing
entirely and were not even on the wishlist.**

**Why this matters, not just "another class":** `branched` (the 5-param BSW
empirical spectrum) will silently absorb a star melt today. That is the same
"good fit of the wrong class" failure mode just found and reported for
vitrimers this session (see §2b) — but for a different molecular architecture,
undetected, with no real data ever tested. Linear-vs-branched-vs-star is
exactly the kind of molecular distinction this product exists to make.

**Theory: Milner-McLeish (1997), Macromolecules 30, 2159.** Parameter-free
given `tau_e`/`G_N` (already available from the Likhtman-McLeish work in
`tube.py`). Arm retraction against an entropic potential U(x), exponential in
retraction depth x (hence a very broad spectrum); dynamic dilution Phi(t)^alpha
as outer arm segments relax and act as solvent for the unrelaxed inner ones;
G*(omega) assembled by integrating over x in [0,1]. Real finding worth keeping
even before building: **the number of arms f barely affects LVE** — this
model can identify "star", not "how many arms", and that limit should be
stated in the eventual class docstring, not discovered later.

**STEP 1 (blocking everything else): get the actual 1997 paper.** I could not
retrieve it — it is paywalled, and the open reviews I could reach (checked
PMC6572337) analyse Milner-McLeish rather than derive its equations.
Transcribing tube theory from memory is exactly what this project's
validation-first rule exists to prevent. **Ask the user for the PDF into
`originals/` before writing any forward-model code.**

**STEP 2, once the paper is in hand — build in the established order:**
forward physics (planted-parameter round-trip, no data needed) → inverse
recovery → cannibalisation check against `branched` (same protocol as BSW/WLM/
has_shoulder: per-class hit counts before/after, **real data must stay 6/6**,
report the numbers before the class is wired into `identify()`'s bank) →
real-data validation.

**Real data is abundant, unlike the vitrimer case** — star melts are a classic
tube-theory model system:
- Four-arm polyisoprene stars, arm Mw 17k-105k (the original MM validation set,
  "excellent" agreement quoted across all arm lengths).
- Roovers' star polybutadienes (the canonical dataset).
- Santangelo & Roland, star polyisobutylene — free PDF at
  http://polymerphysics.net/pdf/Macromolecules_32_1972_99.pdf (my fetcher hit
  an outdated-SSL error on this host; fetch it in a browser instead).
- Several papers show linear AND star analogues side by side — ideal for a
  discriminating pair, since it directly tests what `branched` currently means.

**Two risks flagged in advance, so they are not discovered mid-build:**
1. **May not beat BSW on AICc even with a correct implementation** — a star's
   spectrum is broad, same shape family as BSW's empirical wedges. Mitigating
   factor: MM is ~2 effective free parameters (Z_arm + a modulus scale) against
   BSW's 5, so parsimony should favour a correct star identification even at
   comparable fit quality. This is exactly the kind of claim the
   cannibalisation check exists to verify rather than assume.
2. **Reuse candidates, don't rebuild:** `rheofp.models.maxwell.maxwell_spectrum`
   for the final mode summation, `rheofp.fitting.optimize.multi_restart_fit`
   for fitting, and the `(forward, p0, bounds, k)` registry pattern already
   used throughout `maxwell.py`/`network.py`/`solutions.py`. New code is
   realistically ~100-150 lines (comparable to `network.py`'s 178) — this is
   an addition to the existing architecture, not a new subsystem.

## ~~ACTIVE TASK~~ — explanation layer BUILT 2026-09-07

`rheofp/report.py` + `scripts/explain.py` + `tests/test_report.py` (13 tests).
All three design decisions honoured: a NEW module reading identify()'s existing
output (its contract untouched); ranking by delta AICc with absolute fit
quality alongside; physics explainer only, neural column still to come.
Verified against both worked examples — Tixier gel reproduces delta 2.4 with
`cured_elastomer` fitting better (0.0107 vs 0.0108) and the report says
"nothing in your measurement contradicts that"; Pivokonsky E reproduces
delta 79.3 and reads decisive.

**Unplanned win: the least-bad-winner flag catches the two-plateau blend** —
the one out-of-scope probe BOTH detectors in §1j failed on. It does not
identify the blend (nothing in the bank can); it refuses to pretend the winner
is trustworthy, printing "NOTHING IN THE BANK FITS THIS DATA WELL" where the
Akaike weight alone said 0.9+. That is the OOD problem answered from the
reporting side rather than the detection side, exactly as the design argued.

Correction worth carrying: the notes' "weights collapse to 1.000/0.000" is a
tendency, not a law — the Tixier gel's winner sits at 0.766. Another reason
the report leans on delta AICc and absolute residuals instead.

**Design change, user instruction 2026-09-07 (implemented):** the challenge is
**unconditional**. The user's words: *"just give the warning for all matches by
default - good, bad, false positive whatever... even then - give the message:
'dont think its a melt? this maybe why'"*. Their reasoning is better than what
was first built: a caveat that fires only on a tripped test teaches the reader
that silence means certainty, and silence here means nothing of the kind. The
preceding exchange established why - the misfit flag catches out-of-taxonomy
material that fits BADLY, but the classifier's dominant error mode is a GOOD
fit of the WRONG class (Zimm<->Rouse, elastomer<->gel), which no signal flags.
`challenge()` therefore always emits: absolute fit (stated in both directions),
named live alternatives within delta 10 with their own numbers, unfitted
classes and how to lift them, the standing out-of-taxonomy limit, and any
window limits (no terminal flow / no shoulder). Rendered as "DON'T THINK IT'S
X? THIS MAY BE WHY", with a footer explaining why it is always present so its
appearance is not misread as a warning.

**~~Still to do here~~ — BUILT 2026-09-09 (office PC).** The neural head is a
second column in `rheofp/neural_report.py`, with the AGREEMENT between the two
brains reported as the confidence signal neither self-confidence can provide.
See the top of this file and the office-PC entry in `sessions.md`.

### original brief (kept for reference)

**~~STEP 1: fix `has_shoulder`~~ — DONE 2026-09-07.** The user considered
cutting the vitrimer classes from scope instead and decided to keep them and fix
the rule. The discard is removed; both sticker classes are always on the ballot
and AICc adjudicates them. Pre-registered before/after, planted CROPPED NOISY
curves (n=30/class, identical seeds — note full-window noiseless curves
overstated the strike rate at 39/40, the realistic path was 11/30):

| class | before | after |
|---|---|---|
| sticky_rouse | 18/30 (struck 11/30) | **29/30** (struck 0/30) |
| sticky_reptation | 26/30 (struck 2/30) | **28/30** (struck 0/30) |
| all 7 others | — | **byte-identical** |
| overall | 0.837 | **0.885** |
| real data | 6/6 | **6/6** |

No cannibalisation: the diff of the per-class table is exactly two lines. The
flagship error — a vitrimer reported as a PERMANENT network — went **0/120**.
Cost: two extra candidates fit per call, `identify()` ~1.9 s/curve, suite
~4.5 min. Two regression tests added. **A merge of sticky_rouse +
sticky_reptation into one "vitrimer" class was considered and REJECTED by the
user** — entangled-vs-unentangled is real recoverable information, unlike the
genuinely degenerate Zimm/Rouse pair.

**STEP 2 — build the "why did you say that?" layer**

**Nothing below has been implemented.** The three design decisions are APPROVED
by the user (2026-09-04); they are written down here to be built on a better
machine. Read §1j and §1k first for the evidence behind them.

**The user's framing, which is the whole point:** it is acceptable for the model
to be confidently wrong, PROVIDED the user can see the reasoning and argue with
it. Their words: *"if a person uploads a dataset for material type X, but my
model says it's Y confidently, I would want an error message like 'don't think
your model is Y? It may be X or Z or W. Here are the reasons why'."* This is
worth more than an out-of-distribution detector, and it is achievable — §1j
shows the detector is not.

Under the molecular scope (CLAUDE.md "SCOPE"), this is not a nicety. A user can
referee "is my sample a foam?" by looking at it. They cannot referee
"elastomer or vitrimer?" — so the reported evidence has to do that job.

### DECISION 1 — pre-filter: report now, measure before changing
- **DO NOW (no behaviour change):** the report must state which candidates were
  struck off by the pre-filter, which rule struck them, and what measurement
  would put them back. e.g. *"sticky_rouse and sticky_reptation were not
  considered, because no second G″ peak appears in your window. If you believe
  this material has exchangeable bonds, measure at higher temperature or extend
  to lower frequency."* This alone converts §1k's silent deletion into an
  actionable instruction, at zero risk.
- **DO NOT yet remove the `has_shoulder` discard.** It is unsound reasoning
  (§1k) but the sticky models carry k=4 and may cannibalise simpler classes if
  freed — the exact risk BSW and WLM were both checked against. Run the same
  before/after protocol (planted curves, per-class hit counts, real data must
  stay 6/6) and put the numbers to the user BEFORE changing classifier
  behaviour.

### DECISION 2 — a new function reading identify()'s output; do NOT change identify()
- `identify()` is called by tests, the validation scripts, and the ML baseline.
  Changing its return contract touches all of them for a feature most callers do
  not want. Build `explain(result, ...)` (new module, e.g. `rheofp/report.py`)
  plus a thin `scripts/explain.py` wrapper over it.
- **Everything needed is already returned and currently thrown away**:
  `ranking` (per candidate: name, k, aicc, delta, weight, rms_log, params),
  `allowed`, `features`, `abstain`/`abstain_reason`, and `stack` from
  `identify_stack`. The pre-filter rules are simple and all their inputs are in
  `features`, so `explain()` can re-derive which rule struck which candidate
  without touching `signature_features`.
- **Report contents (worked out 2026-09-04):**
  1. Winner + its ABSOLUTE fit quality in decades, not only its weight.
  2. Ranked alternatives by **ΔAICc, not Akaike weight** — the weights collapse
     to 1.000/0.000 and hide live alternatives. Rule of thumb to print
     (Burnham & Anderson): Δ<2 substantial support, 4–7 considerably less,
     >10 essentially none.
  3. Each alternative's own fit quality. This is what exposes a "least-bad"
     winner: on an out-of-scope curve the winner fit 0.0819 dec and the whole
     rest of the field sat at 0.129–0.50, i.e. nothing fitted well — invisible
     behind a weight of 1.000.
  4. The measured evidence (`features`) in physical words.
  5. Pre-filter discards + reason + how to lift them (Decision 1).
  6. Known-degenerate pairs — `AMBIGUOUS_PAIRS` in `ml/evaluate.py` already
     names Zimm↔Rouse and cured_elastomer↔critical_gel.
  7. "What would settle it": for melt-vs-network, a second temperature —
     `identify_stack` already implements the resolver.
  8. **"Why not X?" contest mode** — the strongest feature. Given a class the
     user believes in, fit it, report its ΔAICc, its fit quality, and the
     specific measured feature that contradicts it.
- **Two real worked examples to test against** (measured 2026-09-04):
  - *Tixier gel* — `critical_gel` ΔAICc 0.0 fit 0.0108; `cured_elastomer`
    ΔAICc 2.4 fit **0.0107**. The runner-up fits BETTER and lost only on
    parsimony. Correct report: "if you know this is a cured elastomer, nothing
    in your measurement contradicts that."
  - *Pivokonsky E* — `branched` ΔAICc 0.0 fit 0.0624; next `zimm` at 79.4.
    Decisive, and the report should read as decisive.

### DECISION 3 — physics explainer first, neural head as a second column later
- The AICc side owns the REASONS (physical statements: "G′ low-frequency slope
  0.99", "loss tangent flat to 0.06 decades"). The neural head owns the better
  RANKING (0.92/0.07 across classes vs AICc's 1.000/0.000) and the better
  accuracy (~0.92 vs ~0.82). Build the physics one first; leave a column for the
  network.
- Needs a trained checkpoint, so do it on a GPU machine. `checkpoints/` is
  gitignored and reproducible: `python scripts/train_classifier.py -n 16000
  --epochs 55` (~12 min on GTX 1660 Ti).
- **Design note worth keeping:** the two brains are mathematically independent,
  so **whether they AGREE is a better confidence signal than either one's own
  certainty.** Both self-confidences are known unreliable on unfamiliar material
  — the network's abstention is trained only against its own synthetic errors
  (§3), and AICc's weight hits 1.000 even when the true class is absent from the
  bank entirely (§1h). Agreement between two independent methods is not subject
  to either failure. Nothing currently looks at this.

## 1. ~~ACTIVE TASK~~ — elastomer / rubber + critical-gel module — **COMPLETE 2026-08-31**
Built, wired into `identify()`, and validated against real data (Darby 2022
cured silicones, Tixier 2004 critical gel, Likhtman-McLeish melt
counterexample), and the stack-level resolver is built too (§1c). 59 tests
pass. Files: `rheofp/models/network.py`,
`scripts/{prep_darby,prep_tixier,validate_network,validate_stack}.py`,
`data/{darby2022,tixier2004}.npz`, `tests/{test_network,test_stack}.py`.
**ALL THREE CLAUDE.md GOALS ARE NOW COMPLETE** (repo restructure, synthetic
generator, ML training pipeline). See §1e below and "What's genuinely open"
at the bottom of this file for what remains.

Full design + literature basis: `docs/elastomer_litreview.md` (read it first;
sections 0, 5, 6 are the operative ones). Summary of decisions already locked:
- Forward model = fractional Kelvin-Voigt (frequency-domain Chasset-Thirion):
  G'(w) = G_inf + c*w^m*cos(pi*m/2), G''(w) = c*w^m*sin(pi*m/2). 3 params.
- Critical gel is a SEPARATE fine class (user decision), same functional family
  with G_inf ~ 0, m ~ 0.5-0.75; label distinctly, don't merge.
- No affine/phantom split; report G_inf model-agnostically (like the XPP scope
  call). SAOS-only input; melt-vs-rubber ambiguity handled by abstention unless
  a temperature stack is present (`io/data.py` already carries T_K per sample).

### Real-data validation — DONE 2026-08-31
Both curves digitized by the user, converted by dedicated prep scripts,
outputs committed to `data/` so validation runs without `originals/`:
  (a) **Darby 2022 Fig. 1a** -> `originals/darby.ods` ->
      `scripts/prep_darby.py` (kPa->Pa there) -> `data/darby2022.npz`.
      pandas can't read .ods without `odfpy` (not in the locked env) — the
      script reads `originals/darby.xlsx`; regenerate with
      `libreoffice --headless --convert-to xlsx originals/darby.ods` on
      another PC. Martin 2008 was the old plan — dropped, no SAOS figure.
  (b) **Tixier 2004 Fig. 2/4** -> `originals/tixier.xlsx` (Pa already) ->
      `scripts/prep_tixier.py` -> `data/tixier2004.npz`. u = 0.762 recovered.

Non-blocking optional extras (never done — do only if asked):
  - Martin 2008 Table 1 single-point check (fitted G_inf vs Ge, tan d) per
    resol ratio — values transcribed in litreview section 3.
  - Villar 2001 Table 2 route-(a) self-consistency.
  - Darby Fig. S1 stiff ratios (SY 10:1 / 20:1) for a wider G_inf range.

### 1c. Stack-level abstention resolver — DONE 2026-08-31
Built in `fitting/identify.py`; `scripts/validate_stack.py`,
`tests/test_stack.py` (13 tests). Suite 46 -> 59 passing.
- `resolve_melt_vs_network(stack)` — two pieces of evidence, in priority
  order: (1) terminal relaxation observed at ANY temperature -> melt outright
  (a permanent network cannot flow at any T); (2) else how far the spectrum
  SHIFTS along omega across the stack. Verdict "melt"/"network"/"ambiguous".
- `shift_factor(ref, cur)` — horizontal log10 a_T by aligning **tan(delta)**
  curves, NOT the moduli. Key choice: tan(delta) is a modulus ratio so the
  vertical shift factor b_T cancels exactly — no simultaneous b_T fit, and no
  assumption about how the plateau scales with T. Coarse scan + parabolic
  refine (the objective is smooth 1-D; a gradient fit stalls on a flat
  tan(delta)).
- `identify_stack(stack)` — the architecture's native set-based input. Runs
  the single-curve pipeline on the COLDEST curve (hardest case: its window is
  likeliest to hide a melt's terminal relaxation), then lets the resolver
  lift the abstention or overturn a network call. It only ever removes
  unjustified confidence or adds justified confidence — never invents any.
- **SHIFT_DECADES_MIN = 0.5** — this is the "T-shift coverage" threshold the
  original spec asked for, now actually grounded: a melt with Ea ~ 60 kJ/mol
  over a 40 K spread shifts ~1.4 decades; a network shifts 0.00. 0.5 sits
  clear of both.
- Adversarial case proven: an entangled melt with a broad mode ladder and the
  terminal region below the window is confidently misclassified as
  `critical_gel` by a single curve (abstain=False!). The stack sees 1.89
  decades of shift and forces the abstention. That case is the reason this
  exists — see `test_stack_overturns_a_network_call_on_a_disguised_melt`.
- Honest limit, tested: with Ea = 0 a melt does not move, so the resolver
  calls it a network. It reports what is observable, not what is true.
- **Gap found later by the generator and fixed**: a critical gel's tan(delta)
  is frequency-INDEPENDENT by construction, so the alignment objective is FLAT
  — every shift fits equally well and the old code returned the grid's
  arbitrary minimum as if it were a measurement. Added
  `MIN_TAN_DELTA_STRUCTURE = 0.15`: `shift_factor` now returns NaN when
  tan(delta) has no structure, and the resolver reports "ambiguous — loss
  tangent is frequency-independent". Worth remembering: a flat objective is
  degeneracy, not a zero answer.

### 1d. Synthetic data generator — DONE 2026-08-31 (CLAUDE.md goal 2)
`rheofp/data/synth.py` + `scripts/generate_dataset.py` + `tests/test_synth.py`
(25 tests). Suite 59 -> 84 passing.
- Samples labelled stacks from ALL 9 classes (7 fine + wormlike_micelle and
  branched as model-only). Labels are PLANTED (from the generating model),
  never fitted.
- Parameter ranges are read from `solutions.MODELS` bounds where they exist,
  so the generated population and the fitters' search space cannot drift
  apart — there is a test asserting this.
- **Stacks are physically coherent, not independent draws**: a T-stack
  Arrhenius-shifts ONE parameter set (networks get Ea = 0 and instead scale
  moduli with absolute T, i.e. entropic elasticity). Independent per-curve
  draws would teach the classifier a correlation no real material has.
- Random window CROPPING (0-2.5 decades) is deliberate: it is what teaches
  abstention, by hiding the terminal region the way a real instrument does.
- ~2% log-normal noise, matching digitizing scatter on real figures.
- Output = canonical npz layout, so generated data loads with the same loader
  as the digitized literature data; carries label/regime/stack_id/n_curves.
- xlsx export exists but is a capped human backdoor only (200 samples), per
  CLAUDE.md. Never in an automated path, do not commit its output.
- Throughput ~1200 examples/s. Identifier round-trip on single cropped noisy
  curves ~82-85%; the confusions are Zimm<->Rouse (differ only in exponent),
  reptation->Zimm when the crop hides the plateau, and gel<->elastomer (nested
  models). Those are REAL ambiguity for the ML model to learn, not defects.

### Build steps (Claude, once asked / once xlsx exists)
Planted-parameter tests need NO data, so building can start before digitizing:
1. DONE (2026-08-31). `rheofp/models/network.py` — new module (the fractional
   springpot family has no mode ladder, so it did not belong in `maxwell.py`).
   `chasset_thirion_spectrum` (3-param) + `critical_gel_spectrum` (2-param bare
   springpot) + `fit_*` via `multi_restart_fit`. Critical gel is kept a genuine
   2-parameter model, not a 3-param fit with G_inf driven small — that is what
   lets AICc adjudicate the two classes on parameter count.
2. DONE (2026-08-31). `tests/test_network.py` +
   `scripts/validate_network.py` (plt.show only). Suite 27 -> 59 passing.
3. DONE (2026-08-31). Both classes wired into `fitting/identify.py` via
   `NETWORK_MODELS`, merged into a new `ALL_MODELS` bank. Pre-filter stays
   permissive: the ONLY hard discard for the network classes is
   `terminal_reached` (a permanent network cannot flow). Abstention decision —
   see "Abstention rule as built" below.
4. DONE (2026-08-31).
   - Melt counterexample: Likhtman-McLeish PS 6 at four low-freq truncations,
     reptation wins every time, network classes never steal it. DONE.
   - Darby 2022 real cured-elastomer: `data/darby2022.npz`, fit with
     `fit_chasset_thirion` -> G_inf recovered to +1%/+4%/+28% (SY/Solaris/EF)
     vs Darby Table 1 (620/120/27 kPa @ 0.01 rad/s); residual < 0.003 dec;
     m ~ 0.23-0.30; identify() -> cured_elastomer + abstain for all 3.
     In validate_network.py + tests (3 parametrized). DONE.
     Note EF is +28% off — the softest, ~55%-sol-fraction kit, digitized off
     the noisiest curve, and Table 1 has +/-30% error there. Acceptable; test
     tol is 35%.
   - Tixier 2004 real critical gel: `data/tixier2004.npz` (moduli in Pa
     already), `scripts/prep_tixier.py`. `fit_critical_gel` -> u = 0.762
     (Tixier Table II range 0.69-0.75), residual < 0.011 dec. identify() ->
     critical_gel, but ΔAICc only ~2.4 / weight 0.77 over cured_elastomer:
     the models are nested (gel = cured, G_inf->0), so when G_inf ~ 0 only
     the param count separates them and ΔAICc ~ 2 is the expected 1-param
     penalty. Correct call, thin margin. Possible future tiebreaker: use the
     frequency-flat-tan(delta) feature (currently computed, unused). Ask
     user first. DONE.
   - Optional anytime: Villar 2001 Table 2 route-(a); Martin 2008 Table 1/2.

### Abstention rule as built (2026-08-31) — revisit if you disagree
The threshold was specified as "decades of flatness / T-shift coverage". Built
deliberately WITHOUT a flatness threshold: from one curve, a melt's absent
terminal relaxation is missing evidence, not evidence of absence, so no number
of flat decades ever proves a network. `melt_rubber_ambiguous()` therefore
abstains whenever best == cured_elastomer AND not terminal_reached AND
n_temperatures < MIN_STACK_TEMPERATURES (= 2). Flat decades are still measured
and reported (`features["flat_decades_lo"]`) as confidence, not as a gate.
`identify(..., n_temperatures=N)` lifts the abstention. Critical gel never
abstains — it has no plateau to confuse with a melt.
Superseded 2026-08-31 for stacks: `identify_stack()` now runs the real per-T
check (see 1c above). `identify()` on a single curve still behaves exactly as
described here — n_temperatures is only a hint there.

## 2. Standing background facts (not blocking)
- XPP/pom-pom: LVE-validated but deliberately NOT a classifier class. Done.
- `docs/rheology_models.md` is a wishlist (elastomers is the first item being
  pulled off it). Other domains there (biofluids, cement, etc.) are future,
  not current scope.
- Commit/push policy: user commits at end of a working session ("when I'm done
  for the day"), not continuously. Ask/confirm before end-of-day sync.


### 1e. ML training pipeline — DONE 2026-09-01 (CLAUDE.md goal 3)
`rheofp/ml/{dataset,model,train,evaluate}.py`, `scripts/train_classifier.py`,
`tests/test_ml.py` (18 tests). Suite 84 -> 102 passing.
- **torch added to the locked env** (2.13.0+cu130). Re-locked properly; numpy
  stayed 2.5.1. See environment.md and the workflow.md preference note — the
  user explicitly wants deps added when needed, not avoided.
- `RheoNet` = conv curve-encoder -> masked attention pool -> two heads, exactly
  the frozen architecture. 246k params. Conv over log-frequency because the
  discriminating features are LOCAL SHAPE (terminal slope, plateau, wing) and
  the generator crops windows to random positions. Attention pool (not mean)
  because a stack's information often sits in ONE curve — the hottest, where
  terminal relaxation finally enters the window.
- Abstention is a **learned logit**, trained against whether the classifier
  actually got that example wrong (detached, so it does not steer the
  classifier). It learns to predict its own failures.
- Leakage guards, both tested: splits are **by stack** (temperature twins must
  never straddle train/test), and normalisation stats come from the **training
  split only**.
- Padding cannot influence output — tested by poisoning padded slots with 1e3
  and asserting identical logits.

**Results (16k examples, 55 epochs, seed 1, GTX 1660 Ti, ~12 min):**
  accuracy 0.932 vs AICc physics baseline 0.680 (+0.252)
  regime accuracy 0.999; abstain 20% -> 0.979, 30% -> 0.992
  stacks beat single curves (0.924 at N=1 -> 0.951 at N=2)
  cured_elastomer and critical_gel are PERFECT and never confused with a melt
  58% of ALL errors are Zimm<->Rouse, which differ only in mode-spacing
  exponent 1.8 vs 2.0 — measured log-slopes 1.05+/-0.70 vs 1.08+/-0.69, i.e.
  near-total overlap. That is physics, not a defect; `evaluate.py` now reports
  `merged_pair_accuracy` and `pair_confusions` so it cannot be misread.

**Two real bugs the tests caught — do not reintroduce:**
1. Head 2 was silently UNTRAINED: `param_targets` was always None so
   `head_params` got zero gradient. Now wired via masked padded targets (a
   2-param gel must not train the 2 unused slots). Verified: MAE 9.96 vs 19.0
   for predicting the mean. Guarded by
   `test_head_two_receives_gradient_from_the_parameter_loss`.
2. `_auc` returned 0.0 for a constant (useless) score instead of 0.5 — ties
   were not rank-averaged. Fixed and tested.

**Known instability:** `rouse_screened` per-class accuracy swings a lot by seed
(0.20 on seed 0, 0.71 on seed 1) — the model sometimes collapses the
degenerate pair onto one member. Check `merged_pair_accuracy` (stable ~0.96)
before concluding anything is broken.

### 1f. First real-data evaluation + density invariance — DONE 2026-09-02
`scripts/eval_real_data.py` runs the trained checkpoint against the digitized
literature sets. Those npz files carry only omega/Gp/Gpp (physics-validation
schema, no label/stack_id/params), so `npz_to_records` cannot read them — the
script builds tensors directly and compares against the ground truth the
physics validation already established.

**The first run scored 0/6, confidently wrong (abstain_p ~ 0 everywhere).**
Cause: the generator emitted EVERY curve at exactly 60 points, so the model
keyed on sampling density. Real curves are 11 (Tixier), 16 (Darby), 85-90
(Pivokonsky). Hand-resampling them to 60 points fixed 4 of 6 immediately,
which is what identified the bug. Not a units/window problem — the real omega
ranges already sat inside the training span.

Fixed in two places, deliberately:
- `rheofp/ml/dataset.py` — new `resample_log_grid()`, called by
  `curve_tensor()`, puts EVERY curve on a fixed `N_GRID`=60 log-omega grid
  over its own window. Density becomes a property of the loader, not the
  model, so an upload of any point count and any frequency range works. The
  window itself is preserved and still reaches the model via `_summary()`.
  Interpolation is linear in log-log (exact for power-law segments).
  `collate_stacks` now asserts the common grid instead of trusting `batch[0]`.
- `rheofp/data/synth.py` — `N_OMEGA_RANGE = (10, 100)`, count drawn per curve
  (a T-stack shares one window but redraws density per curve, since each
  temperature is its own sweep). This varies what the model SEES; the loader
  is what guarantees invariance.
Tests: `test_curve_tensor_is_invariant_to_sampling_density`, plus any-count,
unsorted-input, window-still-distinguished, and mixed-density-stack collation.
Suite 102 -> 112.

**Result after retraining (16k, 55 epochs, seed 1): 4/6, and raw == resampled
(the invariance holds).** Darby 2022 all three cured silicones and Tixier 2004
critical gel are now correct straight from raw digitized points.

Two retrains were run. Both scored 4/6 on real data; the difference is the
`BRANCHED_SIGMA` widening below:
  - before widening: synthetic **0.857** vs 0.627 baseline
  - after widening:  synthetic **0.917** vs 0.627 baseline (shipped checkpoint)
Both are below the old 0.932, but that number is not comparable — it was
measured when every curve had exactly 60 points. ~62% of the remaining error
is the known Zimm<->Rouse degeneracy. Stacks now help monotonically again
(N=1 0.901 -> N=5 0.935), and abstention is sharp: dropping the least-confident
30% takes accuracy to 0.995.

**Pivokonsky LDPE (E and B) still misclassifies as rouse_screened, and this is
a FORWARD-MODEL limit, not a sampling or tuning gap.** Fitting
`branched_spectrum` to that data drives sigma against any ceiling it is given
(tried 12 and 30) and still bottoms out at ~0.19-0.28 decades RMS, while a
10-mode Maxwell fits the same curves to ~0.02 (see `tests/test_pompom.py`).
The synthetic branched population sat at median tan(delta) ~0.32 vs the real
melts' ~0.95-0.99. `BRANCHED_SIGMA` was widened (1.0, 4.0) -> (1.0, 10.0),
moving it to ~0.47 — that helped the SYNTHETIC branched class a lot (it is now
274/277, and overall accuracy rose 0.857 -> 0.917) but did nothing for the real
melts. **The 3-parameter hierarchical double-reptation form cannot represent
real LDPE.** Options: give the branched class a broader/Prony-style forward
model, or accept it as model-only and let abstention carry it.

Caveat worth knowing before trusting abstention here: on the pre-widening
checkpoint the model was appropriately unsure about Pivokonsky
(abstain_p ~0.29); after widening it is confidently wrong (abstain_p ~0.01,
p(rouse_screened) ~0.99). Abstention is trained against the model's own errors
on the SYNTHETIC distribution, so it does not detect a material whose true
class is absent from that distribution. Do not read low abstain_p as evidence
of a correct answer on out-of-distribution material.

### 1g. Branched forward model replaced with BSW — DONE 2026-09-03
> Numbers below are AS MEASURED on 2026-09-03 and partly superseded by §1h:
> the bank is now 9 candidates, not 8, and the "0.700 AICc baseline" was
> measured while `wormlike_micelle` was unreachable. Left unedited as the
> record of what was known at the time.

Closed the §1f blocker (Pivokonsky LDPE misclassified). User chose option (a):
give the branched class a broader forward model, 5 parameters.

**What changed.** New `bsw_spectrum(w, G_N, tau_max, tau_c, n_e, n_g)` +
`fit_bsw` in `rheofp/models/maxwell.py` — the Baumgartel-Schausberger-Winter
relaxation spectrum, two power-law wedges (broad terminal wedge tau^n_e, plus a
high-frequency wedge tau^-n_g switching on below crossover tau_c), discretized
onto a log-tau ladder and fed to the canonical Maxwell sum.
- `model_branched` + `BRANCHED_MODELS` registry (k=5), same
  (forward, p0, bounds, k) shape as the solution/network banks.
- **`identify()`'s bank is now 8 candidates**: `ALL_MODELS = MODELS |
  NETWORK_MODELS | BRANCHED_MODELS`. `MODEL_ONLY_CLASSES` added to identify.py.
  Pre-filter left permissive — branched has no robust single-curve
  contraindication, so nothing hard-discards it.
- `rheofp/data/synth.py` samples BSW params; `BRANCHED_SIGMA` is GONE, replaced
  by BRANCHED_LOG_GN / LOG_TAU_MAX / TAU_C_OFFSET_DECADES / N_E / N_G. tau_c is
  drawn as an offset BELOW tau_max so the two can never cross.
- **`N_PARAMS` 4 -> 5** in `rheofp/ml/dataset.py` (branched is the widest class);
  `model.py` now imports it rather than hardcoding 4. Model 246,129 params.
- `branched_spectrum` / `fit_branched` RETAINED — still used by the tube-model
  context and its tests. Only the classifier's branched forward changed.

**Why BSW and not something else.** The old 3-param hierarchical
double-reptation is a single power-law mode ladder; it cannot make a spectrum
broad enough for real LDPE. Measured, before committing to the design:
  Pivokonsky E: old 0.316 dec RMS -> BSW 0.068     (target was < 0.10)
  Pivokonsky B: old 0.280 dec RMS -> BSW 0.059
Checked it does NOT cannibalise the linear-melt class: on planted reptation
curves, reptation still wins AICc -4522 vs BSW -758, because BSW's
intrinsically broad spectrum cannot fake a sharp reptation terminal. That
property is what makes the class safe to add. Planted-param recovery is exact
and seed-stable (4/5 seeds identical on real data).
G_N is a window-limited AMPLITUDE scale, not a measured plateau modulus — on a
terminal-zone sweep it just sets the overall level. Do not report it as G_N^0.

**Results after retrain (16k, 55 epochs, seed 1, CPU ~9 s/epoch):**
  REAL DATA **6/6** (was 4/6). Pivokonsky E -> branched p=0.92 (abstain 0.04),
  B -> branched p=0.96 (abstain 0.05). Raw == resampled, invariance holds.
  Residual probability on both LDPE melts sits on rouse_screened (0.07/0.04) —
  the old wrong answer, now a minority opinion.
  Synthetic 0.917 vs **0.700** AICc baseline (baseline itself rose from 0.627
  because identify() can finally score branched instead of defaulting).
  merged-pair 0.963; regime 0.999; branched per-class 0.935 (n=277).
  Zimm<->Rouse is now 55% of ALL error; cured_elastomer<->critical_gel is 0%.
  Abstain 20% -> 0.972, 30% -> 0.990. Stacks still beat N=1 (0.909 -> 0.932).

**Side effect worth knowing — two stack tests were reframed.** A broad
entangled melt with terminal below the window used to be called a NETWORK class
by a single curve, and `test_stack_overturns_a_network_call_on_a_disguised_melt`
existed to catch that. With BSW in the bank the same curve now correctly routes
to `branched` (a melt identified as a melt), so there is nothing to overturn.
The overturn logic is still there and still tested, against a new fixture
(`_disguised_network_melt_stack`: one dominant slow mode + a faint fast ladder)
that genuinely still reads as cured_elastomer from one curve. Do not read the
rename as the feature being dropped.

### 1h. Two-brain asymmetry closed — wormlike_micelle registered — DONE 2026-09-04
The generator made 9 classes and the neural head emitted 9, but `identify()`'s
bank held only 8: `wormlike_micelle` had `wlm_spectrum` + `fit_wlm` in
`maxwell.py` and was never given a `(forward, p0, bounds, k)` registry entry.
So the AICc identifier could not emit it at any cost. Found by auditing the
class registries against each other, not by a failing test.

**Two consequences, both real.**
1. *The published physics baseline was measured wrong.*
   `physics_baseline_accuracy` filtered its pool with
   `fine = set(ml.dataset.CLASSES)` — the NEURAL 9-class list — which filters
   nothing. So ~1/9 of the baseline's exam was unanswerable by construction and
   its ceiling was 0.889, not 1.0. Measured on one fixed pool (n=90,
   n_restarts=6): **8-model bank 0.711 overall / 0.800 on what it could emit;
   9-model bank 0.822.** The old 0.711 reproduces the published 0.700 closely,
   which is the evidence the diagnosis is right. **So the headline
   "0.917 vs 0.700" overstated the margin: it is closer to +0.10 than +0.217.**
   The network's 0.917 is untouched — the ML pipeline only calls `identify()`
   for the baseline.
2. *A missing class does not present as low confidence.* Handed 12 planted
   micelles, the 8-model bank said `branched` 11 times at median Akaike weight
   **1.000**, median residual 0.05 decades — `low_confidence` fired once. BSW's
   5 parameters fit a near-single-Maxwell shape easily, so `FLOOR_CHI2` never
   trips. **The none-of-the-above floor cannot detect a class that is not in
   the bank; the most flexible candidate absorbs it instead.** This is the
   physics-side twin of the known abstention limitation in §3.

**Cannibalisation check ran BEFORE wiring** (same discipline as BSW, §1g).
5 planted curves per class, 8-model vs 9-model bank: **no existing class lost a
single correct answer** (zimm 5->5, reptation 4->4, sticky_rouse 3->3,
sticky_reptation 3->3, cured 5->5, gel 5->5, branched 5->5). One `reptation`
curve moved from `branched` to `wormlike_micelle`, i.e. one already-wrong
answer was redistributed. `wormlike_micelle` went 0/5 -> 5/5. Real data stayed
**6/6** (Pivokonsky E/B branched, Darby x3 cured_elastomer, Tixier
critical_gel).

**What changed.** `WLM_MODELS` in `maxwell.py` (`model_wormlike_micelle`, k=4;
`beta` is LINEAR not log10, matching how synth samples it, so a planted vector
and a fitted vector mean the same thing). Bounds are absolute like
`BRANCHED_BNDS` and carry ~2 decades of headroom on both times because a T-stack
Arrhenius-shifts them. `ALL_MODELS` is 9; `MODEL_ONLY_CLASSES` in identify.py is
now `BRANCHED_MODELS | WLM_MODELS` (it disagreed with synth.py's constant of the
same name before). `physics_baseline_accuracy` filters by the BANK and returns
`skipped`; `print_report` warns loudly if anything was dropped.

**Still open from this.** The paired network-vs-baseline number needs a rerun of
`scripts/train_classifier.py` through the fixed path — ~0.82 above is a
standalone measurement at n=90, not the same split the 0.917 came from. Nothing
else depends on it.

**Note `MODEL_ONLY_CLASSES` is still not enforced anywhere.** Both in identify.py
and in ml/evaluate.py, `branched` and `wormlike_micelle` are scored as ordinary
fine labels; the "regime-level only" rule lives in prose and in one unused
constant. Deliberately left alone — it is a change to the FROZEN taxonomy and
belongs with the §3 decision on promoting `branched`, not smuggled in here.

### 1j. Out-of-distribution detection — TWO APPROACHES TRIED, BOTH FAILED 2026-09-04
**Do not re-tread this without reading why.** Goal was a "none of the above"
signal, since AICc always crowns a winner even when the true class is absent
(§1h). Both candidate discriminators were validated before use, per house style,
and both failed validation. Recorded so the ground is not covered twice.

**Context that came late, and matters:** the user clarified mid-session that the
product classifies MOLECULAR architecture, not macroscopic category (now in
CLAUDE.md "SCOPE"). Two of the three out-of-scope test materials used below —
a soft-glassy paste and a Herschel-Bulkley solid — are obvious on sight and are
NOT a threat model worth engineering against. **The relevant unknowns are
molecularly distinct but macroscopically ordinary: blends, block copolymers,
semicrystalline melts, star polymers, filled melts.** Notably the one on-target
probe (a two-plateau blend) is the one BOTH detectors missed.

**Approach 1 — residual STRUCTURE (Wald-Wolfowitz runs test on log-residuals).**
Idea: a right-shaped model leaves noise-like residuals (signs flip often); a
wrong-but-flexible one leaves long same-sign drifts. Measures shape, not size,
so it is independent of FLOOR_CHI2.
  - Worked perfectly on synthetic: 3/3 out-of-scope caught, 0/45 false alarms.
  - **Failed on real data.** Pivokonsky E scored -8.90 and B -8.62 — MORE
    structured than the out-of-scope materials (-6.08, -5.76) — while being
    correctly classified.
  - **Diagnosis: the statistic is a SIGNIFICANCE score, so it grows ~sqrt(n).**
    Scores tracked point count almost monotonically: Tixier 11 pts -0.29,
    Darby 16 pts -3.09, planted 27 pts -1.37, out-of-scope 40 pts -6.08,
    Pivokonsky 85-90 pts -8.6/-8.9. Comparing raw scores across curves of
    different length is invalid, and that is what the test did.
  - **If anyone retries this: use an EFFECT SIZE, not a significance score** —
    e.g. the fraction of residual variance that is systematic, or longest run as
    a fraction of n. That is the fix, and it is unvalidated.

**Approach 2 — relative margin** (winner's structure minus rivals' median).
Motivated by the above: real material always carries model error, but that
applies to every candidate equally. Better, and scale-free:
  in-taxonomy min 1.32 / median 6.31; out-of-scope -3.91, 0.00, 0.00.
  But Pivokonsky E/B again land at 0.20/0.21, inside the out-of-scope band.

**The deciding experiment (walk a Maxwell ladder 2->10 modes and watch what
happens as the fit becomes adequate) — and its verdict.**
  - Pivokonsky E: rms 0.2538 -> 0.0200 (12.7x better) but structure only
    -8.90 -> -7.50. Structure barely moves however good the fit gets.
  - BUT Darby (also real, also digitized, 16 pts) goes -3.09 -> -0.28. So "real
    data is too smooth for clean residuals" is FALSE in general. The difference
    is point count, not realness. **Verdict: Pivokonsky's flag was a FALSE
    ALARM caused by sample size.** An earlier worry in this session that
    `branched` might be a weak explanation of real LDPE was retracted on this
    evidence — the LDPE behaves like ordinary representable material.
  - Two controls that DID hold, worth keeping: (a) planted synthetic branched
    scored -1.37, i.e. the machinery is sound when the model IS the truth;
    (b) **flexibility does not launder a wrong model** — on the out-of-scope
    paste, going from 4 to 20 free parameters moved structure not at all
    (-6.06 -> -6.08) and the fit hit a wall at ~0.071 dec.

**Byproduct worth remembering — SATURATION of a Prony ladder.** How much a
generic Maxwell fit improves from 2 to 10 modes: Darby 35x, planted branched
13x, Pivokonsky E 12.7x, Tixier 11x, Pivokonsky B 9.8x, **out-of-scope paste
3.2x (hits a wall)**. Scale-free, unlike the runs test. But narrow: it detects
only material a sum of relaxation modes cannot represent. Herschel-Bulkley
scored 8.8x (missed) and the two-plateau blend fits exactly at 2 modes
(undetectable — it IS a Prony series, it is just absent from the bank). Useful
someday for the empty Yield-dominated regime; not a general detector.

**Conclusion: there is no working OOD detector, and the explanation layer
(ACTIVE TASK) is the agreed answer instead** — put the reasoning in front of the
user, who knows what they uploaded, rather than trying to infer it.

### 1k. Vitrimers can be struck off the ballot by the pre-filter — FOUND 2026-09-04, NOT FIXED
Vitrimers / associating networks route through `sticky_rouse` +
`sticky_reptation` (CLAUDE.md). `signature_features` contains:

    if not has_shoulder:
        allowed -= {"sticky_rouse", "sticky_reptation"}

`has_shoulder` needs a SECOND G″ maximum with an interior dip. If the window
does not span the bond-exchange time, both vitrimer classes are deleted before
any fitting — unreachable, exactly as `wormlike_micelle` was before §1h.

**Measured: 4 of 12 generated vitrimer curves had both classes struck off**, and
those landed on `cured_elastomer` (a dynamic network reported as PERMANENT — the
flagship molecular error under the scope), `reptation` x2, `wormlike_micelle`.

**Why the rule is unsound:** absent evidence, not evidence of absence — the same
fallacy this project already rejected for melt-vs-rubber. Contrast the sound
discard, `terminal_reached` removing the network classes: that rests on
something OBSERVED (flow), which is impossible for a permanent network. General
principle now in CLAUDE.md: *a hard discard is sound only when grounded in a
positive observation.*

**The stack rescues it, and this is the good news.** `identify_stack` on 6
vitrimer temperature stacks: all 6 correctly refused a permanent-network call
(verdict "melt", shifts 0.56-1.71 decades), 4 of 6 got the exact class right.
The designed mechanism works — on synthetic data.

**Also flagged, my own due diligence:** 2 of the 12 vitrimer curves came back as
`wormlike_micelle`, a class added to the bank on 2026-09-04 (§1h). The
pre-registration check showed no loss on `sticky_rouse` at 5 curves/class, but a
near-single-Maxwell micelle and a sticky-Rouse network with one dominant slow
mode are plausibly confusable. **Run a proper sticky-vs-WLM confusion check on
a bigger sample before trusting the vitrimer classes.**

## 3. What's genuinely open
- **Real-data coverage is still thin even at 6/6**: six curves, three papers,
  all N=1, and four of the six are the same material family (cured PDMS).
  6/6 confirms the BSW work did its job; it is NOT evidence of general
  real-world accuracy.
- ~~**No temperature stack has ever been tested on real material**~~ — **DONE
  2026-09-07, Edera (2024) epoxy vitrimer, `data/edera2024.npz`.** The
  MECHANISM is now validated on real material: `resolve_melt_vs_network`
  returns "melt" (2.50 decades) and refuses to call a dynamic network
  permanent, and `identify_stack` overturns its own single-curve
  `critical_gel` call and abstains. The FINE CLASS fails (no curve identified
  as a vitrimer) but the dataset is deliberately hostile — the paper's own
  central claim is that time-temperature equivalence FAILS for this material,
  2 of 4 curves are glassy/near-glassy (out of taxonomy), and only the 180C
  curve is squarely in the bond-exchange regime. Run
  `scripts/eval_edera_stack.py`; the caveats are printed with the result.
  **The FAIR test was then run — Ricarte (2023), `data/ricarte2023.npz`,
  `scripts/eval_ricarte_stack.py`.** PB-v-4, 5 temperatures 80-160 C, all in
  the rubbery/bond-exchange regime, TTS works for the system. Mechanism
  confirmed a second time (residuals 0.0012-0.018, Arrhenius R^2 0.9922,
  verdict "melt"). **Fine class FAILS: all five curves return `branched` at
  0.047-0.084 dec — good fits, so nothing flags them.** Contest at 120 C:
  sticky_rouse dAICc 167 at 0.203 dec, sticky_reptation dAICc 246 at 0.399
  dec. The sticker models cannot reproduce the curve; this is a
  forward-model problem, not a ranking one. Caveat: that file's G' is one
  shared trace across temperatures (see prep_ricarte.py).

## 2b. ANSWERED 2026-09-07 — no, not over a power-law window. Forward-model limit.
`scripts/diagnose_sticky_models.py` reproduces the whole argument. Tested the
three candidate causes in order on Ricarte PB-v-4 at 120 C:
- **Fitter? NO.** 12 vs 200 restarts agree to 4 decimals.
- **Bounds? PARTLY, and they should be widened regardless.** Freeing the mode
  ceilings improves sticky_rouse 0.203 -> 0.161 and sticky_reptation
  0.390 -> 0.131 dec. But both plateau far above BSW's 0.046, and
  sticky_reptation's `Z` runs to ANY ceiling offered (197/590/1968/7870) with
  RMS frozen at 0.1305 — a runaway nuisance parameter buying nothing.
- **Functional form? YES.** Every model fits G' well (0.004-0.030); the ENTIRE
  failure is in G'' (sticky 0.18-0.23 vs BSW 0.065).

**The physics.** The real curve has G' flat to 0.019 decades and G'' RISING as
omega falls (low-w log-slope **-0.70**). A terminal zone needs G'' ~ w^+1. This
is a power-law wing, and the paper says so independently: the modulus
"transitions from a rubbery plateau into a power law regime", with the true
terminal relaxation OUTSIDE the 0.01-100 rad/s window. Both sticky models are a
few discrete Maxwell modes around one sticker time tau_s, so they make a G''
PEAK at 1/tau_s that must fall away on both sides — they cannot rise
monotonically for four decades. Piling up modes is the only escape, which is
exactly why Nst and Z pin. BSW wins because its power-law wedges ARE a broad
continuous spectrum.

**Corrected mid-investigation, worth keeping:** I first wrote that the
synthetic training population was the wrong shape. It is not. Synthetic
sticky_rouse's low-w G'' slope is -0.71, matching the real -0.70 almost
exactly, and identify() recovers synthetic sticky curves 9/10. The real
difference is G' span: **0.019 dec real vs ~0.26 synthetic, ~10x flatter**. The
models work on the population they were built from; this real material sits at
an extreme EDGE of it. Widening the synthetic G' range toward flatness would
make training more representative but would NOT close the 0.16-vs-0.046 gap —
that gap is the forward model's, not the sampler's.

**DECIDED 2026-09-07 (user): option (b).** Keep the sticky models as they
are; make the ambiguity explicit in the report rather than replacing the
forward models. Implemented same session:

`rheofp/report.py` gains `branched_vitrimer_contradiction(winner_name, w, Gp,
Gpp)` — a NAMED, ALWAYS-CHECKED item in `challenge()` that fires specifically
when the winner is `branched` AND the curve shows a negative low-frequency G''
slope (< 0, a power-law wing) AND a near-flat G' (< 0.3 dec span). Both
thresholds are measured, not asserted: **zero false positives** among 31
curves the classifier genuinely called `branched` from a mixed synthetic
population (branched/reptation/zimm/rouse_screened), and both real Pivokonsky
LDPE curves pass cleanly (slopes +0.73/+0.81, G' span 3.3-3.4 dec) — only real
vitrimer data (slope -0.70, span 0.019 dec) has been observed to trip it. The
message states the physical signature, names WHY the sticky models can't
reach it (built from a handful of Maxwell modes around one sticker time -> a
G'' PEAK, not a rising wing), and names the measurement that would settle it
(reach the sticker peak: higher T or a wider window). This is the
melt-vs-rubber abstention precedent applied to a newly measured degeneracy.

Needs the raw curve, which identify()'s contract does not carry, so `explain()`
and `challenge()` gained optional `w, Gp, Gpp` params (default None -> check
silently skipped, everything else unaffected) rather than touching
identify()'s return shape. `scripts/explain.py` passes them through.
5 new tests (test_report.py), suite 146 -> 151.

~~Cheap and safe, NOT yet done~~ — **TESTED 2026-09-11 AND REJECTED. The
bounds STAY AS THEY ARE.** "Cheap and safe" was an untested assertion that sat
in this file for four days; running the cannibalisation protocol on it
(`scripts/check_sticky_bounds_widening.py`, output
`docs/sticky_bounds_widening_2026-09-11.txt`) showed it is false. Widening
**costs 10 curves overall (0.920 -> 0.887)** and, in the outcome nobody
predicted, **the biggest loser is `sticky_rouse` itself — 29/30 -> 22/30**,
the very class the change was FOR. See §2d below for the full numbers and why.

## 2d. Widening SR_BNDS / SREP_BNDS — TESTED AND REJECTED 2026-09-11

**The bounds are UNCHANGED and should stay that way.** `solutions.py` was never
edited; the check patches `identify()`'s bank in-process only.

Pre-registered accept/reject rule, written into the script's docstring before
running: ACCEPT if the sticker classes do not regress, no other class loses
more than ~1-2 curves, and real data stays 6/6.

| class | before | after | delta | stolen by |
|---|---|---|---|---|
| **sticky_rouse** | **29** | **22** | **-7** | sticky_reptation x4, reptation x3 |
| branched | 30 | 28 | -2 | sticky_reptation x2 |
| wormlike_micelle | 30 | 29 | -1 | sticky_rouse x1 |
| sticky_reptation | 29 | 29 | +0 | — |
| the other six | — | — | **+0** | — |
| **OVERALL** | 276 | 266 | **-10** | **0.920 -> 0.887** |

Real data: **6/6 -> 6/6**, unchanged.

**The result nobody predicted: the biggest loser is `sticky_rouse` itself**,
the class the widening was FOR. The pre-registration expected the sticker
classes to "improve or hold" and worried about *other* classes being
cannibalised. Both sticker classes are k=4, so freeing the bounds hands
`sticky_reptation` enough extra reach to impersonate a planted sticky_rouse
curve (4 of the 7 losses), while `reptation` takes 3 more. The change helps
sticky_rouse's RIVALS more than it helps sticky_rouse.

**Two lessons worth more than the change would have been:**
1. **"Demonstrably binds" does not imply "should be freed."** The 2026-09-07
   diagnosis was right that the bounds bind on a real vitrimer (sticky_rouse
   0.203 -> 0.161 dec when freed). That is a statement about ONE curve's fit
   quality. Classification is a CONTEST, and a bound that limits a model also
   limits how well it impersonates its neighbours.
2. **Real data would NOT have caught this.** 6/6 both ways. The 6 benchmark
   curves contain no sticker class at all, so the only instrument that could
   see this damage is the planted-curve protocol. Anyone tempted to skip it
   because a change "looks safe" should read this row.

Re-runnable: `scripts/check_sticky_bounds_widening.py`, full output committed
as `docs/sticky_bounds_widening_2026-09-11.txt`. **Do not re-litigate without
new evidence** — and note that "the bounds still bind" is not new evidence,
it is the same observation that motivated this rejected change.

## 2c. (superseded framing) original question as first posed
Two real stacks now agree that they cannot. `sticky_rouse` /
`sticky_reptation` in `solutions.py` were validated against PLANTED synthetic
parameters only; neither has ever been fitted to a real measured vitrimer.
Ricarte PB-v-4 is the target and is now in the repo. The question to answer
before any more classifier work on vitrimers: is the failure in the models'
functional form (a real dioxaborolane vitrimer's near-flat G' with slowly
rising G'' may simply not be in their reachable set), in the parameter bounds,
or in the fitter? Protocol: fit each sticker model to the 120 C curve directly
with generous restarts and bounds, plot residuals, and compare against BSW's
0.047. If the models genuinely cannot reach it, that is a forward-model
replacement job of the same kind as branched_spectrum -> BSW on 2026-09-03,
and it has a precedent to follow.
- **Old framing, kept because the reasoning still applies to the fine class:** The stack
  is the only thing that separates a dynamic network (vitrimer) from a permanent
  one (cured elastomer), which is a flagship distinction of the product; it is
  also what rescues the vitrimer misclassification in §1k. Both the resolver and
  the stack-aware model are synthetic-only. Getting ONE real temperature series
  of a vitrimer or a melt would be worth more than any amount of further
  synthetic work.
- Yield-dominated regime has no implemented physics at all (3rd taxonomy
  regime is empty). **Lower priority than it looks** under the molecular scope:
  yield-stress materials (pastes, foams, emulsions) are macroscopically obvious,
  so a user does not need a classifier to spot one. Fill it for completeness,
  not for value. If it is ever built, §1j's saturation byproduct is a ready
  detector for it.
- **Molecular unknowns that ARE worth worrying about**, none in the taxonomy and
  none macroscopically distinguishable: polymer blends / two-phase systems,
  block copolymers, semicrystalline melts, star and comb architectures,
  filled/nanocomposite melts. A blend was the one out-of-scope probe both §1j
  detectors failed to catch.
- ~~**The "model-only" rule is documentation, not behaviour**~~ and
  ~~**should `branched` be promoted?**~~ — **BOTH DECIDED 2026-09-07 (user):
  promote, and retire the model-only tier entirely.** The user's words: *"i am
  happy with saying 'your sample is branched'"*, then approved promoting
  `wormlike_micelle` in the same pass. `MODEL_ONLY_CLASSES` deleted from
  synth.py and identify.py; `ALL_CLASSES == FINE_CLASSES` (9 fine classes);
  stale docstrings in ml/evaluate.py, scripts/validate_tube.py and the tests
  cleaned up. Suite still 125 passed / 2 skipped. Evidence behind it: BSW fits
  real LDPE ~0.06 dec with errors going to zimm/rouse not reptation;
  `wormlike_micelle` measured **40/40 self-correct** and stole no correct
  answers from any other class (n=40/class, seeds 42/7). Note the promotion
  changed no classifier behaviour — the tier was never enforced — so no
  accuracy number moves; what changed is that the docs now match the code.
- Abstention still cannot flag out-of-distribution material: it is trained
  against the model's own errors on the SYNTHETIC distribution. Low abstain_p
  is not evidence of a correct answer on a material whose class is absent from
  training.
- Optional: Zimm/Rouse tiebreaker (now 55% of all error, but may be genuinely
  irreducible from SAOS — the log-slope distributions almost fully overlap);
  critical-gel AICc tiebreaker via the unused frequency-flat-tan(delta)
  feature; Villar/Martin tabulated checks.
