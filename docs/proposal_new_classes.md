# Proposal: the next class(es) — models, equations, methodology

**Written 2026-09-11 for the user's approval. NOTHING HERE IS BUILT.**
This is a menu with a recommendation, not a plan of record. Approve one (or
none) and it moves into `next-actions.md`.

---

## Why these four, and why now

`report.py`'s own out-of-taxonomy warning already names the gap verbatim:
*"blends, block copolymers, comb architectures, semicrystalline and filled
melts are NOT among them, and none of them are visible by eye either."*

That last clause is the whole argument. Per CLAUDE.md's SCOPE section this
tool exists for distinctions a person **cannot make by looking at the jar**.
All four candidates below are molecularly distinct and macroscopically
ordinary — exactly the target — and all four are currently absorbed silently
by `branched` (BSW), which is the documented "good fit of the WRONG class"
failure mode. That mode has now been confirmed three times (vitrimers,
stars, and the 25/30 star absorption before `star` existed), so the prior
that it is happening again here is strong.

---

## Candidate A — COMB / H-POLYMER melts (**my recommendation**)

**The model: the McLeish "pom-pom"/hierarchical-relaxation family, done as
LVE only.** A comb is a backbone carrying `q` side arms. Relaxation is
hierarchical and this is its whole signature:

1. the arms retract first, exactly as in `star.py` — same Milner-McLeish
   arm-retraction physics, same effective potential;
2. the relaxed arms then act as **solvent**, diluting the backbone's
   entanglement network to a fraction `phi_b` of the original;
3. the backbone finally reptates in that **diluted** tube, with its own
   `tau_e` rescaled by dynamic dilution.

Core equations, all of which this repo already has working pieces for:

```
arm retraction      U_eff(s), tau_arm(s)         star.py  (eq 24 / 29, validated)
dilution            G_N,backbone = G_N * phi_b^alpha,   alpha = 4/3
                    phi_b = backbone fraction by volume
backbone reptation  mu(t) + CLF                  tube.py  (Likhtman-McLeish, validated)
assembly            G*(w) = arm term + backbone term, via maxwell_spectrum
```

**Parameters (k = 4):** `G_N`, `Z_arm`, `Z_backbone`, `phi_b`. `tau_e` derived
or shared, as `star.py` already does.

**Why I recommend it:**
- **Highest reuse, lowest new physics.** Both halves are already validated in
  this repo. It is genuinely an assembly job plus a dilution factor, not a new
  derivation. That matters because every forward model here took longer than
  expected.
- **It is the missing rung on a ladder you already own.** linear → star →
  comb → LCB/BSW. Right now `branched` (an *empirical* 5-parameter spectrum)
  is doing duty for every non-linear architecture; a comb class turns one of
  those into real physics.
- **Falsifiable the same way `star` was:** planted round-trip, then real data
  where `Z_arm`/`Z_backbone` are known from synthesis.
- **Real data exists and is well characterised** — Roovers' combs, and the
  McLeish/Read H-polymer sets.

**Risk, stated up front:** at k=4 against BSW's k=5 with a similar broad
spectrum, AICc may not separate them. That is the *same* risk flagged before
`star` was built, where the answer turned out to be that parsimony carried it.
The cannibalisation check is the decider, not argument.

---

## Candidate B — BIDISPERSE / POLYDISPERSE BLENDS

**The model: double reptation.** The cleanest, most standard mixing rule in
LVE, and unusually simple:

```
G(t) = G_N * [ sum_i  w_i * F_i(t)^(1/2) ]^2
```

with `w_i` the weight fraction of component *i* and `F_i` its own single-
component relaxation (from `tube.py`). For a binary blend of two monodisperse
linear melts: `k = 4` (`G_N`, `Z_1`, `Z_2`, `w_1`).

