# Elastomer / rubber module — literature review (2026-07-04)

Purpose: identify (1) the forward-model physics for a basic crosslinked
elastomer/rubber SAOS class, (2) validation-grade datasets, (3) the
melt-vs-elastomer discrimination + abstention grounding.

STATUS: COMPLETE (2026-08-31). Forward model settled, module built (section 6),
and validated against real data — cured elastomer vs **Darby et al. 2022**
(native cured-PDMS SAOS; Martin 2008 has no cured-network spectrum figure, so
it dropped to a tabulated check), critical gel vs **Tixier 2004**, melt
counterexample vs Likhtman-McLeish. See section 3 for the data inventory,
section 6 for the build/validation record.

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

**UPDATE 2026-08-31: the cured-elastomer real-SAOS source is now Darby et al.
(2022), NOT Martin (2008).** On re-reading Martin 2008 (see the corrected
entry below) it has NO figure of crosslinked-network G'(omega)/G''(omega) —
only tabulated low-frequency Ge/tan d (its Table 1) and time-domain G(t) (its
Fig. 6). Darby 2022 has genuine native cured-PDMS frequency sweeps (its
Fig. 1a + Fig. S1). So the route-(b) real-material check for the cured class
is Darby; Martin drops to a tabulated single-point Ge check; Villar stays
route (a). See sections 3a-3c.

**Wrinkle: the two dedicated model-network papers (Villar, and the Martin
crosslinked data) report time-domain stress relaxation G(t) or tabulated
values, NOT oscillatory G'(omega)/G''(omega).** Our classifier is SAOS-only.
Two ways to still use them (in preference order):

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
  elastomer. **CORRECTED 2026-08-31 (the earlier entry overstated this):**
  the paper has NO crosslinked-network frequency-sweep spectrum figure.
  - Fig. 2 = G'/G''/eta* vs omega, but of the *un-crosslinked* EPDM (a melt,
    +/- plasticizer). NOT a cured network.
  - Fig. 6 = stress relaxation G(t) over 10 h at 100 C (time-domain).
  - Table 1 = tan d and Ge at low frequency for the 5 crosslinked resol
    ratios (1, 1/4, 1/7, 1/10, 1/30) -> Ge = 3.3e5, 9.8e4, 5.8e4, 3.4e4,
    2.0e3 Pa; tan d = 0.01, 0.07, 0.12, 0.18, 0.40. Two numbers per sample,
    one frequency. NOT a spectrum.
  - Table 3 = Chasset-Thirion (EN, t0, m) fitted to the Fig. 6 *relaxation*
    (REF: EN=6.3e5 Pa, t0=0.09 min, m=0.067; RES1/4: 2.6e5, 13, 0.070;
    RES1/7: 1.2e5, 104, 0.170; ...).
  - Table 2 = independent crosslink density nu (mol/m3) from equilibrium
    swelling + Pearson-Graessley (REF 124, RES1/4 39, RES1/7 17, RES1/10 6.5,
    RES1/30 1.25).
  USE: (i) Table 1 as a single-frequency check — fitted G_inf should match Ge
  and predicted tan d at that omega should match, per resol ratio; (ii) Table
  3 via route (a) self-consistency; (iii) Table 2 as an independent nu*kB*T
  cross-check on G_inf order of magnitude. Do NOT digitize any Martin figure
  for the cured class — none of them is cured-network SAOS.

- **Darby, Cai, Mason, Pham (2022), J. Appl. Polym. Sci. 139, e52412** —
  "Modulus and adhesion of Sylgard 184, Solaris, and Ecoflex 00-30 silicone
  elastomers with varied mixing ratios." (originals/ "J of Applied Polymer
  Sci - 2022 - Darby ...pdf" + "app52412-sup-0001-supinfo.pdf"; text at
  originals/darby2022-main.txt, darby2022-supp.txt.)
  **This is the route-(b) real cured-elastomer SAOS source.** Native
  G'(omega)/G''(omega) frequency sweeps, 0.01-100 rad/s, 0.1% strain (LVE),
  25 mm parallel plate, platinum-cured (hydrosilylation) PDMS networks -
  permanent covalent networks.
  - Fig. 1a: overlaid G' (filled) / G'' (unfilled) vs omega for SY 184,
    Solaris, EF 00-30 at factory-recommended ratios. The cleanest curves
    (best-cured). PRIMARY digitizing target.
  - Fig. S1 (supp): G'/G'' vs omega for SY (10:1, 20:1, 35:1, 45:1, 60:1),
    Solaris (1:1, 5:1, 10:1, 20:1), EF (1:1, 30:1, 60:1); plus modulus-
    matched G'/G'' overlays at ~30, ~10, ~1 kPa. SECONDARY targets — take a
    couple of the *stiffer* ratios (SY 10:1/20:1) for a G_inf range; skip the
    extreme-ratio soft ones (SY 60:1 = 0.9 kPa etc. — defect-dominated,
    near-critical).
  - Table 1: low-frequency (0.01 rad/s) G' for many ratios (SY 10:1 = 620,
    20:1 = 190, 30:1 = 59 kPa; SO 1:1 = 120; EF 1:1 = 27 kPa). Internal-
    consistency anchor for fitted G_inf.
  - Sol fraction by hexane swelling: SY 10:1 ~4.5%, SO 1:1 ~12%, EF 1:1 ~55%;
    at 30 kPa: SY 35:1 ~24%, SO 5:1 ~26%, EF 1:1 ~55%. A free-chain / defect
    proxy relevant to m, but NOT a crosslink density.
  CAVEATS (record, do not overstate):
  * "Research data are not shared" (explicit statement) -> digitizing the
    figures is the only route.
  * G'' << G' for these near-elastic materials and is noisy on the log plots;
    the paper barely discusses G'' and has a G''/G' label slip in Table 1.
    Expect fits to pin G_inf well and leave (c, m) loosely constrained - an
    honest identifiability result for well-cured rubber, matching the planted
    "weak network" test case, not a failure.
  * Filled systems (silica in Sylgard 184 especially) - real engineering
    elastomers, representative of the target use case, but not pure model
    networks.
  * Single temperature -> does not exercise the abstention-lifting T-stack
    path (fine; the melt counterexample covers abstention).

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
   Net: Tixier Fig. 2/4 validates the critical-gel boundary — DONE
   (`data/tixier2004.npz`, `scripts/prep_tixier.py`, u = 0.762 recovered).
   The cured rubbery-plateau elastomer class rests on **Darby 2022** (native
   cured-PDMS SAOS, route b — see section 3), also DONE. (Superseded
   2026-08-31: the earlier version of this line named Martin 2008 as the
   native-SAOS plateau source, which was wrong — Martin has no cured-network
   spectrum figure.)

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

