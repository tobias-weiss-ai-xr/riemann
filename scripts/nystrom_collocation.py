#!/usr/bin/env python3
"""EPIC-4: overflow-safe chunked-vectorized Nystrom collocation for L_s.

Vectorized Nystrom matrix assembly for the Mayer/Ruelle transfer operator

    (L_s f)(x) = sum_{k=0}^inf (k+1+x)^{-2s} f(1/(k+1+x))

with bounded memory (k in chunks) and log-space barycentric weights, which keeps
the Lagrange basis finite for collocation orders up to N=512+ (the naive product
formula 1/prod(x_j-x_k) overflows for N >= ~400).

Tracked, overflow-safe successor of lambda1_derivative.nystrom_matrix and the
gitignored scripts/_nystrom_vec.py (identical API; only weight computation
differs -- Lagrange interpolation is invariant under a common rescaling of
barycentric weights, so normalization is exact, not approximate).
"""
from __future__ import annotations

import numpy as np
from numpy.polynomial.legendre import leggauss


def _barycentric_weights(x: np.ndarray) -> np.ndarray:
    """w_j = 1/prod_{k!=j}(x_j-x_k), log-space + normalized to max|w|=1 (exact)."""
    n = len(x)
    dx = x[:, None] - x[None, :]
    np.fill_diagonal(dx, 1.0)                      # dummy for zero diagonal
    logabs = -np.log(np.abs(dx)).sum(axis=1)       # log|w_j|
    j = np.arange(n)
    sign = np.where((n - 1 - j) % 2 == 0, 1.0, -1.0)  # ascending nodes -> (-1)^(n-1-j)
    return sign * np.exp(logabs - logabs.max())


def _lagrange_rows(y: np.ndarray, x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Barycentric Lagrange basis at y: L[i,j] = ell_j(y_i)."""
    diff = y[:, None] - x[None, :]                 # (m, n)
    num = w[None, :] / diff                        # (m, n)
    den = num.sum(axis=-1, keepdims=True)          # (m, 1)
    return num / den                                # (m, n)


def nystrom_matrix_vec(s: complex, n: int, nmax: int, chunk: int = 200) -> np.ndarray:
    """A[i,j] = sum_k (k+1+x_i)^{-2s} ell_j(1/(k+1+x_i)), chunked over k."""
    x, _ = leggauss(n)
    x = 0.5 * x + 0.5                              # nodes in (0,1)
    w = _barycentric_weights(x)
    A = np.zeros((n, n), dtype=complex)
    for c0 in range(0, nmax + 1, chunk):
        ks = np.arange(c0, min(c0 + chunk, nmax + 1))
        a = (ks[:, None] + 1) + x[None, :]         # (chunk, n) = k+1+x_i
        wfun = a ** (-2.0 * s)                     # (chunk, n)
        yy = 1.0 / a                               # (chunk, n) preimages
        lag = np.stack([_lagrange_rows(yyi, x, w) for yyi in yy])  # (chunk, n, n)
        A += np.einsum("ki,kij->ij", wfun, lag)
    return A


def leading_pair(s: complex, n: int, nmax: int, chunk: int = 200):
    """(|lambda_1(s)|, |lambda_2(s)|) -- two largest-modulus eigenvalues."""
    A = nystrom_matrix_vec(s, n, nmax, chunk)
    ev = np.linalg.eigvals(A)
    o = np.argsort(-np.abs(ev))
    return float(abs(ev[o[0]])), float(abs(ev[o[1]]))


def margin(s: complex, n: int, nmax: int, chunk: int = 200) -> float:
    """m(s) = min_j |1 - lambda_j(s)| (eigenvalue-1 margin; >0 <=> 1 not in Spec)."""
    ev = np.linalg.eigvals(nystrom_matrix_vec(s, n, nmax, chunk))
    return float(np.min(np.abs(ev - 1.0)))


def leading_eigenvalue_vec(s: complex, n: int, nmax: int, chunk: int = 200) -> complex:
    A = nystrom_matrix_vec(s, n, nmax, chunk)
    ev = np.linalg.eigvals(A)
    return complex(ev[np.argmax(np.abs(ev))])
