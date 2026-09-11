# Session journal

Dated summaries of Claude Code working sessions — for **context across PCs**,
not for resuming conversations. Newest first. Claude: append a short entry at
the end of each working session (what was discussed, decided, and changed).

---

## 2026-09-11 (OFFICE PC, latest) — pre-registered Pryke; widening REJECTED

Two items, both about testing claims before believing them.

**1. Pre-registered the Pryke 2001 predictions BEFORE any data exists**
(`docs/pryke2001_preregistration.md`, commit `b2db295`). Six numbered
predictions with reasoning, plus a ranked "what would count as a genuine
problem" / "what would NOT" split. Nothing to rationalise toward, because the
curves are still undigitized. Notably P2 predicts sample A (Z 3.2) will FAIL
and says so is not a regression — the paper independently reaches the same
Z ~ 4 boundary, blaming its own worst deviations on "marginal degree of
entanglement, with s = 3.2". The OUTCOME section is empty and everything above
it is frozen, so the diff will show what was wrong.

**2. Widening SR_BNDS / SREP_BNDS — TESTED AND REJECTED. Bounds unchanged.**

This had been sitting in next-actions since 2026-09-07 described as **"cheap
and safe"**, repeated across two files until it read as a decided to-do. It is
false. Full numbers in §2d of next-actions and
`docs/sticky_bounds_widening_2026-09-11.txt`:

| | before | after |
|---|---|---|
| **sticky_rouse** | **29/30** | **22/30** |
| branched | 30 | 28 |
| wormlike_micelle | 30 | 29 |
| overall | 276 (0.920) | 266 (**0.887**) |
| real data | 6/6 | 6/6 |

**The biggest loser is `sticky_rouse` itself — the class the change was FOR.**
The pre-registration expected the sticker classes to "improve or hold" and
worried about other classes being cannibalised; the damage went the other way.
Both sticker models are k=4, so freeing the bounds hands `sticky_reptation`
enough reach to impersonate a planted sticky_rouse curve (4 of the 7 losses),
with `reptation` taking 3 more.

**Two lessons worth more than the change would have been:**
- **"Demonstrably binds" does not imply "should be freed."** The 2026-09-07
  diagnosis was correct that the bounds bind (sticky_rouse 0.203 -> 0.161 dec
  on a real vitrimer). But that is one curve's FIT QUALITY, and classification
  is a CONTEST — a bound that limits a model also limits how well it
  impersonates its neighbours.
- **Real data would not have caught this: 6/6 both ways.** The six benchmark
  curves contain no sticker class at all, so only the planted-curve protocol
  could see the damage.

Implementation note for anyone re-running it: `identify()`'s `ALL_MODELS`
holds `(forward, p0, bounds, k)` tuples captured at import, so editing
`solutions.SR_BNDS` alone does NOTHING — the tuple already captured the old
list. The check rebuilds those two entries instead, and a smoke test confirmed
the swap, that `k` stays 4, that other entries are untouched by identity, and
that restore returns the original object. A silent no-op here would have
produced a meaningless "no change, therefore safe" result.

---

## 2026-09-10 (OFFICE PC, part 3, end of session) — next dataset identified

Closed out by finding the paper for the next piece of work: real star-MELT
data of an independent chemistry, which is the standing gap in the `star`
class (all validation so far is PI and PIB).

Searched Crossref rather than trusting recall — worth noting because the first
two DOIs that surfaced (`10.1021/ma00134a060`, `10.1021/ma980060d`) turned out
to be Pearson-Helfand 1984 and MM1998, **both already in `originals/`**. The
Roovers papers that came up are star-in-linear blends, rings, or 32-arm stars
(the latter sits in the known Z >~ 40 two-peak regime — a harder test, not a
first one).

**Landed on Pryke, Blackwell, McLeish & Young, *Macromolecules* 35, 467-472
(2002), DOI 10.1021/ma010350l.** User supplied it as
`originals/ma010350l.pdf`; I read it page by page and confirmed it is the
right paper. Four three-arm 1,2-polybutadiene stars, arm M_w 11.3K-78.6K, plus
their hydrogenated analogues; M_e / G_0 / tau_e given in Table 2 so **Z is
known independently rather than fitted** (Z = 3.2 / 6.8 / 11.0 / 22.1). It is
a direct Milner-McLeish test by McLeish himself, using the same three
parameters this module implements.

**Unplanned corroboration worth keeping:** the paper's own conclusion that its
low-M_a samples "show the largest deviation ... marginal degree of
entanglement, with s = 3.2" is the SAME Z ~ 4 floor this project found
independently from the flat-cost-in-Z analysis. Two different routes to the
same boundary.

**The catch, and it is why this is a to-do and not a result: the data is in
FIGURES.** No numeric G'/G'' anywhere in the PDF — Figures 2 and 3 are log-log
master curves at 333 K over ~9 decades. Same position as every other dataset
here; all of them reached `data/` only after the user digitized them.

Full brief, including both tables transcribed so nobody reopens the PDF, the
recommended minimal scope (Figure 2, the two well-entangled panels first), and
the pre-registration reminder, is at the TOP of `next-actions.md` as the
active task.

---

## 2026-09-10 (OFFICE PC, part 2) — third seed; the question is closed

**Verdict: the gate effect is SMALL BUT REAL. Stop measuring it.**

Ran a third independent seed (23, n=600) against a decision rule committed to
git BEFORE the numbers existed (`9b51840`) — precisely because this file had
already twice read a result after the fact as whatever it happened to be.

| run | n | gate margin | |
|---|---|---|---|
| seed 7 | 200 | +0.006 | 0.3 SE — called "refuted" at the time |
| seed 11 | 600 | +0.019 | 1.8 SE — called "suggestive" at the time |
| seed 23 | 600 | **+0.012** | 1.1 SE — **AMBIGUOUS** by the rule |
| **POOLED** | **1400** | **+0.014** | **2.0 SE** |

Seed 23 landed at +0.012, inside the pre-registered ambiguous band
(CONFIRM ≥ +0.015, REFUTE ≤ +0.005). **No side was picked, and the thresholds
were not renegotiated afterwards.** The pooling is what carries the
conclusion: the margin was positive in all three runs and never flipped sign,
but no single run reaches significance — only the 1231-curve pooled agree arm
does, at 2.0 SE. So the effect is **consistent and small**, and a fourth seed
is not worth running: three runs bracket it, and the residual uncertainty is
about size, not existence.

**All constants in `neural_report.py` are now POOLED over the three runs**, and
the pinning test recomputes the pooling from all three committed files rather
than reading one — so adding, removing or swapping a run without redoing the
constants now fails a test.

| | agree (n=1231) | disagree (n=169) |
|---|---|---|
| physics | 0.945 ± 0.007 | **0.438 ± 0.038** |
| neural | 0.937 | **0.426** |
| either right | 0.975 | **0.864** |

**Three claims the repeat runs corrected — all were single-run artefacts:**
- **"More than halves the fitting side"** was seed 7's 18-curve disagree arm.
  Pooled ratio is 0.46, i.e. "roughly halves".
- **WHICH brain degrades more on a disagreement is NOT stable** — the network
  fell further at seed 11 (0.413 vs 0.493), the fitter at seed 23 (0.395 vs
  0.421). So never advise trusting one side over the other on a split. This is
  now the strongest argument for the shortlist.
- **`agree_degenerate` swings** (physics 0.364 / 0.576 / 0.575) on ~5-7% of
  curves; only its `either right` (0.97-1.00) is quotable.

**What survived best is the SHORTLIST claim**, which is the one built into the
report: one of the two labels is right ~86% on disagreements against 0.44/0.43
individually. Also confirmed in all three runs: a **sharp** disagreement is the
pair's BETTER case (pooled 0.93, n=112) than a mere reordering of the same
short list (0.75, n=51) — though seed 23 narrowed that gap (1.00/0.98/0.85).

**Decision unchanged: agreement stays OUT of `identify()`.** A ~1.4-point gain
on one gate does not justify changing a contract the tests, validation scripts
and ML baseline all depend on.

---

## 2026-09-10 (OFFICE PC, part 1) — the agreement signal, measured properly

Two items off the top of next-actions: more n on the disagree arm, and the
`either right` finding turned into a feature.

**1. n=600 (60/class, seed 11) — and it REVISED the n=200 verdict.**
`docs/agreement_measurement_n600_2026-09-10.txt`. Seed 11 deliberately not
seed 7, so the two runs are independent samples rather than nested. The
disagree arm went 18 -> 75 curves, which is what n=200 could not resolve.

| | agree | disagree |
|---|---|---|
| physics | 0.947 | **0.493** |
| neural | 0.935 | **0.413** |
| either right | 0.971 | **0.907** |

Three corrections to what was written last night, all in the direction of the
larger run:

