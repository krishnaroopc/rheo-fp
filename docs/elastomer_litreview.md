# Elastomer / rubber module — literature review (2026-07-04)

Purpose: identify (1) the forward-model physics for a basic crosslinked
elastomer/rubber SAOS class, (2) validation-grade datasets, (3) the
melt-vs-elastomer discrimination + abstention grounding.

STATUS: five source PDFs obtained + read (in `originals/`, gitignored). Key
findings extracted below. Forward-model equation is settled; validation-data
situation has a wrinkle (both dedicated network papers are time-domain G(t),
not SAOS) — see section 3.

## 0. Extracted forward model (SETTLED) — fractional Kelvin-Voigt = frequency-domain Chasset-Thirion

Time-domain Chasset-Thirion (both validation papers fit this exact form):

    G(t) = G_inf * [ 1 + (tau/t)^m ]

with G_inf the equilibrium modulus, m ~ 0.1-0.3 for well-cured rubber
(Curro-Pincus: m proportional to crosslink density via dangling-end arm
retraction; Villar/Valles confirm m depends strongly on pendant-chain MW).

Its clean frequency-domain analog is a **springpot in parallel with a spring**
(fractional Kelvin-Voigt specialized with an elastic equilibrium term). From
the springpot complex modulus G* = c_b (i*omega)^b = c_b omega^b exp(i*pi*b/2)
(Bonfanti et al. eq 21-22), adding an equilibrium spring G_inf:

    G'(omega)  = G_inf + c_b * omega^b * cos(pi*b/2)
    G''(omega) =         c_b * omega^b * sin(pi*b/2)

where the power-law exponent b == m (Chasset-Thirion exponent). THREE
parameters (G_inf, c_b, b), log-space fittable with the existing
`multi_restart_fit` core. This is the elastomer forward model. Signature:
G' has a plateau (G_inf) plus a weak rising power-law shoulder; G'' is a weak
pure power law omega^m with small, slowly-varying magnitude -> tan(delta) << 1
and only weakly frequency-dependent. Directly answers the "what does the
residual loss look like" question: weak power law omega^m, NOT flat.

Boundary case falls out for free: at b = m = 1/2 with G_inf -> 0 this reduces
to the Winter-Chambon **critical gel** (G' = G'' = C*omega^(1/2), congruent
over >5 decades, tan delta = 1 frequency-independent; Winter-Chambon proved
n=1/2 is the unique Kramers-Kronig-consistent power law at balanced-
stoichiometry GP). So elastomer vs critical-gel vs melt discrimination is a
matter of where (G_inf, b) sit: cured rubber = large G_inf + small b; critical
gel = ~zero G_inf + b~0.5; entangled melt = terminal G'~omega^2 upturn (or
hidden outside window -> abstain).

## 1. Forward model: Chasset–Thirion + Curro–Pincus

The canonical LVE description of a cured rubber is the **Chasset–Thirion
equation**, in complex-modulus form:

    G*(omega) = G0 * (1 + (i*omega*tau)^n)

- `G0`: equilibrium (zero-frequency) modulus -> crosslink density via
  `G0 ~ nu*kB*T` (model-agnostic; no affine/phantom commitment needed).
- `n`: power-law exponent of the slow relaxation tail (dangling chains).
  Typically small (~0.1-0.3) for well-cured rubbers; **Curro & Pincus** showed
  n is tied to crosslink density via arm-retraction of dangling ends.
- `tau`: characteristic relaxation time of the tail.

This gives G' ~ plateau with a weak low-omega upturn-free tail and
G'' ~ G0*n*(omega*tau)^n-type weak power law - exactly the "residual loss"
functional form question. 3 parameters, log-space fittable with the existing
`multi_restart_fit` core. Fits the repo's config-driven, lean style.

Key papers to obtain:
- Chasset, R. & Thirion, P. (1965). Proc. Conf. Phys. Non-Cryst. Solids
  (orig. creep form). Modern G*(omega) form appears in later reviews - a
  usable statement is in soft-adhesion/fractional-viscoelasticity reviews.
- Curro, J.G. & Pincus, P. (1983). "Theory of stress relaxation in networks
  with dangling chains." Macromolecules 16, 559. (exponent <-> crosslink
  density)
