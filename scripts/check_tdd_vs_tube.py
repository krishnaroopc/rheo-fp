"""P3 + P4: TDD-DR against the Likhtman-McLeish tube model on REAL
monodisperse linear melts, and against BSW (`branched`), which currently beats
the correct physics on all three.

Scored against the predictions committed in `docs/tdd_preregistration.md`
BEFORE this was run (commit c98ce33):

  P3  TDD's rms must not be worse than tube.py's by more than 0.005 decades.
      tube reference: 0.0314 / 0.0300 / 0.0222 on PS392 / PS206 / PS105.
  P4  NO prediction registered. Three outcomes were named in advance:
      (a) TDD beats BSW on some/all -> the fault was partly forward-model
          inaccuracy; (b) TDD loses by a similar margin -> the fault is about
          BSW's flexibility, a USEFUL NEGATIVE to be reported as such;
          (c) TDD loses by a LARGER margin -> TDD is worse physics, VETO.

Also reports Z recovery against the paper's true Z (29.5 / 15.5 / 7.9), and
runs the seed sweep that `tube.py` needs and TDD does not - TDD draws no
random numbers, so its answer is identical on every seed by construction.

Run: uv run python scripts/check_tdd_vs_tube.py
"""
from __future__ import annotations

import json

import numpy as np

from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.models import tdd
from rheofp.models.solutions import REP_BNDS

NPZ = "data/katzarova2018.npz"
OUT_JSON = "docs/tdd_vs_tube_2026-09-18.json"

MONO = ["PS392", "PS206", "PS105"]
TRUE_Z = {"PS392": 29.5, "PS206": 15.5, "PS105": 7.9}
# measured 2026-09-17, recorded in CLAUDE.md. Reproduced by this script through
# fit_model to 1e-4 on PS392/PS206, confirming the harness is the shipped one.
TUBE_REF_RMS = {"PS392": 0.0314, "PS206": 0.0300, "PS105": 0.0222}


def _tdd_forward(w, theta):
    """Bank-shaped adapter: (log10 Ge, log10 tau_rep, Z), k=3 - the same
    vector and the same k as `reptation`, so AICc stays comparable."""
    lGe, ltau, Z = theta
    return tdd.Gstar(w, float(np.clip(Z, 2.0, 200.0)), 10.0 ** ltau, 10.0 ** lGe)


def _fit(name, w, Gp, Gpp):
    """Fit through identify()'s OWN fit_model.

    IMPORTANT, and this was a real error on the first run of this script: a
    hand-rolled multi-restart loop is NOT equivalent. Fitting with 10 random
    restarts gave rms 0.0446/0.0422 for `reptation` and 0.0353/0.0369 for
    `branched`, against 0.0315/0.0298 and 0.0250/0.0261 through fit_model -
    i.e. it made EVERY model look worse, and the recorded project numbers
    unreproducible. Always score through the shipped fitter.

    `__tdd__` is registered temporarily so fit_model's name lookup finds it,
    then removed - the bank is never mutated for real.
    """
    tmp = name == "__tdd__"
    if tmp:
        ident.ALL_MODELS[name] = (_tdd_forward, [3.0, 0.0, 20.0], REP_BNDS, 3)
    try:
        return ident.fit_model(name, w, Gp, Gpp)
    finally:
        if tmp:
            ident.ALL_MODELS.pop(name, None)


