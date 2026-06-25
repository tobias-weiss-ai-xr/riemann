#!/usr/bin/env python3
"""
Fix LaTeX mathematical notation issues in cm-arxiv/paper.tex.

This script:
1. Wraps all M_k/M_2 expressions in $...$ math mode
2. Replaces Unicode math symbols with LaTeX-friendly alternatives
3. Ensures all mathematical expressions are properly formatted
"""

import re
from pathlib import Path

# Path to the LaTeX file
TEX_FILE = Path("/workspace/papers/cm-arxiv/paper.tex")

def fix_unicode_math_symbols(content):
    """Replace Unicode math symbols with LaTeX equivalents."""

    replacements = {
        'ℚ': r'$\mathbb{Q}$',  # Rational numbers
        'ℤ': r'$\mathbb{Z}$',  # Integers
        '√': r'$\sqrt{',       # Square root (needs closing brace)
        '∑': r'$\sum$',        # Summation
        '≥': r'$\ge$',         # Greater or equal
        '≤': r'$\le$',         # Less or equal
        '∈': r'$\in$',         # Element of
        '∉': r'$\notin$',      # Not element of
        '≠': r'$\neq$',        # Not equal
        '∞': r'$\infty$',      # Infinity
        '→': r'$\to$',         # Arrow
        '∂': r'$\partial$',    # Partial derivative
        '∫': r'$\int$',        # Integral
        '×': r'$\times$',      # Times
        '÷': r'$\div$',        # Divide
        '±': r'$\pm$',         # Plus minus
        'Δ': r'$\Delta$',      # Delta
        'θ': r'$\theta$',      # Theta
        'λ': r'$lambda$',      # Lambda
        'μ': r'$mu$',          # Mu
        'σ': r'$sigma$',       # Sigma
        'φ': r'$phi$',         # Phi
        'ψ': r'$psi$',         # Psi
    }

    for unicode_char, latex_eq in replacements.items():
        content = content.replace(unicode_char, latex_eq)

    # Fix sqrt (needs closing brace)
    content = content.replace(r'$\sqrt{', r'\sqrt{').replace(r'\sqrt{', r'$\sqrt{}$')

    return content

def fix_m_ratios(content):
    """Wrap M_k/M_2 expressions in $...$ math mode."""

    # Need to wrap M_k/M_2 expressions like M_4/M_2, M_10/M_2
    # Also wrap standalone M_k like M_4, M_10, M_k(d=1)

    # First, wrap the ratios M_k/M_2 where k can be 1-2 digits
    content = re.sub(r'\$?\$?M_(\d{1,2})/M_2\$?\$?', r'$M_\1/M_2$', content)

    # Wrap standalone M_k expressions (1-2 digits)
    content = re.sub(r'\$?\$?M_(\d{1,2})\b\$?\$?', r'$M_\1$', content)

    # Handle M_k(d=x) patterns
    content = re.sub(r'\$?\$?M_(\d{1,2})\(d=(\d+)\)\$?\$?', r'$M_\1(d=\2)$', content)

    return content

def fix_a_p_notation(content):
    """Wrap a_p notation in math mode."""

    # Match a_p, a_23, a_41, etc.
    content = re.sub(r'(?<!\$)a_\d+\b(?!\$)', lambda m: f'${m.group(0)}$', content)
    content = re.sub(r'(?<!\$)a_p\b(?!\$)', r'$a_p$', content)

    return content

def main():
    """Main function to fix the LaTeX file."""
    if not TEX_FILE.exists():
        print(f"ERROR: File not found: {TEX_FILE}")
        return False

    print(f"Reading {TEX_FILE}...")
    with open(TEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Fixing Unicode math symbols...")
    content = fix_unicode_math_symbols(content)

    print("Fixing M_k/M_2 notation...")
    content = fix_m_ratios(content)

    print("Fixing a_p notation...")
    content = fix_a_p_notation(content)

    print(f"Writing fixed content to {TEX_FILE}...")
    with open(TEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\nSUCCESS: LaTeX file fixed!")
    print("\nNext steps:")
    print("  1. cd /workspace/papers/cm-arxiv/")
    print("  2. xelatex -interaction=nonstopmode paper.tex")
    print("  3. Check paper.log for remaining errors")
    print("  4. Verify paper.pdf is generated correctly")
    print("\nNote: Discard the previous paper.pdf - it had compilation errors")

    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)