- Curro, Pearson, Helfand follow-up (1985) — refined exponent predictions.

## 2. Boundary case: critical gel (Winter–Chambon)

At the gel point G' ~ G'' ~ omega^n over the whole window with
frequency-independent tan(delta) (n ~ 0.5-0.7). This is the *boundary* of the
Solid/gel-like regime: a cured elastomer (plateau, tan delta << 1, weak n)
must be distinguished from a critical gel (parallel power laws, tan delta ~
const). Both live in the existing Solid/gel-like regime; the elastomer class
discriminator should test for plateau + small frequency-flat tan delta vs.
parallel power-law scaling.
- Winter, H.H. & Chambon, F. (1986). J. Rheol. 30, 367 (and Chambon & Winter
  1987, J. Rheol. 31, 683).

## 3. Validation datasets — inventory of the obtained PDFs (IMPORTANT wrinkle)

**Wrinkle: the two dedicated network papers report time-domain stress
relaxation G(t), NOT oscillatory G'(omega)/G''(omega).** Our classifier is
SAOS-only. Two ways to still use them (in preference order):

(a) **Reconstruct G*(omega) from published Chasset-Thirion fit parameters.**
    Both papers TABULATE fitted (G_inf, m, tau) per sample. Since we now have
    the exact frequency-domain form (section 0), we can generate G'/G'' curves
    analytically from those real fitted params.
    **CAVEAT (do not overstate this): this is NOT independent validation.**
    Our forward model *is* the Chasset-Thirion form, so generating a curve from
    Chasset-Thirion params and fitting it back only exercises our fitter + our
    time->frequency algebra — it is a self-consistency / planted-parameter
    check (unit-test-grade), and proves nothing about the physics matching a
    real material, because the physics is identical on both ends.
