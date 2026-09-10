# rheo-fp forward models — how each $G'(\omega), G''(\omega)$ was arrived at

Audience: a rheologist. This is the derivation trail from published theory to the
exact expression in the code, including the shortcuts taken and where they bite.
Every forward model is validated (reproduce a published figure + recover planted
parameters) before it is trusted as a label generator or a bank candidate.

**Files.** `rheofp/models/{maxwell,solutions,network,star,tube}.py`;
generator `rheofp/data/synth.py`; identifier bank `rheofp/fitting/identify.py`.

**Sign / FT convention.** Everything uses $G^*(\omega) = G'(\omega) + iG''(\omega)$
with an $e^{+i\omega t}$ kernel. A single Maxwell mode $(g,\tau)$ contributes
$$
g\,\frac{i\omega\tau}{1+i\omega\tau}
= g\,\frac{(\omega\tau)^2}{1+(\omega\tau)^2} + i\,g\,\frac{\omega\tau}{1+(\omega\tau)^2}.
$$
Papers written under $e^{-i\omega t}$ (Milner–McLeish, notably) give the complex
conjugate; the real modulus expressions are identical.

---

## 0. The shared primitive — the discrete relaxation spectrum

`maxwell.maxwell_spectrum(omega, G, tau)` computes, for a set of modes $\{(g_i,\tau_i)\}$,
$$
G'(\omega) = \sum_i g_i \frac{(\omega\tau_i)^2}{1+(\omega\tau_i)^2}, \qquad
G''(\omega) = \sum_i g_i \frac{\omega\tau_i}{1+(\omega\tau_i)^2}.
$$
This is the generalized Maxwell / Prony series — the exact $G^*$ of $N$
Maxwell elements in parallel, equivalently a discrete approximation to
$G^*(\omega) = \int H(\tau)\,\frac{i\omega\tau}{1+i\omega\tau}\,\mathrm{d}\ln\tau$.

**8 of the 10 classes are nothing more than a recipe for building
$\{(g_i,\tau_i)\}$**, then this sum. What follows for those classes is: *what
mode ladder, and why that ladder*. Two classes (`cured_elastomer`,
`critical_gel`) use a fractional element instead and are derived from scratch.

Implementation note: the sum is vectorized as an outer product
$\omega_a \tau_i$, `denom = 1 + (wt)**2`, then `(G * wt**2 / denom).sum(axis=1)`.
No approximation beyond floating point.

---

## 1. `zimm` — dilute linear chain in a good solvent

**Theory.** Rouse–Zimm bead–spring: a chain of $N$ submolecules has $N$
internal normal modes $p = 1\dots N$, each a Maxwell element. The modulus per
mode is $k_BT$ per chain per mode, i.e. $g_p = nk_BT = G$ split evenly,
$g_p = G_{\text{scale}}/N$. The mode times follow
$$
\tau_p = \frac{\tau_1}{p^{\,x}}, \qquad
\begin{cases} x = 2 & \text{Rouse (free-draining)}\\[2pt] x = 3\nu \approx 1.8 & \text{Zimm (non-draining, good solvent)} \end{cases}
$$
The Zimm exponent is $3\nu$ with $\nu \approx 0.588$ (good solvent), commonly
rounded to $1.8$; $\nu = 1/2$ (theta) would give $3/2$.

**From theory to code** (`solutions._rouse_spectrum`, `model_zimm`):

1. `p = arange(1, N+1)`.
2. `tau = tau1 / p**1.8` — the exponent is hard-coded to `1.8`, not fitted. Only
   $(\log G_{\text{scale}}, \log\tau_1, N)$ are free.
3. Equal modulus weight `g = ones_like(tau)`, then renormalized
   `g *= G_scale / g.sum()` so $\sum_i g_i = G_{\text{scale}}$ exactly (the code
   sets the *sum*, not $g_p = G_{\text{scale}}/N$ literally — same thing here,
   but this is the line that matters if anyone changes the weights).
4. Hand `(g, tau)` to `maxwell_spectrum`.

Closed form of what comes out:
$$
G'(\omega) = \frac{G_{\text{scale}}}{N}\sum_{p=1}^{N}
\frac{(\omega\tau_1 p^{-1.8})^2}{1+(\omega\tau_1 p^{-1.8})^2}, \qquad
G''(\omega) = \frac{G_{\text{scale}}}{N}\sum_{p=1}^{N}
\frac{\omega\tau_1 p^{-1.8}}{1+(\omega\tau_1 p^{-1.8})^2}.
$$

