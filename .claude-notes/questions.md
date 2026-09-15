# Questions the user has asked about the NN — and the answers

**What this file is for.** The user periodically asks Claude to *explain* the
classifier rather than change it: how a layer works, why a choice was made,
what a number means. Those sessions produce no commit, so `sessions.md` never
records them and the reasoning is re-derived from scratch every time — at least
twice now (2026-09-11-ish and 2026-09-14). This file is where that reasoning
lives so it is not re-derived a third time.

**Two things it is NOT.** It is not `next-actions.md` (no to-do items here), and
it is not a tutorial to be recited at the user. It is the set of answers already
given, the *level* they were pitched at, and — most valuable — the handful of
places where answering a question turned up something the project did not
already know.

**Claude: append to this file whenever an explanation session happens.** Record
the question, the answer's substance, and the file:line it was verified
against. If an answer was corrected mid-session, record the correction and the
cause, not just the final answer.

---

## Who is asking, and at what level

Stated by the user 2026-09-14: **"I have very preliminary knowledge about ML and
stats."** They are an expert rheologist and the author of this project's
physics; they are not an ML practitioner.

Practical consequences, learned by getting them wrong first:

- **"Explain simply" means drop the vocabulary, not the content.** When asked to
  explain mean+max pooling, the first answer used "invariant", "extent",
  "localised" and was rejected with *"i didnt understand. be simpler."* The
  version that landed used two curves and asked what each summary can't tell
  apart. Same content, no terms of art.
- **They read diagrams carefully and will quote them back.** "concat 6" was them
  reading `docs/rheonet_architecture.html` line 388 (`concat 6 summary ·
  Linear·GELU·Dropout·Linear`) and parsing the token boundary wrongly. Answer the
  diagram they are looking at, and ask which one if unsure.
- **They ask "is this a valid ask?" before requesting analysis.** They are
  checking the method is sound, not asking permission. Answer the methodological
  question honestly — including when the answer is "yes, and here's the sharper
  version of that question."
- **Jargon they DO own:** all of rheology, plus AICc, degeneracy, parameter
  identifiability. Do not explain those.

---

## Answers given (2026-09-14 session)

Each verified against the code at the time, not recalled.

**Q: What error function is used for the test score?**
Two different things, and the distinction mattered to them. The reported
**0.923 is plain accuracy** — `(pred == label).mean()`,
[`ml/evaluate.py:164`](../rheofp/ml/evaluate.py). The **training** objective is a
weighted sum, [`ml/train.py:76-92`](../rheofp/ml/train.py):
`CE(class) + 0.3·CE(regime) + 0.2·BCE(abstain) + 0.1·SmoothL1(params)`.
Also flagged: the model is *selected* on val **accuracy**, not val loss
([`train.py:200`](../rheofp/ml/train.py)), and `abstain_auc` is a third thing
again — rank-based, diagnostic, never optimised.

**Q: Are the model parameters in realistic ranges? Where do the ranges come
from?** Four sources, in descending order of trustworthiness:
1. **Fitted from real data** — BSW/`branched` ranges bracket the Pivokonsky 2006
   LDPE fits ([`data/synth.py:102-114`](../rheofp/data/synth.py)).
2. **Literature theory** — `GEL_U = (0.45, 0.80)` spans Winter-Chambon 0.5 to
   Tixier 0.75.
3. **Measured from the model itself** — `Z_BOUNDS = (4, 60)`, both endpoints
   computed and justified in [`models/star.py:237-249`](../rheofp/models/star.py).
4. **Set by the measurement window, not the material** — `fit_bsw` derives
   τ bounds from the curve's own frequency range. "Realistic" here means
   realistic *for the uploaded data*. This is the weak one; say so.
Also explained: sampling ranges sit *inside* fitter bounds so no planted curve
lands on a bound, and a test enforces generator/fitter agreement.

**Q: What is the size of the omega vector?** Three different numbers, and
conflating them is the trap: the network always sees **60**
(`N_GRID`, [`ml/dataset.py:55`](../rheofp/ml/dataset.py)); the generator draws
**10–100** per curve (`N_OMEGA_RANGE`); a real upload has whatever it has. The
60 is *resolution*, not frequency range — the grid spans each curve's own
window, and window position/width travel separately as summary features.

