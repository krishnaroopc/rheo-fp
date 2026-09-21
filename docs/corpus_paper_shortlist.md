# Real-data corpus — paper shortlist

**Status: citations verified 2026-09-19.** Download list for the
literature-digitization corpus. Target: >= 50 digitizable G'(w)/G''(w)
curve-pairs per class where the physics allows it (see the per-class reality
check).

## What "verified" means here, and what it does NOT mean

Every citation below was checked against the **Crossref API** (title, full
author list, journal, volume, pages, year, DOI). Nothing carrying a DOI in this
file is a remembered citation. Three entries were **cut or demoted** because
they did not survive that check — they are marked inline rather than silently
deleted, so the same wrong guess does not get re-made later.

**The limit, stated plainly: Crossref verifies that a paper EXISTS and what it
is called. It does not verify what is inside the figures.** ACS, AIP and
Elsevier all return HTTP 403 to automated fetching, so figure counts could not
be confirmed except where noted. Claims in this file about *how many curves a
figure holds* are inferences from titles, abstracts and Liu 2006's tables —
treat them as leads, not counts. The single exception is the Suman & Joshi
entry, which a research agent confirmed figure-by-figure before it was cut off.

**Practical consequence:** when a paper turns out to hold fewer curves than
this file suggests, that is expected error in the estimate, not a
mis-citation. Correct the number here as you go.

## Why this list looks the way it does

Current real-data holdings are **48 curves total**, and they are lopsided:

| Class | Real curves today | Source |
|---|---|---|
| `star` | 12 | MM1998 (7), Santangelo (3 incl. linear control), Pryke (2) |
| `reptation` | 9 | Katzarova (6: 3 mono + 3 bimodal), LM2002 Fig10 (6, fit targets) |
| `branched` | 2 | Pivokonsky LDPE |
| `cured_elastomer` | 3 | Darby silicones |
| `critical_gel` | **1** | Tixier |
| `sticky_rouse` / `sticky_reptation` | 9 curves, **0 correctly classified** | Edera, Ricarte (both return `branched`) |
| `zimm` | **0** | — |
| `rouse_screened` | **0** | — |
| `wormlike_micelle` | **0** | — |
| (`comb`, unwired) | 9 | Kapnistos |

Three classes have **zero** real data. Two more have data the pipeline gets
**wrong**. That is where the corpus has to land — not on `star`, which is
already the best-validated class in the project.

## Ground truth is part of the deliverable

Every existing prep script (see `scripts/prep_katzarova2018.py`) records Mw,
PDI, temperature and the derived Z. A digitized curve **without** its
characterization table is much less useful: it can test "what class does the
pipeline say" but not "did it recover the right parameter". So for every
figure, also screenshot the **sample characterization table** and the
**TTS reference temperature / shift factors**.

---

# 1. `rouse_screened` + `reptation` — ONE paper does most of the work

### **Abdel-Goad, Pyckhout-Hintzen, Kahle, Allgaier, Richter & Fetters (2004)**
*"Rheological Properties of 1,4-Polyisoprene over a Large Molecular Weight
Range"*, **Macromolecules 37(21), 8135-8144**, doi:10.1021/ma030557+

**TOP PRIORITY OF THE WHOLE LIST.** Mw from 1.5e3 to 3.2e6 g/mol, anionically
polymerized, PDI 1.02-1.12. Liu 2006 Table 2 lists **11 samples** from it
(75k, 102k, 110k, 128k, 198k, 293k, 464k, 576k, 735k, 963k, 1013k) with BSW
parameters already tabulated.

Why it is worth more than 11 curves: PI has Me ~ 5 kg/mol, so a range starting
at 1.5 kg/mol **crosses the entanglement threshold inside one chemistry, one
lab, one instrument**. That gives `rouse_screened` and `reptation` from the
same source with Z as ground truth — and the unentangled end is the class with
zero real data today.

