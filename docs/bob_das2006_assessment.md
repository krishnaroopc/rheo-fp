# Das et al. (2006) branch-on-branch (BoB): assessment, and why it is not the Plan C model

**Written 2026-09-21, after reading the paper and BEFORE writing any code.**
Source: `originals/das2006_branch_on_branch_bob.pdf` — Chinmay Das, Nathanael
J. Inkson, Daniel J. Read, Mark A. Kelmanson & Tom C. B. McLeish,
"Computational linear rheology of general branch-on-branch polymers",
*J. Rheol.* **50**(2), 207–234 (2006), doi:10.1122/1.2167487.

Companion read alongside it: `originals/larson2001_hierarchical_model.pdf`
(Larson 2001, *Macromolecules* 34, 4556), the Hierarchical Model this paper
builds on and departs from.

This is a **negative result recorded deliberately**, in the same spirit as
`docs/tdd_preregistration.md` and `docs/kapnistos2005_preregistration.md`:
the model was investigated, the reasons it was not built are specific and
checkable, and they are written down so the question is not silently
reopened on a later session's intuition.

---

## What Plan C assumed, and which half survived

Plan C (see `.claude-notes/next-actions.md`) reasoned:

> BSW's 5 parameters describe a CURVE SHAPE, with no constraint tying them to
> a physically realizable branched molecule — so it can bend into a shape that
> merely resembles a linear melt well enough to win an AICc contest. A
> molecular model could not do that, because there is no branched topology
> that produces those shapes.

**First half: correct.** BoB's inputs really are molecular (arm lengths,
branch counts, backbone length, topology).

**Second half: falsified by the paper itself.** BoB does not lose the ability
to produce a linear melt's response — it is *demonstrated on one*. See §3
below. This is the crux, and it is the reason the model was not built.

---

## 1. BoB is an ensemble simulation, not a fittable forward model

This is a hard architectural incompatibility with `identify()`, independent of
any physics judgement.

- **§III F + Fig. 8.** The algorithm generates a large ensemble of
  representative molecules ("of order 10^5" for highly branched systems), then
  marches time multiplicatively (`t_{n+1} = m·t_n`, with `m = 1.001` typical,
  from `t_0 = 1e-5 tau_e`), and at *each* step, for *each* unrelaxed molecule,
  for *each* free end: solves eq 29's quadratic for the retraction increment,
  updates dilation `phi`, tests arm collapse, updates compound-arm effective
  length `Z~` via eq 20, checks supertube activation (Fig. 7), and tests
  reptation via eq 22.
- **Per-arm mutable state**: `collapsed` and `ghost` booleans, stored collapse
  time `t_a` and collapse-time dilation `phi_a`, `relax end` / `next relax`
  pointers, `Z~` and `Z~_end` (§III A, Fig. 4, Fig. 6's five distinct collapse
  scenarios).
- Moduli appear only **at the end**, eq 30, as a sum over the time steps
  actually taken.

`identify()` needs `forward(w, theta)` callable thousands of times inside
`multi_restart_fit`. For calibration: `tube.py` costs **10.67 ms/call and is
already 94.2% of `identify()`'s total runtime** (measured 2026-09-18). BoB is
orders of magnitude past that. It is a separate program, not a bank candidate.

## 2. The parameters are a topology ensemble, not a low-dimensional vector

For the Fig. 11 polybutadiene combs the inputs are: backbone `M_w` **and**
PDI, side-arm `M_w` **and** PDI, a **Poisson mean number of side arms**, and
random attachment points along the backbone (§IV). The prediction is an
average over a generated population; a single molecule is not even the unit of
prediction. There is no `theta` of length 3–5 to fit, which is what every
entry in `ALL_MODELS` is.

## 3. >>> THE DISQUALIFYING FACT: BoB is fitted to a LINEAR melt, on purpose <<<

Fig. 9(a) fits **LIN210, a linear polyisoprene** (Table I: M_w 224 000,
PDI 1.02, architecture "Linear") using **the same `M_e`, `tau_e`, `alpha` and
`p^2`** as the asymmetric stars and H-polymers in the same figure. §IV states
the design goal outright: one parameter set spanning architectures.

For the paper that is a strength — evidence the physics is universal. **For
this project it is exactly the property that has twice triggered a veto:**

- **`comb` was VETOED on it.** Pre-registered criterion P2,
  `docs/kapnistos2005_preregistration.md`: the linear-backbone control c6bb-PS
  came back `comb` at Akaike weight **1.000, ΔAICc 161.8**, rms 0.247 → 0.126.
  "The comb model fits a straight chain better than it fits any real comb in
  the same figure" — flexibility, not physics.