Status 2026-08-31: real-material coverage of the Solid/gel-like regime is DONE.
  - cured elastomer: **Darby 2022** (Sylgard/Solaris/Ecoflex native SAOS,
    Fig. 1a) digitized -> `data/darby2022.npz`. G_inf recovered to +1..+28%
    vs Darby Table 1. (Optional add-ons not done: Fig. S1 stiff ratios;
    Villar 2001 route (a); Martin 2008 Table 1 single-point Ge.)
  - critical gel: **Tixier 2004** (Fig. 2/4, native SAOS near GP) digitized
    -> `data/tixier2004.npz`. u = 0.762 recovered (Table II range 0.69-0.75).
  - melt counterexample: Likhtman-McLeish 2002 PS 6, frequency-truncated.
  All in `tests/test_network.py` + `scripts/validate_network.py`.

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

## 6. Next steps

**Status 2026-08-31:** forward model, discriminators, abstention rule, and the
melt counterexample are BUILT (`rheofp/models/network.py`,
`tests/test_network.py`, `scripts/validate_network.py`; 42 tests pass). Data
sources settled (section 3 / 3b, corrected: Darby 2022 replaces Martin 2008
for the cured class). Remaining:

1. DIGITIZING:
   (a) DONE (2026-08-31). **Darby 2022 Fig. 1a** digitized (WebPlotDigitizer)
       -> `originals/darby.ods` -> `data/darby2022.npz` via
       `scripts/prep_darby.py` (does the kPa->Pa there). 3 samples
       SY184_10-1 / Solaris_1-1 / EF0030_1-1, 16 pts each, 0.1-100 rad/s.
       Fit: G_inf recovered to +1% (SY), +4% (Solaris), +28% (EF, the noisy
       ~55%-sol-fraction kit) vs Darby Table 1; residual < 0.003 decades;
       m ~ 0.23-0.30; identify() -> cured_elastomer for all three (large AICc
       margins), abstains (single curve). Optional later: add stiff Fig. S1
       ratios (SY 10:1 / 20:1).
   (b) DONE (2026-08-31). **Tixier 2004 Fig. 2/4** digitized ->
       `originals/tixier.xlsx` (moduli already in Pa) -> `data/tixier2004.npz`
       via `scripts/prep_tixier.py`. 11 pts, 1-100 rad/s, one near-GP curve.
       Both G' and G'' power-law slopes ~0.755; tan(delta) ~ 2.55 flat
       (spread 0.06 decades). `fit_critical_gel` -> u = 0.762 (Tixier
       Table II range 0.69-0.75; = system III), c = 6.85 Pa, residual
       < 0.011 decades. identify() -> critical_gel, but only ΔAICc ~ 2.4 /
       weight 0.77 over cured_elastomer — the two models are nested (gel =
       cured with G_inf->0) so when G_inf truly ~ 0 only the parameter count
       separates them, and ΔAICc ~ 2 is exactly the 1-param penalty. Correct
       outcome, thin margin. Possible future tiebreaker: use the (unused)
       frequency-flat-tan(delta) feature. Surface to user before adding.
2. DONE. `chasset_thirion_spectrum` + `critical_gel_spectrum` + fits.
3. DONE. Discriminators + abstention wired into `fitting/identify.py`
   (`ALL_MODELS`, `melt_rubber_ambiguous`). Abstention built WITHOUT a
   flatness threshold — see `.claude-notes/next-actions.md` "Abstention rule
   as built".
4. DONE. All three real/planted validation legs pass, in
   `scripts/validate_network.py` and `tests/test_network.py` (46 tests):
   melt counterexample (Likhtman-McLeish PS 6, truncated); Darby 2022 real
   cured-elastomer (1a); Tixier 2004 real critical gel (1b).
   Optional extras not done — Villar 2001 Table 2 route-(a) self-consistency;
   Martin 2008 Table 1 single-point Ge/tan d; Martin Table 2 nu*kB*T
   cross-check. None blocking.

The elastomer / critical-gel module is COMPLETE. Remaining project work is
the stack-level abstention resolver (below) and then ML training.

### Stack-level abstention resolver (not yet built)
`identify(..., n_temperatures=N)` currently TRUSTS N>=2 to mean the
melt-vs-rubber ambiguity is resolvable. The real per-temperature physics check
— does terminal motion (G'~omega^2 upturn) actually walk into the window as T
rises across the stack — is future work. Needs the frozen architecture's
set-based stack input plumbed through `identify`.

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
- https://doi.org/10.1002/app.52412 (Darby et al. 2022, J. Appl. Polym. Sci.
  139, e52412 — Sylgard 184 / Solaris / Ecoflex 00-30 native SAOS; the
  route-(b) cured-elastomer source, added 2026-08-31)
