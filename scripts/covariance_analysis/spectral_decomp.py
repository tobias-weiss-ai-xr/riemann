# scripts/covariance_analysis/spectral_decomp.py
import numpy as np
from scipy import linalg
from loguru import logger

def compute_full_spectrum(correlation_matrix):
    """Compute full eigenvalue decomposition of correlation matrix.

    Args:
        correlation_matrix: P×P symmetric correlation matrix

    Returns:
        Tuple[np.ndarray, np.ndarray]: (eigenvalues_descending, eigenvectors_as_columns)
    """
    logger.info(f"Computing full spectrum of {correlation_matrix.shape} matrix")

    # Use scipy.linalg.eigh for hermitian matrices (faster, more stable)
    eigenvalues, eigenvectors = linalg.eigh(correlation_matrix)

    # Sort eigenvalues in descending order
    idx = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    logger.info(f"Spectrum computed: λ_max={eigenvalues[0]:.4f}, λ_min={eigenvalues[-1]:.4f}")

    # Check PSD (all eigenvalues should be >= -1e-10, allow small numerical errors)
    if np.any(eigenvalues < -1e-10):
        logger.warning(f"Negative eigenvalues found in PSD matrix: {eigenvalues[eigenvalues < 0]}")
        eigenvalues = np.clip(eigenvalues, 0, None)

    return eigenvalues, eigenvectors


def compute_spectral_stats(eigenvalues):
    """Compute spectral statistics from eigenvalue distribution.

    Args:
        eigenvalues: Sorted eigenvalues in descending order

    Returns:
        dict: {effective_rank, entropy}
    """
    # Normalized eigenvalues (sum to 1)
    normalized_evals = eigenvalues / np.sum(eigenvalues)

    # Effective rank: sum(evals) / max(eval)
    effective_rank = np.sum(eigenvalues) / np.max(eigenvalues)

    # Eigenvector entropy: Shannon entropy of normalized spectrum
    # H = -Σ p_i log(p_i), where p_i = λ_i / Σλ
    entropy = -np.sum(normalized_evals * np.log(normalized_evals + 1e-16))

    logger.info(f"Spectral stats: effective_rank={effective_rank:.2f}, entropy={entropy:.3f}")

    return {
        'effective_rank': effective_rank,
        'entropy': entropy
    }