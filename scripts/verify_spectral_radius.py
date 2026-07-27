#!/usr/bin/env python3
"""
Numerical Verification: Spectral Radius of Transfer Operator
============================================================

Purpose: Numerically verify that ρ(L_s) < 1 for Re(s) > 1/2.

This script computes the spectral radius of the truncated transfer operator
L_s^N for various values of s and N, and verifies it is less than 1.

Reference: research/ASSIGNMENT_4_GLOBAL_BOUND.md
"""

import numpy as np
import scipy.linalg as la
from typing import Optional, Tuple
import argparse
import logging
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# =============================================================================
# Transfer Operator Definition
# =============================================================================

def transfer_matrix(s: complex, N: int) -> np.ndarray:
    """
    Construct the N x N truncation of the transfer operator L_s.
    
    The transfer operator is:
        (L_s f)(x) = ∑_{n=1}^∞ (n + x)^{-2s} f(1/(n + x))
    
    For numerical discretization, we use x_i = i/N for i = 1,...,N
    and approximate the sum with n = 1,...,N.
    
    Args:
        s: Complex parameter
        N: Size of truncation
        
    Returns:
        N x N matrix approximation of L_s
    """
    # Discretization points
    x = np.linspace(0, 1, N, endpoint=False)[1:]  # x_i = i/N for i=1,...,N-1
    
    # For simplicity, use x_i = (i + 0.5)/N as midpoints
    x = (np.arange(N) + 0.5) / N
    
    # Construct matrix
    L = np.zeros((N, N), dtype=complex)
    
    for i in range(N):
        for n in range(1, N + 1):
            for j in range(N):
                # Compute (n + x_j)^{-2s} * f(1/(n + x_j))
                # For discretization: f(1/(n + x_j)) ≈ f(x_k) where k is closest
                val = 1 / (n + x[j])
                # Find closest x_k to val
                if val > 0 and val < 1:
                    k = min(int(val * N), N - 1)
                    weight = (n + x[j]) ** (-2 * s)
                    L[i, k] += weight / N  # Normalize by dx
                # For n + x_j >= N, the value 1/(n+x_j) < 1/N, which is outside our grid
                # We ignore these terms (Truncation error)
    
    return L


def eigenvals_spectral_radius(s: complex, N: int = 100) -> Tuple[np.ndarray, float]:
    """
    Compute eigenvalues and spectral radius of truncated L_s.
    
    Args:
        s: Complex parameter
        N: Size of truncation
        
    Returns:
        eigenvalues: Array of eigenvalues
        spectral_radius: Maximum absolute value of eigenvalues
    """
    L = transfer_matrix(s, N)
    eigenvalues = la.eigvals(L)
    spectral_radius = np.max(np.abs(eigenvalues))
    return eigenvalues, spectral_radius


# =============================================================================
# Verification Functions
# =============================================================================

def verify_spectral_bound(s_real: float, s_imag: float = 0.0, N: int = 100) -> dict:
    """
    Verify that ρ(L_s) < 1 for s = s_real + i*s_imag.
    
    Args:
        s_real: Real part of s
        s_imag: Imaginary part of s
        N: Size of truncation
        
    Returns:
        Dictionary with results and status
    """
    s = complex(s_real, s_imag)
    
    result = {
        's': s,
        's_real': s_real,
        's_imag': s_imag,
        'N': N,
    }
    
    try:
        eigenvalues, rho = eigenvals_spectral_radius(s, N)
        result['eigenvalues'] = eigenvalues
        result['spectral_radius'] = rho
        result['spectral_radius < 1'] = rho < 1
        result['status'] = 'PASS' if rho < 1 else 'FAIL'
        
        # Leading eigenvalue
        leading_idx = np.argmax(np.abs(eigenvalues))
        result['leading_eigenvalue'] = eigenvalues[leading_idx]
        result['leading_eigenvalue_abs'] = np.abs(eigenvalues[leading_idx])
        
    except Exception as e:
        result['error'] = str(e)
        result['status'] = 'ERROR'
    
    return result


def evaluate_on_grid(N_values: list = [50, 100, 200], 
                    s_real_values: list = [0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0]) -> list:
    """
    Evaluate spectral radius for multiple values of N and Re(s).
    
    Args:
        N_values: List of truncation sizes
        s_real_values: List of real parts to test
        
    Returns:
        List of verification results
    """
    results = []
    
    for s_real in s_real_values:
        for N in N_values:
            result = verify_spectral_bound(s_real, s_imag=0.0, N=N)
            results.append(result)
            
            status_msg = f"s={s_real}: ρ(L_s)={result.get('spectral_radius', '?'):.6f} " \
                        f"(N={N}) [{result.get('status', '?')}]"
            logger.info(status_msg)
    
    return results


