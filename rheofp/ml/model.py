"""Two-head set model for SAOS stacks.

Shape of the network, following the frozen architecture:

    per-curve encoder      1-D conv over log-frequency -> curve embedding
    masked attention pool  variable-length stack -> one stack embedding
    head 1 (classify)      fine class, with abstention
    head 2 (regress)       always-emitted model parameters

Why a conv encoder rather than an MLP on the raw grid: the discriminating
features here are LOCAL SHAPE in log-frequency - a terminal slope of 2, a
plateau, a power-law wing, a G'' shoulder. Convolutions over the frequency
axis pick those up wherever they sit in the window, which matters because the
generator deliberately crops windows to random positions.

Why masked attention pooling rather than a mean: a stack's information is
often carried by ONE curve - the hottest, where terminal relaxation finally
enters the window. A mean would dilute it; attention can select it. The N=1
case falls out for free (attention over one element is the identity).

Abstention is a learned LOGIT, not a threshold bolted on afterwards. It is
trained by the loss in train.py, so the model can express "this input does not
discriminate" rather than being forced to pick a class it cannot justify.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from rheofp.ml.dataset import N_CHANNELS, N_SUMMARY, N_PARAMS, CLASSES, REGIMES

# ── config ────────────────────────────────────────────────────────────────
CONV_WIDTHS = (64, 96, 128)
KERNEL = 5
EMBED_DIM = 128
ATTN_HEADS = 4
DROPOUT = 0.10
N_PARAMS_OUT = N_PARAMS   # head 2 emits a fixed-width parameter vector
                          # (widest class: branched/BSW, 5 params)


class CurveEncoder(nn.Module):
    """One spectrum -> one embedding, via strided convs over log-frequency."""

    def __init__(self, in_ch=N_CHANNELS, widths=CONV_WIDTHS, embed=EMBED_DIM):
        super().__init__()
        layers = []
        c_prev = in_ch
        for c in widths:
            layers += [nn.Conv1d(c_prev, c, KERNEL, padding=KERNEL // 2),
                       nn.GELU(),
                       nn.BatchNorm1d(c)]
            c_prev = c
        self.conv = nn.Sequential(*layers)
        # mean+max over frequency, concatenated with the per-curve summary
        self.proj = nn.Sequential(
            nn.Linear(2 * c_prev + N_SUMMARY, embed), nn.GELU(),
            nn.Dropout(DROPOUT), nn.Linear(embed, embed))

    def forward(self, x, summary):
        # x: (M, n_points, C) -> conv wants (M, C, n_points)
        h = self.conv(x.transpose(1, 2))
        pooled = torch.cat([h.mean(dim=2), h.amax(dim=2), summary], dim=1)
        return self.proj(pooled)


class MaskedAttentionPool(nn.Module):
    """Pool a variable-length set of curve embeddings into one vector.

    A learned query attends over the stack. Padded slots are masked to -inf
    before the softmax, so they contribute exactly zero - the guarantee the
    collate function's mask exists to provide.
    """

    def __init__(self, embed=EMBED_DIM, heads=ATTN_HEADS):
        super().__init__()
        self.query = nn.Parameter(torch.randn(1, 1, embed) * 0.02)
        self.attn = nn.MultiheadAttention(embed, heads, dropout=DROPOUT,
                                          batch_first=True)
        self.norm = nn.LayerNorm(embed)

    def forward(self, h, mask):
        # h: (B, n_max, E); mask: (B, n_max) True where a real curve sits
        q = self.query.expand(h.shape[0], -1, -1)
        pooled, weights = self.attn(q, h, h, key_padding_mask=~mask,
                                    need_weights=True)
        return self.norm(pooled.squeeze(1)), weights.squeeze(1)


class RheoNet(nn.Module):
    """Encoder + masked pooling + two heads."""

    def __init__(self, n_classes=len(CLASSES), n_regimes=len(REGIMES),
                 embed=EMBED_DIM, n_params=N_PARAMS_OUT):
        super().__init__()
        self.encoder = CurveEncoder(embed=embed)
        self.pool = MaskedAttentionPool(embed=embed)
        self.trunk = nn.Sequential(
            nn.Linear(embed, embed), nn.GELU(), nn.Dropout(DROPOUT))
        # head 1: fine class + one extra abstain logit + a regime view
        self.head_class = nn.Linear(embed, n_classes)
        self.head_abstain = nn.Linear(embed, 1)
        self.head_regime = nn.Linear(embed, n_regimes)
        # head 2: always emits parameters, never abstains
        self.head_params = nn.Sequential(
            nn.Linear(embed, embed), nn.GELU(), nn.Linear(embed, n_params))

    def forward(self, x, summary, mask):
        B, n_max, n_pts, C = x.shape
        flat = x.reshape(B * n_max, n_pts, C)
        flat_s = summary.reshape(B * n_max, -1)
        h = self.encoder(flat, flat_s).reshape(B, n_max, -1)
        # zero the padded embeddings so nothing downstream can read them
        h = h * mask.unsqueeze(-1)
        pooled, attn = self.pool(h, mask)
        z = self.trunk(pooled)
        return {
            "class_logits": self.head_class(z),
            "abstain_logit": self.head_abstain(z).squeeze(-1),
            "regime_logits": self.head_regime(z),
            "params": self.head_params(z),
            "attention": attn,
        }


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
