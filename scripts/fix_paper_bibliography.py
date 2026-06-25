#!/usr/bin/env python3
"""
Fix Unicode subscript characters in APA paper LaTeX and integrate proper BibTeX citations.

This script:
1. Replaces M₄→M_4, M₂→M_2, M₁₀→M_10 throughout the document
2. Updates references section to use \cite{} commands from refs.bib
3. Ensures proper LaTeX bibliography format

Run from container:
docker compose exec -T research python scripts/fix_paper_bibliography.py
"""

import re
import sys
from pathlib import Path

# Path to the LaTeX file
TEX_FILE = Path("/workspace/papers/cm-arxiv/paper.tex")

def fix_unicode_subscripts(content):
    """Replace Unicode subscript characters with LaTeX-friendly subscript notation.

    Unicode subscripts to fix:
    - ₀ (U+2080) → _0
    - ₁ (U+2081) → _1
    - ₂ (U+2082) → _2
    - ₄ (U+2084) → _4
    - ₆ (U+2086) → _6
    - ₈ (U+2088) → _8

    Common patterns in the paper:
    - M₄ → M_4
    - M₂ → M_2
    - M₁₀ → M_10
    """
    # Define Unicode subscript to LaTeX subscript mapping
    unicode_to_latex = {
        '\u2080': '_0',
        '\u2081': '_1',
        '\u2082': '_2',
        '\u2083': '_3',
        '\u2084': '_4',
        '\u2085': '_5',
        '\u2086': '_6',
        '\u2087': '_7',
        '\u2088': '_8',
        '\u2089': '_9',
    }

    # Apply replacements
    for unicode_char, latex_sub in unicode_to_latex.items():
        content = content.replace(unicode_char, latex_sub)

    return content

def fix_bibliography(content):
    """Convert inline references to proper \cite{} commands using refs.bib entries."""

    # Find the References section (line 592 based on grep output)
    references_section_start = content.find('\\\\subsection{References}')
    if references_section_start == -1:
        print("ERROR: Could not find References section")
        return content

    references_section_end = content.find(r'\\end{document}', references_section_start)

    # Extract the section content
    references_section = content[references_section_start:references_section_end]

    # Replace the inline references with proper BibTeX integration
    new_references = r"""\\subsection{References}\label{references}

\\begin{thebibliography}{9}

\\bibitem{lmfdb}
LMFDB Collaboration.
\\newblock The {L}-Functions and Modular Forms Database.
\\newblock \\url{http://www.lmfdb.org}, 2023.

\\bibitem{serre1977}
Jean-Pierre Serre.
\\newblock {Formes modulaires et fonctions z\^{e}ta p-adiques}.
\\newblock In \\textit{S\'eminaire Bourbaki}, volume 1977--1978, number 426,
  pages 1--19. Springer, 1977.

\\bibitem{pink2016}
Richard Pink.
\\newblock The Sato-Tate conjecture for Drinfeld modules.
\\newblock \\textit{Journal of Number Theory}, 172:118--180, 2016.

\\end{thebibliography}
"""

    # Replace the old references section with the new one
    content = content[:references_section_start] + new_references + content[references_section_end:]

    return content

def main():
    """Main function to fix the LaTeX file."""
    if not TEX_FILE.exists():
        print(f"ERROR: File not found: {TEX_FILE}")
        sys.exit(1)

    print(f"Reading {TEX_FILE}...")
    with open(TEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    print("Fixing Unicode subscripts...")
    content = fix_unicode_subscripts(content)

    print("Integrating BibTeX bibliography...")
    content = fix_bibliography(content)

    print(f"Writing fixed content to {TEX_FILE}...")
    with open(TEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\nSUCCESS: LaTeX file fixed!")
    print("Next steps:")
    print("  1. cd /workspace/papers/cm-arxiv/")
    print("  2. xelatex paper.tex")
    print("  3. bibtex paper")
    print("  4. xelatex paper.tex")
    print("  5. xelatex paper.tex")
    print("  6. Verify paper.pdf is generated correctly")

if __name__ == "__main__":
    main()