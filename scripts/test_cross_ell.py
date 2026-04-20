"""Quick test: Can T_2 eigenvalue statistics predict T_3 eigenvalue statistics?
This validates the cross-ℓ prediction task before building the full GNN pipeline."""

from cypari2 import Pari
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut
import json

pari = Pari()


def compute_hecke_eigenvalues(p, ell):
    """Compute eigenvalues of T_ell on S_2(Gamma_0(p))."""
    code = (
        f"my(mf=mfinit([{p},2],1));"
        f"my(B=mfbasis(mf));"
        f"my(M=matrix(#B,#B));"
        f"for(k=1,#B,"
        f"  my(TBk=mfhecke(mf,B[k],{ell}));"
        f"  my(coords=mftobasis(mf,TBk));"
        f"  for(j=1,#B,M[j,k]=coords[j])"
        f");"
        f"M"
    )
    M = np.array(pari(code).python(), dtype=float)
    return np.linalg.eigvalsh(M)


def is_prime(n):
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


def eigenvalue_stats(eigs):
    """Compute summary statistics of eigenvalues."""
    return np.array(
        [
            np.mean(eigs),
            np.std(eigs),
            np.min(eigs),
            np.max(eigs),
            np.median(eigs),
            np.percentile(eigs, 25),
            np.percentile(eigs, 75),
            np.max(np.abs(eigs)),  # spectral radius
            eigs[-1] if len(eigs) > 0 else 0,  # largest
            eigs[0] if len(eigs) > 0 else 0,  # smallest
            len(eigs),  # dimension
            np.sum(eigs > 0) / len(eigs),  # fraction positive
        ]
    )


# Collect data for primes with dim >= 4
primes = [p for p in range(47, 1000) if is_prime(p)]
data = []

print("Computing Hecke eigenvalues for primes with dim >= 4...")
for p in primes:
    dim = int(pari(f"mfdim([{p},2], 1)"))
    if dim < 4:
        continue

    eigs_2 = compute_hecke_eigenvalues(p, 2)
    eigs_3 = compute_hecke_eigenvalues(p, 3)
    eigs_5 = compute_hecke_eigenvalues(p, 5)

    stats_2 = eigenvalue_stats(eigs_2)
    stats_3 = eigenvalue_stats(eigs_3)
    stats_5 = eigenvalue_stats(eigs_5)

    data.append(
        {
            "p": p,
            "dim": dim,
            "stats_2": stats_2,
            "stats_3": stats_3,
            "stats_5": stats_5,
            "eigs_2": eigs_2,
            "eigs_3": eigs_3,
            "eigs_5": eigs_5,
        }
    )

print(f"Collected {len(data)} primes")

# ============= EXPERIMENT 1: T_2 stats → T_3 stats =============
print("\n=== Experiment 1: T_2 stats → T_3 stats (Linear Regression) ===")

X = np.array([d["stats_2"] for d in data])
y_mean = np.array([d["stats_3"][0] for d in data])  # mean eigenvalue of T_3
y_std = np.array([d["stats_3"][1] for d in data])  # std
y_radius = np.array([d["stats_3"][7] for d in data])  # spectral radius