**Limits / caveats.**
- Terminal: $G' \sim \omega^2$, $G'' \sim \omega$ (dominated by $p=1$).
- Intermediate: the mode sum gives the power law $G',G'' \sim \omega^{1/x} = \omega^{0.556}$ for Zimm (vs $\omega^{1/2}$ Rouse).
- Finite $N$ saturates $G'$ at the top of the window at $\approx G_{\text{scale}}$ — a numerical plateau, not an entanglement plateau. `N` is bounded $[2, 200]$; the pre-filter's `has_plateau` test is built to not be fooled by this.
- **Sampling bounds** (`synth`, from `solutions.ZIMM_BNDS`): $\log_{10}G_{\text{scale}} \in [-2,8]$, $\log_{10}\tau_1 \in [-4,4]$, $N \in [2,200]$.

## 2. `rouse_screened` — screened / concentrated solution

Byte-identical to `zimm` except step 2 uses exponent `2.0`
(`model_rouse`, `_rouse_spectrum(..., exponent=2.0)`):
$$
\tau_p = \tau_1/p^2.
$$
Same three parameters, same bounds.

> **This is the crux degeneracy.** `zimm` and `rouse_screened` differ *only* by
> $x = 1.8$ vs $2.0$ in the mode-spacing exponent. The resulting $G^*$ curves
> differ by a few percent in slope over the intermediate zone — below the 2%
> noise floor for a short window. In the current model this pair is ~58% of all
> residual classification error, and `star` (k=3, also a broad terminal
> spectrum) now ties into the same cluster on the AICc side. Nothing in the
> forward physics will fix this; it is a genuine identifiability limit of SAOS.

## 3. `reptation` — entangled linear melt

Two forwards exist. **The bank uses the cheap one** (`solutions.model_reptation`);
the Likhtman–McLeish 2002 implementation (`tube.py`) is used for real linear-melt
fitting and as the `branched_spectrum` building block.

### Bank version (`model_reptation`)

Doi–Edwards $G(t) = G_e \sum_{p\,\text{odd}} \frac{8}{\pi^2 p^2} e^{-p^2 t/\tau_d}$,
transformed mode-by-mode, **plus** a Rouse sub-ladder between $\tau_e$ and $\tau_d$
for the high-$\omega$ rise that pure D–E lacks:

$$
\text{reptation: } \tau_p = \tau_d/p^2,\quad g_p = G_e\,\frac{8}{\pi^2 p^2}, \quad p = 1,3,\dots,29
$$
$$
\text{Rouse: } \tau_q = \tau_e/q^2,\quad g_q = G_e/Z, \quad q = 1\dots Z, \qquad \tau_e \equiv \tau_d/Z^3
$$

**Steps** (`model_reptation`): `p = arange(1,31,2)`; `g_rep = Ge*8/(pi**2*p**2)`;
`tau_rep = tau_d/p**2`; `tau_e = tau_d/Z**3`; `q = arange(1, round(Z)+1)`;
`g_rouse = full(q, Ge/Z)`; `tau_rouse = tau_e/q**2`; concatenate; `maxwell_spectrum`.

**Params** $(\log G_e, \log\tau_d, Z)$, $Z \ge 2$ enforced. Bounds
$\log_{10}G_e \in [0,8]$, $\log_{10}\tau_d \in [-3,5]$, $Z \in [2,200]$.

**Caveats.**
- $\tau_e = \tau_d/Z^3$ is the textbook scaling with prefactor 1 — not $3Z^3\tau_e$ (that is `tube.tau_d0`). The bank model's $\tau_e$ is a derived bookkeeping time, not a fitted friction time.
- Odd modes truncated at $p = 29$. Fine for $G^*$ over a normal window; do not use this ladder for $G(t)$ at short times.
- No CLF, no CR. The terminal peak is sharper than a real polydisperse melt — which is *intentional* here: it is what lets AICc separate `reptation` from the deliberately-broad `branched`/BSW spectrum.

### Reference version (`tube.py`, Likhtman–McLeish 2002)

