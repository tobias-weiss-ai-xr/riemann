"""
Mode Analysis Module for Covariance Structure Analysis.

Extracts top K modes from correlation matrices and compares their
structure across dimension classes to identify driver modes that
distinguish d≤6 from d>6 forms.
"""

import numpy as np
from scipy.spatial.distance import cosine as cosine_distance
from scipy.stats import wasserstein_distance
import json
from loguru import logger


def extract_top_modes(eigenvalues, eigenvectors, k=5):
    """Extract top-k eigenvectors with their statistics.

    Args:
        eigenvalues: Sorted eigenvalues (descending)
        eigenvectors: Eigenvectors as columns
        k: Number of top modes to extract

    Returns:
        List[dict]: Mode info with eigenvalue, explained_variance, eigenvector
    """
    normalized_evals = eigenvalues / np.sum(eigenvalues)

    modes = []
    for i in range(min(k, len(eigenvalues))):
        modes.append({
            'index': i,
            'eigenvalue': float(eigenvalues[i]),
            'explained_variance': float(normalized_evals[i]),
            'eigenvector': eigenvectors[:, i].tolist()
        })

    logger.info(f"Extracted top {len(modes)} modes (k={k})")

    return modes


def compute_mode_magnitude(mode):
    """Compute L2 norm of eigenvector."""
    eigvec = np.array(mode['eigenvector'])
    return float(np.linalg.norm(eigvec))


def normalize_modes(modes):
    """Normalize each mode eigenvector to unit L2 norm."""
    for mode in modes:
        eigvec = np.array(mode['eigenvector'])
        mag = np.linalg.norm(eigvec)
        mode['eigenvector'] = (eigvec / mag).tolist()
    return modes


def analyze_mode_structure(low_modes, high_modes, n_modes=3):
    """Compare mode structures between low and high dimension classes.

    Args:
        low_modes: List of mode dicts for low-dim class
        high_modes: List of mode dicts for high-dim class
        n_modes: Number of top modes to compare

    Returns:
        dict: cosine_similarity matrix, value ratios, kl divergences
    """
    # Normalize modes for cosine similarity
    low_norm = normalize_modes([m.copy() for m in low_modes[:n_modes]])
    high_norm = normalize_modes([m.copy() for m in high_modes[:n_modes]])

    # Compute pairwise cosine similarities
    cos_sim = np.zeros((n_modes, n_modes))
    for i in range(n_modes):
        for j in range(n_modes):
            low_vec = np.array(low_norm[i]['eigenvector'])
            high_vec = np.array(high_norm[j]['eigenvector'])
            # Cosine similarity = 1 - cosine_distance for normalized vectors
            cos_sim[i, j] = 1.0 - cosine_distance(low_vec, high_vec)

    # Compute value ratios
    value_ratio = [
        high_modes[j]['eigenvalue'] / low_modes[i]['eigenvalue']
        for i in range(n_modes)
        for j in [i]  # Compare mode i to mode i
    ]

    # Compute KL divergence between explained variance distributions
    low_explained = np.array([m['explained_variance'] for m in low_modes[:n_modes]])
    high_explained = np.array([m['explained_variance'] for m in high_modes[:n_modes]])

    # Add small epsilon to avoid log(0)
    eps = 1e-10
    low_explained = np.clip(low_explained, eps, 1.0)
    high_explained = np.clip(high_explained, eps, 1.0)

    kl_div = np.sum(low_explained * np.log(low_explained / high_explained))

    logger.debug(f"Cosine similarity: {cos_sim}")
    logger.debug(f"Value ratios: {value_ratio}")
    logger.debug(f"KL divergence (explained variance): {kl_div:.6f}")

    return {
        'cosine_similarity': cos_sim.tolist(),
        'value_ratio': value_ratio,
        'kl_divergence_explained_variance': float(kl_div)
    }


def compare_spectra(low_evals, high_evals, low_vecs, high_vecs):
    """Compare two spectral decompositions.

    Args:
        low_evals: Eigenvalues for low-dim class
        high_evals: Eigenvalues for high-dim class
        low_vecs: Eigenvectors for low-dim class
        high_vecs: Eigenvectors for high-dim class

    Returns:
        dict: Comparison metrics (kl_divergence, wasserstein_distance, eigenvector_distances)
    """
    # Normalize eigenvalues
    low_probs = low_evals / np.sum(low_evals) + 1e-16
    high_probs = high_evals / np.sum(high_evals) + 1e-16

    # KL divergence: D_KL(P||Q)
    kl_div = np.sum(low_probs * np.log(low_probs / high_probs))

    # Wasserstein-1 distance
    wasserstein = wasserstein_distance(low_evals, high_evals)

    # Eigenvector similarity: cosine distance between corresponding eigenvectors
    n_modes = min(len(low_vecs[0]), len(high_vecs[0]))
    eigenvector_distances = []

    for i in range(n_modes):
        if i < low_vecs.shape[1] and i < high_vecs.shape[1]:
            v_low = low_vecs[:, i]
            v_high = high_vecs[:, i]
            cos_dist = cosine_distance(v_low, v_high)
            eigenvector_distances.append(float(cos_dist))
        else:
            eigenvector_distances.append(1.0)  # Maximum distance if one doesn't exist

    logger.info(f"Spectrum comparison: KL={kl_div:.3f}, Wasserstein={wasserstein:.3f}")

    return {
        'kl_divergence': float(kl_div),
        'wasserstein_distance': float(wasserstein),
        'eigenvector_distances': eigenvector_distances
    }


def identify_driver_modes(low_eigenvectors, high_eigenvectors, top_k=5, threshold=0.3):
    """Identify eigenvectors that differ significantly between classes.

    Args:
        low_eigenvectors: List of eigenvectors for low-dim class
        high_eigenvectors: List of eigenvectors for high-dim class
        top_k: Number of top modes to check
        threshold: Cosine distance threshold for "significant difference"

    Returns:
        List[int]: Indices of driver modes (most different eigenvectors)
    """
    n = min(top_k, len(low_eigenvectors), len(high_eigenvectors))
    distances = []

    for i in range(n):
        v_low = np.array(low_eigenvectors[i])
        v_high = np.array(high_eigenvectors[i])
        cos_dist = cosine_distance(v_low, v_high)
        distances.append((i, cos_dist))

    # Sort by distance descending and filter by threshold
    driver_modes = [
        idx for idx, dist in sorted(distances, key=lambda x: x[1], reverse=True)
        if dist >= threshold
    ]

    logger.info(f"Identified {len(driver_modes)} driver modes (threshold={threshold}): {driver_modes}")

    return driver_modes