**Q: What is SmoothL1 and why not CE?** SmoothL1 = quadratic near zero, linear
beyond |r|=1, so large residuals cannot dominate. Chosen because unidentifiable
parameters (τ_e outside the window, Z below ~4 where cost is flat) *guarantee*
occasional huge residuals, and because head 2 is an auxiliary term at weight
0.1. **CE is not a worse choice — it is inapplicable:** it needs a fixed set of
discrete categories and has no notion of *how far* wrong an answer is. Noted as
genuinely un-tuned: the 1.0 transition point is PyTorch's default.

**Q: Why is the attention layer needed?** Because a stack must become one
vector, and **a mean is the wrong inductive bias**: stack information is
typically carried by ONE curve (the hottest, where terminal relaxation enters
the window), and a mean attenuates it by 1/N. Attention weights the curves and
learns the weights from the curves themselves. N=1 is the identity, so single
curves need no separate path. Measured: 0.898 at N=1 → ~0.94 at N≥2.

**Q: What is mean+max, and why both?** Each summary of a filter's 60 responses
is blind to something the other sees — max cannot distinguish a blip from a
full-width feature, mean drowns a sharp spike in 59 quiet points. **Both blind
spots are real discriminators here:** plateau breadth (BSW vs reptation) needs
mean; the G″ shoulder (sticker classes) needs max.

**Q: What is "concat 6"?** A misparse of the architecture diagram — it reads
"concat *6 summary*", i.e. concatenate the six summary scalars. 256 + 6 = 262 →
128. **I had said "4 summary features" earlier in the same session from memory;
`N_SUMMARY = 6`.** Corrected in-session.

**Q: Why a conv encoder and not a plain linear one?** Because windows are
cropped up to 2.5 decades at random, so the same physical feature lands at a
different grid position on every curve. A position-fixed layer would relearn
each feature at all 60 positions from a fraction of the data each time; a
sliding filter learns it once. Second reason: a Linear layer has no notion that
point 31 neighbours point 32, and a slope only exists between neighbours.

**Q: Walk through the whole network, no jargon.** Nine steps, delivered as prose
and then as diagrams. The framing that worked, and worth reusing: **at nearly
every step something is deliberately withheld so the network cannot lean on it
— point count, window position — then handed back through a controlled channel
where it is genuinely informative.** Most of the design is about controlling
what is allowed to count as a clue.

**Q: What is the "mixing stage" in step 8?** The shared trunk,
[`ml/model.py:99-100`](../rheofp/ml/model.py) — `Linear · GELU · Dropout`, 128→128.
Shared by all four readouts, which is why it exists: it must build one
representation serving class, regime, abstention and parameters at once. Head 2
gets its own extra `Linear·GELU·Linear` because regressing continuous values
needs more than picking a class.

---

## Artifacts produced for the user (all in `docs/`, all untracked as of writing)

| file | what it is |
|---|---|
| `rheonet_three_readings.html` | 3 tabs of the nine-step walkthrough — layperson / rheologist / ML. Text, not diagrams. Superseded in practice by the next one. |
| `rheonet_flowcharts.html` | The same three audiences as **drawn SVG flowcharts**. This is what they wanted when they said "flowchart". |
| `sliding_detectors.html` | Step 4 alone, in three diagrams: one detector sliding; the same feature in three cropped windows; three passes compounding 5 points into ~29. |
| `rheonet_embedding_analysis.html` + `embed_data.js` | PCA + k-means on the curve embeddings (see below). **The .js must ship with the .html.** |

**Conventions these settled on** (reuse them): inherit the palette and typefaces
from the existing `docs/rheonet_architecture.html` — warm neutrals, teal accent,
Spectral + IBM Plex — rather than introducing a second visual identity. Tabs
with arrow-key nav. Light and dark both handled via tokens.

**A recurring defect to avoid:** the first `rheonet_flowcharts.html` shipped with
overlapping boxes and text, because SVG coordinates were written without
checking box bounds against each other. The user found it immediately. **There
is no browser or Node on these machines, so a drawn diagram cannot be
self-checked — build on a strict grid with generous uniform box heights, and
say plainly that the render is unverified.**

---

## >>> Findings that came OUT of an explanation session <<<

These are the reason this file is worth keeping. Answering a question forced a
measurement that the project had not made.

### 1. The embedding geometry supports the Zimm↔Rouse degeneracy claim (2026-09-14)

User asked whether PCA on the curve embeddings was "a valid ask". It was, and
the sharper version of it is: **does the representation itself place zimm and
rouse_screened on top of each other, or does the classifier merely draw a bad
boundary between them?** Measured on 6,589 held-out curves:

