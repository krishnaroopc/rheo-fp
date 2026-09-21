# Why `comb.py` out-fits a linear chain — measured diagnosis, 2026-09-21

**Status: DIAGNOSIS ONLY. No code changed, nothing re-wired, no claim that
this fixes anything.** The reparameterisation this implies is proposed at the
end and is NOT built.

This closes the question `docs/kapnistos2005_preregistration.md` left open:

> **A 5-parameter model preferring a linear chain over a comb** is a fact about
> `comb.py`, not about the bank. Before any future attempt, that is the thing
> to explain.

Context: Plan C's goal is a branched class that *cannot* out-fit a linear
chain. BoB (Das 2006) was rejected as the vehicle — see
`docs/bob_das2006_assessment.md` — and the user chose (2026-09-21) to pursue
the goal by reparameterising `comb.py` instead.

---

## Method

`fit_comb` was run directly on all nine real curves in
`data/kapnistos2005.npz` (Kapnistos et al. 2005: six model combs, a linear
backbone control `c6bb-PS`, and three `lc*-PBd` combs), and the **fitted
parameter vectors** were read out — which the 2026-09-16 evaluation never did;
it scored only which class won. Probe scripts were scratch, not committed;
the numbers below are reproducible from `fit_comb` at its defaults.

## Result 1 — the fitted parameters, and the first surprise

| sample | rms | s_a | s_b | phi_b |
|---|---|---|---|---|
| **c6bb-PS** (LINEAR control) | **0.1258** | 24.59 | **72.08** | 0.1096 |
| c612-PS | 0.2420 | 20.01 | **120.00** ← ceiling | 0.1190 |
| c622-PS | 0.3938 | 17.23 | **120.00** ← ceiling | 0.1470 |
| c632-PS | 0.3686 | 14.28 | **120.00** ← ceiling | 0.1739 |
| c642-PS | 0.3210 | **2.00** ← floor | **120.00** ← ceiling | 0.2587 |
| c652-PS | 0.0725 | **2.00** ← floor | **120.00** ← ceiling | 0.3091 |
| lc3-PBd | 0.3352 | 33.11 | **120.00** ← ceiling | 0.1054 |
| lc1-PBd | 0.3231 | 25.07 | **120.00** ← ceiling | 0.1396 |
| lc2-PBd | 0.2850 | 20.29 | **120.00** ← ceiling | 0.1635 |

**`s_b` pins to its ceiling of 120 on eight of nine curves — and the ONE
curve where it does not pin is the linear control, which is also the one
curve `comb` wins.** Two of the combs additionally drive `s_a` to its floor
of 2.0.

This is the `tdd` rejection signature exactly: **a parameter at its bound is
not identified by the data, it is absorbing misfit.** On the real combs the
model is not fitting an architecture at all — it is running out of cross-bar
and being stopped by a bound. Their rms (0.24–0.39, except c652-PS) is
correspondingly terrible. Plan A's at-bound check would have flagged all
eight automatically.

**My first hypothesis was wrong and is recorded so it is not retried:** I
expected `phi_b` to run to its *ceiling* (0.95 = all backbone, no arms = a
linear chain). It does the opposite — `phi_b = 0.11` on the linear control,
i.e. the model explains a **branch-free molecule as 89% dangling-arm
material.** The `PHI_B_BOUNDS` ceiling is not the leak.

## Result 2 — >>> THE MECHANISM: it wins the linear chain via its STAR limit <<<

On `c6bb-PS` the winning configuration is **long arms** (`s_a` = 24.6, a
strongly entangled arm) and a cross-bar worth only `s_b·phi_b` = **7.9**
effective entanglements. Arm material is 89% of the volume. So the curve is
carried by the **arm-retraction term**, not by cross-bar reptation — and
"arm retraction with a negligible cross-bar" *is a star*.

The comb model contains the star as an interior limit, and that limit is what
absorbs a linear melt.

This predicts `comb` should cannibalise `star`, and that is precisely what the
pre-registered P3 measured: **`star` 5/7 → 4/7, with surviving margins
collapsing from ΔAICc 194–225 to 7.6–27.4**, and `comb` taking the two
known-truncated stars Ma95k/Ma105k at ΔAICc 157/165. Three independent
observations (P2's linear win, P3's star cannibalisation, and these parameter
vectors) are one mechanism, not three problems.

