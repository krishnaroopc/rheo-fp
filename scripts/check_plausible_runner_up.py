"""Would eliminating implausible classes and re-ranking give the RIGHT answer?

READ-ONLY. Changes nothing, decides whether the user's iterative-elimination
loop is worth building (2026-09-21).

The loop idea: fit all 10, check the winner's numbers, eliminate the class if
they are impossible, re-rank the survivors, repeat until everything is green.

The question this answers, and the ONLY thing that makes the loop worth
building: on the calls identify() currently gets WRONG, is the next candidate
with plausible numbers actually the TRUE class? If it is, the loop converts
wrong answers into right ones. If the plausible runner-up is ALSO wrong, the
loop just trades one wrong answer for another.

It also measures the risk the loop carries: on calls identify() gets RIGHT,
would elimination throw the right answer away? Pivokonsky's LDPE melts are
the known case - `branched` is correct there AND its n_e is out of range.
"""
import numpy as np

from rheofp.fitting.identify import identify
from rheofp.plausibility import at_bound_warning
from rheofp.ranges import out_of_range_parameters
from rheofp.fitting.identify import ALL_MODELS

# Ground truth from the source papers, as recorded in CLAUDE.md / the prep
# scripts. "None" means the paper's material is not in the taxonomy at all.
TRUTH = {
    "data/darby2022.npz":      {"SY184_10-1": "cured_elastomer",
                                "Solaris_1-1": "cured_elastomer",
                                "EF0030_1-1": "cured_elastomer"},
    "data/tixier2004.npz":     {"Tixier2004_gel": "critical_gel"},
    "data/pivo2006.npz":       {"E": "branched", "B": "branched"},
    "data/katzarova2018.npz":  {"PS105": "reptation", "PS206": "reptation",
                                "PS392": "reptation"},
    "data/mm1998.npz":         {"PI4_Ma11k": "star", "PI4_Ma17k": "star",
                                "PI4_Ma36k": "star", "PI4_Ma44k": "star",
                                "PI4_Ma47k": "star", "PI4_Ma95k": "star",
                                "PI4_Ma105k": "star"},
    "data/pryke2002.npz":      {"PBD3_Ma38k": "star", "PBD3_Ma78k": "star"},
    "data/santangelo1999.npz": {"S217": "star", "S490": "star",
                                # L176/HM/HL/ML are the LINEAR controls
                                "L176": "reptation", "HM": "reptation",
                                "HL": "reptation", "ML": "reptation"},
}


def implausible(name, params):
    """Does this candidate fail either safety check? Returns a reason or None."""
    reasons = []
    entry = ALL_MODELS.get(name)
    if entry is not None:
        w = at_bound_warning(name, params, entry[2])
        if w and w["n_hard"]:
            reasons.append("at-bound:" + ",".join(
                p["param"] for p in w["pinned"] if p["note"] is None))
    bad = out_of_range_parameters(name, params)
    if bad:
        reasons.append("out-of-range:" + ",".join(
            f"{b['param']}={b['value']:.3g}" for b in bad))
    return "; ".join(reasons) or None


def main():
    n_wrong = n_wrong_fixed = n_wrong_unchanged = 0
    n_right = n_right_broken = 0
    rows = []

    for path, truth in TRUTH.items():
        d = np.load(path, allow_pickle=True)
        for nm, true_cls in truth.items():
            key = f"{nm}__omega"
            if key not in d:
                continue
            w = d[key]; gp = d[f"{nm}__Gp"]; gpp = d[f"{nm}__Gpp"]
            res = identify(w, gp, gpp)
            ranked = res["ranking"]
            winner = ranked[0]

            # Walk the ranking, skipping candidates that fail a check. This is
            # exactly the user's loop, done in one pass (elimination cannot
            # change the RELATIVE order of the survivors, since AICc per
            # candidate does not depend on which others are present).
            survivor = None
            for r in ranked:
                if implausible(r["name"], r["params"]) is None:
                    survivor = r
                    break

            correct_now = winner["name"] == true_cls
            correct_after = survivor is not None and survivor["name"] == true_cls
            wreason = implausible(winner["name"], winner["params"])

            if correct_now:
                n_right += 1
                broke = wreason is not None and not correct_after
                n_right_broken += broke
                verdict = "BREAKS" if broke else "keeps"
            else:
                n_wrong += 1
                if correct_after:
                    n_wrong_fixed += 1
                    verdict = "FIXES"
                else:
                    n_wrong_unchanged += 1
                    verdict = "still wrong"

            rows.append((nm, true_cls, winner["name"],
                         "flagged" if wreason else "clean",
                         survivor["name"] if survivor else "(none pass)",
                         verdict))
            print(f"{nm:14s} true={true_cls:16s} winner={winner['name']:16s} "
                  f"{'FLAGGED' if wreason else 'clean  '} -> "
                  f"first-plausible={survivor['name'] if survivor else '(none)':16s} "
                  f"{verdict}")

    print()
    print("=" * 78)
    print(f"currently WRONG : {n_wrong:2d}   of which elimination FIXES: {n_wrong_fixed}"
          f"   still wrong: {n_wrong_unchanged}")
    print(f"currently RIGHT : {n_right:2d}   of which elimination BREAKS: {n_right_broken}")
    print("=" * 78)
    net = n_wrong_fixed - n_right_broken
    print(f"NET change if the eliminating loop shipped: {net:+d} curves")


if __name__ == "__main__":
    main()
