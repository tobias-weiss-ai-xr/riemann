"""
Load trained GNN checkpoint and export test-set embeddings.

Usage:
    python scripts/extract_gnn_embeddings.py --target z1
    python scripts/extract_gnn_embeddings.py --target rank
    python scripts/extract_gnn_embeddings.py --target cm
    python scripts/extract_gnn_embeddings.py --all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch_geometric.loader import DataLoader as PyGDataLoader
from loguru import logger

# Add scripts to PythonPATH
sys.path.insert(0, str(Path(__file__).parent))

from train_lmfdb_gnn import (
    TraceIndexChebConv,
    TraceIndexGCN,
    load_dataset,
)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = DATA_DIR / "models"


def load_checkpoint(ckpt_path: Path):
    """Load checkpoint and return model + config metadata."""
    # Set weights_only=False for backward compatibility with old checkpoints
    checkpoint = torch.load(
        ckpt_path,
        map_location="cuda" if torch.cuda.is_available() else "cpu",
        weights_only=False
    )
    config = checkpoint["config"]
    print(f"Loaded checkpoint: {ckpt_path}")
    print(f"  Model type: {config['model_type']}")
    print(f"  K: {config['K']}")
    print(f"  Hidden dim: {config['hidden_dim']}")
    print(f"  Layers: {config['num_layers']}")
    print(f"  Target: {checkpoint['target']}")
    print(f"  Best epoch: {checkpoint['best_epoch']}")
    print(f"  Val loss: {checkpoint['val_loss']:.4f}")
    return checkpoint, config


def build_model_from_config(config):
    """Rebuild model from checkpoint config."""
    if config["model_type"] == "gcn":
        return TraceIndexGCN(
            node_feat_dim=config["node_feat_dim"],
            hidden_dim=config["hidden_dim"],
            num_layers=config["num_layers"],
            num_targets=config["num_targets"],
        )
    elif config["model_type"] == "chebconv":
        return TraceIndexChebConv(
            node_feat_dim=config["node_feat_dim"],
            hidden_dim=config["hidden_dim"],
            K=config["K"],
            num_layers=config["num_layers"],
            num_targets=config["num_targets"],
        )
    else:
        raise ValueError(f"Unknown model type: {config['model_type']}")


def extract_embeddings(
    target: str,
    checkpoint_dir: Path = None,
    model_type: str = "chebconv",
    data_dir: Path = None,
    output_dir: Path = None,
):
    """Load checkpoint and export test-set embeddings."""
    from loguru import logger
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    )

    checkpoint_dir = checkpoint_dir or MODEL_DIR
    data_dir = data_dir or DATA_DIR / "lmfdb" / "gnn_trace_index"
    output_dir = output_dir or MODEL_DIR

    # Load checkpoint
    ckpt_path = checkpoint_dir / f"lmfdb_gnn_{model_type}_{target}.pt"
    if not ckpt_path.exists():
        logger.error(f"Checkpoint not found: {ckpt_path}")
        return

    checkpoint, config = load_checkpoint(ckpt_path)

    # Rebuild model and load state
    model = build_model_from_config(config)
    model.load_state_dict(checkpoint["model_state_dict"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    logger.info(f"Model loaded on device: {device}")

    # Load data
    train_graphs, val_graphs, test_graphs = load_dataset(data_dir, target)
    logger.info(f"Test set size: {len(test_graphs)}")

    # Create test loader
    test_loader = PyGDataLoader(test_graphs, batch_size=64, shuffle=False, num_workers=0)

    # Export embeddings
    logger.info("Extracting test-set embeddings...")
    all_embeddings, all_raw_preds, all_targets = [], [], []

    with torch.no_grad():
        for batch in test_loader:
            batch = batch.to(device)
            out, embeddings = model(batch, return_embeddings=True)
            all_embeddings.append(embeddings.cpu())
            all_raw_preds.append(out.cpu())
            all_targets.append(batch.y)

    # Concatenate and save
    all_embeddings = torch.cat(all_embeddings, dim=0).numpy()
    all_raw_preds = torch.cat(all_raw_preds, dim=0).numpy()
    all_targets = torch.cat(all_targets, dim=0).cpu().numpy()

    output_dir.mkdir(parents=True, exist_ok=True)
    emb_path = output_dir / f"gnn_embeddings_{target}.npy"
    pred_path = output_dir / f"gnn_raw_preds_{target}.npy"
    target_path = output_dir / f"gnn_test_targets_{target}.npy"

    np.save(emb_path, all_embeddings)
    np.save(pred_path, all_raw_preds)
    np.save(target_path, all_targets)

    logger.info(f"✓ Saved embeddings: {emb_path} (shape: {all_embeddings.shape})")
    logger.info(f"✓ Saved predictions: {pred_path} (shape: {all_raw_preds.shape})")
    logger.info(f"✓ Saved targets: {target_path} (shape: {all_targets.shape})")

    return {
        "embeddings_path": str(emb_path),
        "predictions_path": str(pred_path),
        "targets_path": str(target_path),
        "num_samples": all_embeddings.shape[0],
        "embedding_dim": all_embeddings.shape[1],
    }


def main():
    parser = argparse.ArgumentParser(description="Extract GNN embeddings from checkpoint")
    parser.add_argument(
        "--target",
        choices=["z1", "rank", "cm"],
        help="Target variable (z1, rank, or cm)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Extract embeddings for all three targets (z1, rank, cm)",
    )
    parser.add_argument(
        "--model",
        choices=["gcn", "chebconv"],
        default="chebconv",
        help="Model type to load checkpoint from",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=None,
        help="Directory containing checkpoint files",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Directory containing train/val/test split data",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save extracted embeddings/predictions",
    )
    args = parser.parse_args()

    if not args.all and not args.target:
        parser.error("Either --target or --all must be specified")

    targets = ["z1", "rank", "cm"] if args.all else [args.target]

    from loguru import logger
    logger.info(f"Extracting embeddings for targets: {targets}")

    results = {}
    for target in targets:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing target: {target}")
        logger.info(f"{'='*60}")
        result = extract_embeddings(
            target=target,
            checkpoint_dir=Path(args.checkpoint_dir) if args.checkpoint_dir else None,
            model_type=args.model,
            data_dir=Path(args.data_dir) if args.data_dir else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
        results[target] = result

    # Save summary
    summary_path = MODEL_DIR / "embedding_extraction_summary.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"\n✓ Summary saved: {summary_path}")


if __name__ == "__main__":
    main()