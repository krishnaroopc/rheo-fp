# Rheological Model Reference

Wishlist / literature survey for future expansion — broader than the current
frozen classifier taxonomy (see CLAUDE.md: 3 regimes, 8 fine classes, 6
model-only classes, scoped to polymer melts/solutions/networks). "Implemented"
rows have working, validated code; everything else is a candidate future
domain, not a current gap.

| Material Class | Popular Rheological Model | Extractable Parameters (Regression Targets) | Key Implementation / Reference | Status |
|---|---|---|---|---|
| Polymer Melts & Solutions | Doi-Edwards (Tube) Model | Entanglement molecular weight ($M_e$), reptation time ($\tau_d$), plateau modulus ($G_N^0$), number of entanglements per chain ($Z$) | Likhtman & McLeish (2002). Macromolecules, 35(16), 6332-6343. (Quantitative tube model implementation) | Implemented — `rheofp/models/tube.py` |
| Polymer Melts & Solutions | Rouse & Zimm Models | Total molecular weight ($M_w$), radius of gyration ($R_g$), monomeric friction coefficient | Rouse, P. E. (1953). The Journal of Chemical Physics, 21(7), 1272-1280. | Implemented — `rheofp/models/solutions.py` |
| Elastomers, Rubbers & Gels | Rubber Elasticity Theory (Affine & Phantom Networks) | Crosslink density ($\nu$), average molecular weight between crosslinks ($M_c$), network mesh size | Treloar, L. R. G. (1975). The Physics of Rubber Elasticity. Oxford University Press. | Wishlist |
| Elastomers, Rubbers & Gels | Poroelastic Models (Specific to Hydrogels) | Solvent permeability, drained/undrained bulk modulus, Poisson's ratio | Xu et al. (2022) | Wishlist |
| Soft Glassy Materials (Emulsions, Foams, Suspensions) | Soft Glassy Rheology (SGR) Model | Effective "noise temperature" ($x$), yield stress ($\sigma_y$) | Sollich et al. (1997). Physical Review Letters, 78(10), 2020. | Wishlist (glassy regime was explicitly dropped from the current taxonomy — revisit if reintroduced) |
| Soft Glassy Materials (Emulsions, Foams, Suspensions) | Bingham / Herschel-Bulkley (Oscillatory adaptation) | Yield stress ($\sigma_y$), consistency index ($K$), flow behavior index ($n$) | Ewoldt et al. (2008). Journal of Rheology, 52(6), 1427-1458. (LAOS implementation) | Wishlist |
| Suspensions (Hard Spheres) | Krieger-Dougherty Model | Maximum packing fraction ($\phi_m$), intrinsic viscosity ($[\eta]$) | Krieger & Dougherty (1959). Transactions of the Society of Rheology, 3, 137-152. | Wishlist |
| Polymer Blends & Emulsions | Palierne Model | Interfacial tension ($\alpha$), dispersed phase droplet radius ($R$), volume fraction ($\phi$) | Palierne, J. F. (1990). Rheologica Acta, 29(3), 204-214. | Wishlist |
| Vitrimers & Dynamic Networks | Sticky Rouse / Sticky Reptation Models | Bond activation energy ($E_a$), average bond lifetime/dissociation rate, topological relaxation time | Winne et al. (2019) | Implemented — `rheofp/models/maxwell.py` (`sticky_maxwell_stack`, Arrhenius temperature-tying) |
| Wormlike Micelles | Cates Model (Living Polymers) | Scission time ($\tau_{break}$), reptation time ($\tau_{rep}$), plateau modulus ($G_0$), contour length | Cates, M. E. (1987). Macromolecules, 20(9), 2289-2296. | Implemented — `rheofp/models/maxwell.py` (`wlm_spectrum`, practical WLM) |
| Bitumen & Asphalt | Christensen-Anderson-Marasteanu (CAM) Model | Glassy modulus ($G_g$), crossover frequency ($\omega_c$), rheological index ($R$) | Christensen & Anderson (1992). Journal of the Association of Asphalt Paving Technologists, 61. | Wishlist |
| Polyelectrolytes & Coacervates | Dobrynin Scaling Model / Transient Network Models | Electrostatic blob size, effective charge density, ionic association (sticker) lifetime, fraction of condensed counterions | Dobrynin et al. (1995). Macromolecules, 28(6), 1859-1871. | Implemented — `rheofp/models/solutions.py` (polyelectrolyte c-stack discriminator) |
| Shape-Memory Polymers | Thermoviscoelastic Models (Multi-branch Maxwell + WLF/Arrhenius shift) | Glass transition temperature ($T_g$), rubbery plateau modulus, glassy modulus, thermal shift factors ($C_1$, $C_2$) | Qi et al. (2008). Journal of the Mechanics and Physics of Solids, 56(5), 1730-1751. | Wishlist |
| Biofluids & Soft Tissues | Fung's Quasilinear Viscoelasticity (QLV) / Fractional Springpot Models | Instantaneous elastic response, long-term elastic modulus, fractional order parameter ($\alpha$ or $\beta$) | Bonfanti et al. (2020) | Wishlist |
| Biofluids (Specifically Blood) | Casson Model | Casson yield stress ($\sigma_c$), Casson viscosity ($\eta_c$) | Casson, N. (1959). Rheology of Disperse Systems, 84-104. | Wishlist |
| Cementitious Materials | Thixotropic Elasto-Viscoplastic Models (e.g., Roussel Model) | Static yield stress ($\sigma_{y,s}$), dynamic yield stress ($\sigma_{y,d}$), thixotropic structural buildup rate ($A_{thix}$), plastic viscosity ($\eta_p$) | Roussel, N. (2006). Cement and Concrete Research, 36(4), 711-719. | Wishlist |
| Food Systems (Doughs, Dairy) | Fractional Zener Model / Burgers Model (for creep/recovery) | Zero-shear viscosity ($\eta_0$), retardation time, instantaneous compliance ($J_0$), strain-hardening index | van der Sman et al. (2023) | Wishlist |
| Broad Pseudo-plastic/Shear-thinning Fluids | Carreau-Yasuda Model | Zero-shear viscosity ($\eta_0$), infinite-shear viscosity ($\eta_\infty$), relaxation time ($\lambda$), power-law index ($n$), Yasuda transition parameter ($a$) | Yasuda et al. (1981). Rheologica Acta, 20(2), 163-178. | Wishlist (steady-shear model — not SAOS/LVE; would need a different input pipeline) |