Implemented close to verbatim, eq. numbers in the docstring:
- $\mu(t)$ — single-chain tube survival: reptation modes (eq 13, $p^\ast_{\text{odd}}$, $\tilde G(Z)$ from eq 12) **plus** the early-time CLF continuum $\int w(\varepsilon)e^{-\varepsilon t}\mathrm{d}\varepsilon$ with $w \propto \varepsilon^{-5/4}$ (eq 14, $\varepsilon^\ast$).
- $R(t)$ — Rubinstein–Colby constraint release: tube-segment mobilities sampled from $P(\varepsilon)$ = inverse Laplace of $\mu$, mode count via a **vectorized Sturm sequence** (`_Mcount_vectorized`), averaged over `nchains`.
- $G^*(\omega)$: $\tfrac45\mu(t)R(t)$ fitted to a non-negative Prony series (`nnls`), transformed analytically, then the eq-19 longitudinal ($g = G_e/5Z$ per mode, $p<Z$) and high-frequency transverse ($g = G_e/Z$, $\tau_p = \tau_R/2p^2$) Rouse sums added.
- **Speed**: cache the Prony modes across frequency points (`_prony_modes_cache`) — never recompute per $\omega$. ~10–22× with the vectorized Sturm sequence.
- **Validity window** (`valid_window`): $[1/(30\tau_d),\, 1/\tau_R]$. Outside it, $G''$ can exceed $G_e$ unphysically; the generator keeps synthetic linear-melt curves inside this band.

## 4. `sticky_rouse` — unentangled associating chain (transient network / vitrimer)

**Theory.** Leibler–Rubinstein–Colby sticky Rouse. Below the sticker lifetime
$\tau_s$ the strands between stickers relax as bare Rouse chains (fast, carrying
the transient-network plateau $G_s$); the network only *renews* on the timescale
$\tau_s \gg \tau_R$, which carries the same $G_s$. Between $\tau_R$ and $\tau_s$
the loss modulus dips — the **sticker shoulder**.

**Mode ladder** (`solutions.model_sticky_rouse`):
$$
\text{fast: } \tau_p = \tau_R/p^2, \quad g_p = G_s/N_{\text{st}}, \quad p = 1\dots N_{\text{st}}
\qquad
\text{slow: } \tau = \tau_s, \quad g = G_s.
$$
Concatenate `[tau_s]` with the fast ladder, `[Gs]` with the fast weights,
`maxwell_spectrum`.

**Steps / guards.** `tau_R = 10**min(log tau_R, log tau_s - 0.5)` — forces at
least half a decade of separation so the shoulder is always resolved (this is a
modelling choice, not physics: a real system with $\tau_R \to \tau_s$ has *no*
shoulder). `Nst = max(2, round(Nst))`.

**Params** $(\log G_s, \log\tau_s, \log\tau_R, N_{\text{st}})$, $k=4$.
Bounds: $\log_{10}G_s \in [0,7]$, $\log_{10}\tau_s \in [0,5]$,
$\log_{10}\tau_R \in [-5,1]$, $N_{\text{st}} \in [2,150]$.

## 5. `sticky_reptation` — entangled associating chain

**Theory.** Same idea one level up: the tube is renewed only as fast as stickers
permit, so terminal relaxation is at $\tau_{st} \gg \tau_s$. Three features in
$G''$: the entanglement plateau / high-$\omega$ Rouse wing, the sticker bump at
$\tau_s$, and the slow terminal at $\tau_{st}$.

**Mode ladder** (`solutions.model_sticky_reptation`):
$$
\text{reptation: } \tau_p = \tau_{st}/p^2,\ g_p = G_e\tfrac{8}{\pi^2 p^2}\ (p\ \text{odd}, \le 29)
$$
$$
\text{sticker: } \tau = \tau_s,\ g = \tfrac12 G_e
$$
$$
\text{Rouse: } \tau_q = \tau_s/q^2,\ g_q = G_e/Z,\ q = 1\dots Z, \qquad \tau_e \equiv \tau_s/Z^2
$$

Note the Rouse sub-ladder here hangs off $\tau_s$ (not $\tau_e$ as in class 3),
and $\tau_e = \tau_s/Z^2$ — a different bookkeeping choice, reflecting that the
sub-tube dynamics between stickers are what is being represented. Sticker weight
$\tfrac12 G_e$ is a fixed fraction, not fitted. Guard `tau_s = 10**min(log tau_s, log tau_st - 0.5)`.

**Params** $(\log G_e, \log\tau_{st}, Z, \log\tau_s)$, $k=4$.
Bounds: $\log_{10}G_e \in [0,8]$, $\log_{10}\tau_{st} \in [1,6]$,
$Z \in [2,200]$, $\log_{10}\tau_s \in [-2,4]$.

> **Temperature-stack coupling (classes 4, 5, and every non-network class).** A
> stack is one $\theta$ with all times Arrhenius-shifted:
> $\tau(T) = \tau_{\text{ref}}\exp[(E_a/R)(1/T - 1/T_{\text{ref}})]$
> (`maxwell.arrhenius_shift`), $E_a \in [20, 120]$ kJ/mol,
> $T_{\text{ref}} = 298.15$ K, stack spread 10–60 K. This is the *only* thing
> separating classes 4/5 from class 6: the vitrimer's whole spectrum walks
> along $\log\omega$ with $T$; the permanent network's does not (it only scales
> $G \propto T$). `resolve_melt_vs_network` measures that walk by aligning
> $\tan\delta(\omega)$ curves horizontally — $\tan\delta$ cancels the vertical
> shift factor exactly, so no $b_T$ fit is needed.

