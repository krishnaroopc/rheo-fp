# The 10 classes — parameters and sampling ranges

Companion to `docs/forward_models.md` (which has the full derivations). This is
just the parameter reference.

Conventions:

- Moduli and characteristic times are sampled in **log10**. Everything else
  (N, Z, Nst, m, u, n_e, n_g, beta) is sampled linearly.
- The ranges below are the **generator's** (`rheofp/data/synth.py`). The AICc
  fitting bank (`rheofp/fitting/identify.py`) uses a deliberately *wider*
  search space for some classes.
- Fixed constants (Zimm exponent 1.8, the Doi-Edwards 8/pi^2 weights, the
  tau_e scalings) are not parameters and are not listed.

---

## Summary table

| # | Class | k | Parameters | Forward model |
|---|-------|---|------------|---------------|
| 1 | zimm | 3 | log G_scale, log tau_1, N | Zimm bead-spring, tau_p = tau_1 / p^1.8 |
| 2 | rouse_screened | 3 | log G_scale, log tau_1, N | Rouse bead-spring, tau_p = tau_1 / p^2 |
| 3 | reptation | 3 | log G_e, log tau_d, Z | Doi-Edwards odd modes + Rouse sub-ladder (tau_e = tau_d / Z^3) |
| 4 | sticky_rouse | 4 | log G_s, log tau_s, log tau_R, Nst | Fast strand-Rouse ladder + slow network-renewal mode at tau_s |
| 5 | sticky_reptation | 4 | log G_e, log tau_st, Z, log tau_s | Reptation ladder + sticker mode (½G_e at tau_s) + Rouse sub-ladder (tau_e = tau_s / Z^2) |
| 6 | cured_elastomer | 3 | log G_inf, log c, m | Fractional Kelvin-Voigt: G' = G_inf + c w^m cos(pi m/2), G'' = c w^m sin(pi m/2) |
| 7 | critical_gel | 2 | log c, u | Bare springpot (the G_inf -> 0 limit of #6) |
| 8 | wormlike_micelle | 4 | log G_0, log tau_rep, log tau_br, beta | Cates single Maxwell mode at tau = sqrt(tau_rep tau_br) + high-w G'' correction |
| 9 | branched | 5 | log G_N, log tau_max, log tau_c, n_e, n_g | Baumgartel-Schausberger-Winter two-wedge relaxation spectrum, discretized |
| 10 | star | 3 | log G_N, Z, log tau_e | Milner-McLeish arm retraction, eq-26 modulus integral over arm coordinate s |

---

## Sampling ranges

### 1. zimm  &  2. rouse_screened

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_scale | -2 .. 8 | log10 Pa |
| log10 tau_1 | -4 .. 4 | log10 s |
| N (modes) | 2 .. 200 | integer |

Same ranges for both classes. They differ only in the fixed mode-spacing
exponent: 1.8 (zimm) vs 2.0 (rouse_screened).

### 3. reptation (bank version)

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_e | 0 .. 8 | log10 Pa |
| log10 tau_d | -3 .. 5 | log10 s |
| Z (entanglements) | 2 .. 200 | — |

### 4. sticky_rouse

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_s | 0 .. 7 | log10 Pa |
| log10 tau_s (sticker / terminal) | 0 .. 5 | log10 s |
| log10 tau_R (strand Rouse) | -5 .. 1 | log10 s |
| Nst (Rouse modes per strand) | 2 .. 150 | integer |

Code enforces tau_R < tau_s by at least 0.5 decades.

### 5. sticky_reptation

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_e | 0 .. 8 | log10 Pa |
| log10 tau_st (sticky-reptation terminal) | 1 .. 6 | log10 s |
| Z (entanglements) | 2 .. 200 | — |
| log10 tau_s (sticker) | -2 .. 4 | log10 s |

Code enforces tau_s < tau_st by at least 0.5 decades. Sticker mode weight is a
fixed ½ G_e, not a parameter.

### 6. cured_elastomer

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_inf (equilibrium modulus) | 3.0 .. 6.5 | log10 Pa |
| log10 c (springpot quasi-modulus) | 2 .. 5 | log10 Pa s^m |
| m (power-law exponent) | 0.05 .. 0.45 | — |

Fitting bank widens G_inf down to 1e-4 Pa so a nearly-uncrosslinked sample can
be represented.

### 7. critical_gel

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 c (springpot quasi-modulus) | 0 .. 4 | log10 Pa s^u |
| u (gel exponent) | 0.45 .. 0.80 | — |

u is deliberately not fixed at 0.5: Winter-Chambon 0.5 through Tixier (2004)
end-linked PDMS 0.75. Fitting window 0.40 .. 0.85.

### 8. wormlike_micelle

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_0 (plateau) | 0 .. 4 | log10 Pa |
| log10 tau_rep (reptation) | -1 .. 3 | log10 s |
| log10 tau_br (breaking) | -4 .. 0 | log10 s |
| beta (high-w correction amplitude) | 0.2 .. 1.5 | linear |

Dominant relaxation time is tau = sqrt(tau_rep tau_br). beta is linear (not
log) so a planted and a fitted value mean the same thing.

### 9. branched (BSW spectrum)

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_N (amplitude scale) | 2.5 .. 6.0 | log10 Pa |
| log10 tau_max (longest time) | -1 .. 3 | log10 s |
| log10 tau_c (crossover time) | drawn as 0.2 .. 4.0 decades *below* tau_max | log10 s |
| n_e (terminal-wedge exponent) | 0.15 .. 0.75 | — |
| n_g (glassy-wedge exponent) | 0.40 .. 0.70 | — |

tau_c is an offset below tau_max, so the two wedges never cross. G_N is a
window-limited amplitude, not a measured plateau modulus.

### 10. star (Milner-McLeish)

| Parameter | Range | Units |
|-----------|-------|-------|
| log10 G_N (plateau modulus) | 3.5 .. 6.5 | log10 Pa |
| Z (entanglements per arm) | 5 .. 55 | — |
| log10 tau_e (entanglement-segment Rouse time) | **derived, not drawn** | log10 s |

tau_e is back-computed: a star's spectrum spans ~23-24 decades while a sweep
window is ~3-5, so the *terminal* time tau(1) is placed relative to the window
(offset -3 .. +1 decades from 1/w_lo) and tau_e follows from tau(1)/tau_e being
a fixed function of Z alone. Z is the only shape parameter. Arm count does not
enter the model at all and cannot be recovered. Z itself is biased high on real
data and is not a reportable output.

---

## What the generator adds to every curve

| Effect | Setting |
|--------|---------|
| Frequency span | log10 w in [-2, 3] rad/s |
| Window crop | up to 2.5 decades removed, split between the two ends |
| Point count | drawn per curve in [10, 100], then resampled to a fixed internal grid by the ML loader |
| Noise | 2% multiplicative log-normal (sigma = 0.02 decades) on G' and G'' |
| Stack size N | {1,2,3,4,5} with weights (0.40, 0.10, 0.15, 0.15, 0.20) |
| Temperature stack | one theta, times Arrhenius-shifted; Ea in [20, 120] kJ/mol; T_ref 298.15 K; spread 10-60 K. Networks (6, 7) do not shift — moduli scale G ∝ T instead. |
