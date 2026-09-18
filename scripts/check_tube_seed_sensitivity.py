"""Are the Katzarova class calls stable under the tube model's RNG seed?

`tube.R_of_t` estimates constraint release by SAMPLING `LM_NCHAINS = 20`
chains. The seed is fixed (`LM_RNG_SEED = 0`), so every shipped result is
reproducible - but reproducible is not the same as converged. Measured
convergence of `tube.Gstar` against an nchains=480 reference:

    nchains    dG'(dec)    dG''(dec)
        20     1.5e-02     1.3e-02      <- SHIPPED
        60     3.3e-03     6.9e-03
       240     3.9e-03     3.6e-03

So the forward model carries ~1.3e-2 decades of sampling error, while the
AICc bank routinely adjudicates rms margins of ~2e-4 decades. Any margin
smaller than that noise is a property of the DRAW, not of the physics.

>>> RESULT (2026-09-18, seeds 0-4, docs/tube_seed_sensitivity_2026-09-18.txt)

    PS392   branched on 5/5 seeds   dAICc +51.6 .. +68.9   STABLE
    PS206   branched on 5/5 seeds   dAICc +27.7 .. +44.8   STABLE
    PS105   reptation on seed 0 ONLY; branched on 1,2,3,4  *** FLIPS ***

`branched` scores an identical rms on every seed (it does no sampling);
reptation's rms swings 0.02045 - 0.02685. PS105's `reptation` call, recorded
on 2026-09-17 as evidence that the BSW fault was "2/3, not 3/3", is therefore
an artifact of seed 0. On this evidence the fault is 3/3, as first recorded.

PS392/PS206 are unaffected - their margins are far above the noise - so the
BSW fault itself stands. Only the PS105 requalification is withdrawn.

Diagnostic only: changes nothing, ships nothing. Run:
    uv run python scripts/check_tube_seed_sensitivity.py <out.json> [--seeds 0 1 2]
"""
import sys, json
import numpy as np
from rheofp.models import solutions
from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz

SEEDS = [int(a) for a in sys.argv[2:]] or [0, 1, 2, 3, 4]
SAMPLES = ["PS392", "PS206", "PS105"]
ds = load_npz("data/katzarova2018.npz")

print("shipped LM_NCHAINS=%d, LM_RNG_SEED=%d\n"
      % (solutions.LM_NCHAINS, solutions.LM_RNG_SEED))

rows = {}
for s in SAMPLES:
    rec = ds[s]
    rows[s] = []
    print("%s:" % s)
    print("  %4s %-16s %10s %10s %10s"
          % ("seed", "winner", "rms_win", "rms_rept", "rms_branch"))
    for sd in SEEDS:
        solutions.LM_RNG_SEED = sd          # vary ONLY the sampling draw
        r = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"])
        by = {m["name"]: m for m in r["ranking"]}
        rept, br = by.get("reptation"), by.get("branched")
        d = (rept["aicc"] - br["aicc"]) if (rept and br) else float("nan")
        rows[s].append({"seed": sd, "winner": r["best"],
                        "rms_reptation": rept["rms_log"] if rept else None,
                        "rms_branched": br["rms_log"] if br else None,
                        "daicc_rept_minus_branch": d})
        print("  %4d %-16s %10.5f %10.5f %10.5f   dAICc(rept-branch)=%+8.2f"
              % (sd, r["best"], by[r["best"]]["rms_log"],
                 rept["rms_log"] if rept else float("nan"),
                 br["rms_log"] if br else float("nan"), d))
    winners = {x["winner"] for x in rows[s]}
    print("  -> %s across seeds: %s\n"
          % ("STABLE" if len(winners) == 1 else "*** FLIPS ***",
             sorted(winners)))

solutions.LM_RNG_SEED = 0
json.dump(rows, open(sys.argv[1], "w"), indent=2, default=float)
print("wrote " + sys.argv[1])