## 6. `cured_elastomer` — permanent crosslinked network

**Derived from scratch — not a mode ladder.** Fractional Kelvin–Voigt element:
a Hookean spring $G_\infty$ in parallel with a *springpot* $(c, m)$. The
springpot is the frequency-domain form of Chasset–Thirion power-law relaxation,
$G^*_{\text{sp}}(\omega) = c(i\omega)^m$. Using
$(i\omega)^m = \omega^m e^{i\pi m/2} = \omega^m[\cos\tfrac{\pi m}{2} + i\sin\tfrac{\pi m}{2}]$
and adding the spring in parallel:

$$
\boxed{\;
G'(\omega) = G_\infty + c\,\omega^m \cos\!\frac{\pi m}{2}, \qquad
G''(\omega) = c\,\omega^m \sin\!\frac{\pi m}{2}
\;}
$$

Direct in code (`network.chasset_thirion_spectrum`): `springpot = c*omega**m`;
`Gp = G_inf + springpot*cos(pi*m/2)`; `Gpp = springpot*sin(pi*m/2)`. No sum, no
discretization, exact.

**Params** $(\log G_\infty, \log c, m)$, $k=3$, $m \in (0.01, 0.99)$ but sampled
$[0.05, 0.45]$ (a cured elastomer has weak power-law dispersion). Signature:
$G' \to G_\infty > 0$ as $\omega \to 0$ (**never flows**); $\tan\delta = G''/G' \ll 1$
and rising slowly. Bounds $\log_{10}G_\infty \in [3.0, 6.5]$, $\log_{10}c \in [2,5]$
in `synth`; wider $[-4,9]$ in the fitting bank so a nearly-uncrosslinked sample
can push $G_\infty$ to effectively zero.

## 7. `critical_gel` — polymer at the gel point

**The $G_\infty \to 0$ limit of class 6.** Winter–Chambon: at the gel point
$G(t) = c\,t^{-u}$, whose $G^*$ is the bare springpot. Setting $G_\infty = 0$
above:
$$
G'(\omega) = c\,\omega^{u}\cos\!\frac{\pi u}{2}, \qquad
G''(\omega) = c\,\omega^{u}\sin\!\frac{\pi u}{2}
\qquad\Longrightarrow\qquad
\tan\delta = \tan\frac{\pi u}{2} \;\; (\omega\text{-independent}).
$$
`network.critical_gel_spectrum` just calls `chasset_thirion_spectrum(omega, 0.0, c, u)`.

**Params** $(\log c, u)$, $k=2$ — a *genuine* 2-parameter model, not a
3-parameter fit driving $G_\infty$ small. This is deliberate: it lets AICc
adjudicate gel ($k=2$) vs cured elastomer ($k=3$) on parameter count when the
data are ambiguous.

**$u$ is not $1/2$.** Winter–Chambon $n = 1/2$ is the balanced-stoichiometry,
entanglement-free special case. Tixier et al. (2004) measure $u = 0.69$–$0.75$
on end-linked PDMS. Sampled range `GEL_U = [0.45, 0.80]`; fitting window
`GEL_U_RANGE = [0.40, 0.85]`. **Do not narrow to 0.5.**

The frequency-independent $\tan\delta$ is also why `shift_factor` returns `NaN`
for a critical gel in a temperature stack — there is no structure in
$\tan\delta(\omega)$ to align against, so no $T$-shift is measurable *even in
principle* (`MIN_TAN_DELTA_STRUCTURE`).

## 8. `wormlike_micelle` — Cates living polymer

**Theory.** Cates: reversible scission couples to reptation. When
$\tau_{\text{break}} \ll \tau_{\text{rep}}$ the stress relaxes as a *single*
exponential with $\tau = \sqrt{\tau_{\text{rep}}\tau_{\text{break}}}$ — a Maxwell
fluid — with deviations at high $\omega$ (a $G''$ upturn) as internal Rouse/bending
modes turn on.

