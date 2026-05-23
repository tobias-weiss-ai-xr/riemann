## Experiment 13: GNN + Sklearn Ensemble (In Progress)

### Motivation

Combine GNN graph representations with sklearn ML predictions via stacking ensemble to:
1. Leverage complementary insights (GNN: structural patterns, sklearn: trace statistics)
2. Benchmark if fusion improves over standalone GNN or sklearn
3. Test if focal loss improves rare-class (rank-2) detection

### Implementation

#### Files Created
- `scripts/extract_gnn_embeddings.py` - Loads GNN ChebConv K=5 checkpoints, extracts 256-dim embeddings from test set
- `scripts/train_ensemble_sklearn.py` - Trains RandomForest on Hecke traces (rank: 96% acc, cm: 100% acc)
- `scripts/train_ensemble.py` - Stacking ensemble meta-learner (PyTorch MLP on concatenated features)
- `scripts/evaluate_ensemble.py` - Eval framework comparing GNN, sklearn, ensemble side-by-side
- `scripts/extract_sklearn_predictions.py` - Reproduces stratified 80/10/10 split, exports predictions

#### Architecture
- **z1**: GNN-only ensemble (no sklearn baseline in LMFDB ML CSV)
- **rank**: GNN (256-dim) + sklearn (RFR 3-class probs) > MLP classifier (64 > 3)
- **cm**: GNN (256-dim) + sklearn (RFR binary probs) > MLP classifier (64 > 2)
- **Focal loss**: For rank classification, emphasize rank-2 (rare: 1.5% in dataset, weight=8.0)

### Results

#### Test Set Size
- GNN test set: 4637 samples (80/10/10 split on 46347-filtered LMFDB subset)
- Sklearn test set: 5381 samples (80/10/10 split on full 53779 LMFDB records)
- **BLOCKER**: Sample alignment issue - GNN uses filtered subset (46347 vs 53779). Need LMFDB IDs in GNN dataset to filter sklearn predictions.

#### GNN Baseline (ChebConv K=5)
Extracted from trained checkpoints at `data/models/chebconv_K5/`:
- **z1**: 4637 tests > 256-dim embeddings, R2 ~ -0.2 (fails)
- **rank**: 4637 tests > 3-class logits, accuracy ~ 0.33 (random)
- **cm**: 4637 tests > 2-class logits, accuracy ~ 0.97

#### Sklearn Baseline
Trained RandomForest on Hecke traces:
- **rank**: 5381 tests > 96% accuracy (missing rank-2 alignment)
- **cm**: 5381 tests > 100% accuracy

#### Ensemble
- **z1**: GNN-256 > MLP (256 > 1) — Ready to test once data aligned
- **rank**: GNN-256 + RFR-3 > MLP (259 > 64 > 3) — Feature size mismatch due to test set misalignment
- **cm**: GNN-256 + RFR-2 > MLP (258 > 64 > 2) — Ready to test once data aligned

### Findings

1. **GNN performance on graph-structured traces fails** (consistent with Exp 12): Local subgraph features carry zero information about global spectral/trace properties (vertex-transitive property). GNN R2 < 0, accuracy near random.

2. **Sklearn dominates for LMFDB traces**: RandomForest achieves 96-100% accuracy from raw Hecke traces, consistent with Exp 10. The ML baseline wins decisively.

3. **Ensemble potential unclear**: With-sklearn fusion may boost GNN from random to competitive, but standalone sklearn already near-ceiling. Benefit depends on whether GNN embeddings capture orthogonal signal.

4. **Data alignment blocker**: GNN dataset built on filtered LMFDB subset (likely by level or conductor). Without LMFDB IDs stored in GNN dataset metadata, cannot align test indices. Need to modify `build_lmfdb_gnn_dataset.py` to save IDs.

5. **Focal loss ready but untested**: Weighted cross-entropy (rank-2 weight=8.0) implemented. Will measure impact once ensemble trains with aligned data.

### Next Steps

1. **Fix data alignment**:
   - Modify `build_lmfdb_gnn_dataset.py` to save LMFDB IDs in metadata.json
   - Re-build GNN dataset with IDs preserved
   - Re-run `extract_sklearn_predictions.py` with GNN subset filtering

2. **Run ensemble training**:
   - `python scripts/train_ensemble.py --target all --use-focal-loss`
   - Compare metrics: GNN vs sklearn vs ensemble

3. **Evaluate rare-class detection**:
   - Benchmark focal loss vs standard cross-entropy
   - Report per-class F1 for rank-2

### Status

**Phase 1 (infrastructure)**: Complete
- Embeddings, sklearn training, ensemble code, framework.

**Phase 2 (data alignment)**: Blocked
- Need LMFDB IDs stored during GNN dataset build.

**Phase 3 (training + evaluation)**: Pending
- Ensemble training pending alignment fix.