(b) **Digitize genuine measured SAOS curves** (native G'(omega)/G''(omega))
    for a true measured-data validation. This is the only route that actually
    tests the physics against reality.

Why NOT to digitize Villar specifically: its measured data is time-domain
G(t) master curves (Figs 2-3), not SAOS. Making it a real check would need
digitizing G(t) AND a G(t)->G*(omega) transform (Schwarzl/Ninomiya or
spectrum inversion), which injects approximation error — a *muddier* check
than a native-SAOS set, not a cleaner one. Villar's genuine value is as a
controlled-architecture model network used via route (a) only. For a second
real-material validation, prefer another paper reporting native SAOS G'/G''
(see section 3b) over fighting Villar's time-domain data.

Obtained PDFs (all in originals/, text extracted):

- **Vega, Villar, Alessandrini, Vallés (2001), Macromolecules 34, 4591** —
  "Terminal Relaxation of Model PDMS Networks with Pendant Chains." Model
  end-linked PDMS, controlled pendant content. Data = stress-relaxation G(t)
  master curves (Figs 2-3, time-domain); only a low-freq elastic modulus comes
  from its dynamic runs, no full SAOS spectra to digitize. Table 2 tabulates
  G_inf + Chasset-Thirion exponent m per network. USE VIA (a) ONLY
  (self-consistency, not real-data validation — see caveat above). Do NOT
  digitize; not worth the time-domain transform.

- **Martin, Barrès, Cassagnau, Sonntag, Garois (2008), Polymer 49, 1892** —
  "Viscoelasticity of randomly crosslinked EPDM networks." REAL engineering
  elastomer. Has BOTH: (i) frequency sweeps with a genuine G' low-frequency
  plateau + tan(delta) (Fig. showing G'/G'' vs rad/s; low-freq G'/Ge and tan d
  in Table 1) — digitizable measured SAOS, route (b); and (ii) stress
  relaxation modeled with Chasset-Thirion (route a). Crucially, crosslink
  density is independently obtained via **equilibrium swelling +
  Pearson-Graessley** (Tables 2-3), so G_inf recovery is checkable against an
  independent structural measurement. This is the strongest single validation
  source — real material, real SAOS, independent crosslink density.

Physics/theory PDFs obtained:
- **Curro & Pincus (1983), Macromolecules 16, 559** — "A Theoretical Basis for
  Viscoelastic Relaxation of Elastomers in the Long-Time Limit." Derives
  Chasset-Thirion from dangling-end reptation; m proportional to crosslink
  density v (m = v/(a*p)); predicts Plazek shift-factor exponent x ~ 2/m.
- **Winter & Chambon (1986), J. Rheol. 30, 367** — gel-point criterion;
  n=1/2 unique K-K-consistent exponent at balanced-stoichiometry GP;
  G'=G''=C*omega^(1/2) congruent over >5 decades. Defines the critical-gel
  boundary of the Solid/gel-like regime.
- **Bonfanti, Kaplan, Charras, Kabla — "Fractional viscoelastic models for
  power-law materials" (arXiv 2003.07834)** — springpot + fractional
  Kelvin-Voigt complex-modulus algebra used in section 0.

Not yet obtained (optional, would strengthen): Urayama guest-PDMS, the
cm0343507 damping-elastomer PDMS (both likely also time-domain / relaxation).

## 3b. Second native-SAOS elastomer dataset — candidates (need PDF, user to fetch)

Goal: a SECOND real material reporting native G'(omega)/G''(omega) frequency
sweeps (route b), to not rest validation on EPDM alone. Ranked:

1. **OBTAINED (originals/39_1_online.pdf) — Tixier, Tordjeman, Cohen-Solal &
   Mutin, "Structural effects on the viscoelasticity of PDMS networks close to
   the sol-gel threshold," J. Rheol. 48(1), 39 (2004).** End-linked PDMS,
   controlled structure (3 crosslinkers, functionality/Mn in Table I; critical
   stoichiometric ratios r_c per system).
   **What it actually covers (read 2026-07-04) — recalibrated from the earlier
   over-promise:** its strength is the CRITICAL-GEL / near-threshold regime,
   NOT a fully-cured rubbery plateau.
   - Figs 2-4: native SAOS G'(omega)/G''(omega) frequency sweeps near the gel
     point -> power law G'~G''~omega^u with frequency-independent phase angle
     delta = u*pi/2. DIGITIZABLE, and the strongest native-SAOS anchor for the
     critical-gel boundary class.
   - Key physics nuance: u is NOT the universal 1/2. Tixier measures
     u_I=0.69, u_II~similar, u_III=0.75 — u varies with chemistry (f/Mn),
     Table II. So the critical-gel discriminator must be "G'~G''~omega^u with
     tan(delta) frequency-independent, u in ~0.5-0.75," NOT u fixed at 0.5.
     Winter-Chambon's n=1/2 is the special balanced-stoichiometry,
     entanglement-free case; real gels spread higher.
   - Above-threshold (cured) data is mostly the zero-frequency modulus G vs
     distance-to-threshold epsilon (Fig 6) and NORMALIZED master curves
     G*(omega)/G*(omega*) (Fig 7) — scaling collapses, not raw cured-network
     spectra with an absolute plateau. So this does NOT give a clean
     large-G_inf/small-m cured-elastomer SAOS curve.
   Net: use Tixier (or Winter-Chambon Fig 3) to validate the critical-gel
   boundary. The cured rubbery-plateau elastomer class still rests on EPDM
   (Martin 2008, native SAOS plateau) + Villar via route (a).

2. **Chambon & Winter's own near-GP PDMS SAOS** (the data underlying Winter &
   Chambon 1986, already in originals/) — congruent G'(omega)=G''(omega) over
   >5 decades. This IS native SAOS but it is the critical-gel point specifically,
   not a fully cured rubber. Useful as the anchored boundary case; figures in
   the 1986 PDF (Fig. 3) are digitizable if wanted.

3. **"Elasticity recovery of crosslinked EPDM: influence of the chemistry and
   nanofillers," Rheol. Acta (2020), s00397-020-01246-0** — same group as the
   Martin 2008 EPDM paper; companion material. Likely time-domain recovery
   (route a) rather than native SAOS — lower priority, but same-lineage
   crosslink-density methodology.

Recommendation: fetch candidate 1 (J. Rheol. 2004 PDMS sol-gel). Combined with
EPDM (Martin 2008), that gives two independent real materials AND the critical-
gel boundary, covering the whole Solid/gel-like discriminator. Villar stays
route-(a) only. No further digitizing beyond EPDM Fig. + (optionally) the
J. Rheol. 2004 PDMS frequency sweeps.