Sensitivity check: the fit is *sharply* located in that corner, not flat —
moving `phi_b` from 0.1096 to 0.08 shifts `log10 G'` by up to **1.47 decades**
(and to 0.05, by 3.09). So this is a real optimum the fitter drives to, not a
plateau it wanders onto.

## Result 3 — every fit violates its own geometry, by a consistent factor

For a monodisperse H/pom-pom the cross-bar fraction is **not free**; ML1998
eq 10 fixes it as `phi_b = s_b / (s_b + 2 q s_a)`. `comb.py` already
implements this as `phi_b_from_architecture()` but deliberately does **not**
impose it (docstring: polydispersity and the comb-vs-H ambiguity break the
identity, and ML1999's own Table 2 fits `phi_b` separately).

Comparing fitted `phi_b` against that identity at the module's fixed `q = 2`:

| sample | phi_b fitted | phi_b geometric | ratio |
|---|---|---|---|
| c6bb-PS (LINEAR) | 0.1096 | 0.4229 | **0.26** |
| c612-PS | 0.1190 | 0.5999 | **0.20** |
| c622-PS | 0.1470 | 0.6352 | **0.23** |
| c632-PS | 0.1739 | 0.6775 | **0.26** |
| c642-PS | 0.2587 | 0.9375 | **0.28** |
| c652-PS | 0.3091 | 0.9375 | **0.33** |
| lc3-PBd | 0.1054 | 0.4754 | **0.22** |
| lc1-PBd | 0.1396 | 0.5448 | **0.26** |
| lc2-PBd | 0.1635 | 0.5965 | **0.27** |

**All nine sit at 0.20–0.33 of their geometric value — a factor of 3–5 low,
and remarkably consistent.** These are not physically realizable
architectures. And the gap is a *lower bound on the violation*: the real
Kapnistos combs carry ~6 arms, and larger `q` makes `phi_b_geom` smaller…
which for a *comb* means the fitted value is even further from any real
molecule with that `s_a`/`s_b`.

**This is the BSW disease inside a molecular model.** `comb.py`'s parameters
have molecular *names*, but with `phi_b` free the model can describe
molecules that cannot exist — which is exactly the "unconstrained curve-shape
knob" Plan C set out to eliminate. Having molecular parameters is not the
same as being molecularly constrained.

## Proposed reparameterisation — NOT BUILT, and it needs pre-registration

Impose the geometry instead of fitting around it:

* **Drop `phi_b` as a free parameter**; compute it from `phi_b_from_architecture(s_a, s_b, q)`.
* That takes the model from **k = 5 to k = 4** — a parsimony gain against
  BSW's k = 5, which is how `star` (k = 3) earned its place.
* It should close the star limit: `phi_b` can no longer be driven to 0.11
  while `s_a` is long, because the geometry ties them.
* `q` then stops being purely degenerate with `tau_e` (it enters `phi_b`
  too), so whether to fix or free it must be **measured, not assumed**.

**Predicted failure mode to pre-register against:** the real combs currently
pin `s_b` at its ceiling. Constraining `phi_b` removes a degree of freedom
that was absorbing misfit, so their rms may get *worse*, not better — and P1
(real combs → `comb`) could still fail at 0/6. A cleaner, more honest model
that still cannot win its own material is a legitimate outcome and must not be
rescued by re-freeing the parameter.

**Required before any of this is believed**, per the house protocol that has
now vetoed `tdd` and `comb` and produced this diagnosis:

1. Pre-register predictions in `docs/` and **commit before fitting** — with
   P2 (`c6bb-PS` must NOT return `comb`) as a standing veto, and `star`'s
   `test_star.py` margin floor of 50 as a second.
2. Planted round-trip first: does the k=4 model still recover a planted comb?
3. Cannibalisation check, n=30/class, identical seeds, real data must hold
   6/6.
4. `star` must survive at 5/7 on MM1998 with its margins intact.

Nothing above is evidence that the reparameterised model works. It is
evidence about **why the current one fails**, which is what was asked for.