**Form** (`maxwell.wlm_spectrum`). Dominant Maxwell mode:
$$
G'(\omega) = G_0\,\frac{(\omega\tau)^2}{1+(\omega\tau)^2}, \qquad
\tau = \sqrt{\tau_{\text{rep}}\tau_{\text{br}}},
$$
$$
G''(\omega) = G_0\,\frac{\omega\tau}{1+(\omega\tau)^2}
\;+\;\underbrace{\beta\,G_0\,\frac{\sqrt{x}}{1 + 1/x}}_{\text{high-}\omega\text{ correction}},
\qquad x = \omega\tau_{\text{br}}.
$$
The correction term: `corr = beta*G0*sqrt(x)/(1 + 1/max(x,tiny))`. As $x \to 0$
it $\to \beta G_0 x^{3/2} \to 0$ (no effect at low $\omega$); as $x \gg 1$ it
$\to \beta G_0\sqrt{x}$, the $\omega^{1/2}$ Rouse-like wing. It is a
*practical* parameterization of the high-$\omega$ excess, not a first-principles
mode sum.

**Params** $(\log G_0, \log\tau_{\text{rep}}, \log\tau_{\text{br}}, \beta)$, $k=4$.
$\beta$ is **linear** (not $\log$) — so a planted and a fitted $\beta$ mean the
same thing. Bounds: $\log_{10}G_0 \in [0,4]$, $\log_{10}\tau_{\text{rep}} \in [-1,3]$,
$\log_{10}\tau_{\text{br}} \in [-4,0]$, $\beta \in [0.2, 1.5]$ (`synth`); the
fitting bank widens the times by $\pm$ decades for Arrhenius headroom.

**History note.** WLM was briefly generated but *absent from the identifier
bank* — a wormlike micelle then came back as `branched` at Akaike weight 1.000,
0.05-decade residual. A missing class does not present as low confidence; it
presents as a confident wrong answer from the most flexible candidate. Now
`WLM_MODELS` in the bank; there is a test that every generated class has a
candidate.

## 9. `branched` — long-chain-branched melt (LDPE)

**Model: the Baumgärtel–Schausberger–Winter (BSW) continuous relaxation
spectrum.** Chosen after the 3-parameter hierarchical double-reptation
`branched_spectrum` was shown *unable* to represent real LDPE (bottoms out at
$\gtrsim 0.28$ decades RMS on Pivokonsky 2006 E and B, any $\sigma$; a 10-mode
Maxwell reaches 0.02). BSW reaches ~0.06–0.07.

**Continuous spectrum** (two power-law wedges):
$$
H(\tau) = n_e\,G_N\left[
\left(\frac{\tau}{\tau_{\max}}\right)^{n_e}
+ \left(\frac{\tau}{\tau_c}\right)^{-n_g}\mathbf{1}\{\tau < \tau_c\}
\right], \qquad \tau \le \tau_{\max}.
$$
- Terminal wedge $\tau^{n_e}$: broad, $n_e \sim 0.2$–$0.7$. A single-power-law mode ladder cannot be made this wide — this is the whole point of BSW for LCB.
- Glassy/Rouse wedge $\tau^{-n_g}$: switches on below the crossover time $\tau_c$, $n_g \sim 0.4$–$0.7$.

**Discretization to $G^*$** (`maxwell.bsw_spectrum`):
1. Log-$\tau$ ladder, `n_modes = 120`, from $\tau_{lo} = 10^{-4}\min(\tau_c,\tau_{\max})$ to $\tau_{\max}$.
2. `dln = log_tau[1] - log_tau[0]`.
3. `H = n_e*G_N*(tau/tau_max)**n_e`; add `n_e*G_N*(tau/tau_c)**(-n_g)` where `tau < tau_c`.
4. Mode weights `g_i = H_i * dln` (i.e. $g_i = H(\tau_i)\,\Delta\ln\tau$), then `maxwell_spectrum`.

$G^*$ is therefore
$\sum_i H(\tau_i)\Delta\ln\tau \cdot \frac{i\omega\tau_i}{1+i\omega\tau_i}$,
a Riemann sum of $\int H(\tau)\frac{i\omega\tau}{1+i\omega\tau}\mathrm{d}\ln\tau$.

**Params** $(\log G_N, \log\tau_{\max}, \log\tau_c, n_e, n_g)$, $k=5$.
In `synth`, $\tau_c$ is drawn as an *offset below* $\tau_{\max}$ (0.2–4.0 decades)
so the two never cross. Bank bounds are absolute (not data-scaled) so the merged
registry is static: $\log_{10}G_N \in [0.5, 6]$, $\log_{10}\tau_{\max} \in [-3,4]$,
$\log_{10}\tau_c \in [-7, 2.9]$, $n_e \in [0.05, 0.90]$, $n_g \in [0.20, 1.00]$.