## 4. Counterexample for abstention logic (melt masquerading as rubber)

Need a high-Mw entangled melt **temperature stack**: at low T (or short
window) it shows only a plateau (looks crosslinked); at higher T the terminal
crossover enters the window. Notes:
- The repo already has Likhtman–McLeish (2002) PB melt data
  (`data/likhtman_mcleish2002_fig10/11.npz`) — single-T curves whose terminal
  region IS in-window; can synthesize the ambiguous case by truncating the
  frequency window, which is a controlled, planted-truth way to test
  abstention.
- A real TTS dataset (PB or PS melt, multiple T) would strengthen this;
  essentially any TTS master-curve paper with per-T raw curves works.

## 5. Design implications for the module

DECISION (2026-07-04, user): **critical gel is its own SEPARATE fine class**,
NOT merely the G_inf->0 limit of the elastomer model. So the taxonomy gains
TWO new fine classes in the Solid/gel-like regime: (i) cured elastomer/rubber,
(ii) critical gel. They share the same fractional forward family but are
reported/labeled distinctly.

- Forward: `chasset_thirion_spectrum(omega, G_inf, c, m)` (fractional
  Kelvin-Voigt: G' = G_inf + c*omega^m*cos(pi m/2),
  G'' = c*omega^m*sin(pi m/2)). New `rheofp/models/network.py` (or into
  maxwell.py — decide at build time). Critical gel is the same functional
  form with G_inf ~ 0 and m ~ 0.5-0.75, but is fit/scored and labeled as a
  distinct class (per the decision above), not silently merged.
- Fine-class discriminators within Solid/gel-like regime:
  * cured elastomer  -> large G_inf plateau, tan(delta) << 1, weak m~0.1-0.3.
  * critical gel     -> G_inf ~ 0, G'~G''~omega^u with tan(delta) frequency-
                        independent, u ~ 0.5-0.75 (NOT fixed 0.5 — see Tixier).
  * high-Mw melt     -> abstain unless a T-stack rules out terminal relaxation
                        (G'~omega^2 upturn) entering the window.
- Abstention rule needs a threshold (decades of flatness / T-shift coverage)
  — a real design decision, grounded via the counterexample dataset.
- No affine-vs-phantom discrimination: report G_inf (and nu*kB*T-derived
  density) model-agnostically. Same honesty policy as the XPP scope decision.

## 6. Next steps (where we paused 2026-07-04)

Lit-review phase complete; physics + data sources settled. Remaining:
1. USER (manual, WebPlotDigitizer -> xlsx, same as pivo2006.xlsx): digitize
   (a) EPDM (Martin 2008) frequency sweep -> cured-elastomer real-data check,
   (b) Tixier Fig 2 or 4 -> critical-gel real-data check.
   Not a blocker for starting the build (planted-parameter tests need no data).
2. BUILD (Claude, when asked): `chasset_thirion_spectrum` forward + fit,
   planted-parameter recovery tests, then wire the two new fine-class
   discriminators + abstention into `fitting/identify.py`, then real-data
   validation against the digitized xlsx + Villar route-(a) reconstruction +
   the Likhtman-McLeish truncated-window melt counterexample.

## Sources (web survey)

- https://pubs.acs.org/doi/abs/10.1021/ma00148a020 (dangling-chain relaxation)
- https://www.sciencedirect.com/science/article/abs/pii/0032386188901760
  (apparent power-law relaxation of networks)
- https://www.researchgate.net/publication/231688731 (Villar/Vallés PDMS
  pendant chains)
- https://pubs.acs.org/doi/10.1021/cm0343507 (irregular end-linked PDMS
  damping elastomer)
- https://www.sciencedirect.com/science/article/abs/pii/S0032386108001419
  (EPDM networks viscoelasticity)
- https://rheology.tripod.com/z04.39.pdf (Winter gel-point review)
- https://arxiv.org/pdf/2003.07834 (fractional/power-law LVE review incl.
  Chasset–Thirion complex-modulus form)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11562782/ (2024 molecular model,
  entangled network LVE — modern context)
