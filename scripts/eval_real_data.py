"""Run the trained RheoNet checkpoint against the real literature datasets.

These npz files (data/darby2022.npz, tixier2004.npz, pivo2006.npz) were built
for the FORWARD-PHYSICS validation in next-actions.md / CLAUDE.md, not for the
ML pipeline: they carry raw omega/Gp/Gpp per sample but no label/regime/
stack_id/params, so rheofp.ml.dataset.npz_to_records cannot read them. This
script builds model input tensors directly from the raw curves (each sample
treated as its own N=1 stack, since none of them carry a temperature series)
using the checkpoint's stored normalisation, and reports what the classifier
says next to the ground truth established by the physics validation.

    python scripts/eval_real_data.py
"""
import numpy as np
import torch

from rheofp.io.data import load_npz
from rheofp.ml.dataset import curve_tensor, _summary, CLASSES
from rheofp.ml.model import RheoNet

CHECKPOINT = "checkpoints/rheonet.pt"

# The synthetic generator emits EVERY curve at exactly 60 points
# (rheofp.data.synth), so the model has never seen another sampling density.
# The literature curves are digitized at whatever density the source figure
# had (11-90 points) - resampling to a 60-point log-omega grid isolates
# whether a mismatch is about point density/OOD sampling vs the underlying
# spectrum shape.
RESAMPLE_N = 60


def resample(w, gp, gpp, n=RESAMPLE_N):
    lw = np.log10(w)
    grid = np.linspace(lw.min(), lw.max(), n)
    gp_i = 10 ** np.interp(grid, lw, np.log10(gp))
    gpp_i = 10 ** np.interp(grid, lw, np.log10(gpp))
    return 10 ** grid, gp_i, gpp_i

# Ground truth from the physics validation (next-actions.md 1b, CLAUDE.md
# pom-pom section) - these are NOT ML labels, they are what fitting +
# AICc + literature Table values already established.
GROUND_TRUTH = {
    "data/darby2022.npz": {
        "SY184_10-1": "cured_elastomer",
        "Solaris_1-1": "cured_elastomer",
        "EF0030_1-1": "cured_elastomer",
    },
    "data/tixier2004.npz": {
        "Tixier2004_gel": "critical_gel",
    },
    "data/pivo2006.npz": {
        # Pivokonsky LDPE melts - branched (pom-pom/XPP validated in
        # pompom.py per CLAUDE.md); classifier's branched class is the
        # taxonomy match, not reptation (that's linear melts).
        "E": "branched",
        "B": "branched",
    },
}


def load_checkpoint(path=CHECKPOINT, device="cpu"):
    ckpt = torch.load(path, map_location=device, weights_only=False)
    model = RheoNet()
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt["norm"], ckpt["classes"]


def predict_one(model, norm, classes, w, gp, gpp, T_K=float("nan")):
    """Single curve as an N=1 stack -> (pred_class, class_probs, abstain_p)."""
    x = curve_tensor(w, gp, gpp)
    s = _summary(w, gp, gpp, T_K)
    x = (x - norm["x_mean"]) / norm["x_std"]
    s = (s - norm["s_mean"]) / norm["s_std"]
    xt = torch.from_numpy(x.astype(np.float32))[None, None]     # (1,1,pts,C)
    st = torch.from_numpy(s.astype(np.float32))[None, None]     # (1,1,S)
    mask = torch.ones(1, 1, dtype=torch.bool)
    with torch.no_grad():
        out = model(xt, st, mask)
    probs = torch.softmax(out["class_logits"], dim=-1)[0].numpy()
    abstain_p = torch.sigmoid(out["abstain_logit"])[0].item()
    pred = classes[int(probs.argmax())]
    return pred, probs, abstain_p


def main():
    model, norm, classes = load_checkpoint()
    print(f"loaded {CHECKPOINT}  classes={len(classes)}\n")

    for label, use_resample in (("raw digitized points", False),
                                 (f"resampled to {RESAMPLE_N} pts (training density)", True)):
        print(f"\n#### {label} ####\n")
        n_total = n_correct = 0
        for path, truth in GROUND_TRUTH.items():
            data = load_npz(path)
            print(f"=== {path} ===")
            for sample, fields in data.items():
                w, gp, gpp = fields["omega"], fields["Gp"], fields["Gpp"]
                if use_resample:
                    w, gp, gpp = resample(w, gp, gpp)
                expected = truth.get(sample)
                pred, probs, abstain_p = predict_one(
                    model, norm, classes, w, gp, gpp,
                    fields.get("T_K", float("nan")))
                top3_idx = np.argsort(probs)[::-1][:3]
                top3 = ", ".join(f"{classes[i]}={probs[i]:.2f}" for i in top3_idx)
                mark = ""
                if expected is not None:
                    n_total += 1
                    ok = pred == expected
                    n_correct += ok
                    mark = "  OK" if ok else f"  MISMATCH (expected {expected})"
                print(f"  {sample:15s} pred={pred:20s} abstain_p={abstain_p:.2f}"
                      f"  top3=[{top3}]{mark}")
            print()

        if n_total:
            print(f"accuracy ({label}): {n_correct}/{n_total} "
                  f"({n_correct/n_total:.1%})")


if __name__ == "__main__":
    main()
