"""
Evaluate trained GNN on SL(2,F_p) Cayley graphs.

Loads a checkpoint and runs inference on test primes, reporting
spectral gap prediction error, Ramanujan classification accuracy,
and per-prime breakdown.

Usage:
    python evaluate.py --checkpoint data/models/gat_spectral_gap.pt
    python evaluate.py --checkpoint data/models/gat_spectral_gap.pt --target ramanujan_ratio
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from loguru import logger

from train_gnn import SpectralGNN, load_dataset

DATA_DIR = Path(__file__).parent.parent / "data"


def parse_primes(spec: str) -> list[int]:
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return [
            p
            for p in range(int(lo), int(hi) + 1)
            if all(p % d for d in range(2, int(p**0.5) + 1)) and p >= 2
        ]
    return [int(x.strip()) for x in spec.split(",")]


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained GNN")
    parser.add_argument(
        "--checkpoint",
        type=str,
        required=True,
        help="Path to model checkpoint (.pt)",
    )
    parser.add_argument(
        "--target",
        type=str,
        choices=["spectral_gap", "ramanujan_ratio", "is_ramanujan"],
        default="spectral_gap",
    )
    parser.add_argument(
        "--test-primes",
        type=str,
        default="53-101",
        help="Primes for evaluation",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model
    out_channels = 2 if args.target == "is_ramanujan" else 1
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)

    # Handle both state_dict and full model saves
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        state_dict = checkpoint["model_state_dict"]
        model_type = checkpoint.get("model_type", "gat")
        hidden = checkpoint.get("hidden_channels", 64)
    elif isinstance(checkpoint, dict):
        state_dict = checkpoint
        model_type = "gat"
        hidden = 64
    else:
        logger.error("Unsupported checkpoint format")
        return

    model = SpectralGNN(
        hidden_channels=hidden,
        out_channels=out_channels,
        model_type=model_type,
    ).to(device)
    model.load_state_dict(state_dict)
    model.eval()
    logger.info(f"Loaded model from {args.checkpoint} ({model_type})")

    # Load test data
    test_primes = parse_primes(args.test_primes)
    test_data = load_dataset(test_primes, args.target)

    if len(test_data) == 0:
        logger.error("No test data found. Run compute_eigenvalues.py first.")
        return

    logger.info(f"Evaluating on {len(test_data)} primes: {test_primes}")

    # Per-graph evaluation
    results = []
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for data in test_data:
            data = data.to(device)
            batch = torch.zeros(data.num_nodes, dtype=torch.long, device=device)
            out = model(data.x, data.edge_index, batch)

            if args.target == "is_ramanujan":
                pred_label = out.argmax(dim=1).item()
                true_label = data.y.item()
                correct = pred_label == true_label
                results.append(
                    {
                        "prime": data.prime,
                        "pred": pred_label,
                        "true": true_label,
                        "correct": correct,
                    }
                )
                all_preds.append(pred_label)
                all_targets.append(true_label)
            else:
                pred = out.squeeze().item()
                true = data.y.squeeze().item()
                results.append(
                    {
                        "prime": data.prime,
                        "pred": pred,
                        "true": true,
                        "abs_error": abs(pred - true),
                        "rel_error": abs(pred - true) / (abs(true) + 1e-8),
                    }
                )
                all_preds.append(pred)
                all_targets.append(true)

    # Summary statistics
    print("\n" + "=" * 70)
    print(f"EVALUATION RESULTS — target: {args.target}")
    print(f"Model: {args.checkpoint}")
    print("=" * 70)

    if args.target == "is_ramanujan":
        accuracy = sum(r["correct"] for r in results) / len(results)
        print(
            f"\nAccuracy: {accuracy:.1%} ({sum(r['correct'] for r in results)}/{len(results)})"
        )
        print(f"\n{'Prime':>8} {'Pred':>6} {'True':>6} {'OK':>4}")
        print("-" * 30)
        for r in results:
            print(
                f"{r['prime']:>8} {r['pred']:>6} {r['true']:>6} {'✓' if r['correct'] else '✗':>4}"
            )
    else:
        preds = np.array(all_preds)
        targets = np.array(all_targets)
        mae = np.mean(np.abs(preds - targets))
        rmse = np.sqrt(np.mean((preds - targets) ** 2))
        mre = np.mean(np.abs(preds - targets) / (np.abs(targets) + 1e-8))
        r2 = 1 - np.sum((preds - targets) ** 2) / (
            np.sum((targets - targets.mean()) ** 2) + 1e-8
        )

        print(f"\nMAE:  {mae:.6f}")
        print(f"RMSE: {rmse:.6f}")
        print(f"MRE:  {mre:.4%}")
        print(f"R²:   {r2:.4f}")
        print(
            f"\n{'Prime':>8} {'Predicted':>12} {'Actual':>12} {'Abs Err':>10} {'Rel Err':>10}"
        )
        print("-" * 56)
        for r in results:
            print(
                f"{r['prime']:>8} {r['pred']:>12.6f} {r['true']:>12.6f} "
                f"{r['abs_error']:>10.6f} {r['rel_error']:>10.2%}"
            )

    print("=" * 70)


if __name__ == "__main__":
    main()