| pair | separation ratio | reading |
|---|---|---|
| **zimm ↔ rouse_screened** | **0.095** | superimposed — centroids 0.24 apart vs ~2.5 within-class spread |
| cured_elastomer ↔ critical_gel | 2.220 | well separated |
| star ↔ branched | 1.041 | adjacent |
| zimm ↔ cured_elastomer | 1.681 | distinct |

**So the 58%-of-all-error Zimm↔Rouse confusion is degeneracy in the
representation, not a boundary problem.** There is no gap for a better boundary
to occupy. This is independent of the physical argument the project already
makes, and agrees with it.

### 2. Two things that contradict `AMBIGUOUS_PAIRS` as written

- **`cured_elastomer ↔ critical_gel` is the second-FARTHEST pair in the whole
  matrix** (raw distance 3.85; only `cured ↔ wormlike_micelle` at 4.12 is
  farther). It is in `AMBIGUOUS_PAIRS` and `merged_pair_accuracy` collapses it,
  so part of the 0.968 merged figure is credit for a merge doing no work. This
  is *consistent* with the measured zero errors between them — but the pair is
  listed for nested-model reasons the representation does not reflect. **Not
  changed; recorded.** A user decision.
- **`branched ↔ star` is the fourth-CLOSEST pair (1.40)** and is deliberately
  NOT in `AMBIGUOUS_PAIRS` — a decision recorded in `evaluate.py:92-107` on the
  grounds that the network shows no such degeneracy (star 0.996, its one error
  going to wormlike_micelle). That reasoning still holds for the *classifier*.
  But the *representation* places them adjacent, and k-means with no labels put
  639 star + 413 branched in one cluster at 0.588 purity. **This is the same
  neighbourhood as the AICc bank's documented failure** where the 9-model bank
  absorbed 25/30 star melts into `branched`. Two unrelated methods, one blind
  spot.

### 3. k-means corroborates, and splits one class three ways

ARI(cluster, true) = **0.381** — above chance, far from a match; k-means assumes
round equal clusters in 128-D where neither holds, so it is corroboration, not
measurement. What it shows: **three separate pure `cured_elastomer` clusters**
(purity 1.000 / 0.980 / 0.991) — the unsupervised view splits that class rather
than confusing it. And **cluster 4 is a 2304-curve pile-up at 0.295 purity**
mixing sticky_reptation, zimm, reptation, rouse_screened — the terminal-flow
classes collapse into one region, which is where the classifier's errors live.

### 4. >>> `data/synthetic_train.npz` IS STALE AND DOES NOT MATCH THE CHECKPOINT <<<

Found while setting up the PCA run, and it would have silently corrupted it.

| | `data/synthetic_train.npz` | `checkpoints/rheonet.pt` |
|---|---|---|
| dated | 3 Sep | 9 Sep |
| classes | **9 — `star` count is 0** | 10 |
| stacks | 2000 | test split alone is 2400 |

The 9 Sep retrain regenerated the dataset at 16k with `star` included, **and
that file was never committed.** Anything that loads `data/synthetic_train.npz`
and compares against `checkpoints/rheonet.pt` is comparing across a class
boundary. Regenerated this session as `data/synthetic_train_10class.npz`
(`-n 16000 --seed 1`, 42,783 curves, 1600/class); split at seed 1 reproduces
**exactly 2400 test stacks**, matching the checkpoint. Statistically identical
to the retrain's data, not byte-identical. **Untracked, ~24 MB — needs a
commit/ignore decision.**

---

## Method notes for re-running the embedding analysis

- Script lives in the session scratchpad, not the repo. It takes embeddings
  **per curve from `CurveEncoder`, before attention pooling** — that is the
  representation the question is about; post-pooling would give stack-level
  vectors mixing temperatures.
- **scikit-learn is NOT in the locked env** and must not be added for this
  (CLAUDE.md: do not loosen). PCA = numpy SVD on the centred matrix; k-means =
  Lloyd's + k-means++ in numpy. Both short enough to audit.
- **Node is not installed on these machines**, so the dataviz skill's
  `validate_palette.js` cannot run. Do not ship an unvalidated 10-hue
  categorical scale — the embedding scatter highlights one or two classes
  against neutral grey instead, which suits the pairwise questions better anyway.
- Quote the **centroid-separation table**, not the scatter: PC1+PC2 carry only
  39% of variance and 16 components are needed for 90%.