# =============================================================================
# Critical Line Test
# =============================================================================

def test_critical_line(s_real: float = 0.5, 
                      s_imag_values: list = [0.0, 10.0, 20.0, 30.0],
                      N: int = 200) -> list:
    """
    Test spectral radius on or near the critical line Re(s) = 1/2.
    
    At s = 1/2, we expect ρ(L_s) = 1 (leading eigenvalue is 1).
    For Re(s) > 1/2, we expect ρ(L_s) < 1.
    
    Args:
        s_real: Real part (use 0.5 for critical line)
        s_imag_values: Imaginary parts to test
        N: Size of truncation
        
    Returns:
        List of verification results
    """
    results = []
    
    for s_imag in s_imag_values:
        # Test s = 1/2 + i*im
        result_at_half = verify_spectral_bound(s_real, s_imag, N)
        results.append(result_at_half)
        
        # Test s = 1/2 + ε + i*im for small ε
        for eps in [0.01, 0.05, 0.1, 0.2]:
            result_above = verify_spectral_bound(s_real + eps, s_imag, N)
            results.append(result_above)
            
            rho_half = result_at_half.get('spectral_radius', float('nan'))
            rho_above = result_above.get('spectral_radius', float('nan'))
            
            logger.info(f"s={s_real:g}+{eps:g}+i{s_imag:g}: " \
                       f"ρ={rho_above:.6f} (vs ρ={rho_half:.6f} at Re(s)={s_real:g})")
    
    return results


# =============================================================================
# Main Execution
# =============================================================================

def main(args=None):
    """Main function for spectral radius verification."""
    parser = argparse.ArgumentParser(
        description='Numerically verify spectral radius bound for transfer operator'
    )
    parser.add_argument('--N', type=int, default=100, help='Truncation size (default: 100)')
    parser.add_argument('--s-reals', nargs='+', type=float, 
                        default=[0.6, 0.7, 0.8, 0.9, 1.0, 1.5, 2.0],
                        help='Real parts to test')
    parser.add_argument('--s-imags', nargs='+', type=float, default=[0.0],
                        help='Imaginary parts to test')
    parser.add_argument('--test-grid', action='store_true', 
                        help='Run full grid test')
    parser.add_argument('--test-critical', action='store_true',
                        help='Run critical line test')
    parser.add_argument('--output', type=str, default='data/verify_spectral_radius.json',
                        help='Output file for results')
    
    args = parser.parse_args(args)
    
    logger.info("Starting spectral radius verification")
    logger.info(f"Parameters: N={args.N}, s_reals={args.s_reals}, s_imags={args.s_imags}")
    
    results = []
    
    # Direct evaluation
    for s_real in args.s_reals:
        for s_imag in args.s_imags:
            result = verify_spectral_bound(s_real, s_imag, args.N)
            results.append(result)
            logger.info(f"s={s_real}+{s_imag}i: " \
                       f"ρ={result.get('spectral_radius', '?'):.6f} " \
                       f"[{result.get('status', '?')}]")
    
    # Grid test
    if args.test_grid:
        logger.info("\nRunning grid test...")
        grid_results = evaluate_on_grid(N_values=[50, 100, 200],
                                        s_real_values=args.s_reals)
        results.extend(grid_results)
    
    # Critical line test
    if args.test_critical:
        logger.info("\nRunning critical line test...")
        critical_results = test_critical_line(s_real=0.5, N=args.N)
        results.extend(critical_results)
    
    # Save results
    import json
    import pickle
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON (minimal)
    json_data = []
    for r in results:
        json_data.append({
            's_real': r.get('s_real'),
            's_imag': r.get('s_imag'),
            'N': r.get('N'),
            'spectral_radius': r.get('spectral_radius'),
            'status': r.get('status'),
            'leading_eigenvalue': str(r.get('leading_eigenvalue')),
        })
    
    with open(args.output, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    logger.info(f"\nResults saved to {args.output}")
    
    # Summary
    pass_count = sum(1 for r in results if r.get('status') == 'PASS')
    fail_count = sum(1 for r in results if r.get('status') == 'FAIL')
    error_count = sum(1 for r in results if r.get('status') == 'ERROR')
    
    logger.info(f"\nSummary: {pass_count} PASS, {fail_count} FAIL, {error_count} ERROR")
    
    if fail_count > 0 or error_count > 0:
        logger.warning("Some tests failed or encountered errors")
        return 1
    
    logger.info("All spectral radius tests PASSED!")
    return 0


if __name__ == '__main__':
    exit(main())
