# References

Literature underlying the models implemented in `rheofp/`. Source PDFs are
kept locally in `originals/` (gitignored) and are not distributed with this
repository - citations only, below.

- Likhtman, A. E., & McLeish, T. C. B. (2002). Quantitative theory for linear
  dynamics of linear entangled polymers. *Macromolecules*, 35(16), 6332-6343.
  — `rheofp/models/tube.py`

- McLeish, T. C. B., & Larson, R. G. (1998). Molecular constitutive equations
  for a class of branched polymers: The pom-pom polymer. *Journal of
  Rheology*, 42(1), 81-110. — `rheofp/models/pompom.py`

- Verbeeten, W. M. H., Peters, G. W. M., & Baaijens, F. P. T. (2001).
  Differential constitutive equations for polymer melts: The extended
  pom-pom model. *Journal of Rheology*, 45(4), 823-843. — `rheofp/models/pompom.py`
  (XPP extension of McLeish & Larson 1998; verification dataset, Table III)

- Leibler, L., Rubinstein, M., & Colby, R. H. (1991). Dynamics of reversible
  networks. *Macromolecules*, 24(16), 4701-4707. — sticky-Maxwell / associating
  network physics, `rheofp/models/maxwell.py`

- Rubinstein, M., & Semenov, A. N. (1998). Thermoreversible gelation in
  solutions of associating polymers. 1. Statics. *Macromolecules*, 31(4),
  1386-1397; and (2001) 2. Linear dynamics. *Macromolecules*, 34(4), 1058-1068.
  — sticky-reptation / sticky-Rouse models, `rheofp/models/solutions.py`

- Stukalin, E. B., Cai, L.-H., Kumar, N. A., Leibler, L., & Rubinstein, M.
  (2013). Self-healing of unentangled polymer networks with reversible bonds.
  *Macromolecules*, 46(18), 7525-7541. — vitrimer/associating-network Arrhenius
  temperature-tying, `rheofp/models/maxwell.py`

- Colby, R. H. (2010). Structure and linear viscoelasticity of flexible
  polymer solutions: comparison of polyelectrolyte and neutral polymer
  solutions. *Rheologica Acta*, 49(5), 425-442. — polymer-solution
  concentration-scaling, `rheofp/models/solutions.py`

- Dobrynin, A. V., Colby, R. H., & Rubinstein, M. (1995). Scaling theory of
  polyelectrolyte solutions. *Macromolecules*, 28(6), 1859-1871. —
  polyelectrolyte c-stack discriminator, `rheofp/models/solutions.py`

- Pivokonsky, R., Zatloukal, M., & Filip, P. (2006). On the predictive/fitting
  capabilities of the advanced differential constitutive equations for
  branched LDPE melts. *Journal of Non-Newtonian Fluid Mechanics*, 135(1),
  58-73. — `rheofp/models/pompom.py` LVE verification target (data/pivo2006.npz,
  Tables 2/3; see module docstring for validation scope). Also the real-data
  target for the branched class's BSW spectrum (`bsw_spectrum` in
  `rheofp/models/maxwell.py`): E and B fit to ~0.06-0.07 decades RMS.

- Baumgärtel, M., Schausberger, A., & Winter, H. H. (1990). The relaxation of
  polymers with linear flexible chains of uniform length. *Rheologica Acta*,
  29(5), 400-408; and Baumgärtel, M., & Winter, H. H. (1992). Interrelation
  between continuous and discrete relaxation time spectra. *Journal of
  Non-Newtonian Fluid Mechanics*, 44, 15-36. — the BSW relaxation-time
  spectrum (two power-law wedges); `bsw_spectrum` / `model_branched` in
  `rheofp/models/maxwell.py`, the branched / long-chain-branched melt class.

- Chasset, R., & Thirion, P. (1965). Viscoelastic relaxation of rubber
  vulcanizates. In *Proc. Conf. Phys. Non-Cryst. Solids*, 345-359. —
  power-law relaxation of crosslinked networks; frequency-domain form is the
  forward model in `rheofp/models/network.py`

- Curro, J. G., & Pincus, P. (1983). A theoretical basis for viscoelastic
  relaxation of elastomers in the long-time limit. *Macromolecules*, 16(4),
  559-562. — Chasset-Thirion exponent m tied to crosslink density,
  `rheofp/models/network.py`

- Winter, H. H., & Chambon, F. (1986). Analysis of linear viscoelasticity of
  a crosslinking polymer at the gel point. *Journal of Rheology*, 30(2),
  367-382. — critical-gel criterion (`critical_gel_spectrum`),
  `rheofp/models/network.py`

- Tixier, T., Tordjeman, P., Cohen-Solal, G., & Mutin, P. H. (2004).
  Structural effects on the viscoelasticity of PDMS networks close to the
  sol-gel threshold. *Journal of Rheology*, 48(1), 39-52. — critical-gel
  real-data validation (native SAOS, exponent u = 0.69-0.75),
  `rheofp/models/network.py`

- Vega, D. A., Villar, M. A., Alessandrini, J. L., & Vallés, E. M. (2001).
  Terminal relaxation of model poly(dimethylsiloxane) networks with pendant
  chains. *Macromolecules*, 34(13), 4591-4596. — model PDMS network,
  route-(a) parameter self-consistency check (Table 2), `rheofp/models/network.py`

- Martin, G., Barrès, C., Cassagnau, P., Sonntag, P., & Garois, N. (2008).
  Viscoelasticity of randomly crosslinked EPDM networks. *Polymer*, 49(7),
  1892-1901. — cured-EPDM tabulated Ge/tan d (Table 1) + swelling-based
  crosslink density (Table 2) single-point checks, `rheofp/models/network.py`

- Darby, D. R., Cai, Z., Mason, C. R., & Pham, J. T. (2022). Modulus and
  adhesion of Sylgard 184, Solaris, and Ecoflex 00-30 silicone elastomers
  with varied mixing ratios. *Journal of Applied Polymer Science*, 139(25),
  e52412. — cured-elastomer real-data validation (native cured-PDMS SAOS,
  Fig. 1a / Fig. S1), `rheofp/models/network.py`
