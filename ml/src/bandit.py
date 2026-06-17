"""Channel orchestration — a contextual Thompson-sampling bandit.

Once we know a customer is Persuadable, the next question is *how* to reach them.
Different customers respond to different channels. A static rule can't adapt; a
bandit learns online which channel actually moves each segment, balancing
exploration (try channels we're unsure about) against exploitation (use what works).

This is the "self-optimizing" layer — and unlike a fixed model, you can watch it
converge live in the demo. We use a Beta-Bernoulli Thompson sampler per
(segment, channel): sample a success rate from each channel's posterior, play the
argmax, observe the reward, update. Over rounds it locks onto the best channel per
segment and its cumulative reward pulls away from random targeting.

Run:  python -m src.bandit
Emits: ml/artifacts/bandit.json
"""
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
    """Ground-truth (hidden from the bandit) channel response rate per segment.

    Synthesized so each segment has a genuinely different best channel — that's the
    structure the bandit must discover. In production this is the real world; here it
    lets us prove the bandit finds the right answer.
    """
    truth = {}
    for i, seg in enumerate(segments):
        base = 0.08 + 0.02 * (i % 3)
        rates = np.array([base, base, base, base])
        rates[i % len(CHANNELS)] += 0.10          # one channel clearly wins
        rates[(i + 2) % len(CHANNELS)] += 0.04     # one is a runner-up
        truth[seg] = np.clip(rates, 0.01, 0.95)
    return truth


def run(segments_per_round: np.ndarray, seg_list: list[str], truth, n_rounds: int):
    """Play the bandit and a random baseline on the same stream; track cumulative
    reward (conversions) for both so we can show the gap widening."""
    n_seg, n_ch = len(seg_list), len(CHANNELS)
    seg_idx = {s: i for i, s in enumerate(seg_list)}
    alpha = np.ones((n_seg, n_ch))   # Beta successes + 1
    beta = np.ones((n_seg, n_ch))    # Beta failures + 1

    ts_cum, rand_cum, oracle_cum = 0, 0, 0
    curve = []
    for t in range(n_rounds):
        s = seg_idx[segments_per_round[t]]
        rates = truth[seg_list[s]]

        # Thompson: sample a plausible rate per channel, exploit the best draw.
        sample = RNG.beta(alpha[s], beta[s])
        ch = int(np.argmax(sample))
        reward = int(RNG.random() < rates[ch])
        alpha[s, ch] += reward
        beta[s, ch] += 1 - reward
        ts_cum += reward

        # Baselines on the same context: random channel, and an oracle upper bound.
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
    # Context = (bucket × history_segment) keeps it rich but small.
    df["seg"] = df["bucket"].astype(str) + " · " + df["history_segment"].astype(str)
    seg_list = sorted(df["seg"].unique())
    truth = latent_response(seg_list)

    # Simulate a stream of customers proportional to the real population mix.
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