**Caveats.**
- $G_N$ is a **window-limited amplitude scale**, not a measured plateau modulus — on a terminal-zone sweep it is just an overall vertical scale. Do not report it as $G_N^0$.
- BSW's intrinsic breadth *cannot* fake a sharp reptation terminal, which is what keeps AICc's `branched` vs `reptation` call honest.
- BSW is the most flexible model in the bank → it silently absorbs out-of-bank classes (documented for vitrimers, and for star melts before class 10 was added: 25/30 planted stars came back `branched`). The `branched_vitrimer_contradiction()` reporter exists to flag the specific case of a `branched` winner that also shows a vitrimer power-law $G''$ wing.

## 10. `star` — star-polymer melt (Milner–McLeish)

**Theory.** A star cannot reptate (branch point pinned); stress relaxes by
**arm retraction** — the free end retracts a fractional distance $s \in [0,1]$
back down its tube against an entropic potential, then re-emerges in a new
direction. Milner & McLeish, *Macromolecules* 1997, 30, 2159, **with the 1998
erratum** (*Macromolecules* 31, 7479, Appendix). Eq. numbers below are the 1997
paper's.

### The modulus integral (eq 26)

$$
G^*(\omega) = (\alpha + 1)\,G_N \int_0^1 (1-s)^{\alpha}\,
\frac{i\omega\,\tau(s)}{1 + i\omega\,\tau(s)}\,\mathrm{d}s,
\qquad \alpha = \frac{4}{3}\ \text{(Colby–Rubinstein dilution exponent)}.
$$
The weight $(\alpha+1)(1-s)^\alpha$ integrates to 1 over $[0,1]$, so mode weights
sum to $G_N$ and the plateau is recovered on a wide window. **Discretized**
(`star.star_spectrum`): `s = linspace(eps, 1-eps, 400)`;
`g = G_N*(alpha+1)*(1-s)**alpha * ds`; `tau = tau_of_s(s, Z, tau_e)`;
`maxwell_spectrum(omega, g, tau)`. Under $e^{+i\omega t}$ this is the standard
Maxwell kernel; the paper's $-i\omega\tau/(1-i\omega\tau)$ is the $e^{-i\omega t}$
conjugate.

### The effective potential (eq 24)

Integrating the hierarchical retraction relation (eq 7) with dynamic dilution
$N_e(\phi) = N_e\phi^{-\alpha}$, $\phi = 1-s$:
$$
U_{\text{eff}}(s) = \frac{15Z}{4}\cdot
\frac{1 - (1-s)^{1+\alpha}\big(1 + (1+\alpha)s\big)}{(1+\alpha)(2+\alpha)}
\qquad [k_BT],
$$
$Z = N_a/N_e$ = entanglements **per arm**. At $\alpha = 1$ this collapses to the
Ball–McLeish form $15Z(s - \tfrac23 s^3)/8$ (eq 8) — checked to machine
precision in the tests. `star.ueff`; derivative `star.dueff_ds` collapses to
$\tfrac{15Z}{4}s(1-s)^\alpha$.

### The retraction time $\tau(s)$ (eqs 13, 29, joined by 22)

**Early (unactivated) branch, eq 13** — for $s$ below $s^\ast \sim (N_e/N)^{1/2}$
the barrier is sub-$k_BT$ and the end moves as a Rouse chain end:
$$
\tau_{\text{early}}(s) = \frac{225\pi^3}{256}\,Z^2\,\tau_R\,s^4,
\qquad \tau_R = Z^2\tau_e
\quad\Rightarrow\quad \tau_{\text{early}} \propto Z^4\tau_e\,s^4.
$$
(The $Z^4$ follows independently from eq 12 — derivation in the `_tau_early`
docstring. It is a small-$s$ asymptote and is *huge* at $s \to 1$ by
construction; eq 22 is what keeps it from being evaluated there alone.)