**Why it is attractive:** it is the most *common* real-world case by a wide
margin — nearly every industrial melt is polydisperse — and the equation is
four lines. It would also give the classifier a principled answer to "is this
one species or two?", which is currently unanswerable.

**Why I did not rank it first:** a broad blend and a comb and an LCB melt all
produce *broad spectra*, and this class would sit right on top of `branched`
in exactly the region where BSW already wins. The degeneracy risk is the
highest of the four. Worth doing, but I would want the comb built first so
there is a clean physical alternative on the ballot when it is tested.

---

## Candidate C — BLOCK COPOLYMERS (ordered / microphase-separated)

**The model:** below the order-disorder transition these show a low-frequency
**power-law plateau** from the ordered mesophase — `G' ~ w^(1/2)` for lamellae,
`w^(1/3)` for cylinders (Rubinstein-Obukhov / Kawasaki-Onuki).

**Verdict: NOT recommended yet.** Two problems. (1) The signature is a
low-frequency power law that is *already* what `critical_gel` fits
(Winter-Chambon), so it collides with an existing class rather than filling a
gap. (2) The exponent depends on mesophase *geometry*, which is an
out-of-scope structural question SAOS alone cannot settle — it would put the
tool in the position of claiming something it cannot support, which is the
failure mode this project keeps catching.

---

## Candidate D — SEMICRYSTALLINE / FILLED melts

**The model:** both are **suspension-like** — a rigid filler (crystallites or
particles) in a viscoelastic matrix. The LVE signature is a low-frequency
`G'` plateau from a percolated network, usually modelled as a Krieger-Dougherty
or power-law modulus enhancement on top of the matrix spectrum.

**Verdict: NOT recommended.** This is the one place where the existing
taxonomy *is* nearly right: a filled melt with a percolated network looks like
`cured_elastomer` because, rheologically, it **is** a solid network at low
frequency. Adding a class here buys little and risks the cured/gel pair that
currently scores 1.000/0.992. Also, per SCOPE, a filled compound is usually
known to be filled — it is not a hidden distinction.

---

## Recommended methodology (whichever you pick)

Unchanged from the star build, because it worked and caught two real bugs:

1. **Get the paper into `originals/` first.** No transcription from memory —
   the eq-29 prefactor and the 1/2 erratum are the standing evidence for why.
2. **Forward physics → planted round-trip.** Exact recovery with no noise,
   then under 2%. No data needed for this step.
3. **Document the transcription traps in the module docstring as you hit
   them**, as `star.py` does.
4. **Pre-register predictions BEFORE any real data is fitted** — this is now
   the house habit and it has paid twice (the bounds widening, and Pryke's P4).
5. **Cannibalisation check before wiring into `ALL_MODELS`:** n=30/class
   planted cropped noisy curves, identical seeds through both banks, per-class
   before/after, **real data must hold 6/6**. Report the numbers even if they
   are bad — the `star` build cost `zimm` 2/30 and that was published.
6. **Close the generator gap in the same session** (`synth.py` +
   `CLASS_REGIME` + `FINE_CLASSES`), or the bank can emit a class the neural
   head has never seen. That exact bug shipped once (`wormlike_micelle`).
7. **Retrain, then re-measure the physics baseline on the same split.**
8. State the class's **limits** in the docstring — for a comb, almost
   certainly "cannot count the arms", by the same LVE argument that makes
   `star` unable to report arm number.

---

## What I would do

**Candidate A (comb/H-polymer).** Best ratio of new capability to new physics,
reuses two validated modules, and fills the obvious hole in a ladder that
currently jumps from one arm-retraction class straight to an empirical
spectrum. Then B (blends) once A gives it a physical competitor on the ballot.

**Estimated shape of the work**, based on how `star` actually went: forward
model + tests ~1 session; planted recovery + cannibalisation ~1; real data
+ retrain ~1. Call it three working sessions, with the caveat that `star` was
estimated the same way and the eq-29 prefactor alone cost most of a session.