- **It is the BSW fault itself.** `branched` beats the verbatim
  Likhtman–McLeish tube model on all three of Katzarova's monodisperse linear
  polystyrenes (rms 0.0250/0.0261/0.0207 vs 0.0314/0.0300/0.0222).

Plan C's goal was to **remove** a model's ability to produce the bad shape.
BoB does not remove it; the paper exhibits it deliberately. Building it would
spend multiple sessions to arrive at a veto that is predictable now.

## 4. BoB does not arrive as settled physics — two constants, one inconsistent

- **The dilation exponent `alpha` has no single working value.** p.223:
  `alpha = 4/3` fits the symmetric star SS105 and the linear LIN210
  simultaneously at one `M_e`/`tau_e`; but for "comb molecules with large
  number of side arms and for branched m-PE resins, `alpha = 4/3` predicts
  much lower moduli at low frequencies." They report **everything at
  `alpha = 1`**, which "predicts about 20% lower plateau modulus but allows us
  to fit all the samples considered." The conclusions list this as an open
  problem: "inability of finding a single dilation exponent which describes
  both the plateau modulus and long time relaxation correctly."
  **`star.py` is built and validated at `alpha = 4/3`** (Colby–Rubinstein)
  across three chemistries. So adopting BoB means either contradicting a
  validated module or accepting a known inconsistency in the branched regime
  Plan C is aimed at.
- **`p^2 = 1/40`** here, against **`1/12`** in Kapnistos 2005 and **`1/6`** in
  ML1999 — which `comb.py` already records as "a factor of two between two
  papers on the same quantity". Das et al. explain their lower value (branch
  points hop in the *dilated* tube, not the thin tube) and flag the small
  value as a question their own work raises. A third value, not a resolution.

## 5. Reptation is in the UNDILATED tube, and they say this biases them

§II E / p.215: "we use the undilated tube for reptation in all of our
calculations. This will mean that for linear molecules with large
polydispersity, our estimated relaxation times will probably be
overestimates." Relevant because a future blend class would inherit that bias.

---

## What the paper IS worth keeping for

It was not a wasted read. Three concrete, reusable things:

1. **It is the second real comb dataset the project needs.** `CLAUDE.md`'s comb
   section states reopening `comb` would need "real comb data from a second
   source (ML1999 Fig 6 ... figure-only so it needs digitizing)". Das 2006
   **Table II + Fig. 11** are four polybutadiene combs (PBC2/7/9/11) with
   backbone and side-arm `M_w`, PDIs, and mean arm counts tabulated — from
   Daniels et al. (2001) and Fernyhough et al. (2001). Figure-only for the
   curves, so still a digitizing job, but the molecular characterisation is in
   the table. Note PBC2 is the one they fit worst.
2. **Appendix A's multimode Kramers first-passage treatment** (eqs A1–A3) is a
   genuine improvement over `comb.py`'s single-mode effective potential: it
   gives an *ergodicity factor* `g_i(t) = 1 - exp(-2t/tau_i)` so a mode
   contributes to the retraction potential only once it has had time to explore
   its own equilibrium distribution, with effective free-arm length
   `Z~(t) = sum_i (1 - e^{-2t/tau_i}) Z_i`. The paper notes this reproduces a
   Rouse scaling `tau_n ~ n^2 zeta/k` for an equal-arm comb.
3. **Eqs 24/25 give `G'_fast`/`G''_fast` analytically in the frequency domain**
   (the Likhtman–McLeish longitudinal + Rouse-in-tube modes summed over arms),
   and **eq 30 gives the slow modes as a Maxwell-like sum over time steps** —
   so BoB never needs a numerical Fourier transform. Worth remembering as
   independent confirmation of the route `comb.py` and `star.py` already take
   (mode ladder through `maxwell_spectrum`), and of the aliasing hazard that
   forced `comb.py` off ML1998 and `tdd.py` onto NNLS.

## Decision

**BoB is not built and is not the Plan C model.** Recorded, with the paper's
own page references, so this is a closed question rather than a matter of
taste. Plan C's *goal* — a branched class constrained so it cannot out-fit a
linear chain — is unchanged and still open; the user elected (2026-09-21) to
pursue it by reparameterising `comb.py` rather than by importing BoB. The
c6bb-PS control remains the cheap decisive test, and `comb.py`'s own
`phi_b` ceiling is the first thing to examine (see next-actions).