### **Colby, Fetters & Graessley (1987)**, *"The melt viscosity-molecular weight
relationship for linear polymers"*, **Macromolecules 20, 2226-2237**,
doi:10.1021/ma00175a030 — verified via Crossref.
### **Colby, Fetters, Funk & Graessley (1991)**, Macromolecules 24, 3873
Monodisperse polybutadiene, PDI < 1.05. Liu Table 1 draws samples B1-B4
(70.9k, 130k, 355k, 925k) from these. The 1991 paper covers solutions as well
as melts — relevant to `rouse_screened` in the semidilute regime.
**Caveat on the 1987 paper:** its title is *melt viscosity*, so its headline
figures may be eta_0 vs M rather than frequency sweeps. Confirm it carries
G'/G'' curves before committing screenshot effort.

### **Raju, Menezes, Marin, Graessley & Fetters (1981)**, *"Concentration and
molecular weight dependence of viscoelastic properties in linear and star
polymers"*, **Macromolecules 14, 1668-1676**, doi:10.1021/ma50007a011
Surfaced during verification and worth flagging: **concentration AND molecular
weight dependence, linear AND star, in one paper.** That combination feeds
`rouse_screened` (the concentration axis), `reptation`, and `star` at once.

### **Wang, Wang, Halasa & Hsu (2003)**, *"Relaxation Dynamics in Mixtures of
Long and Short Chains: Tube Dilation and Impeded Curvilinear Diffusion"*,
**Macromolecules 36, 5355-5371**, doi:10.1021/ma0210426
Verified via Crossref — **and note the title correction: this is a BLEND paper,
not a pure monodisperse study.** The four monodisperse PBD (43.8k, 99.1k, 208k,
412k, PDI 1.01 — the tightest in Liu's compilation) are its *components*, and
they are the source of Liu 2006 Fig. 4, which plots all four as master curves,
G' in (a) and G'' in (b). Two consequences: (1) digitize the pure components
for `reptation`, being careful not to pick up blend curves by mistake, and
(2) the blend curves themselves are a ready-made **blend** test set alongside
Struglinski & Graessley, for open item (a).

### **Baumgärtel, De Rosa, Machado, Masse & Winter (1992)**, *"The relaxation
time spectrum of nearly monodisperse polybutadiene melts"*, **Rheologica Acta
31, 75-82**, doi:10.1007/bf00396469
Verified via Crossref. PBD21/41/97/201 — Winter's own BSW-parameterized data,
which makes it the natural check on the `branched`/BSW fault, since the BSW
parameters are published alongside the curves.

### **Onogi, Masuda & Kitagawa (1970)**, *"Rheological Properties of Anionic
Polystyrenes. I. Dynamic Viscoelasticity of Narrow-Distribution
Polystyrenes"*, **Macromolecules 3, 109-116**, doi:10.1021/ma60014a001
Verified via Crossref. The title says *dynamic viscoelasticity of
narrow-distribution* polystyrenes — exactly the target. The classic
monodisperse PS series (215k-581k), historically the most-digitized LVE dataset
in existence, so it doubles as a check that your digitization pipeline
reproduces published numbers.

### **Schausberger, Schindlauer & Janeschitz-Kriegl (1985)**, *"Linear
elastico-viscous properties of molten standard polystyrenes"*, **Rheologica
Acta 24, 220-227**, doi:10.1007/bf01332600
Verified via Crossref. Monodisperse PS 290k/750k/2540k at 180 C.
**It is a two-part paper** — Part II is Schindlauer, Schausberger &
Janeschitz-Kriegl, **Rheol. Acta 24, 228-231**, doi:10.1007/bf01332601
(note the author order rotates). Grab both while you have the volume open.

**Note:** `originals/liu2006_plateau_modulus_methods.pdf` (Liu et al. 2006,
Polymer 47, 4461) is **already in the repo** and is the index to all of the
above — its Tables 1-3 give Mw, PDI, T and the source reference for every
sample. Read it first.

---

# 2. `zimm` — READ THIS BEFORE DOWNLOADING ANYTHING

**This class may not be buildable from conventional rheometry, and that is a
finding, not a shopping problem.**

A truly dilute solution has moduli of order mPa — below a rotational
rheometer's resolution. The real Zimm data in the literature is **intrinsic**
moduli [G'], [G''] measured with Birnboim-Schrag multiple-lumped resonators at
100-6000 Hz and **extrapolated to zero concentration**, or obtained by
oscillatory flow birefringence. Those are reduced/normalized quantities, not
G' in Pa on an absolute axis.

Sources (Schrag & Lodge, Univ. of Wisconsin, 1970s-80s, Macromolecules /
J. Polym. Sci.): theta-solvent polystyrene and poly(alpha-methylstyrene)
solutions, h* = 0.15, ~2.8 decades of reduced frequency.

**Decision needed from you before I spend your download effort here** — see
the question at the end of my message. The honest alternative is that `zimm`
is validated on synthetic data only and the report says so.

---

# 3. `wormlike_micelle` — zero real data today

### **Rehage & Hoffmann (1991)**, *"Viscoelastic surfactant solutions: model
systems for rheological research"*, **Mol. Phys. 74(5), 933-973**
A 40-page review — reviews reprint many systems' curves in one place, which is
exactly what a digitization corpus wants. CTAB/NaSal, the canonical
near-perfect Maxwell system.

### **Berret, Appell & Porte (1993)**, *"Linear rheology of entangled wormlike
micelles"*, **Langmuir 9, 2851-2854**
Cetylpyridinium chlorate / sodium chlorate brine, concentration series,
Cole-Cole representation.

### **Fischer & Rehage (1997)**, *"Rheological Master Curves of Viscoelastic
Surfactant Solutions by Varying the Solvent Viscosity and Temperature"*,
**Langmuir 13, 7012-7020**, doi:10.1021/la970571d
Citation verified via Crossref. **The title is the reason to get it** — master
curves built by varying two variables is a multi-curve source by construction.

### **Kern, Zana & Candau**, *"Rheological properties of semidilute and
concentrated aqueous solutions of CTAB..."*, **Langmuir 8, 437-440 (1992)**,
doi:10.1021/la00038a020
Citation verified via Crossref. Note the series has siblings worth checking
together: **Langmuir 5, 1225 (1989)** doi:10.1021/la00089a018 and
**Langmuir 7, 1344 (1991)** (CTAC) doi:10.1021/la00055a010. Three papers, same
group, same method, different surfactant/salt — good chemistry diversity.

### **Raghavan & Kaler (2001)**, *"Highly Viscoelastic Wormlike Micellar
Solutions Formed by Cationic Surfactants with Long Unsaturated Tails"*,
**Langmuir 17, 300-306**, doi:10.1021/la0007933
Citation verified via Crossref (issued online 2000-12-16, 2001 issue).

**What to capture besides the curves:** surfactant + salt concentrations and
temperature. The class's discriminator is the Maxwell single-relaxation
signature plus the high-frequency Rouse-Zimm upturn, and `beta` in the bank's
`WLM_MODELS` keys off the deviation from a pure Maxwell.

---

# 4. `sticky_rouse` / `sticky_reptation` — the class the pipeline gets WRONG

This is the highest-value target after the melts, because there is a
**measured, documented failure** here: every curve in Edera 2024 and Ricarte
2023 identifies as `branched`, diagnosed in
`scripts/diagnose_sticky_models.py` as a genuine forward-model limit (discrete
Maxwell modes cannot reproduce a real vitrimer's power-law G'' wing).

More real data decides whether that is a forward-model failure to fix or a
class boundary to report.

### **Chen, Tudryn & Colby (2013)**, *"Ionomer dynamics and the sticky Rouse
model"*, **J. Rheol. 57(5), 1441-1462**, doi:10.1122/1.4818868
Citation verified via Crossref. The canonical reference **for the exact
forward model in the bank**. Polyester
ionomers, series of ionic content, LVE master curves predicted by sticky
Rouse with the sticker lifetime from dielectric spectroscopy — so the sticker
time is **independently measured**, which is rare and valuable ground truth.

### **Ricarte, Tournilhac, Cloître & Leibler (2020)**, *"Linear Viscoelasticity
and Flow of Self-Assembled Vitrimers: The Case of a Polyethylene/Dioxaborolane
System"*, **Macromolecules 53, 1852-1866**, doi:10.1021/acs.macromol.9b02415
Citation verified via Crossref. **Best single addition in this section.** It is
a DIFFERENT paper from the Ricarte 2023 already in the repo — different first
author group (Leibler, ESPCI vs Shanbhag), different chemistry
(polyethylene/dioxaborolane vs polybutadiene). Its whole subject is linear
viscoelasticity, so the figures are G'/G'' by construction. A second,
independent vitrimer chemistry is exactly what is needed to decide whether the
`branched`-absorbs-vitrimers failure is a forward-model limit or a data quirk.

### Vitrimers with temperature series (the stack mechanism's real test):
- **Montarnal, Capelot, Tournilhac & Leibler (2011)**, *"Silica-Like Malleable
  Materials from Permanent Organic Networks"*, **Science 334, 965-968**,
  doi:10.1126/science.1212648 — the founding vitrimer paper. Verified.
- **Capelot, Montarnal, Tournilhac & Leibler (2012)**, *"Metal-Catalyzed
  Transesterification for Healing and Assembling of Thermosets"*, **JACS 134,
  7664-7667**, doi:10.1021/ja302894k — verified. Note it is a JACS healing
  paper, so check the SI for the rheology rather than assuming the main text
  carries frequency sweeps.
- **Röttger et al.**, Science 2017, 356, 62 — dioxaborolane vitrimers
  (citation not re-verified; same group as the Ricarte 2020 above, which is
  the better rheology target).

### **Chen, Döhler & Binder (2016)**, *"Rheology of hydrogen-bonded dendritic
supramolecular polymer networks in the melt state"*, **Polymer 107, 466-473**,
doi:10.1016/j.polymer.2016.08.046
Verified via Crossref. Replaces the vague "Stadler et al." entry in the
previous draft — this one is confirmed, is about melt-state rheology, and
covers supramolecular H-bonded networks, i.e. `sticky_rouse` territory.

### **CUT from the previous draft: "Zhang & Guan metallo-supramolecular
networks."** Crossref returns nothing matching that description. I could not
name a real paper, so it is removed rather than sent to you as a guess.

### Note: **Leibler, Rubinstein & Colby (1991)** Macromolecules 24, 4701 is the
*theory* behind the sticky models (no data of its own).

---

# 5. `critical_gel` — one real curve today

### **Scanlan & Winter (1991)**, *"Composition dependence of the viscoelasticity
of end-linked PDMS at the gel point"*, **Macromolecules 24, 47-54**
**Five** model PDMS networks, stoichiometry varied — so the relaxation exponent
*n* **varies between samples**. That is genuine diversity, not one curve
repeated, and it directly exercises `GEL_U = (0.45, 0.80)` in `synth.py`.

### **Chambon & Winter (1987)**, J. Rheol. 31(8), 683-697
Imbalanced-stoichiometry crosslinking PDMS — the founding paper. Already have
`winter_chambon1986_gelpoint.pdf` in `originals/`; the **1987** one is the
data-rich sibling.

### **Suman & Joshi (2020)**, *"On the universality of the scaling relations
during sol-gel transition"*, **J. Rheol. 64, 863-877**, doi:10.1122/1.5134115
— **FIGURE-VERIFIED, 12 curves in two figures**
(Citation confirmed via Crossref; note the exact title is "the scaling
relations", not "the critical scaling exponents" as my first draft had it.
A follow-up exists: Bhattacharyya, Suman & Joshi, *Phys. Fluids* 35 (2023),
doi:10.1063/5.0137753, on thermoresponsive PVA.)
Fig 1(a): **6 curves**, Laponite, sol -> gel -> post-gel, n = 0.29.
Fig 1(c): **6 curves**, PVOH, n = 0.753.
The value here is the **spread in n** — 0.29 and 0.753 sit at opposite ends of
`GEL_U = (0.45, 0.80)` in `synth.py`, and 0.29 is *outside* it on the low side.
That makes this both a test set and a check on whether the generator's range is
drawn correctly. It also gives the pre-gel and post-gel curves as legitimate
near-miss negatives.

### **Izuka, Winter & Hashimoto (1992)**, *"Molecular weight dependence of
viscoelasticity of polycaprolactone critical gels"*, **Macromolecules 25,
2422-2428**, doi:10.1021/ma00035a020
Authors confirmed from the full Crossref record: Akihiro Izuka, H. Henning
Winter, Takeji Hashimoto. Polycaprolactone diol end-linked with a
trifunctional isocyanate; the abstract states a power-law relaxation spectrum
H = G_0/Gamma(n) * (t/lambda_0)^-n. A **molecular-weight series of critical
gels**, so several curves with a systematic ground truth.

### **Izuka, Winter & Hashimoto (1994)**, *"Temperature Dependence of
Viscoelasticity of Polycaprolactone Critical Gels"*, **Macromolecules 27,
6883-6888**, doi:10.1021/ma00101a028
Same three authors, confirmed. The companion paper — a temperature series on
the same chemistry, so it feeds the stack mechanism, not just the single-curve
class.

**Method note, worth carrying forward:** a search-result snippet listed the
1992 paper as "Izuka & Hashimoto" and I briefly recorded that as a correction
to this file. It was wrong — the snippet had truncated the author list, and
the full `api.crossref.org/works/<doi>` record shows all three. **Verify
authorship against the full record, never a search snippet.**

### Gelation series in other chemistries — worth one each for chemistry
diversity: polyurethane gelation, gelatin, PVA/borax, kappa-carrageenan.

**Capture the full cure series** (pre-gel, at gel, post-gel) where the figure
shows it: the off-gel-point curves are legitimate near-miss negatives and are
as valuable as the critical curve itself.

---

# 6. `cured_elastomer` — three real curves today

### **Villar & Vallés** PDMS networks — `villar2001_pdms_networks.pdf` is
**already in `originals/`**; check whether it has a crosslink-density series
worth digitizing before downloading anything new.
### **Martin (2008) EPDM** — `martin2008_epdm.pdf` also **already present**.
### **Batra, Cohen & Archer (2005)**, *"Stress Relaxation of End-Linked
Polydimethylsiloxane Elastomers with Long Pendent Chains"*, **Macromolecules
38, 7174-7180**, doi:10.1021/ma050933l
Verified via Crossref. **The most interesting elastomer entry**, because
pendent chains are exactly what makes a cured network relax slowly instead of
holding a flat plateau — so these are near-miss negatives that probe the
`cured_elastomer` / sticker boundary, not just more flat plateaus. Caveat: the
title says *stress relaxation*, i.e. G(t), so check whether the paper also
reports frequency sweeps before digitizing. If it is G(t) only, it is NOT
directly usable — this project's `G(t) -> G*(w)` conversions have already
produced one 0.12-0.30 decade bug (see the TDD note in CLAUDE.md).

### **DEMOTED: Patel, Malone, Cohen, Gillmor & Colby (1992)**, *"Elastic
modulus and equilibrium swelling of poly(dimethylsiloxane) networks"*,
**Macromolecules 25, 5241-5251**, doi:10.1021/ma00046a021
Citation is real and verified, **but the title and abstract are equilibrium
elastic modulus and swelling — static measurements, not frequency sweeps.**
It is a crosslink-density ground-truth reference, not a source of G'(w)/G''(w)
curves. Do not spend a download on it for the corpus.

### **CUT: "Urayama model networks."** Crossref returns nothing matching the
description I gave. Removed rather than passed on as a guess.

Note `docs/elastomer_litreview.md` already exists — read it before buying
duplicates.

---

# 7. `branched` — two real curves today, and an ACTIVE OPEN FAULT

`branched` (BSW) currently **beats the verbatim Likhtman-McLeish tube model on
all three of Katzarova's monodisperse linear melts**. That is the project's
standing fault. More real branched data is useful, but **more real
monodisperse LINEAR data is what actually adjudicates it** — which is why
section 1 is the priority.

### **Wood-Adams, Dealy, deGroot & Redwine (2000)**, *"Effect of Molecular
Structure on the Linear Viscoelastic Behavior of Polyethylene"*,
**Macromolecules 33, 7489-7499**, doi:10.1021/ma991533z
Verified via Crossref, full author list confirmed. LCB metallocene PE with
characterized branching levels — and the title is the exact subject.

### **Gabriel & Münstedt (2002)**, *"Influence of long-chain branches in
polyethylenes on linear viscoelastic flow properties in shear"*,
**Rheologica Acta 41, 232-244**, doi:10.1007/s00397-001-0219-6
Verified via Crossref.

### **Stadler, Kaschta & Münstedt (2008)**, *"Thermorheological Behavior of
Various Long-Chain Branched Polyethylenes"*, **Macromolecules 41, 1328-1333**,
doi:10.1021/ma702367a
Verified via Crossref. "Various" LCB polyethylenes plus thermorheological
behaviour means multiple materials AND temperature series.

### **Liu, Li, Chen & He (2004)**, *"Influence of long-chain branching on linear
viscoelastic flow properties and dielectric relaxation..."*, **Polymer 45,
2803-2812**, doi:10.1016/j.polymer.2004.02.030
Surfaced during verification; same Liu group as the 2006 index paper already
in `originals/`.

### **Trinkle & Friedrich** van Gurp-Palmen analyses — NOT re-verified; listed
as a concept worth having (vGP is an architecture diagnostic independent of the
fit) rather than a confirmed citation.

---

# 8. `star` — already the best-validated class; LOW priority

12 real curves across three chemistries (PI, PIB, PBd). Only add if a source is
cheap.

### **Roovers, Toporowski & Martin (1989)**, *"Synthesis and characterization of
multiarm star polybutadienes"*, **Macromolecules 22, 1897-1903**,
doi:10.1021/ma00194a064
Verified via Crossref. **Multiarm** is the point: `star.py` predicts LVE
depends only on ARM length and not arm number (the Pearson-Helfand result), and
this project has never tested that against real multiarm data. It is the one
star acquisition that would test a prediction rather than re-confirm the class.

Note `originals/struglinski_graessley1985_polydispersity_blends.pdf` is **Struglinski & Graessley 1985**,
*"Effects of polydispersity on the linear viscoelastic properties of entangled
polymers. 1."*, **Macromolecules 18, 2630-2643** — DOI confirmed to match the
file already present. 5 series x 7-10 compositions, flagged in
`prep_katzarova2018.py` as the future **blend** test set. Parts 2 and 3 exist
(**Macromolecules 19, 1754 (1986)**, doi:10.1021/ma00160a047;
**Macromolecules 21, 783 (1988)**, doi:10.1021/ma00181a039) and are the natural
companions when the blend class is built.

---

# Open questions for the user

1. **`zimm`**: is intrinsic-modulus / oscillatory-flow-birefringence data
   acceptable, or should the class be marked synthetic-only? See section 2.
2. **Priority order** if the download budget is limited: my recommendation is
   Abdel-Goad 2004 first, then the sticky/vitrimer set, then wormlike micelles,
   then critical gels.
