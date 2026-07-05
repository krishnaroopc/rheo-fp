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
  Tables 2/3; see module docstring for validation scope)
