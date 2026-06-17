from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ART = Path(__file__).resolve().parents[1] / "artifacts"
SCORES = ART / "scores.parquet"

CHANNELS = ["Email", "Push", "SMS", "WhatsApp"]
RNG = np.random.default_rng(7)

def latent_response(segments: list[str]) -> dict[str, np.ndarray]:
    truth = {}
    for i, seg in enumerate(segments):
        base = 0.08 + 0.02 * (i % 3)
        rates = np.array([base, base, base, base])
        rates[i % len(CHANNELS)] += 0.10
        rates[(i + 2) % len(CHANNELS)] += 0.04
        truth[seg] = np.clip(rates, 0.01, 0.95)
    return truth

def run(segments_per_round: np.ndarray, seg_list: list[str], truth, n_rounds: int):
    n_seg, n_ch = len(seg_list), len(CHANNELS)
    seg_idx = {s: i for i, s in enumerate(seg_list)}
    alpha = np.ones((n_seg, n_ch))
    beta = np.ones((n_seg, n_ch))

    ts_cum, rand_cum, oracle_cum = 0, 0, 0
    curve = []
    for t in range(n_rounds):
        s = seg_idx[segments_per_round[t]]
        rates = truth[seg_list[s]]

        sample = RNG.beta(alpha[s], beta[s])
        ch = int(np.argmax(sample))
        reward = int(RNG.random() < rates[ch])
        alpha[s, ch] += reward
        beta[s, ch] += 1 - reward
        ts_cum += reward

        rand_cum += int(RNG.random() < rates[RNG.integers(n_ch)])
        oracle_cum += int(RNG.random() < rates.max())

        if t % max(1, n_rounds // 80) == 0 or t == n_rounds - 1:
            curve.append({"round": t + 1, "thompson": ts_cum,
                          "random": rand_cum, "oracle": oracle_cum})

    learned = {seg_list[s]: CHANNELS[int(np.argmax(alpha[s] / (alpha[s] + beta[s])))]
               for s in range(n_seg)}
    return curve, learned, alpha, beta

def main() -> None:
    df = pd.read_parquet(SCORES)
    df["seg"] = df["bucket"].astype(str) + " · " + df["history_segment"].astype(str)
    seg_list = sorted(df["seg"].unique())
    truth = latent_response(seg_list)

    n_rounds = 6000
    stream = df["seg"].sample(n_rounds, replace=True, random_state=1).values
    curve, learned, alpha, beta = run(stream, seg_list, truth, n_rounds)

    final = curve[-1]
    lift = 100 * (final["thompson"] - final["random"]) / max(final["random"], 1)
    pct_of_oracle = 100 * final["thompson"] / max(final["oracle"], 1)
    print(f"[bandit] {n_rounds} rounds, {len(seg_list)} segments x {len(CHANNELS)} channels")
    print(f"[bandit] final conversions  thompson={final['thompson']} "
          f"random={final['random']} oracle={final['oracle']}")
    print(f"[bandit] +{lift:.1f}% vs random, {pct_of_oracle:.1f}% of oracle ceiling")

    out = {
        "channels": CHANNELS,
        "curve": curve,
        "learned_best_channel": learned,
        "summary": {
            "rounds": n_rounds,
            "lift_vs_random_pct": round(lift, 1),
            "pct_of_oracle": round(pct_of_oracle, 1),
            "final": final,
        },
    }
    (ART / "bandit.json").write_text(json.dumps(out, indent=2))
    print(f"[bandit] wrote {ART / 'bandit.json'}")

if __name__ == "__main__":
    main()
