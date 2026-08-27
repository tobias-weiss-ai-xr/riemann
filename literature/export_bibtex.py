#!/usr/bin/env python3
"""Standard BibTeX export for a *-research corpus.

Self-contained: writes paper/references.bib from papers.yaml.

Standard pipeline mimic shared across all research repos.

Usage:
    python3 scripts/export_bibtex.py
"""

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent


def sanitize_bibtex(text):
    text = text.replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")
    return re.sub(r"([{}_])", r"\\\1", text)


def main():
    yaml_path = Path(__file__).resolve().parent / "papers.yaml"
    if not yaml_path.exists():
        print("papers.yaml not found — nothing to export.")
        return
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    papers = data.get("papers", [])
    entries = []
    for i, paper in enumerate(papers):
        words = re.findall(r"[a-z]+", paper.get("title", f"paper{i}").lower())
        key = "".join(words[:3]) or f"paper{i}"
        date = paper.get("date", "")
        year = date[:4] if date else "0000"
        authors = paper.get("authors", [])
        author_str = " and ".join(authors) if authors else "Unknown"
        title = sanitize_bibtex(paper.get("title", ""))
        url = paper.get("url", "")
        venue = paper.get("venue", "")
        if isinstance(venue, list):
            venue = ", ".join(str(v) for v in venue)
        abstract = paper.get("abstract", "")
        if authors:
            # pick the first author whose surname has letters (guards empty strings)
            first = next((a for a in authors if a and re.search(r"[a-zA-Z]", a)), "")
            if first:
                surname = re.findall(r"[a-zA-Z]+", first)[-1].lower() if re.findall(r"[a-zA-Z]+", first) else ""
                key = f"{surname}{year}{key[:20]}"
            else:
                key = f"{year}{key[:25]}"
        else:
            key = f"{year}{key[:25]}"
        entry = [f"@article{{{key},", f"  title = {{{title}}},", f"  author = {{{author_str}}},",
                 f"  year = {{{year}}},", f"  url = {{{url}}},"]
        if venue:
            entry.append(f"  journal = {{{sanitize_bibtex(venue)}}},")
        if abstract:
            entry.append(f"  abstract = {{{sanitize_bibtex(abstract[:500])}}},")
        entry.append("}")
        entries.append("\n".join(entry))
    out = REPO / "references.bib"
    if not entries:
        print("No papers to export.")
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n\n".join(entries) + "\n", encoding="utf-8")
    print(f"Exported {len(papers)} papers to {out}")


if __name__ == "__main__":
    main()