**Activated branch, eq 29** (first-passage time, eq 24 into eq 21 with
$D_{\text{eff}} = 2D_R$):
$$
\tau_{\text{act}}(s) = A(Z)\,
\frac{e^{U_{\text{eff}}(s)}}{\sqrt{\,s^2(1-s)^{2\alpha} + K^{-2}\,}},
$$
$$
A(Z) = \frac{1}{2}\cdot\frac{\sqrt{30}\,\pi^{5/2}}{30}\,Z^{3/2}\,\tau_e
\;\approx\; \frac{1}{2}\cdot 13.2\,Z^{3/2}\tau_e,
$$
$$
K = \left(\frac{15Z}{4}\right)^{\!\alpha/(1+\alpha)}
(1+\alpha)^{-(2\alpha+1)/(1+\alpha)}\;\Gamma\!\left(\frac{1}{1+\alpha}\right).
$$
Three transcription traps, all live in this project's history:
1. **The leading $\tfrac12$** is the authors' own erratum (MM1998 Appendix, under eq 10: "eq 29 of ref 1 with an additional factor of 1/2, mistakenly omitted"). This module was transcribed from the 1997 paper and inherited the error — found by fitting known-$Z$ data and getting $Z$ high by 1.4–2.2×.
2. **$Z^{3/2}$, not $Z^{5/2}$**: eq 29 folds the *constant* part $\tfrac{15Z}{4}$ of $U'_{\text{eff}}$ out of the eq-19 $1/U'_{\text{eff}}$ prefactor into the square-root denominator (hence a bare $s^2(1-s)^{2\alpha}$ there, not $(U'_{\text{eff}})^2$). That extracted $\tfrac{15Z}{4}$ must be divided out of $A(Z)$; leaving it in gives $Z^{5/2}$ and $\tau_{\text{act}}$ ~1 decade high. Cross-checks: MM's own "$\tau \sim \tau_e (N/N_e)^{3/2}e^{U_{\text{eff}}}$" scaling remark, and Ball–McLeish's $t_0 = \tau_e$ anchor.
3. **$K^{-2}$ (reciprocal) inside the root**, regularizing $s \to 1$ where $U_{\text{eff}}$ has a non-quadratic maximum.

**Crossover, eq 22** (`star.tau_of_s`):
$$
\tau(s) = \frac{\tau_{\text{early}}(s)}{1 + \tau_{\text{early}}(s)/\tau_{\text{act}}(s)}
\quad(\text{follows the faster branch}).
$$

### The added arm-Rouse high-frequency term (not in MM)

MM scope eq 26 to end at the $G''$ minimum (section IV, comment 1); a real SAOS
window goes past it, and without a term there the fitter inflates $Z$ to cover
the gap. `star._arm_rouse_modes` adds the Likhtman–McLeish eq-19 form (reused
from `tube.py`) on the **arm** ($Z$ = entanglements per arm, $\tau_R = Z^2\tau_e$):
$$
\text{longitudinal: } \tau_p = \tau_R/p^2,\ g_p = \tfrac{G_N}{5Z},\ p = 1\dots Z-1
$$
$$
\text{transverse: } \tau_p = \tau_R/2p^2,\ g_p = \tfrac{G_N}{Z},\ p \ge Z
\ \text{(truncated 2 decades below } 1/\omega_{\max}\text{, capped 4000 modes)}
$$
`arm_rouse=False` recovers the paper's bare eq-26 result (used for the analytic
tests). Effect on real data: median $|Z\text{ error}|$ 44% → 30%; fitted $G_N$
440–490 → 366–436 kPa (PI's true ~400).

### Parameters, limits, what it can and cannot say

**Params** $(\log G_N, Z, \log\tau_e)$, $k=3$. $G_N$ = pure vertical scale
(but with arm-Rouse on, $G'$ rises **above** $G_N$ at high $\omega$ — $G_N$ is
the plateau *level*, not the curve max). $\tau_e$ = pure horizontal scale.
**$Z$ is the only shape parameter** — it sets the barrier height and hence the
spectrum width ($\sim$2.9 decades at $Z=5$ to $\sim$7.4 at $Z=40$).

- **Arm count $f$ does not appear in $G^*$ at all.** Real prediction of the theory (LVE depends only on arm length) — reproduces Pearson–Helfand arm-number independence of viscosity. The class says "star", never "how many arms".
- **Past $Z \approx 40$: two $G''$ maxima**, as the Rouse and activated relaxations separate. Numerically converged (peak positions identical for $n_s$ 400→64000) — physics, not quadrature. Any feature assuming one loss peak misreads a high-$Z$ star; spectrum width must not be read off the global $G''$ peak near $Z \approx 40$.
- **$Z$ is not a quantitative output** — biased high 17–84% on the MM1998 four-arm PI stars. The cause is that below $Z \approx 4$ the fitting cost is *flat* in $Z$: $U_{\text{eff}}(1)$ is only 1–2 $k_BT$ and the activated terminal time sits under a decade above the arm's own Rouse time, so there is no star-specific shape left to constrain $Z$. (`Z_BOUNDS` floors at 4, but that floor is *not* what binds — refitting at floors 4/3/2/1 leaves the weakly-entangled arms at $Z \approx 7$–9, unmoved. Measured, `c40a286`.) Report the class only.
- **The two MM1998 misses are decisive losses, not ties** — $\Delta$AICc 57 and 103, star's RMS 20–55% worse than `branched`. The predictor of success is `terminal_reached`: where flow is observed in the window the class is 5/5; where it is not, 1/5. All four real-data failures across MM1998 + Santangelo sit in that second row (including Santangelo's *linear* control, returned as `star`). Cause is the missing low-frequency asymptote, not window width. Left for the report layer, not made a pre-filter discard (that would be the `has_shoulder` missing-evidence fallacy again).
- **$\alpha$ sensitivity is damped here**: terminal time moves ~0.16 decades between $\alpha = 1$ and $4/3$, where $U_{\text{eff}}(1)$ alone implies ~1.03 — because eq 22 blends the early and activated branches within ~0.3 decades of each other at $s \to 1$ for realistic $Z$. This is MM's own "simple crossover function", not a bug, but quantify against real data before any $\alpha$-dependent claim.

**Sampling** (`synth`): $\log_{10}G_N \in [3.5, 6.5]$, $Z \in [5, 55]$ (inside the
fitter's $[4, 60]$). **$\tau_e$ is derived, not drawn** — a star's spectrum spans
~23–24 decades while a window is ~3–5, so the *terminal* time is placed relative
to the window ($-3$ to $+1$ decades offset from $1/\omega_{lo}$) and $\tau_e$
back-computed via `_star_terminal_decades(Z)` $= \log_{10}[\tau(1)/\tau_e]$.
Measured 51% `terminal_reached` over $n=120$. The first offset range was
sign-inverted → 0% terminal over 60 curves, which would have taught the
classifier "stars never flow" — **re-measure that fraction if the range is
touched.**

---

## Cross-cutting: what the generator does to every curve

Per example (`synth.make_example`):
- **Point count** drawn $\in [10, 100]$ per curve (digitized figure ≈ 10–20, rheometer sweep ≈ 50–100). The ML loader then resamples to a fixed internal log-$\omega$ grid (`resample_log_grid`), so raw and resampled inputs give identical predictions — do not reintroduce a fixed-density assumption. Training at one fixed count taught the model to lean on density and it failed every real curve.
- **Window crop**: full span is $\log_{10}\omega \in [-2, 3]$; a random crop up to 2.5 decades is removed, distributed between the two ends. Teaches abstention rather than "no terminal region ⇒ the material has none".
- **Noise**: 2% multiplicative log-normal ($\sigma = 0.02$ decades) on both $G'$ and $G''$ — matches digitizing scatter on published figures.
- **Stacks**: $N \in \{1,2,3,4,5\}$ with weights $(0.40, 0.10, 0.15, 0.15, 0.20)$ — $N=1$ is the common real case. A stack is one $\theta$ + one $E_a$, Arrhenius-shifted per $T$ (networks: $G \propto T$ instead). Independent per-curve draws would teach a correlation no real material has.

## Validation status per class (as of 2026-09-09)

| Class | Forward validated against | Real-data check |
|---|---|---|
| zimm / rouse_screened | planted-parameter recovery; Colby (2010) scaling exponents | — (degenerate pair) |
| reptation (bank) | planted recovery | via linear-melt family |
| reptation (tube.py) | Likhtman–McLeish (2002) Fig. 10 reproduced verbatim | — |
| sticky_rouse / sticky_reptation | planted recovery; Arrhenius tying | Edera 2024, Ricarte 2023 vitrimers: **stack mechanism confirmed, fine class fails** — both come back `branched` (forward-model limit: discrete Maxwell modes can't reproduce a real vitrimer's power-law $G''$ wing) |
| cured_elastomer | planted recovery; `tests/test_network.py` | Darby 2022 cured silicones ✓ (6/6 literature set) |
| critical_gel | planted recovery | Tixier 2004 critical gel ✓ |
| wormlike_micelle | planted recovery; 40/40 self-correct vs sticky classes | 6/6 held after adding to bank |
| branched (BSW) | Pivokonsky 2006 LDPE E & B to ~0.06 decades | ✓ (part of the 6/6) |
| star | MM's own analytic statements (eq 8 limit, Fig 2 potential ratio, $\log\tau(1)/\tau_0 = 13.8$, eq-22 handoff); planted recovery exact | **partial** — `identify()` returns `star` for 5/7 MM1998 stars; success tracks `terminal_reached` (5/5 where flow is seen, 1/5 where not); the 2 misses go to `branched` at $\Delta$AICc 57/103 (decisive). No star-*melt* data yet; $Z$ not reportable |

**Overall (10-class, retrained):** synthetic accuracy 0.923 (merged-pair 0.968,
regime 0.999) vs AICc physics baseline 0.907 on the same split. 6/6 literature
single curves. Abstention is calibrated against the model's own errors on the
synthetic distribution and **cannot** flag molecularly-distinct
out-of-distribution material (blends, block copolymers, semicrystalline melts,
filled melts — none in the taxonomy).