- **The gate comparison flipped from refuted to suggestive.** Agreement gates
  to 0.935 against **0.916** (network's own p) and **0.912** (abstention) at
  matched coverage — **+0.019 / +0.023**, where n=200 gave +0.006. Against an
  SE of ~0.011 that is ~1.7 SE. So "not supported" is **withdrawn**, but this
  is not established either. Wording everywhere is now "comparable, possibly a
  little better", and a test pins it there.
- **"More than halves" was an artefact of 18 curves.** At n=600 it is
  0.947 -> 0.493, i.e. exactly half; pooled over both runs the disagree arm is
  0.473 +- 0.052 against 0.941 +- 0.009, a factor of 2.0. Now says "halves".
- **The NETWORK degrades more than the fitter on a disagreement** here
  (0.935->0.413 vs 0.947->0.493) — the reverse of n=200. So **neither side is
  reliably the one to trust when they split.** That is the strongest argument
  yet for the shortlist rather than picking a winner.

Also: `agree_degenerate` **reversed** between runs (physics 0.364/neural 0.636
-> 0.576/0.394). ~5% of curves and unstable — only its `either right` figure is
quotable, and the report now says outright that which member to prefer is not
stable between runs. And `star -> branched` appears **10x** in the n=600
disagreements **with the PHYSICS side right**, the opposite direction from
MM1998: **the real-data n=7 pattern does not generalise.**

**2. The pair beats either member — built as `YOUR SHORTLIST: A or B`.**
`pair_note()` in `neural_report.py`. This was the most robust thing the n=200
run produced and it is the one result that got STRONGER at the larger n: one of
the two labels is correct **97%** (agree), **91%** (disagree), **98%** (sharp
disagreement), against 0.493/0.413 for the methods individually on those same
cases. Framed as a two-item list to settle with outside knowledge — never a
winner with a dissent, and **never averaged into one verdict, which would
destroy exactly this result**.

Worth keeping: **the SHARP disagreements are the pair's BEST case (98%), not
its worst**, which is the opposite of what the alarming wording around them
suggests. When the two methods diverge completely they are usually diverging
onto the right answer and a wrong one, rather than both missing.

**3. Removed an overstatement that was still in the code.** Two of the four
agreement texts said "stronger evidence than either one's own confidence score"
and "worth more than either" — the exact claim n=200 refuted. They now quote
measured constants instead of asserting a verdict. **Two guards added:** the
constants are pinned by a test against the committed measurement file (so
user-facing numbers cannot drift from the run they came from), and a test
asserts no agreement text ever re-acquires the refuted claim.

One honest note carried into the notes: on Santangelo L176 the shortlist reads
`cured_elastomer or star` and the truth is neither (it is a linear melt). That
is inside the measured ~9%, and the text does not promise otherwise, but the
shortlist is a strong prior and not a guarantee.

---

## 2026-09-09 (OFFICE PC) — the second brain wired into the report

Office PC (RTX A1000). Pulled `1108064`, worked through the three items
next-actions listed as next: verify the unverified commit, build the neural
column, connect the discard/unopposed-winner gap.

**0. The unverified commit is verified.** `uv run pytest -m "not slow"` ->
**213 passed, 2 skipped, 13:34** on the office PC, run over the NEW code (so it
confirms the laptop's unverified commit and this session's work at once).
Arithmetic: the laptop's expected 196 + this session's 17 new tests
(3 in `test_report.py`, 14 in `test_neural_report.py`) = 213.

**1. THE NEURAL HEAD IS NOW report.py's SECOND COLUMN** —
`rheofp/neural_report.py` (new), `tests/test_neural_report.py` (14 tests),
`--neural` / `--checkpoint` on `scripts/explain.py`.

Design honoured exactly as DECISION 3 approved it: a NEW module, importing
FROM `report.py` and never the other way, so `import rheofp.report` still
costs no torch and the AICc pipeline keeps working on a machine with no
checkpoint. `explain_with_neural()` returns explain()'s dict with two keys
ADDED (`neural`, `agreement`) — a test asserts every pre-existing key is
byte-identical, so no existing consumer moves. torch is imported lazily inside
the two functions that need it.

Four agreement outcomes, not two, and the middle one matters: `agree`,
`agree_degenerate` (they split, but only across a known-inseparable pair —
Zimm/Rouse, cured/gel — which must NOT be reported with the same alarm as a
real split), `disagree_ranked` (network's class is a live AICc alternative,
delta < 10), `disagree` (it is not even on the short list — also the shape
out-of-taxonomy material produces, since each side falls back on its own
least-bad class and they need not agree on which).

**The payoff is measured, and it is better than expected.** On Milner-McLeish
1998's seven-star set the agreement signal **separates the AICc hits from the
AICc misses perfectly**:

| | AICc says | network says | verdict |
|---|---|---|---|
| Ma11k..Ma47k (5 curves) | `star` (right) | `star` 0.99-1.00 | **agree** |
| Ma95k, Ma105k (2 curves) | `branched` (WRONG) | `star` 0.99 | **disagree** |

Both misses are true stars whose windows never reach terminal flow. AICc calls
them `branched` at **delta 56.5 and 102.6** — decisive, and decisively wrong —
with nothing in the AICc report expressing doubt, and the network's abstention
head reads 0.00 on them. So NEITHER self-confidence flags these; only the
comparison between the two does. That is the whole thesis of the column,
confirmed on real data at n=7 with no counterexample.

Also flagged: **Santangelo L176**, the linear PIB control that `identify()`
returns as `star` at weight 1.000 with no alternative inside delta 10. The
network does not say star, so the disagreement now carries the warning the
AICc report could not.

Both real benchmark curves and the Tixier gel come back **agree**, so the
signal is not simply firing everywhere.

**THEN IT WAS MEASURED PROPERLY, AND THE n=7 HEADLINE DID NOT HOLD UP.**
`scripts/measure_agreement.py` (new, kept, re-runnable) over **200 planted
curves**, 20/class, seed 7 — full output committed as
`docs/agreement_measurement_2026-09-09.txt`:

| group | n | phys acc | neural acc | either right |
|---|---|---|---|---|
| agree (any) | 182 | 0.923 | 0.940 | 0.962 |
| — agree (exact) | 171 | 0.959 | 0.959 | 0.959 |
| — agree_degenerate | 11 | **0.364** | 0.636 | **1.000** |
| disagree (any) | 18 | **0.389** | 0.500 | 0.889 |
| ALL | 200 | 0.875 | 0.900 | 0.955 |

The signal is **real but modest**: a disagreement more than halves the physics
side's accuracy (0.923 -> 0.389). **But it does NOT clearly beat the network's
own top-class probability as a gate** — 0.940 against 0.934 at matched 91%
coverage, i.e. **+0.006 on n=200, well inside sampling error.** The
pre-registered claim (`P(correct|agree) >> P(correct|disagree)` *and* better
than either self-confidence) is **half-supported: the first part holds, the
second does not.**

So the honest statement of what this column is worth: agreement is
**independent** of both self-confidences and therefore fails *differently* from
them — not measurably *better* than them. That is still worth having, because
the failure modes it does not share are the documented ones (§1h, §3), but it
is not the reliability gate the n=7 result made it look like.

**Two specifics worth carrying:**
- **`agree_degenerate` earned its separate bucket.** Physics 0.364 / neural
  0.636 there, with either-brain-right at **1.000** — it is the Zimm<->Rouse
  pair almost exactly. Folding it into plain "agree" would have inflated the
  headline; reporting it with the alarm of a real split would have cried wolf.
- **`star -> branched` appears 3x among the synthetic disagreements with the
  PHYSICS side RIGHT** — the opposite direction from MM1998, where the network
  was right about exactly that pair. So **the real-data pattern does not
  generalise**, and the MM1998 result should be quoted as what it is: a
  striking n=7 observation, not the general behaviour.

**2. The discard / unopposed-winner link is built** — a new
`unopposed_after_discard` item in `challenge()`, plus 3 tests. Fires only when
an ABSENCE-grounded discard (currently just `reptation`, struck for want of a
plateau) coincides with a winner that has no surviving alternative inside
delta 10. It explicitly does NOT fire on discards resting on a positive
observation (`terminal_reached` striking the network classes — flow was seen,
and a permanent network cannot flow, so that comparison is settled, not
missing). Tested on Ma36k, where both kinds of discard are present at once and
only `reptation` may be named.

**A claim in next-actions turned out to be wrong and is corrected, not
propagated.** The notes said the L176 false positive happened because "the
pre-filter struck `reptation`, so the plausibly correct class was never on the
ballot". **It does not reproduce.** On L176 `signature_features` returns all
ten classes allowed; `reptation` WAS fitted and lost on its own merits, at
delta 429.8 / rms 0.256 against star's 0.043. So the L176 story is simply
"star fits a linear PIB better than reptation does", which is a forward-model
overlap, not a pre-filter deletion. The link built above is still correct and
still valuable — it just fires on Pivokonsky E and MM1998 Ma36k rather than on
the curve the notes cited.

---

## 2026-09-09 (LAPTOP) — laptop bootstrap + step 4 closed

First session on the reformatted laptop (i7-10750H, 32 GB, GTX 1660 Ti).

**Bootstrap.** git + GitHub CLI + VS Code were already installed; uv was not,
and `.venv/` was absent. Installed uv 0.12.12 via winget, set the global git
identity, `uv sync` reproduced the env first try (Python 3.12.14,
`torch 2.13.0+cpu` — the intended Windows resolution, not a fault).
**`uv run pytest -m "not slow"` -> 185 passed, 2 skipped, 14:31** (and 194
passed, 2 skipped, 12:15 at end of session with the 9 new tests). Repo is at
`C:\Users\krish\repos\rheo-fp` here, not the `C:\Users\krish\rheo-fp` the
bootstrap section assumes. `originals/` junction not set up (optional).

**Step 4 (star real-data validation) CLOSED. Both open questions had answers
that contradicted what next-actions had guessed**, which is the reason this
entry is worth reading rather than skimming.

1. **`Z_BOUNDS`' floor of 4 was NOT making the weakly-entangled arms
   unfittable.** That claim was in this file, in next-actions AND in star.py's
   docstring, and it was wrong in all three. Refit at floors 4/3/2/1: the two
   arms sit at Z = 9.12 and 6.66 regardless — far ABOVE the floor, never on it.
   The actual cause is that below Z ~ 4 the cost is FLAT in Z, because
   Ueff(1) is only 1-2 kBT there and the activated terminal time sits under a
   decade above the arm's own Rouse time. So the floor was asserting exactly
   the right thing and stays at 4. **The lesson is the project's recurring
   one:** a plausible mechanical explanation ("a bound is clamping it") that
   nobody had actually measured, and the measurement said otherwise. Cost of
   checking: one 4-column table.
2. **The two misses are decisive losses, not zimm-style ties** (dAICc 57 and
   103, star's rms 20-55% worse), and **the predictor is `terminal_reached`,
   not Z.** Where terminal flow is observed the class is 5/5; where it is not,
   1/5 — and all four real-data failures across both datasets are in that
   second row, including Santangelo's LINEAR control coming back as `star`.
   A non-terminal window breaks the class in both directions.
   Ruled out as the cause: narrow windows (MM1998 covers 104-211% of the
   model's own predicted spectrum width at the true Z). It is specifically the
   missing low-frequency asymptote.
   **Explicitly NOT turned into a pre-filter discard** — that would be the
   `has_shoulder` missing-evidence fallacy a fourth time. Left for the report
   layer, with the decision put to the user.

**Also found and fixed while in there: `report.py` was telling users, in
user-facing output, that "only nine classes exist in this bank" and that "star
and comb architectures" are NOT among them.** Both false since `star` was
wired in. Now derived from `len(ALL_MODELS)` so it cannot go stale again, and
"star" removed from the out-of-taxonomy list. The test that covers that block
only asserted the item's `kind`, never its text, which is how it survived.

**Files:** `tests/test_star.py` 31 -> **40** (7 parametrized terminal-flow
tests + a decisive-win test on Ma36k + a Z_BOUNDS test that pins finding 1);
docstring/bounds comment corrections in `rheofp/models/star.py`; the stale
"NOT yet merged into ALL_MODELS" comment on `STAR_MODELS` fixed; `report.py`
text fix; CLAUDE.md star paragraph + "Current state" rewritten with the real
envelope.

**Star caveat: user said yes, "in rheology friendly language" — BUILT.**
`challenge()` gains a second `window` item when the winner is `star` and
terminal flow was not reached. Written as physics, not statistics: arm
retraction along the tube, retraction time exponential in arm length, the
characteristic shape therefore living in the terminal zone, the measured
low-frequency slopes against the 2/1 flow limits, and the actionable fix
(extend the low-frequency end, or measure warmer and shift by TTS). Two tests,
one of them a counterpart on a star that DID reach flow so the caveat cannot
drift into being unconditional.

**What justified it — look at this before softening it.** `challenge()` on
Santangelo L176, a LINEAR PIB that comes back as `star`: weight **1.000**, fit
**0.036 dec** described as "a genuinely good fit", and **no alternative inside
dAICc 10**, so the alternatives section is empty. Nothing in the standard
report signals any doubt at all. Also exposed, and NOT addressed: the
pre-filter had struck `reptation` (no wide plateau) on that same curve, so the
plausibly correct class was never on the ballot and `star` won unopposed - and
the report states both facts without connecting them.

**RETRAINED on the laptop (seed 0, the script default - the published run was
seed 1).** Being a different seed made it more useful than a repeat:
accuracy **0.922** vs the published 0.923, regime 0.999, merged-pair 0.963,
`star` 0.984, cured<->gel still 0 errors. Three things worth carrying:
1. **The seed instability has largely resolved.** This file records
   `rouse_screened` at **0.20 on seed 0**; it now reads **0.651**, and overall
   accuracy is within 0.001 across the two seeds.
2. **The published "+0.016 margin" over the physics baseline is not a
   resolvable number.** The baseline is n=150, sampling error ~+/-0.027, i.e.
   bigger than the margin. Across seeds the baseline moved 0.907 -> 0.860 and
   the margin +0.016 -> +0.062 while the network side barely moved. Say "at
   least as good as the physics baseline, gap not measurable at n=150".
3. `star`'s 4 errors here include **2 to `branched`**, where the seed-1 run's
   single error went to `wormlike_micelle` and was read as evidence the two
   brains do NOT disagree about what absorbs stars. Four errors is far too few
   to overturn that, but it is no longer clean evidence for it either.

**Environment gotcha fixed:** `git push` hung indefinitely - git was set to
Git Credential Manager, which blocks on an invisible GUI prompt in a
non-interactive shell. `gh` was already authenticated, so `gh auth setup-git`
fixed it permanently. Expect this on any fresh Windows PC.

**Also confirmed while answering a user question, worth not re-investigating:**
on this laptop `python` on PATH is `WindowsApps\python.exe`, a **0-byte
Microsoft Store alias**, not an interpreter. That is the state environment.md
prescribes ("do not install Python"), not a fault - but it means any bare
`python` invocation opens the Store instead of running code. Everything goes
through `uv run`. uv, git, gh and code all resolve normally in a
newly-opened terminal (verified against the registry PATH); only the
mid-session shell had a stale PATH.

**LEFT UNVERIFIED - first job next session.** The star caveat and its two
tests landed at the very end. `tests/test_report.py` passed 25/25, which does
cover the changed code, but the confirming FULL non-slow run was stopped
mid-run at the user's request (end of day). Expect **196 passed, 2 skipped**.
Run it before building anything on top.

**Next task is set in next-actions:** the neural head as `report.py`'s second
column - the two brains' AGREEMENT as a confidence signal neither
self-confidence can provide. Needs a checkpoint, which does not travel in git.

---

## 2026-09-09 (office PC, part 2) — star REAL-DATA validation: two bugs found and fixed

Continued the same session. User supplied two papers into `originals/`
(`ma9815556.pdf` Santangelo-Roland-Puskas 1999; `ma980060d.pdf` Milner-McLeish
1998) and then hand-digitized both into xlsx. **This is step 4, the real-data
validation of `star` that had been blocked since the class was built.**

**New files:** `scripts/prep_santangelo.py` -> `data/santangelo1999.npz`
(2 six-arm PIB stars + a LINEAR control, Tref 80 C), `scripts/prep_mm1998.py`
-> `data/mm1998.npz` (7 monodisperse four-arm PI stars, Z = Ma/Me = 2.3-21),
`scripts/validate_star_real.py`.

**Digitizing traps recorded in the prep docstrings, both caught by checking
rather than assuming:**
- MM1998's column order is **REVERSED vs the Fig. 1 caption**. "In order of
  increasing terminal time" means the LEFTMOST curve is the LARGEST arm, so
  `w1` = Ma 105k, not 11.4k. Verified from the data (G'' peak moves
  monotonically 0.32 -> 21.9 rad/s).
- MM1998 moduli are **dyn/cm^2, not Pa** (x0.1). Established from physics: as
  dyn/cm^2 the plateau is 310-420 kPa, matching PI's known ~0.4 MPa; as Pa it
  would be 3-4 MPa, an order of magnitude too stiff.
- Santangelo's axes are `a_T*omega` and `b_T*G'` — MASTER CURVES. The
  temperature suffixes are PROVENANCE, not interpretation temperatures
  (user confirmed); both isotherms per sample concatenate into one 80 C curve.

**THE HEADLINE: fitting known-Z data exposed TWO REAL BUGS in `star.py`.**
Z came back wrong by a median 44%, systematically HIGH, with good-looking rms —
the project's own "good fit of the wrong parameters" mode.
1. **The eq-29 prefactor was 2x too large** — and this is the AUTHORS' OWN
   ERRATUM, printed in MM1998's Appendix under eq 10: *"This is eq 29 of ref 1
   with an additional factor of 1/2, which was mistakenly omitted in the
   earlier paper."* star.py was transcribed from the 1997 paper, so it
   inherited the mistake. The erratum was sitting unread in `originals/`.
   Small effect alone (a constant prefactor is a rigid shift tau_e absorbs).
2. **The arm's own Rouse modes were missing** — the larger effect. MM scope
   eq 26 explicitly (1997 section IV, comment 1) to *"the terminal region up to
   the start of the high-frequency Rouse regime [the minimum in G''(omega)]"*;
   their Fig. 5 shows data rising away above the theory there. A real SAOS
   window extends past that minimum, so the fitter widened the spectrum —
   i.e. inflated Z — to cover a region the retraction integral cannot reach.
   Added `_arm_rouse_modes`, REUSING the already-validated Likhtman-McLeish
   eq-19 form from `tube.py` rather than inventing physics; `arm_rouse=False`
   recovers the paper's bare result and the analytic tests use it.

**Measured effect (5 samples with Z above the bounds floor):** median |Z error|
**44% -> 30%**, every rms improved, fitted G_N **440-490 -> 366-436 kPa**
against PI's true ~400, and the systematic top-band G'' deficit at known Z
(-0.21..-0.37 dec) is gone. **New consequence, tested:** G' now rises ABOVE
G_N at high frequency (~2.4x on a wide window) — G_N is the plateau LEVEL, not
the curve maximum.

**A performance bug I introduced and caught.** The first version bounded the
mode sum by tau_e, which at the top of fit_star's bound reached ~3.7 MILLION
modes and a 60x3.7M temporary per call — one fit took minutes and timed out.
Fixed by truncating on the WINDOW instead (modes far below the fastest measured
time contribute nothing). Convergence verified at 1/2/3/4 decades of floor;
worst case **193 ms -> 4 ms**.

**Process note worth keeping: I nearly did the wrong thing twice.**
- Diagnosed `torch 2.13.0+cpu` + idle nvidia-smi as a broken env and was about
  to edit pyproject.toml — environment.md already documented it as intended
  Windows behaviour that "must not be fixed with a per-PC torch variant".
- Reported "+2%/+9% Z recovery by excluding the Rouse wing" from ONE favourable
  cutoff; testing 0/1/1.5/2 decades gave 44/35/48/36% — non-monotonic, no real
  effect. Retracted. There was also no wing in that data to exclude (G'' is
  monotone to the window edge in all seven curves).
Both times the fix was to read the notes/paper before acting on process state.

**Status at session end:** 31 star tests pass (28 + 3 new). Real-data benchmark
held **6/6**, `identify()` returned `star` on **5/7** MM1998 stars (the two
misses are the highest-Z arms -> `branched`).

**Cannibalisation check DONE and PASSED** — matched before/after, seed 11,
n=20/class, OLD model reproduced exactly by monkeypatch:
overall **0.845 -> 0.855**, `star` self-recovery **18/20 -> 20/20**, the other
eight classes **byte-identical**. The star fix cost nothing. (This n=20 run is
an internal before/after only, NOT comparable to the published 0.885 at n=30.)

**NOT done at session end (user stopped for the day):** the full non-slow test
suite was interrupted mid-run — `tests/test_star.py` was 31/31 but the rest is
unconfirmed. And CLAUDE.md's star paragraph + "Current state" still need the
star.py fixes folded in once the suite is green. Both are in next-actions as
laptop tasks.

**Z remains NOT a reportable output** (+17-84% biased); the class says "star",
never "Z = ...". In the module docstring.

**COMMITTED AND PUSHED at session end** (user asked to sync before switching to
the laptop). 7 modified + 5 new files in one commit.

---

## 2026-09-09 (office PC, latest) — 10-class RETRAIN done; star validated on the neural side

Office PC (RTX A1000). User asked "what is next on the agenda", then said go.
Executed the ACTIVE TASK that had been tagged for this machine: retrain the
classifier on the ten-class distribution after `star` landed.

**Ran:** `git pull` (already current), `uv sync` (clean), full suite
(**182 passed, 2 skipped, 5:07**), then
`train_classifier.py -n 16000 --epochs 55 --seed 1`, then
`eval_real_data.py`.

**Results — all 10-class now:** accuracy **0.923** (was 0.917 at 9 classes;
it went UP on a harder problem), merged-pair **0.968**, regime **0.999**,
physics baseline **0.907 on the SAME split** (n=150, `skipped`=0), real data
**6/6** with raw == resampled.

**Three questions the retrain existed to answer, all settled:**
- **`star` = 0.996 (239/240)**, single error to `wormlike_micelle`. NOT
  zimm/rouse (the AICc three-way tie does not reproduce in the network) and NOT
  `branched` (the two brains do not disagree about what absorbs stars).
  => **`star` stays OUT of `AMBIGUOUS_PAIRS`**; the "revisit once a checkpoint
  exists" comment in `ml/evaluate.py` is now answered in place.
- **§1h baseline pairing CLOSED** — same-split baseline at last. The +0.016
  margin must be read against a baseline that rose ~0.82 -> 0.907 *because the
  bank was fixed*, not a weakened network.
- **`rouse_screened` did not collapse** on seed 1 (0.737).

**Unchanged:** 58% of all error is still Zimm<->Rouse; cured/gel still zero.

**A misdiagnosis worth recording so it is not repeated.** Saw `torch 2.13.0+cpu`
and an idle `nvidia-smi` mid-run and concluded the locked env was broken on this
PC; was about to kill the run and edit `pyproject.toml`. `environment.md`
already documented the opposite: **Windows resolves `+cpu` from the shared lock
by design** (CUDA extras carry `sys_platform == 'linux'` markers) and it "must
not be fixed with a per-PC torch variant" — CPU is ~9 s/epoch vs ~11 on a
1660 Ti, i.e. faster. Measured 7.4-10.9 s/epoch this run. The real long pole is
the **AICc baseline after training**, not the epochs. Also had two PIDs
swapped and asserted the wrong one was the test suite. Lesson: read the notes
before reading process state. Rewrote environment.md's GPU section, which had
flatly claimed "resolves to the CUDA build" and caused the confusion.

**Docs corrected** (some were stale independently of the retrain): CLAUDE.md
taxonomy bullet 9 -> **10 generated fine classes**; the "Open gap: `synth.py`
cannot generate `star`" paragraph (closed 2026-09-09 step 3b) rewritten to keep
the derived-`tau_e` design note and the sign-inversion bug lesson; "Current
state" paragraph replaced with the 10-class numbers; `evaluate.py` baseline
docstring nine -> ten; next-actions header + ACTIVE TASK section.

**No active task now.** Next substantive step is **step 4, real-data validation
of `star`** — BLOCKED on the user supplying star melt data (Roovers PB stars /
four-arm PI / Santangelo-Roland PIB). `star` is the only class in the bank with
zero real-data validation.

---

## 2026-09-09 (office PC, later) — Housekeeping: originals/ consolidated into OneDrive

Office PC (RTX A1000). Started as "update yourself and tell me what's next" —
pulled `dbd136e` (the laptop's star-polymer session, already complete and
pushed: star is a fine class, in `identify()`'s bank AND generated by
`synth.py`, so `ml/dataset.CLASSES` is 10 too). No code work this session; it
turned into an `originals/` cleanup at the user's direction.

**Machine identity clarified and saved to central memory:** this is the OFFICE
PC (RTX A1000); the laptop is the GTX 1660 Ti. GPU tells you which is which.

**`originals/` consolidated (commits `df70f00`, `6a5a0cf`).** It was being
copied onto every PC (user: "too many redundancies") and had drifted into a
nested `originals/rheo_fingerprinting/` layout. Now:
- One shared copy in OneDrive at
  `C:\Users\krish\OneDrive - UCB-O365\CUB\ML\rheo_fingerprinting\originals\`
  (same path on every Windows PC). Repo's `originals/` is a **junction** to it
  (`mklink /J`, no admin — a symlink needs admin/Dev Mode). Invisible to git,
  still gitignored. Setup documented in `environment.md`.
- Files flattened; `prep_edera.py` / `prep_ricarte.py` updated to the flat
  paths. Both regenerate byte-identical `data/*.npz`.
- **Paper PDFs renamed to `firstauthor+year`** (`milner_mcleish1997_star.pdf`,
  `tixier2004_pdms_gel.pdf`, `curro_pincus1983.pdf`, …). Doc/comment refs
  updated in `references.md`, `elastomer_litreview.md`, `star.py`,
  `test_star.py` — no code opens those paths. The **digitized-data xlsx keep
  npz-matching names** (`pivo2006.xlsx`, `edera2024.xlsx`, `ricarte2023.xlsx`,
  `likhtman_mcleish2002.xlsx`).
- **`originals/archive/`** with a README: dropped-XPP papers (McLeish-Larson
  98, Verbeeten 01), never-referenced Konstantinou HDPE + Schausberger 1985 PS,
  the original Jupyter notebooks + `codebase/`, notebook-era
  `interpolate_rheology`, `garbage/`, one-off `rheo-fp-report.html`.

**Confirmed `originals/` is NOT in git** (gitignored, fully untracked — not even
`.gitkeep`) — answering the user's worry about it going public. Only the derived
`data/*.npz` are committed, which is what lets third parties run the code.

**Correction:** an intermediate commit note claimed the three star-polymer
papers were laptop-only; they ARE in OneDrive. All present.

**Gotcha for next time — OneDrive locks files while syncing.** Bash
`mv`/`rm` in `originals/` hit "Device or resource busy" repeatedly. Fix: stop
the OneDrive process, rename with PowerShell `Rename-Item`, restart
`C:\Program Files\Microsoft OneDrive\OneDrive.exe`.

**Suite: 182 passed, 2 skipped** (~6 min — the notes' "~17 min" fear was
overstated). Star + report subset re-run after the doc renames: 51 passed.

**Two CLAUDE.md inconsistencies noticed, NOT fixed** (belong with the
post-retrain CLAUDE.md update): it still says "9 generated fine classes" (it's
10) and still carries a stale "Open gap: `synth.py` cannot generate `star`"
paragraph — that gap was closed the same day (step 3b). `synth.py`'s
`FINE_CLASSES` includes `star`.

**Next is unchanged: RETRAIN** (office PC ACTIVE TASK). `checkpoints/rheonet.pt`
is a Sep-3 9-class model.

---

## 2026-09-09 — Star-polymer class: forward physics + inverse recovery (steps 1-2)

Home PC. Sync first: pulled `274c9bf..8510b32` (the 2026-09-07 docs-only
handoff), `uv sync` clean, baseline suite confirmed **151 passed, 2 skipped**
in 10 min. `originals/` present.

**User supplied all three papers on request** — Milner-McLeish 1997
(`ma961559f.pdf`), and when the prefactor could not be pinned down from it
alone, the two precursors it builds on: Ball-McLeish 1989 (`ma00194a066.pdf`)
and Pearson-Helfand 1984 (`ma00134a060.pdf`). Getting the precursors was what
actually resolved the build; see below.

**Built** `rheofp/models/star.py` (forward physics, `fit_star`, `STAR_MODELS`
registry k=3), `tests/test_star.py` (27 tests, ~10 s), `scripts/validate_star.py`.
**Deliberately NOT wired into `identify()`** — the cannibalisation check against
`branched` has not run, and a test asserts `"star" not in ALL_MODELS` to keep it
that way until it does.

**The build was not smooth, and the reason is worth carrying.** Three separate
transcription traps in the 1997 paper, each of which produced a plausible-looking
but wrong model; full detail is in next-actions §ACTIVE TASK and in the module
docstrings. The short version:
  - eq 8 is printed across two lines and reads `(s - 2s^3/3)`; it is really
    `(s^2 - 2s^3/3)`. My first "verification" failed because my *reference*
    was wrong, not the code — worth remembering that a failing check can
    indict the check.
  - eq 29's prefactor: the `15Z/4` pulled out of `U'eff` into the denominator
    has to be divided out of the prefactor. Getting this wrong gave `Z^{5/2}`
    instead of `Z^{3/2}`, which meant **the eq-22 crossover never fired at
    all** — terminal relaxation stayed Rouse-like and the whole alpha
    dependence collapsed to 0.00 decades where the potential demands 1.03.
  - eq 13's `(N/Ne)^2 tau_R` genuinely is `Z^4`; it only looks wrong because
    it is an `s << s*` asymptote evaluated where it does not apply.

**What broke the deadlock was Ball-McLeish, not more algebra.** Their eq 8
writes the same activated time as `t(s) = t_0 exp[U(s)]` and states plainly
that `t_0` is "the Rouse time for an entanglement length" — an O(1) anchor that
immediately rules out a prefactor of `~10^4 tau_e`. Pearson-Helfand eqs 1.9/1.10
supplied the matching fact that the natural diffusive time is built on the tube
FLUCTUATION length, not the full primitive path. Before that I had spent several
iterations moving the discrepancy around rather than closing it, and had
(correctly) stopped and asked for the papers rather than tuning a constant to
match a figure.

**Validation.** eq 24 collapses onto eq 8 at alpha=1 to 3.6e-15; Ueff(1)/U_PH(1)
= 0.257 against ~0.26 read off their Figure 2, and exactly 1/3 at alpha=1 as the
text says; the Pearson-Helfand barrier reproduces the paper's quoted
log(tau(1)/tau_0) = 13.8; eq-22 handoff lands at s = 0.183 where the text wants
~0.2; terminal slopes exact; G' recovers 0.963 G_N; G'' spans ~5.9 decades
against "five decades". Planted recovery exact (rms 0.0000 dec), and Z survives
2% noise to within 0.4%. Z is not degenerate with tau_e — profile cost 5.9e-29
at the true Z=17 vs 1.6e-02 one unit away.

**Two limits found while fitting, both now pinned by tests.** (1) At low Z with
the plateau cropped away, Z is not recoverable under noise (~20% error) even
though the profile minimum is still correct — so Z must never be reported from a
terminal-only sweep. (2) **Past Z ~ 40 the model predicts TWO G'' maxima**, the
Rouse and activated relaxations having separated; converged for n_s 400..64000,
so it is physics, not quadrature. This one has teeth beyond the star class:
**any feature or pre-filter that assumes a single loss peak will misread a
high-Z star** — the same shape of bug as the `has_shoulder` discard fixed on
2026-09-07.

**Step 3 (cannibalisation) also done this session, and `star` is now WIRED IN.**
`scripts/check_star_cannibalisation.py`, n=30 planted cropped noisy curves per
class, identical seeds through both banks. Result: real data **6/6 -> 6/6**,
eight of nine existing classes identical, `branched` 30/30 both ways, `star`
self-recovery 29/30. **The finding that justifies the class: with the 9-model
bank, `branched` (BSW) absorbed 25/30 planted star melts silently and
confidently** — the same "good fit of the WRONG class" failure documented for
vitrimers, now confirmed for a second architecture and previously invisible.

**The one cost was `zimm` 23/30 -> 21/30, and I checked both before wiring.**
They are exact ties: identical rms to four decimals at identical k=3, dAICc
0.07 and 0.00, with `rouse_screened` tied alongside on one of them. AICc has no
parsimony lever between two k=3 models, so the winner is float noise. `star`
joined the known Zimm<->Rouse degenerate cluster rather than displacing
anything. **User approved wiring in on that evidence.**

Two hypotheses I formed and then disproved, worth not re-treading: (a) "star
cannot impersonate zimm" — false, it fits 11/30 of the generator's cropped
noisy zimm curves under FLOOR_CHI2, though the fit overlap is far larger than
the classification damage because ties don't move winners; (b) "cropping causes
the overlap" — false, correlation with window width is +0.06, i.e. nil. I had
stated (a) too confidently on 6 clean curves before the larger run corrected it.

**Wiring opened a REVERSE invariant gap, now declared rather than left silent.**
`synth.py` cannot generate `star`, so the bank can emit a class the neural head
has never seen — the mirror image of the wormlike_micelle bug (there a
generated class was unanswerable; here a bank class is untrainable). Added
`test_bank_classes_the_generator_cannot_produce_are_declared` listing `star` as
a known deliberate exception, so any further drift fails.

**Byproduct finding, separate from the star work and untouched:** `has_shoulder`
fires on 92% of planted stars (the Z >~ 35 two-peak split) but ALSO on 72% of
`branched` and 75% of `reptation`, which have no stickers — and only 62% of
`sticky_rouse`. So report.py:240's "characteristic of a reversibly associating
network" overstates it for every class, not just stars. Flagged for a decision.

**Step 3b — `synth.py` now generates `star`**, closing the reverse bank/generator
gap the wiring opened. `tau_e` is DERIVED rather than drawn: a star spans ~23
decades against a ~4-decade window, so the terminal time is anchored to the
window and tau_e back-computed from Z. **Caught a real bug doing it** — the
first offset range gave `terminal_reached` **0%**, i.e. no planted star ever
flowed, which would have taught the classifier that stars never reach terminal
flow. Fixed to 51% (n=120). Same shape as the fixed-60-point density bug: a
sampling artifact that would have been learned as physics.

**`has_shoulder` investigated at the user's request, then LEFT ALONE by user
decision.** Full numbers in next-actions §2b-bis, marked DO NOT RE-INVESTIGATE.
The finding is worth carrying anyway: the detector fires on NOISE, not shape —
noise-on vs noise-off on the same population gives 63-95% across every class
versus 0-15%, and `cured_elastomer` (no second G" peak by construction) trips
it 85% of the time. Separately, the shoulder is genuinely absent from ~90% of
windows even for clean sticker curves, so no prominence threshold rescues it —
swept 0.02/0.05/0.10/0.20 and none separates the sticker classes. **This
vindicates the 2026-09-07 has_shoulder fix on stronger grounds than existed
then**: the old discard would have deleted the correct vitrimer class in the
large majority of cases, not merely in principle.

**Three things I got wrong this session and corrected, all now recorded with
measurements rather than my reasoning:** (1) claimed `star` was the suite's
performance bottleneck — it is third, behind `branched` and `sticky_reptation`,
and `N_S` is a useless speed dial since the cost is in restarts; (2) claimed
"star cannot impersonate zimm" from 6 clean curves — on the generator's cropped
noisy population it fits 11/30 under FLOOR_CHI2; (3) attributed the star
shoulder rate to the Z>=35 two-peak split — it is noise, and the rate is nearly
flat in Z. Also broke a `test_report.py` assertion by rewording a sentence such
that `_wrap` split the phrase it checked; fixed the test to check the structured
field instead of rendered text.

**Next, and it is FOR THE OFFICE PC** (user's call, 2026-09-09): **retrain**.
The checkpoint is stale — ten classes now — so every published ML number is a
9-class measurement. Full instructions and what to watch for are in
next-actions under ">>> ACTIVE TASK FOR THE OFFICE PC <<<". Step 4 (real-data
validation of the star class) stays blocked on star melt data.

---

## 2026-09-07 — Promoted branched + wormlike_micelle; framework sweep; latent NaN found

Home PC (RTX A1000, `originals/` present). Session began as a walkthrough of the
2026-09-04 commit and turned into two decisions and a cleanup pass.

**Explained "MODEL_ONLY_CLASSES is documentation, not behaviour" to the user,
and it led to a decision.** Demonstrated it concretely: a planted `branched`
curve returns `best='branched'` at weight 1.000 — the constant was defined in
two modules, read by nothing but two test assertions, and never coerced anything
to regime level. **User decided: promote.** Their words — *"i am happy with
saying 'your sample is branched'"*. Asked about `wormlike_micelle` separately
rather than sweeping it along; user promoted it too. That empties the tier, so
`MODEL_ONLY_CLASSES` is deleted outright and `ALL_CLASSES == FINE_CLASSES`
(**9 fine classes**). No behaviour changed and no accuracy number moved — the
docs now match the code instead of describing an intent nobody built.

Evidence gathered before promoting, not after: BSW fits real LDPE ~0.06 dec with
errors landing on zimm/rouse rather than reptation; `wormlike_micelle` measured
**40/40 self-correct** at mean weight 1.000, stealing no correct answers from any
other class (n=40/class). That also closes the 2026-09-04 "run a proper
sticky-vs-WLM confusion check" item — the suspicion came from 2 of 12 vitrimer
curves landing on WLM, but that traffic is the `has_shoulder` pre-filter deleting
the sticky classes (§1k), not WLM being greedy. Two bugs, one symptom.

**Measured §1k properly while answering a user question about it.** The user
asked whether a wormlike micelle could be confused with a vitrimer. It cannot —
WLM is 40/40 — but the mirror image is bad: `signature_features` strikes the
sticky classes off the ballot in **39/40 (sticky_rouse)** and **21/40
(sticky_reptation)** on full-window noiseless curves. Downstream, planted
`sticky_rouse` lands on `reptation` 58%, `branched` 15%, `cured_elastomer` 8%
(a dynamic network called permanent). Sharper than the notes' earlier
"4 of 12". User asked whether deleting vitrimer would make the problem go away;
verified the rule touches only those two classes and no other class's accuracy
depends on them (7-class sweep, all top-answer-correct), so the cut would be
clean — but **user chose to keep vitrimer and fix the rule instead.**

**Framework-wide sweep for obsolete/redundant code (user asked).** AST pass:
only 3 of 89 public functions unreferenced, 2 of those legitimate public API
(`G_of_t` documented for plotting, `fit_linear_melt` the LM fitter). Archived
rather than deleted, with a README in each archive dir saying what superseded
what: 7 orphaned npz files from the original restructure and the notebook-era
`prep_interpolate.py` (superseded by `resample_log_grid`). Removed
`pompom.load_samples`, a narrower duplicate of `io.data.load_xlsx`.
Confirmed `branched_spectrum`/`fit_branched` are NOT dead — they are the live
negative control proving BSW was needed. 24 MB `synthetic_train.npz` is
correctly gitignored.

**The sweep found a real latent bug.** An exact fit on a noiseless synthetic
curve gives `sse == 0` -> `aicc = -inf` -> the winner's delta is
`inf - inf = NaN` -> **every Akaike weight is NaN**, while the winning name
still looks right because it sorts first. Measured pre-fix on a planted zimm
curve: `best_weight nan`, deltas `[nan, inf, inf, inf]`. Real/noisy data never
reach zero residual so it stayed hidden — but **the planned `explain()` layer is
built entirely on these deltas and would have been reading garbage.** Fixed with
`SSE_FLOOR = 1e-30` in `fit_model`; regression test added. Lesson: the numbers a
feature will depend on are worth checking before building on them.

Suite **125 -> 126 passed / 2 skipped**. Real data still **6/6** on both raw and
resampled. Two commits, not yet pushed at time of writing.

**Then fixed `has_shoulder` (same session).** User rejected merging
sticky_rouse + sticky_reptation into one "vitrimer" class — entangled vs
unentangled is real recoverable information, unlike the degenerate Zimm/Rouse
pair — and asked for the fix instead. Removed the discard; both sticker classes
are always on the ballot now. Pre-registered before/after, planted cropped noisy
curves, n=30/class, identical seeds: `sticky_rouse` **18/30 -> 29/30**,
`sticky_reptation` **26/30 -> 28/30**, overall **0.837 -> 0.885**, real data
**6/6 -> 6/6**, and the per-class table diff is exactly two lines — the two k=4
models cannibalised nothing. Vitrimer-reported-as-permanent-network: **0/120**.
Worth noting the earlier full-window noiseless measurement (39/40 struck)
OVERSTATED the problem; on the realistic cropped+noisy path it was 11/30. Cost
is latency: ~1.9 s/curve, suite 2m21s -> 4m30s. Two regression tests added.

**Then built `explain()` (same session).** `rheofp/report.py`,
`scripts/explain.py`, `tests/test_report.py` (13 tests). Suite **126 -> 141**.
Both worked examples reproduce: Tixier gel delta 2.4 with `cured_elastomer`
fitting BETTER (0.0107 vs 0.0108) and the report saying "nothing in your
measurement contradicts that"; Pivokonsky E delta 79.3, reads decisive.
`--why-not X` fits a class the user believes in — including one the pre-filter
struck off — and reports its case.

**The unplanned win: the least-bad-winner flag catches the two-plateau blend,**
the single out-of-scope probe BOTH §1j detectors failed on. It cannot identify
the blend, but it prints "NOTHING IN THE BANK FITS THIS DATA WELL" where the
Akaike weight said 0.9+ confident. The OOD problem answered from the reporting
side instead of the detection side — which is what the design predicted and is
now demonstrated rather than argued.

Small correction carried into the notes: "weights collapse to 1.000/0.000" is a
tendency, not a law (the Tixier winner is 0.766). It is why the report ranks on
delta AICc and absolute residuals rather than weight.

**Then the user improved the design.** After I explained that the misfit flag
only catches out-of-taxonomy material that fits BADLY - and that the dominant
error mode (a good fit of the wrong class) gets no warning at all - they
instructed: *"just give the warning for all matches by default - good, bad,
false positive whatever."* Implemented as `challenge()`, printed
unconditionally under "DON'T THINK IT'S X? THIS MAY BE WHY". The reasoning is
sound and worth keeping: **a caveat that appears only when a test trips teaches
the reader that a quiet report means a sure answer**, which is precisely the
inference this classifier cannot support. The section carries a footer saying
it is always printed, so its presence is not misread as a warning. Content is
per-measurement, not boilerplate: absolute fit in both directions, named live
alternatives within delta 10 with their numbers, unfitted classes, window
limits, and the standing nine-class limit. Suite **141 -> 146**.

**FIRST REAL TEMPERATURE STACK (same session).** User supplied
`originals/rheo_fingerprinting/edera2024.xlsx` — digitized Fig. 3a-d of Edera,
Chappuis, Cloitre & Tournilhac (2024, Polymer; preprint arXiv:2401.10569),
an epoxy/Zn(acac)2 transesterification vitrimer. This paper was chosen from a
search because it publishes RAW UNSHIFTED per-temperature sweeps, which almost
every vitrimer paper omits in favour of a master curve alone. `prep_edera.py`
-> `data/edera2024.npz` (4 temperatures, T_K attached); `eval_edera_stack.py`
runs the evaluation. Panel->temperature was ambiguous (the caption orders
CURVES right-to-left, not panel labels) so I asked rather than guessed; user
confirmed a=180C, b=85C, c=75C, d=30C, which is also what the moduli require
(G' rises monotonically as T falls, tan_d peaks in b at the alpha-relaxation).
Columns are ragged (a and d carry one point fewer) — dropna per column, never
per row, or the longer panels get truncated.

**Result, split cleanly in two:**
- **The mechanism WORKS on real material.** `resolve_melt_vs_network` returns
  verdict **"melt"** across the stack (2.50 decades of shift) — i.e. it
  correctly refuses to call a dynamic network permanent, which is the single
  distinction the temperature stack exists to make and the flagship molecular
  claim of the product. `identify_stack` then overturns its own
  single-curve `critical_gel` call and abstains. **This closes the
  longest-standing gap in the project: the stack was synthetic-only until now.**
- **The fine class FAILS.** No curve is identified as a vitrimer; three of four
  land on critical_gel, one on cured_elastomer (the 85C curve does abstain).

**But this dataset is deliberately hostile and the failure must not be
overread.** I chose the paper *because* the material is thermo-rheologically
complex — its central claim is that time-temperature EQUIVALENCE fails (two
relaxations, ~680 and ~130 kJ/mol). Measured that independently: the log10
tan_delta VALUE ranges of the four curves mostly do not overlap AT ALL, and a
horizontal shift cannot move a curve vertically, so those alignment residuals
(1.04, 2.40) are irreducible by construction, not a bug. Also 2 of 4 curves are
glassy or near-glassy — a regime deliberately dropped from the taxonomy, so
out-of-scope material — and only the 180C curve sits squarely in the rubbery
bond-exchange regime the sticker models describe. One curve is not a stack.

**Live test of the new challenge layer, mixed result worth keeping:** the 75C
curve trips `nothing_fits` (0.168 dec), but the genuinely out-of-scope GLASSY
30C curve does NOT (0.136 dec, "poor" but under FLOOR_CHI2) — it is reported as
critical_gel without the strongest warning. Confirms the caveat already written
into the layer: the misfit flag catches out-of-taxonomy material only when it
fits badly ENOUGH, and 0.15 decades is a threshold, not a truth.

**SECOND REAL STACK, the FAIR test — Ricarte (2023), same session.** User
supplied `ma3c00883.pdf` + SI and then `ricarte2023.xlsx` (Fig. 3A only).
Confirmed from the SI that Figs. 3A/S14A/S15A/S16A are captioned "SAOS **as
measured**" with the shifted version beside them in panel B — the arrangement
we wanted. PB-v-4, dioxaborolane-metathesis polybutadiene, 5 temperatures
(80-160 C), omega 0.01-100 rad/s. `prep_ricarte.py` -> `data/ricarte2023.npz`,
`eval_ricarte_stack.py` for the evaluation.

**Data limitation found before trusting it, user informed and chose to
proceed:** G' is BYTE-IDENTICAL across all five temperatures — one traced curve
copied into five columns. The paper does say G' is "approximately constant", so
this is a small distortion rather than a wrong one, but per-T G' scatter and any
vertical b_T signal are absent BY CONSTRUCTION and no result may be read as
evidence about them. Temperature information lives entirely in G''.

**This is the fair test Edera could not be** — TTS demonstrably works for this
system, all five curves are in the rubbery/bond-exchange regime, five
temperatures is a real stack. None of the Edera excuses apply.

- **Mechanism: WORKS, second real confirmation.** Alignment residuals
  **0.0012-0.018** (vs Edera's 1.04-2.40 — these spectra genuinely superpose).
  Verdict **"melt"**, correctly refusing a permanent-network call. Our
  independently measured shifts are Arrhenius to **R^2 = 0.9922**. Magnitude
  36.7 kJ/mol vs the paper's 15.1 — recorded as a ~2x discrepancy, NOT claimed
  as agreement; different windows and the shared-G' artifact both bear on it.
  The linearity is the real result.
- **Fine class: FAILS, and this one counts.** All five temperatures return
  **`branched`**, never a sticker class, at fits of **0.047-0.084 decades** —
  i.e. GOOD fits, so no misfit flag fires. Exactly the failure mode the report
  layer was built to expose and explicitly cannot repair: a good fit of the
  wrong class.
- **Contest mode did its job diagnostically.** At 120 C: `sticky_rouse` dAICc
  167 at **0.203 dec**, `sticky_reptation` dAICc 246 at **0.399 dec**, against
  branched's 0.047. The sticker models are not narrowly losing on parsimony —
  they cannot reproduce this curve at all. A broad BSW spectrum simply
  describes a nearly-flat G' with slowly-rising G'' better than they do. That
  is a FORWARD-MODEL finding, not a ranking bug, and it is the most actionable
  thing to come out of either real stack.

**Honest overall position after two real stacks:** the regime-level answer and
the dynamic-vs-permanent call are right on real material; the fine sticker
classes are not recovered from real vitrimer data. The `has_shoulder` fix
earlier today was necessary but is clearly not sufficient — it put the sticker
classes on the ballot, and they lost on merit.

**Investigated it immediately (§2b), and it is ANSWERED.**
`scripts/diagnose_sticky_models.py`. Tested fitter / bounds / functional form
in that order on Ricarte 120 C:
- Fitter: NO (12 vs 200 restarts agree to 4 dp).
- Bounds: PARTLY — freeing the mode ceilings gives sticky_rouse 0.203->0.161
  and sticky_reptation 0.390->0.131, but both plateau far above BSW's 0.046,
  and sticky_reptation's `Z` runs to ANY ceiling (197/590/1968/7870) with RMS
  frozen at 0.1305. A runaway nuisance parameter.
- **Functional form: YES.** All models fit G' fine; the ENTIRE failure is G''
  (sticky 0.18-0.23 vs BSW 0.065).

**Physics:** the real curve has G' flat to 0.019 dec and G'' RISING as omega
falls (low-w slope **-0.70**); a terminal zone needs +1. It is a power-law
wing, which the paper independently states ("rubbery plateau into a power law
regime", true terminal outside the window). Both sticky models are a few
discrete Maxwell modes about one tau_s, so they produce a G'' PEAK that must
fall away either side — they cannot rise monotonically for 4 decades. Piling up
modes is the only escape, hence the pinned Nst/Z. BSW wins because its wedges
ARE a broad continuous spectrum.

**I made a claim mid-investigation and corrected it.** I first concluded the
synthetic training population was the wrong shape. It is not — synthetic
sticky_rouse's low-w G'' slope is -0.71 vs the real -0.70, and identify()
recovers synthetic sticky curves 9/10. The real difference is G' span: 0.019
dec real vs ~0.26 synthetic, **~10x flatter**. The models work on the
population they were built from; this material sits at an extreme edge of it.
Widening the synthetic G' range would make training more representative but
would NOT close the 0.16-vs-0.046 gap — that is the forward model's.

**Left as an explicit user decision, deliberately NOT chosen:** (a) give the
sticker classes a broad-spectrum forward model — risk being that it converges
on BSW and stops being distinguishable from `branched`, worse than an honest
failure; or (b) accept the limit and make it explicit in the challenge section,
naming the measurement that would separate them. (b) follows the melt-vs-rubber
precedent. Cheap and safe either way: widen SR_BNDS/SREP_BNDS, which
demonstrably bind.
  *[Correction added 2026-09-11: the "cheap and safe" half of that sentence was
  wrong and is now measured — widening was tested under the cannibalisation
  protocol and REJECTED (costs 10 curves, hurts `sticky_rouse` most). The
  "demonstrably bind" half stands; it just does not imply the bounds should be
  freed. See the 2026-09-11 entry.]*

**User decided: option (b).** Keep the sticky models, make the ambiguity
explicit instead. Implemented `branched_vitrimer_contradiction()` in
`report.py` — fires when the winner is `branched` and the curve shows both a
NEGATIVE low-w G'' slope (power-law wing) and a near-flat G' (<0.3 dec span).
Calibrated against measurement, not asserted: 0 false positives across 31
synthetic `branched` winners (mixed truth), both real Pivokonsky LDPE curves
pass clean, only real vitrimer data trips it. Threaded `w, Gp, Gpp` as optional
params through `explain()`/`challenge()` (default None, check silently skipped)
rather than touch identify()'s contract. 5 new tests, suite 146 -> 151.

**Next:** ~~widen SR_BNDS/SREP_BNDS under the cannibalisation protocol (they
demonstrably bind per §2b, cheap and safe, not yet done)~~ — **DONE 2026-09-11
and REJECTED; "cheap and safe" was wrong, it costs 10 curves and hurts
`sticky_rouse` most. Bounds unchanged. See the 2026-09-11 entry.**; then the neural head
as the report's second column.

**End-of-session: audited the taxonomy for missing MOLECULAR architectures
(user request), scoped star polymers as the next addition.** User asked
"am I forgetting common models?" with the molecular-not-macroscopic filter
already established. Audit against the existing `docs/rheology_models.md`
wishlist plus the frozen taxonomy found the wishlist is mostly macroscopic
material categories (bitumen, food, cement — rightly out of scope), but
**star polymers are missing entirely and aren't even on the wishlist.** This
matters because `branched` (BSW, an empirical broad spectrum) will silently
absorb a star melt today — the same "good fit of the wrong class" failure
just found for vitrimers, on a different molecular architecture. Also flagged,
lower priority: comb/H-polymers (same family), block copolymers (ordered
microphase-separated melts show a power-law plateau and would likely be
misread as `critical_gel` — a real cross-class error, not a near-miss),
bidisperse/polydisperse blends (double reptation — already the one probe both
§1j OOD detectors missed), filled/nanocomposite melts. Recommended stars
first: same theoretical family as the already-validated Likhtman-McLeish work,
real data is abundant (four-arm PI stars, Roovers PB stars, Santangelo-Roland
star PIB), and it's a direct test of what `branched` actually means.

**Scoped, not built.** Theory is Milner-McLeish (1997, Macromolecules 30,
2159) — parameter-free given `tau_e`/`G_N` (already have both from
Likhtman-McLeish), arm retraction against an entropic potential U(x)
(exponential in retraction depth x, hence the very broad spectrum), dynamic
dilution Phi(t)^alpha as outer segments relax and act as solvent for inner
ones, G*(omega) assembled by integrating over x in [0,1]. Real finding worth
keeping: **arm number f barely affects LVE** — this would identify "star" but
not "how many arms". Most machinery is reusable (`maxwell_spectrum`,
`multi_restart_fit`, the `(forward,p0,bounds,k)` registry pattern); new code
is realistically ~100-150 lines, comparable to `network.py`.

**Two real risks flagged before any building starts:**
1. **Could not obtain the actual 1997 paper** — it's paywalled and open
   reviews (checked PMC6572337) analyse MM rather than derive its equations.
   Transcribing tube theory from memory is exactly what the validation-first
   rule exists to prevent. **BLOCKED on the user supplying the PDF** into
   `originals/` before any code is written.
2. **May not beat BSW on AICc** even with the paper in hand — a star's
   spectrum is broad, same shape family as BSW's empirical wedges. The
   mitigating factor: MM is ~2 effective params (Z_arm + modulus scale) vs
   BSW's 5, so parsimony should favour a correct star identification if the
   fit is even comparable. Must run the same before/after cannibalisation
   check against `branched` as every other addition this session, and the
   informative result either way is what happens to `branched`'s accuracy on
   the real Pivokonsky LDPE curves.

**User: proceed tomorrow.** Nothing built. Journal, next-actions and the
cross-PC docs updated and pushed to close out this machine's session.

---

## 2026-09-04 — New Linux PC; found + closed a 9-vs-8 class asymmetry between the two "brains"

**Fourth machine** (Linux, `Documents/projects/rheo-fingerprinting/rheo-fp`).
No uv, no `.venv` — installed uv 0.12.10 via the standalone script to
`~/.local/bin` (no sudo, per environment.md; do NOT use the distro package
manager). `uv sync` built the env clean; torch resolved to the **CUDA** build
as designed on Linux, though this box has no `nvidia-smi` so training would run
CPU. Baseline confirmed **120 passed / 3 skipped** (`-m "not slow"`) before
touching anything. `originals/` is ABSENT here; nothing needed it.

**Session was a Q&A walkthrough of the project, and one question found a real
bug.** While tabulating the material classes I noticed the generator and the
neural head carry **9** classes while `identify()`'s bank carries **8** —
`wormlike_micelle` had forward physics and a fitter in `maxwell.py` but no
`(forward, p0, bounds, k)` registry entry, so the AICc identifier could never
emit it. Full detail in next-actions.md §1h. The two things it broke:
- **The published physics baseline was measured wrong.**
  `physics_baseline_accuracy` filtered its pool by the *neural* class list —
  a no-op — so ~1/9 of its exam was unanswerable and its ceiling was 0.889.
  Re-measured on one fixed pool (n=90): 8-model bank **0.711**, 9-model bank
  **0.822**. The 0.711 reproduces the published 0.700, which is what confirmed
  the diagnosis. So **"0.917 vs 0.700" overstated the margin — it is nearer
  +0.10 than +0.217.** The network's own 0.917 is untouched.
- **A missing class does not look like low confidence.** 12 planted micelles
  through the old bank: `branched` 11/12, median Akaike weight **1.000**,
  median residual 0.05 decades, `low_confidence` fired once. BSW fits a
  near-single-Maxwell shape easily, so `FLOOR_CHI2` never trips. Worth
  internalising: **the none-of-the-above floor cannot catch an absent class —
  the most flexible candidate in the bank swallows it.** Same blind spot as the
  known abstention limitation, arriving down the physics path. It also means
  the BSW cannibalisation check on 2026-09-03 was necessarily incomplete: it
  could only test against classes already IN the bank.

**Fixed**, with the cannibalisation check run *before* wiring, as with BSW:
no existing class lost a correct answer (per-class hits identical 8- vs
9-model), `wormlike_micelle` 0/5 -> 5/5, real data still **6/6**. Added
`WLM_MODELS` (k=4; `beta` linear not log10, matching synth's parameterisation),
merged into `ALL_MODELS`, reconciled `MODEL_ONLY_CLASSES` — which had two
different values under one name in identify.py and synth.py — and pointed the
baseline's pool filter at the bank, with a `skipped` count so a future
divergence shows up in the report instead of in the score. Suite **120 -> 125**
(`-m "not slow"`), and one previously-skipped bounds-drift parametrisation now
actually runs (3 skips -> 2), which is the test that would have caught this
years earlier had the bank been in its `banks` dict.

**Deliberately NOT done:** `MODEL_ONLY_CLASSES` is still not enforced anywhere —
`branched` and `wormlike_micelle` are scored as ordinary fine labels in both
identify.py and ml/evaluate.py. That is a FROZEN-taxonomy change and belongs
with the standing §3 decision about promoting `branched`, not as a side effect
of a bug fix. Recorded in §3.

**Then the session turned into a design conversation, and two bigger things came
out of it.**

**1. SCOPE CLARIFIED by the user, and it invalidates a chunk of my afternoon.**
The product classifies **molecular / microstructural architecture** — linear vs
branched melt, elastomer vs vitrimer, cured vs critical gel — NOT macroscopic
category. Their point: *"a soft paste, foam is macroscopic - anyone can see that
just by looking at it."* I had spent a long stretch trying to build an
out-of-distribution detector using a soft-glassy paste and a Herschel-Bulkley
solid as the threat model. Those are the wrong targets. Now recorded at the top
of CLAUDE.md so nobody repeats it. Note the one on-target probe I happened to
use — a two-plateau polymer blend — is the one both detectors failed to catch.

**2. OOD detection: two approaches, both failed validation. Full write-up in
next-actions §1j.** Short version: a residual-structure (runs) test separated
synthetic cases perfectly but flagged the correctly-classified Pivokonsky melts
harder than the genuinely foreign material. Diagnosis — the runs statistic is a
SIGNIFICANCE score growing like sqrt(n), and the scores tracked point count
(11 pts -> -0.29 ... 90 pts -> -8.90) rather than wrongness. A relative-margin
variant was better but hit the same wall. **I raised an alarm mid-session that
`branched` might be a weak explanation of real LDPE, and then retracted it** —
the deciding experiment showed Darby (also real, also digitized) reaches -0.28,
so real data CAN give clean residuals and Pivokonsky's flag was a sample-size
artifact. Lesson worth carrying: do not compare significance scores across
datasets of different size; use an effect size.
Two controls did hold and are worth keeping: the machinery is sound when the
model IS the truth, and **flexibility does not launder a wrong model** (4 -> 20
free parameters moved the out-of-scope structure score not at all).

**3. Found a live defect at the heart of the molecular scope — next-actions
§1k, NOT fixed.** `signature_features` strikes BOTH vitrimer classes off the
ballot whenever no second G″ peak is visible. That is missing-evidence
reasoning — the same fallacy this project already rejected for melt-vs-rubber —
and it measured 4 of 12 generated vitrimer curves deleted before scoring, one
returned as `cured_elastomer`, i.e. a dynamic network reported as permanent.
The general principle, now in CLAUDE.md: **a hard discard is sound only when it
rests on a positive observation.** `terminal_reached` qualifies; `has_shoulder`
does not. Good news: `identify_stack` rescued all 6 vitrimer stacks I threw at
it, which makes the untested-on-real-material temperature stack the single most
load-bearing gap in the project.

**User approved a design (built NOTHING — instructions only, deliberately).**
They accepted that being confidently wrong is tolerable *if the reasoning is
visible and arguable*, which sidesteps the detector problem entirely and is the
better product anyway: under the molecular scope a user cannot referee
"elastomer or vitrimer?" by eye, so the evidence must. Three decisions recorded
as the ACTIVE TASK at the top of next-actions.md: report pre-filter discards now
but measure before removing the shoulder rule; put the report in a NEW function
over `identify()`'s existing (currently discarded) output rather than changing
its contract; physics explainer first with the neural head as a later second
column. Design note kept: **whether the two brains agree is a better confidence
signal than either one's own certainty**, since both self-confidences are known
to fail on unfamiliar material.

**Housekeeping this session:** purged stale knowledge — CLAUDE.md still said the
project was "a collection of validated notebooks" awaiting conversion (goal 1
finished 2026-07-04); README and `pompom.py` still routed branched melts through
`branched_spectrum` (BSW replaced it 2026-09-03); environment.md still said
"102 tests"; workflow.md still said three machines. CLAUDE.md now also
distinguishes the DESIGN taxonomy (8 fine + 6 model-only) from what is actually
built (7 fine + 2 model-only, 2 regimes), which had been quoted interchangeably.

**Committed and pushed** at the user's request, ending work on this machine.

---

## 2026-09-03 — Windows PC bootstrapped; BSW replaces the branched forward model; real data 4/6 -> 6/6

**First session on this Windows home PC since the uv migration.** It had no uv
and no `.venv` (it predates that change). Installed uv 0.12.8 via winget —
matches the Linux PC's version — then `uv sync`. Baseline confirmed 112 passing
before touching anything. Two notes for next time on this machine:
- winget says "restart your shell"; uv is not on PATH in the session that
  installed it. Full path:
  `C:\Users\krish\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`.
- **torch resolves to 2.13.0+cpu here, not +cu130.** This is EXPECTED and
  correct per environment.md: the lock's CUDA extras are marked
  `sys_platform == 'linux'`, so Windows takes PyPI's CPU wheel. This box does
  have an NVIDIA RTX A1000, but training runs on CPU (~9 s/epoch at 16k, vs
  ~11 s/epoch on the Linux GTX 1660 Ti — barely different at this model size).
  Do not "fix" this by adding a per-PC torch variant; it would break the
  single-lock guarantee.
- `originals/` is ABSENT on this PC (only an unrelated `rheo_fingerprinting`
  folder). Nothing needed it this session — every derived `data/*.npz` is
  committed, which is exactly the point of that design.

**The work: closed the §1f blocker.** User picked option (a) — give the branched
class a broader forward model — and specified a two-exponent BSW spectrum with
5 parameters. Full detail in next-actions.md §1g; the short version:
- Prototyped `bsw_spectrum` and measured it against Pivokonsky BEFORE writing
  anything into the repo. Old model 0.316/0.280 decades RMS on E/B; BSW
  0.068/0.059. Also checked up front that it does not steal planted reptation
  curves (reptation AICc -4522 vs BSW -758) — that was the real risk with a
  more flexible model, and it is why the class is safe to add.
- Wired into `identify()`'s bank (now 8 candidates), the synth generator, and
  the ML pipeline (`N_PARAMS` 4 -> 5, model imports it instead of hardcoding).
- **Real data 4/6 -> 6/6.** Both LDPE melts now `branched` at p=0.92/0.96.
  Synthetic 0.917 vs a 0.700 baseline (the BASELINE rose too, 0.627 -> 0.700,
  because identify() can finally score branched). branched per-class 0.935.
- Suite 112 -> 121.

**Two things I got wrong along the way, both worth remembering:**
1. I wrote a smoke test asserting a larger terminal-wedge exponent `n_e`
   flattens tan(delta). It does not — `n_e` reshapes the spectrum
   non-monotonically. Replaced with a claim that IS robustly true (BSW keeps
   tan(delta) > 0.5 over more decades than a single Maxwell mode). Lesson: do
   not assert a monotonic relationship in a test without checking it first.
2. Two stack tests failed after the change because the "disguised melt" fixture
   now correctly classifies as `branched` instead of a network class. That is
   the fix WORKING one level upstream, not a regression — but the overturn
   logic still needs a genuine test case, so I built a new fixture that really
   does still read as cured_elastomer from one curve. Reframed rather than
   deleted.

**Also this session:** generated a private HTML project report to
`C:\Users\krish\OneDrive - UCB-O365\CUB\ML\rheo_fingerprinting\originals\rheo-fp-report.html`
(local file, not published anywhere).

**Process note the user pushed on:** asked how long each step took, and I could
only give the times commands print themselves — I have no timer on my own edits
and correctly declined to invent numbers. Same for "what time did I send X":
the transcript carries no per-message timestamps. Keep saying "unknown" rather
than guessing; there is precedent for a bad time estimate in the 2026-09-01
entry.

---

## 2026-09-02 — First real-data evaluation; density-invariance bug found + fixed

Ran the trained classifier against the digitized literature data for the first
time (the "main open item" from 2026-09-01). Two findings, both real.

**1. The model scored 0/6 on real curves — confidently wrong (abstain_p ~ 0).**
Sanity-checked the harness first (18/20 on synthetic through the identical code
path), so it was the model, not the plumbing. Cause: the generator emitted every
curve at exactly 60 points, so the model keyed on sampling density. Real data is
11-90 points. Hand-resampling to 60 fixed 4/6 on the spot, which is what pinned
the diagnosis. Fixed structurally rather than by patching the training
distribution alone: `resample_log_grid()` in `rheofp/ml/dataset.py` now puts
every curve on a fixed 60-point log-omega grid over its own window, so ANY
uploaded point count and frequency range works; the generator additionally
varies density (`N_OMEGA_RANGE = (10, 100)`, redrawn per curve within a stack).
User's framing: "the external user can upload any number of data points across
any freq range. the framework should adjust accordingly."
After retraining: **4/6, and raw == resampled** — the invariance holds. Darby
(3 cured silicones) and Tixier (critical gel) now correct from raw points.
Synthetic accuracy 0.917 vs 0.627 baseline (0.857 before the branched widening
below). Not comparable to the old 0.932, which was measured at a uniform 60
points. Suite 102 -> 112.

**2. Pivokonsky LDPE still fails — and it is a forward-model limit, not tuning.**
Fitting `branched_spectrum` to that data drives sigma against any ceiling given
(12, then 30) and still bottoms out at ~0.19-0.28 decades RMS; a 10-mode
Maxwell fits the same curves at ~0.02. Synthetic branched sat at median
tan(delta) ~0.32 vs the real ~0.95-0.99. Widened `BRANCHED_SIGMA` to
(1.0, 10.0) (-> ~0.47). That helped the SYNTHETIC class a lot (274/277, overall
0.857 -> 0.917) and did nothing for the real melts. Recorded in
next-actions.md §1f: the 3-parameter hierarchical double-reptation form cannot
represent real LDPE — either give the branched class a broader forward model or
keep it model-only behind abstention.

Unwelcome side effect, worth remembering: pre-widening the model was
appropriately unsure on Pivokonsky (abstain_p ~0.29); post-widening it is
confidently wrong (~0.01, p(rouse_screened) ~0.99). Abstention is trained
against the model's own errors on the synthetic distribution, so it cannot flag
a material whose true class is not in that distribution. Low abstain_p is not
evidence of a correct answer on out-of-distribution material.

New: `scripts/eval_real_data.py` (reports raw AND resampled, so a regression in
the invariance shows up immediately).

---

## 2026-09-01 — ML training pipeline; all three CLAUDE.md goals complete

- **Scope correction from the user, important.** I had treated the locked env
  as a reason to avoid adding `torch` and asked permission. User clarified:
  "computer-agnostic" means *the same across machines*, NOT *keep deps
  minimal* — **install whatever is needed**, just re-lock so every PC and any
  third-party GitHub user gets the identical thing. Recorded in workflow.md
  under Preferences. Do not repeat that hesitation.
- **torch 2.13.0+cu130 added** via `uv add torch`, `requirements.txt`
  regenerated. numpy stayed 2.5.1 — no resolver collateral. CUDA works on this
  PC's GTX 1660 Ti. Also registered a `slow` pytest marker.
- **Built `rheofp/ml/`** — dataset, model, train, evaluate — plus
  `scripts/train_classifier.py` and `tests/test_ml.py`. **Suite 84 -> 102.**
  `RheoNet` (246k params) is the frozen architecture made real: conv
  curve-encoder -> masked attention pool -> two heads. Conv because the
  discriminating features are local shape in log-frequency and windows are
  randomly cropped; attention rather than mean because a stack's information
  often sits in one curve (the hottest).
- **Abstention is a learned logit**, trained against whether the classifier
  actually erred (detached). It predicts its own failures rather than applying
  a threshold after the fact.
- **Results** (16k examples, 55 epochs, ~12 min): accuracy **0.932 vs 0.680**
  for the AICc physics baseline (+0.252). Regime 0.999. Abstaining on the
  least-confident 20% -> 0.979, 30% -> 0.992. Stacks beat single curves.
  cured_elastomer and critical_gel perfect, never confused with a melt.
- **The dominant error is physics, not a defect**: 58% of all errors are
  Zimm<->Rouse, which differ only in mode-spacing exponent (1.8 vs 2.0);
  measured log-slope distributions overlap almost entirely (1.05+/-0.70 vs
  1.08+/-0.69). Added `merged_pair_accuracy` + `pair_confusions` to
  evaluate.py so this is reported honestly instead of looking like failure.
  Caveat: `rouse_screened` per-class accuracy is seed-unstable (0.20 vs 0.71);
  the merged-pair number (~0.96) is the stable one.
- **Two real bugs caught by the tests, both now guarded:**
  1. Head 2 was silently UNTRAINED — `param_targets` was always None, so
     `head_params` received zero gradient. Wired through with masked padded
     targets; verified MAE 9.96 vs 19.0 for predict-the-mean.
  2. `_auc` gave 0.0 instead of 0.5 for a constant score (ties not
     rank-averaged).
- Gitignored `checkpoints/` and `data/synthetic_train*.npz` — both are
  reproducible from scripts, so nothing generated travels via git.
- Process note: a training run was left in the background overnight and I
  misreported its elapsed time as ~10 min when it was 9h21m (idle, not
  computing). Actual compute is ~12 min. Piping through `tail` also hides all
  progress until exit — don't do that for long runs.
- **All three CLAUDE.md goals are now complete.** What's genuinely open: the
  model has never seen REAL data (everything is synthetic), no real
  temperature stack has been tested, and the yield-dominated regime still has
  no physics. See next-actions.md §3.
- One portability fix: `ndarray.ptp()` is gone in NumPy 2 — used `np.ptp()`.
- `originals/` is present on this PC (all 6 PDFs + pivo2006.xlsx).
- NOT committed — left in the working tree for the user's end-of-day sync.

---

## 2026-08-31 — Linux PC set up; elastomer + critical-gel module BUILT

- **New machine** (Linux/CachyOS, first session here). Cloned the repo to
  `~/Documents/local_drive/coding/rheo-fp`. Installed uv 0.12.8 via the
  standalone installer to `~/.local/bin` (NOT pacman — no sudo needed);
  `uv sync` built `.venv` with Python 3.12.14 + the locked deps. Baseline
  confirmed 27/27 before touching anything. Note: system Python here is 3.14,
  so always go through `uv run` — and `~/.local/bin` must be on PATH.
- **Built the elastomer/critical-gel module** (next-actions §1 steps 1-3, and
  the melt-counterexample half of step 4). Suite **27 -> 42 passing**.
  - `rheofp/models/network.py` (new module — the fractional springpot family
    has no mode ladder, so it did not belong in `maxwell.py`):
    `chasset_thirion_spectrum(w, G_inf, c, m)` and `critical_gel_spectrum(w,
    c, u)`, plus log-space fits on `multi_restart_fit`, plus
    `tan_delta_spread` as the gel discriminating statistic.
  - **Design call**: critical gel is a genuine **2-parameter** model (bare
    springpot), not the 3-param element with G_inf driven small. Both fit the
    same data equally well, so parameter count via AICc is what actually
    separates the two classes. A test asserts the 3-param fit drives
    G_inf < 1e-3 * springpot on true gel data.
  - `fitting/identify.py`: banks merged into `ALL_MODELS = MODELS |
    NETWORK_MODELS`. Pre-filter kept permissive per the original lesson — the
    ONLY hard discard added is `terminal_reached` removing both network
    classes (a permanent network cannot flow).
  - `identify()` gained `n_temperatures` and returns `abstain` /
    `abstain_reason`. Head 2 still always emits a model, per the frozen
    two-head architecture.
- **Abstention threshold — decided, please review.** Spec said "decades of
  flatness / T-shift coverage"; built with **no flatness threshold**, because
  from a single curve a melt's absent terminal relaxation is missing evidence,
  not evidence of absence — no number of flat decades ever proves a network.
  Abstains whenever best == cured_elastomer AND not terminal_reached AND
  n_temperatures < 2. Flat decades are measured and reported as confidence,
  not as a gate. Recorded in next-actions.md under "Abstention rule as built".
- **Melt counterexample passed**: Likhtman-McLeish (2002) PS 6 truncated at
  wmin = 1e-5/1e-2/1e-1/1e0 — reptation wins on AICc every time, so the
  network classes never steal real melt data. Useful finding: the ambiguity
  does NOT materialize against a real melt, because reptation's plateau +
  Rouse wing outfits a flat springpot. Also noticed `terminal_reached` is
  False even on PS 6's full window (its low-w slope is 1.02, under the 1.4
  threshold) — pre-existing detector behavior, left alone rather than tuned.
- **Validation scope, do not overstate**: both new classes are
  planted-parameter validated ONLY. Real-material validation still needs the
  user to digitize figures to xlsx. `scripts/validate_network.py` prints that
  reminder on every run.
- **Data-source correction (later same session).** Re-read Martin 2008
  (EPDM): it has NO crosslinked-network G'(w)/G''(w) figure — Fig. 2 is the
  *un-crosslinked* polymer, Fig. 6 is time-domain G(t), and only tabulated
  low-freq Ge/tan d (Table 1) + swelling-based nu (Table 2) describe the
  cured networks. So Martin cannot be the route-(b) cured-elastomer SAOS
  source. User supplied **Darby et al. 2022, J. Appl. Polym. Sci. 139,
  e52412** (Sylgard 184 / Solaris / Ecoflex 00-30) — main PDF + supp now in
  `originals/` (+ darby2022-main.txt / darby2022-supp.txt). It HAS native
  cured-PDMS frequency sweeps (Fig. 1a, Fig. S1), 0.01-100 rad/s, LVE. That
  is now the route-(b) source; Martin drops to a Table 1 single-point Ge
  check; Villar stays route (a). `docs/elastomer_litreview.md` section 3 / 3b
  / 6 and next-actions.md updated. Caveats on Darby: data-not-shared (must
  digitize), noisy G'' (expect G_inf pinned, c/m loose), filled systems,
  single T. Digitizing targets are now Darby Fig. 1a (+ optional stiff
  Fig. S1 ratios) and Tixier Fig. 2/4.
- **Darby Fig. 1a digitized + validated (still same session).** User
  digitized it into `originals/darby.ods` (moduli in kPa). New
  `scripts/prep_darby.py` converts kPa->Pa and writes `data/darby2022.npz`
  (committed) — 3 samples SY184_10-1 / Solaris_1-1 / EF0030_1-1, 16 pts,
  0.1-100 rad/s. `fit_chasset_thirion`: G_inf vs Darby Table 1 (0.01 rad/s)
  to +1% (SY, 629 vs 620 kPa), +4% (Solaris, 124 vs 120), +28% (EF, 19.4 vs
  27 — softest, ~55% sol fraction, noisiest curve, Table 1 itself +/-30%
  there); log-residual < 0.003 dec; m ~ 0.23-0.30. `identify()` -> all 3
  cured_elastomer with big AICc margins, abstains (single curve). Wired into
  `scripts/validate_network.py` (now 4-panel) + `tests/test_network.py` (3
  parametrized real-data tests). **Suite 42 -> 45 passing.** Cured-elastomer
  class is now REAL-DATA validated; only Tixier critical-gel check remains.
- pandas needs `odfpy` for .ods, deliberately NOT added to the locked env
  (one-off prep). Used `libreoffice --headless --convert-to xlsx` ->
  `originals/darby.xlsx`, which `prep_darby.py` reads. Both gitignored.
- Extracted the two Darby PDF figures with `pdfimages` to scratchpad to read
  Fig. 1a / Fig. S1 (pdftotext gave only text). Nothing new installed.
- **Tixier Fig. 2/4 digitized + validated (same session) — module now
  COMPLETE.** User digitized into `originals/tixier.xlsx` (moduli in Pa
  already, so no conversion). New `scripts/prep_tixier.py` -> committed
  `data/tixier2004.npz` (1 curve, 11 pts, 1-100 rad/s). Both G'/G''
  power-law slopes ~0.755; tan(delta) ~ 2.55 flat (spread 0.06 dec).
  `fit_critical_gel` -> u = 0.762 (Tixier Table II 0.69-0.75; = system III),
  c = 6.85 Pa, residual < 0.011 dec. `identify()` -> critical_gel, but
  ΔAICc only ~2.4 / weight 0.77 over cured_elastomer — the two are nested
  (gel = cured with G_inf->0), so when G_inf truly ~0 only param count
  separates them and ΔAICc ~2 is exactly the 1-param penalty. Correct call,
  thin margin; noted a possible future tiebreaker (the unused
  frequency-flat-tan(delta) feature) — ask user before adding.
  Wired into validate_network.py (now 5-panel) + tests (1 more). **Suite
  45 -> 46 passing.** The elastomer / critical-gel module is done: forward
  model, discriminators, abstention, and real-data validation for both
  classes + the melt counterexample.
- **Stack-level abstention resolver BUILT (same session).** `identify.py` gains
  `resolve_melt_vs_network(stack)`, `shift_factor(ref, cur)` and
  `identify_stack(stack)`; `scripts/validate_stack.py` + `tests/test_stack.py`
  (13 tests). **Suite 46 -> 59 passing.**
  - Evidence 1: terminal relaxation at ANY temperature -> melt outright.
  - Evidence 2: horizontal shift of the spectrum across the stack.
    SHIFT_DECADES_MIN = 0.5 — this finally grounds the "T-shift coverage"
    threshold the original spec asked for (melt @ Ea 60 kJ/mol over 40 K
    shifts ~1.4 dec; network shifts 0.00).
  - **Design choice worth keeping**: alignment is done on **tan(delta)**, not
    the moduli. tan(delta) is a modulus ratio so the vertical shift factor b_T
    cancels exactly — only the horizontal shift needs fitting, and nothing has
    to be assumed about how the plateau scales with T. Verified by a test that
    a pure 3x vertical rescaling reports zero shift.
  - Coarse scan + parabolic refine rather than a gradient fit: the objective is
    a smooth 1-D curve and L-BFGS-B stalls on a flat tan(delta).
  - `identify_stack` runs the single-curve pipeline on the COLDEST curve (its
    window is likeliest to hide a melt's terminal relaxation) then applies the
    resolver. It only removes unjustified confidence or adds justified
    confidence.
  - **The payoff case**: an entangled melt (broad mode ladder, terminal below
    window) is confidently called `critical_gel` by a single curve with
    abstain=False. The stack measures 1.89 decades of shift and forces the
    abstention. This is why the feature exists.
  - Honest limit, tested: Ea = 0 -> the melt does not move -> resolver says
    "network". It reports what is observable, not what is true.
- **Synthetic data generator BUILT (same session).** `rheofp/data/synth.py`,
  `scripts/generate_dataset.py`, `tests/test_synth.py` (25 tests). **Suite
  59 -> 84 passing.** Labelled stacks from all 9 classes; labels planted not
  fitted; parameter ranges read from the fitters' own bounds (tested, so the
  population and search space cannot drift); stacks share ONE parameter set
  with an Arrhenius shift (networks: Ea = 0, moduli scale with absolute T);
  random window cropping is what teaches abstention; ~2% log-normal noise;
  canonical npz out; tqdm bar; ~1200 ex/s; xlsx is a capped human backdoor.
  Round-trip through `identify()` ~82-85% on single cropped noisy curves —
  the residual confusions (Zimm<->Rouse, gel<->elastomer) are real physical
  ambiguity, which is exactly what the ML model needs to learn.
- **Generator surfaced a real bug in the stack resolver, now fixed.** A
  critical gel's tan(delta) is frequency-independent by construction, so the
  tan(delta) alignment objective is FLAT — every shift fits equally well, and
  `shift_factor` was returning the scan grid's arbitrary minimum as though it
  were a measurement (2.23 decades of pure noise). Added
  `MIN_TAN_DELTA_STRUCTURE = 0.15`; `shift_factor` now returns NaN and
  `resolve_melt_vs_network` reports "ambiguous — loss tangent is
  frequency-independent". Lesson: a flat objective is degeneracy, not a zero
  answer. Covered by tests in both test_synth.py and test_stack.py.
- Next project work: the ML training pipeline (CLAUDE.md goal 3).

---

## 2026-07-04 (later still) — Elastomer/rubber module: literature review + scope decisions

- Clarified `docs/rheology_models.md` is a **wishlist**, not current scope: added
  an Implemented/Wishlist status column. Vitrimers + polyelectrolytes already
  covered; elastomers/gels/biofluids/shape-memory/etc. are future ambition.
- Worked through what a **basic elastomer/rubber module** needs. Key physics
  ambiguity established: a permanently crosslinked elastomer and a very-high-Mw
  entangled melt can look identical in a single SAOS curve; distinguishing them
  needs a **temperature stack** (melt's terminal relaxation is T-dependent and
  eventually enters the window; a true network's plateau doesn't). Ties into the
  frozen architecture's existing abstention design. `io/data.py` already carries
  optional `T_K` per sample, so the plumbing exists. User confirmed: users will
  enter T for their data.
- Ran a literature review (web + 6 PDFs the user dropped into `originals/`,
  gitignored). Full writeup: **`docs/elastomer_litreview.md`**. Outcomes:
  - **Forward model settled**: fractional Kelvin-Voigt = frequency-domain
    Chasset-Thirion: G' = G_inf + c*omega^m*cos(pi m/2),
    G'' = c*omega^m*sin(pi m/2). 3 params, fits with existing optimizer.
    Grounded in Curro-Pincus (1983), Bonfanti springpot algebra.
  - **Data wrinkle**: the model-network papers (Villar/Valles 2001) are
    time-domain G(t), not SAOS. Villar -> route (a) param-reconstruction only
    (self-consistency, NOT independent validation — do not overstate, do not
    digitize). EPDM (Martin 2008) is the real cured-elastomer SAOS source
    (native G'/G'' + crosslink density via swelling). Tixier (2004, J. Rheol.
    48, 39) is native-SAOS but CRITICAL-GEL/near-threshold, not cured plateau;
    it anchors the gel boundary and shows u ~ 0.69-0.75 (NOT universal 0.5).
  - Melt-vs-rubber abstention counterexample: reuse existing Likhtman-McLeish
    melt npz, frequency-truncated (planted-truth).
- **DECISION (user): critical gel is a SEPARATE fine class**, not the
  G_inf->0 limit of the elastomer model. Taxonomy gains two new Solid/gel-like
  fine classes: cured elastomer + critical gel (same fractional family, scored
  and labeled distinctly). Recorded in `elastomer_litreview.md` sections 5-6.
- **Nothing built yet** — stopped at end of lit-review. Next: user digitizes
  EPDM + Tixier figures to xlsx; then build `chasset_thirion_spectrum` +
  discriminators + abstention. See `docs/elastomer_litreview.md` section 6.
- Also this session: installed `poppler-utils` (PDF text extraction) and
  `uv`-nothing-new; saved autonomy + roadmap + env facts to Claude's
  cross-conversation memory.

---

## 2026-07-04 (later) — Validated XPP pom-pom against real Pivokonsky (2006) data

- User supplied the real target data in `originals/` (gitignored, local-only):
  `1-s2.0-S0377025706000085-main.pdf` (Pivokonsky, Zatloukal & Filip 2006) and
  `pivo2006.xlsx`. Found `data/pivo2006.npz` was **already converted** from
  this same xlsx (committed in the original restructure commit `54539be`) —
  samples `E`=LDPE Escorene LD165BW1, `B`=LDPE Bralen RB0323, matching the
  paper's Fig. 2 (90 and 85 points respectively).
- Installed `poppler-utils` (winget) to extract the paper's text — got the
  full 10-mode Maxwell + XPP nonlinear parameter tables (Tables 2 and 3) for
  both melts directly from the PDF (`pdftotext -layout`).
- Rewrote `scripts/validate_pompom.py` to fit real data instead of the
  substitute Verbeeten (2001) set: `fit_maxwell` (10 modes) recovers both
  melts' measured G'/G'' to **< 0.02 decades** mean log10 error (well under a
  0.10 tolerance). Added `tests/test_pompom.py` (4 tests, all passing —
  27/27 total now).
- **Important validation-scope nuance**: only the LVE regime is validated.
  The paper's nonlinear XPP parameters (`q_i`, `λb/λs`, `α_i` in Tables 2/3)
  were fit against nonlinear flow data (extensional/shear viscosity, normal
  stress coefficients — Figs. 3-9) not digitized here. `build_xpp_table()`
  correctly assembles those published values onto the fitted linear modes,
  but true nonlinear-XPP flow prediction remains **unvalidated**. Don't
  overstate this as "fully validated" — see `rheofp/models/pompom.py`
  docstring for the precise scope.
- Updated `rheofp/models/pompom.py` docstring, `README.md` status, `CLAUDE.md`,
  and `docs/references.md` to reflect LVE-validated status (removed
  "NOT YET VALIDATED").
- **Scope decision, confirmed with user**: product only ever ingests SAOS/LVE
  data, and XPP is indistinguishable from generic multimode Maxwell in that
  regime (nonlinear q_i/α_i/λb/λs are underdetermined by LVE alone). So XPP is
  **not a classifier output class** — branched melts route through
  `branched_spectrum` (hierarchical double-reptation, already in
  `maxwell.py`) instead. `pompom.py` stays validated but out of
  `fitting/identify.py`'s model bank; recorded in its docstring + CLAUDE.md +
  README so this isn't re-litigated when ML training starts.
- Committed at end of day 2026-07-04 (env setup + pompom validation + docs all
  in one end-of-day sync).

---

## 2026-07-04 — Set up second PC + reproducible env + cross-PC brain

- Cloned `rheo-fp` to this (home) PC at `C:\Users\krish\rheo-fp`.
- User required **identical Python + dependency versions across PCs** — repo
  must be computer-agnostic, no dependency issues. The repo was NOT reproducible:
  `requirements.txt` was unpinned, and PCs differed (office 3.12, home had 3.14).
- Decided (with user): standardize on **Python 3.12** + **uv lockfile**.
- Installed uv (0.11.26) and Python 3.12.13 via uv on this PC.
- Added `pyproject.toml` (pins `requires-python = "==3.12.*"`, deps, hatchling
  build of `rheofp`, `dev` group = pytest). Generated `uv.lock`. Ran `uv sync` →
  `.venv` with locked versions; `rheofp` installed editable. **23/23 tests pass.**
- Regenerated `requirements.txt` as a pinned+hashed `uv export` (pip fallback).
- Fixed `.vscode/settings.json`: was a hardcoded office `Python312` path →
  now relative `${workspaceFolder}/.venv/Scripts/python.exe`.
- Set up cross-PC brain like the website: `CLAUDE.md` cross-PC section +
  `.claude-notes/` (README, workflow, environment, this journal).
- Note: `gh` CLI installed on this PC but not yet authenticated
  (`gh auth login` still pending — only needed for PR/issue work).

---

