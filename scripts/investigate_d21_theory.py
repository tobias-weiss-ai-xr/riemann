# scripts/investigate_d21_theory.py
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
import json

def prime_factors(n: int) -> list[int]:
    """Return prime factors of n"""
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors

def factorize_dimension(d: int) -> list[int]:
    """Prime factorization of dimension d"""
    return prime_factors(d)

def dimensions_with_shared_factors(target_dim: int, max_dim: int = 12) -> dict[int, list[int]]:
    """Find dimensions that share prime factors with target_dim"""
    target_factors = set(prime_factors(target_dim))
    shared = {}
    for d in range(1, max_dim + 1):
        d_factors = prime_factors(d)
        if any(f in target_factors for f in d_factors):
            shared[d] = d_factors
    return shared

def analyze_d21_algebraic_properties():
    """Gather number theory properties of d=21 and neighbors"""
    properties = {
        '21': {
            'factors': prime_factors(21),
            'divisors': [1, 3, 7, 21],
            'phi': 12,  # Euler's totient
            'squarefree': True,
            'cyclotomic_field_degree': 12,  # Q(zeta_21)
        },
        'neighbors': {}
    }

    # Compare with nearby dimensions
    for d in [19, 20, 22, 23]:
        properties['neighbors'][str(d)] = {
            'factors': prime_factors(d),
            'squarefree': len(set(prime_factors(d))) == len(prime_factors(d))
        }

    return properties

def check_smooth_transitions(dim_factor_map: dict[int, list[int]]) -> dict[int, float]:
    """Check correlation smoothness across dimensions with shared factors"""
    # Load existing cross-form correlation results
    corr_path = Path('data/galois_correlation/cross_form_correlation.csv')
    if not corr_path.exists():
        logger.warning("Cross-form correlation data not found")
        return {}

    df = pd.read_csv(corr_path)
    correlations = dict(zip(df['dim'], df['mean_rho']))

    results = {}
    for d in dim_factor_map:
        if d in correlations:
            results[d] = correlations[d]

    return results

def main():
    logger.info("Investigating classical number theory connection to d=21 phase transition")

    # 1. Analyze d=21 algebraic properties
    props = analyze_d21_algebraic_properties()
    logger.info(f"d=21 properties: {props['21']}")
    logger.info(f"Neighbor dimensions: {props['neighbors']}")

    # 2. Find all dimensions with shared prime factors (limited to d ≤ 12 in our data)
    shared_dims = dimensions_with_shared_factors(21, max_dim=12)
    logger.info(f"Dimensions ≤12 sharing factors with 21: {shared_dims}")

    # 3. Check correlation smoothness
    corr_by_factors = check_smooth_transitions(shared_dims)
    logger.info(f"Correlations for dimensions with d=21 factors: {corr_by_factors}")

    # 4. Compare with dimensions without shared factors
    all_dims_1_to_12 = list(range(1, 13))
    no_shared = {d: prime_factors(d) for d in all_dims_1_to_12 if d not in shared_dims}
    corr_no_shared = check_smooth_transitions(no_shared)
    logger.info(f"Correlations for dimensions WITHOUT d=21 factors: {corr_no_shared}")

    # 5. Save results
    out_dir = Path('data/d21_theory')
    out_dir.mkdir(exist_ok=True)

    with open(out_dir / 'prime_factors.json', 'w') as f:
        json.dump({'shared_with_21': shared_dims, 'no_shared': no_shared, 'correlations': {
            'with_21_factors': corr_by_factors, 'without_21_factors': corr_no_shared
        }}, f, indent=2)

    with open(out_dir / 'galois_groups.json', 'w') as f:
        json.dump(props, f, indent=2)

    logger.info("Theory analysis complete. Results saved to data/d21_theory/")

if __name__ == '__main__':
    main()