def main():
    data = load_npz(NPZ)
    rows = []

    print(f"{'sample':>7} {'model':>12} {'rms_dec':>9} {'k':>3} {'AICc':>10} "
          f"{'Z_fit':>7} {'Z_true':>7} {'Zerr%':>7}")
    print("-" * 72)

    for name in MONO:
        d = data[name]
        w, Gp, Gpp = d["omega"], d["Gp"], d["Gpp"]
        row = {"sample": name, "true_Z": TRUE_Z[name]}

        r = _fit("__tdd__", w, Gp, Gpp)
        z_tdd = float(r["params"][2])
        row.update(tdd_rms=float(r["rms_log"]), tdd_aicc=float(r["aicc"]),
                   tdd_Z=z_tdd)
        print(f"{name:>7} {'tdd':>12} {r['rms_log']:9.4f} {3:3d} "
              f"{r['aicc']:10.1f} {z_tdd:7.2f} {TRUE_Z[name]:7.1f} "
              f"{100*(z_tdd-TRUE_Z[name])/TRUE_Z[name]:+7.1f}")

        r = _fit("reptation", w, Gp, Gpp)
        z_tube = float(r["params"][2])
        row.update(tube_rms=float(r["rms_log"]), tube_aicc=float(r["aicc"]),
                   tube_Z=z_tube)
        print(f"{name:>7} {'tube (LM)':>12} {r['rms_log']:9.4f} {3:3d} "
              f"{r['aicc']:10.1f} {z_tube:7.2f} {TRUE_Z[name]:7.1f} "
              f"{100*(z_tube-TRUE_Z[name])/TRUE_Z[name]:+7.1f}")

        r = _fit("branched", w, Gp, Gpp)
        row.update(bsw_rms=float(r["rms_log"]), bsw_aicc=float(r["aicc"]),
                   bsw_k=int(r["k"]))
        print(f"{name:>7} {'branched BSW':>12} {r['rms_log']:9.4f} "
              f"{r['k']:3d} {r['aicc']:10.1f} {'-':>7} {'-':>7} {'-':>7}")
        print()
        rows.append(row)

    # ---------------- P3 ----------------
    print("=== P3: TDD vs tube.py on real monodisperse PS ===")
    print("    (bar: TDD may not be worse than tube by more than 0.005 dec)")
    p3_ok = True
    for r in rows:
        ref = TUBE_REF_RMS[r["sample"]]
        margin = r["tdd_rms"] - r["tube_rms"]
        ok = margin <= 0.005
        p3_ok &= ok
        print(f"  {r['sample']:>7}  tdd {r['tdd_rms']:.4f}  tube {r['tube_rms']:.4f} "
              f"(ref {ref:.4f})  diff {margin:+.4f}  {'OK' if ok else 'FAIL'}")
    print(f"  P3: {'PASS' if p3_ok else 'FAIL'}")

    # ---------------- P4 ----------------
    print("\n=== P4: does TDD close the BSW fault? ===")
    print("    LOWER AICc WINS (identify() sorts ascending). dAICc below is")
    print("    reptation-candidate minus BSW, so POSITIVE = BSW still wins.")
    print("    Incumbent tube margins were 50.7 / 28.9 / 12.1.")
    n_tdd_wins = 0
    for r in rows:
        d_tdd = r["tdd_aicc"] - r["bsw_aicc"]      # >0 => BSW wins
        d_tube = r["tube_aicc"] - r["bsw_aicc"]
        tdd_wins = d_tdd < 0
        n_tdd_wins += tdd_wins
        r["dAICc_tdd_minus_bsw"] = float(d_tdd)
        r["dAICc_tube_minus_bsw"] = float(d_tube)
        verdict = "TDD wins" if tdd_wins else "BSW STILL WINS"
        print(f"  {r['sample']:>7}  TDD-BSW {d_tdd:+8.1f}   "
              f"tube-BSW {d_tube:+8.1f}   -> {verdict}")
    print(f"  TDD beats BSW on {n_tdd_wins}/3 "
          f"(tube beats BSW on 0/3 - the standing fault)")

    # ---------------- determinism ----------------
    print("\n=== determinism: TDD is seed-independent BY CONSTRUCTION ===")
    d = data["PS105"]
    vals = []
    for seed in range(5):
        ident.ALL_MODELS["__tdd__"] = (_tdd_forward, [3.0, 0.0, 20.0],
                                       REP_BNDS, 3)
        try:
            r = ident.fit_model("__tdd__", d["omega"], d["Gp"], d["Gpp"],
                                seed=seed)
        finally:
            ident.ALL_MODELS.pop("__tdd__", None)
        vals.append(r["rms_log"])
    print(f"  PS105 rms over 5 restart seeds: "
          f"{min(vals):.5f} - {max(vals):.5f}  (spread {max(vals)-min(vals):.2e})")
    print("  tube.py's own spread on PS105 was 0.02045-0.02685 (1.3e-2 dec of")
    print("  SAMPLING noise), which is what forced the PS105 withdrawal.")

    with open(OUT_JSON, "w") as fh:
        json.dump(dict(rows=rows, p3_pass=bool(p3_ok),
                       tdd_beats_bsw=int(n_tdd_wins)), fh, indent=2)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