loo = LeaveOneOut()
results = {}
for name, y_target in [("mean", y_mean), ("std", y_std), ("radius", y_radius)]:
    preds = np.zeros(len(data))
    for train_idx, test_idx in loo.split(X):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X[train_idx])
        X_test = scaler.transform(X[test_idx])
        model = Ridge(alpha=1.0)
        model.fit(X_train, y_target[train_idx])
        preds[test_idx] = model.predict(X_test)

    ss_res = np.sum((y_target - preds) ** 2)
    ss_tot = np.sum((y_target - np.mean(y_target)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    mae = np.mean(np.abs(y_target - preds))

    results[name] = {"r2": r2, "mae": mae}
    print(f"  {name}: R²={r2:.4f}, MAE={mae:.4f}")

# ============= EXPERIMENT 2: T_2 + dim → T_3 stats (with graph size) =============
print("\n=== Experiment 2: T_2 stats + dim → T_3 stats ===")

X2 = np.column_stack([X, np.array([d["dim"] for d in data])])

for name, y_target in [("mean", y_mean), ("std", y_std), ("radius", y_radius)]:
    preds = np.zeros(len(data))
    for train_idx, test_idx in loo.split(X2):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X2[train_idx])
        X_test = scaler.transform(X2[test_idx])
        model = Ridge(alpha=1.0)
        model.fit(X_train, y_target[train_idx])
        preds[test_idx] = model.predict(X_test)

    ss_res = np.sum((y_target - preds) ** 2)
    ss_tot = np.sum((y_target - np.mean(y_target)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    mae = np.mean(np.abs(y_target - preds))
    print(f"  {name}: R²={r2:.4f}, MAE={mae:.4f}")

# ============= EXPERIMENT 3: T_2 → T_3 eigenvalue prediction (full vector) =============
print(
    "\n=== Experiment 3: T_2 eigenvalues → T_3 eigenvalues (padded to fixed length) ==="
)

# Use primes with dim in a reasonable range
subset = [d for d in data if 10 <= d["dim"] <= 50]
print(f"  Subset: {len(subset)} primes with 10 <= dim <= 50")
if len(subset) >= 5:
    max_dim = max(d["dim"] for d in subset)

    X_full = np.zeros((len(subset), max_dim))
    y_full = np.zeros((len(subset), max_dim))
    masks = np.zeros((len(subset), max_dim))

    for i, d in enumerate(subset):
        eigs2_sorted = np.sort(d["eigs_2"])[::-1]
        eigs3_sorted = np.sort(d["eigs_3"])[::-1]
        X_full[i, : len(eigs2_sorted)] = eigs2_sorted
        y_full[i, : len(eigs3_sorted)] = eigs3_sorted
        masks[i, : len(eigs3_sorted)] = 1.0

    # LOO-CV on masked MSE
    total_mse = 0
    total_count = 0
    for train_idx, test_idx in loo.split(X_full):
        model = Ridge(alpha=1.0)
        model.fit(X_full[train_idx], y_full[train_idx])
        pred = model.predict(X_full[test_idx])
        mask = masks[test_idx]
        mse = np.sum(mask * (pred - y_full[test_idx]) ** 2) / np.sum(mask)
        total_mse += mse
        total_count += 1

    avg_mse = total_mse / total_count
    avg_var = np.mean([np.var(d["eigs_3"]) for d in subset])
    r2_approx = 1 - avg_mse / avg_var if avg_var > 0 else 0
    print(
        f"  Masked MSE: {avg_mse:.4f}, Avg variance: {avg_var:.4f}, Approx R²: {r2_approx:.4f}"
    )

# ============= EXPERIMENT 4: Deligne bound compliance =============
print("\n=== Experiment 4: Deligne bound compliance ===")
violations = 0
total = 0
for d in data:
    for ell, key in [(2, "eigs_2"), (3, "eigs_3"), (5, "eigs_5")]:
        bound = 2 * np.sqrt(ell)
        if np.any(np.abs(d[key]) > bound + 1e-6):
            violations += 1
        total += 1
print(f"  Violations: {violations}/{total} ({100 * violations / total:.1f}%)")

# ============= EXPERIMENT 5: Cross-ℓ correlation analysis =============
print("\n=== Experiment 5: Cross-ℓ eigenvalue correlation ===")
corrs_23 = []
corrs_25 = []
for d in data:
    if d["dim"] >= 2:
        c23 = np.corrcoef(d["eigs_2"], d["eigs_3"])[0, 1]
        c25 = np.corrcoef(d["eigs_2"], d["eigs_5"])[0, 1]
        corrs_23.append(c23)
        corrs_25.append(c25)
print(f"  corr(T2,T3): mean={np.mean(corrs_23):.4f}, std={np.std(corrs_23):.4f}")
print(f"  corr(T2,T5): mean={np.mean(corrs_25):.4f}, std={np.std(corrs_25):.4f}")

# Save results
summary = {
    "n_primes": len(data),
    "dim_range": [min(d["dim"] for d in data), max(d["dim"] for d in data)],
    "exp1_r2": {k: v["r2"] for k, v in results.items()},
    "deligne_violations": violations,
    "cross_l_corr": {
        "T2_T3": float(np.mean(corrs_23)),
        "T2_T5": float(np.mean(corrs_25)),
    },
}
print(f"\nSummary: {json.dumps(summary, indent=2)}")
