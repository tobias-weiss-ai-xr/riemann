"""
Validates CM classification dataset integrity and extracts CM-specific statistics.
Returns dataset summary for paper methodology section.
"""
import pandas as pd
import numpy as np
from scipy import stats

def load_dataset(path="data/lmfdb/lmfdb_sql_weight2_ml.csv"):
    """Load LMFDB 53K dataset"""
    df = pd.read_csv(path)
    return df

def validate_cm_stats(df):
    """Compute CM form statistics by dimension"""
    cm_by_dim = df[df["is_cm"] == True].groupby("dim").size()
    non_cm_by_dim = df[~df["is_cm"]].groupby("dim").size()

    stats = {
        "total_forms": len(df),
        "total_cm": int((df["is_cm"] == True).sum()),
        "total_non_cm": int((df["is_cm"] == False).sum()),
        "cm_by_dim": cm_by_dim.to_dict(),
        "non_cm_by_dim": non_cm_by_dim.to_dict(),
        "cm_percentage": (df["is_cm"] == True).sum() / len(df) * 100
    }
    return stats

def extract_prime_traces(df, n_primes=25):
    """
    Extract first n_primes from trace columns.
    Prime indices: 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97
    """
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97][:n_primes]
    trace_cols = [f"trace_{p}" for p in primes]
    return df[trace_cols].values

def compute_sato_tate_moments(traces, dim_column, max_moment=20):
    """
    Compute Sato-Tate moments by dimension using CORRECTED computation:
    - Use only PRIME indices (done in extract_prime_traces)
    - Normalize by 2 * dim * sqrt(p) for each prime
    - Average across primes for each moment
    """
    prime_indices = np.array([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97])
    sqrt_p = np.sqrt(prime_indices)

    moments_by_dim = {}
    for dim in dim_column.unique():
        dim_mask = (dim_column == dim)
        dim_traces = traces[dim_mask]  # Shape: (n_forms_dim, n_primes)

        # Normalize: x_p = a_p / (2 * dim * sqrt(p))
        x_p = dim_traces / (2 * dim * sqrt_p)

        # Compute moments across all primes for this dimension
        moments = {}
        for k in range(1, max_moment + 1):
            if k % 2 == 0:  # Even moments only
                M_k = np.mean(x_p ** k)
                moments[f"M_{k}"] = float(M_k)

        # Add M_4/M_2 ratio
        if "M_4" in moments and "M_2" in moments:
            moments["M_4/M_2"] = moments["M_4"] / moments["M_2"]

        moments_by_dim[int(dim)] = moments

    return moments_by_dim

if __name__ == "__main__":
    # Load dataset
    df = load_dataset()
    print(f"Dataset loaded: {len(df)} forms")
    print(f"Columns: {df.columns.tolist()[:20]}...")

    # Validation
    stats = validate_cm_stats(df)
    print(f"\nDataset validation:")
    print(f"Total forms: {stats['total_forms']}")
    print(f"CM forms: {stats['total_cm']} ({stats['cm_percentage']:.2f}%)")
    print(f"Non-CM forms: {stats['total_non_cm']}")

    # Extract features
    traces = extract_prime_traces(df, n_primes=25)
    moments = compute_sato_tate_moments(traces, df["dim"], max_moment=20)

    print(f"\nSato-Tate moments by dimension:")
    for dim in sorted(moments.keys())[:5]:  # First 5 dimensions
        ms = moments[dim]
        print(f"Dim {dim}: M_2={ms.get('M_2', 0):.4f}, M_4={ms.get('M_4', 0):.4f}, M_4/M_2={ms.get('M_4/M_2', 0):.4f}")

    # Save for paper
    import json
    with open("data/cm_validation_statistics.json", "w") as f:
        json.dump({"dataset_stats": stats, "sato_tate_moments": moments}, f, indent=2)

    print(f"\nResults saved to data/cm_validation_statistics.json")