"""
Knowledge Graph ingestion script — loads the SL(2,Z) → ζ(s) theory chain into Neo4j.

Usage:
    python ingest.py --all              # Load everything
    python ingest.py --schema-only      # Constraints + indexes only
    python ingest.py --theory           # Groups, Graphs, Functions, Operators, Theorems
    python ingest.py --papers           # Papers, Researchers, AI Approaches
    python ingest.py --dry-run          # Print queries without executing
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from neo4j import GraphDatabase

load_dotenv()

CYPHER_DIR = Path(__file__).parent.parent / "cypher"
CYPHER_FILES = {
    "schema": "00-schema.cypher",
    "groups": "01-groups.cypher",
    "graphs": "02-graphs.cypher",
    "functions": "03-functions.cypher",
    "operators": "04-operators.cypher",
    "theorems": "05-theorems.cypher",
    "papers": "06-papers-approaches.cypher",
    "equivalences": "07-rh-equivalences.cypher",
    "papers-extended": "08-papers-extended.cypher",
    "graphs-extended": "09-graphs-extended.cypher",
    "equivalences-extended": "10-rh-equivalences-extended.cypher",
}

THEORY_FILES = [
    "groups",
    "graphs",
    "functions",
    "operators",
    "theorems",
    "equivalences",
    "equivalences-extended",
]
PAPERS_FILES = ["papers", "papers-extended"]
GRAPH_FILES = ["graphs", "graphs-extended"]


def get_driver() -> GraphDatabase.driver:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "riemann-research")
    logger.info(f"Connecting to Neo4j at {uri}")
    return GraphDatabase.driver(uri, auth=(user, password))


def read_cypher(name: str) -> str:
    path = CYPHER_DIR / CYPHER_FILES[name]
    if not path.exists():
        logger.error(f"Cypher file not found: {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def split_cypher(cypher: str) -> list[str]:
    """Split Cypher into statements, respecting // comments and string literals.

    Uses regex to find balanced CREATE/MERGE blocks and ; as delimiters.
    Handles semicolons inside string literals by tracking quote state.
    """
    import re

    # First, remove full-line comments
    lines = cypher.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        # Remove inline comments (not inside strings)
        # Simple approach: if // appears and no open quote, strip it
        in_str = False
        quote_char = None
        comment_pos = -1
        for i, ch in enumerate(line):
            if in_str:
                if ch == "\\" and i + 1 < len(line):
                    continue  # skip escaped char
                if ch == quote_char:
                    in_str = False
            else:
                if ch in ('"', "'"):
                    in_str = True
                    quote_char = ch
                elif ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                    comment_pos = i
                    break
        if comment_pos >= 0:
            cleaned_lines.append(line[:comment_pos])
        else:
            cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Split on semicolons that are NOT inside string literals
    statements = []
    current = []
    in_str = False
    quote_char = None

    for ch in text:
        if in_str:
            current.append(ch)
            if ch == "\\" and len(current) > 1:
                continue  # next char is escaped
            if ch == quote_char:
                in_str = False
        else:
            if ch in ('"', "'"):
                in_str = True
                quote_char = ch
                current.append(ch)
            elif ch == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(ch)

    # Flush remaining
    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def execute_cypher(
    driver: GraphDatabase.driver, cypher: str, dry_run: bool = False
) -> None:
    """Execute a Cypher file, splitting on ; boundaries."""
    statements = split_cypher(cypher)

    for i, stmt in enumerate(statements):
        cleaned = stmt.strip()
        if not cleaned:
            continue

        if dry_run:
            preview = cleaned[:120].replace("\n", " ")
            logger.info(f"[DRY RUN] Statement {i + 1}: {preview}...")
            continue

        try:
            with driver.session() as session:
                session.run(cleaned)
            logger.info(f"  ✓ Statement {i + 1} executed")
        except Exception as e:
            logger.warning(f"  ✗ Statement {i + 1} failed: {e}")
            # Continue — some statements may fail on re-run (e.g., constraints already exist)


def ingest(
    driver: GraphDatabase.driver, names: list[str], dry_run: bool = False
) -> None:
    for name in names:
        cypher = read_cypher(name)
        logger.info(f"Loading {CYPHER_FILES[name]} ({len(cypher)} bytes)...")
        execute_cypher(driver, cypher, dry_run=dry_run)
    logger.success("Ingestion complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest theory into Neo4j knowledge graph"
    )
    parser.add_argument(
        "--all", action="store_true", help="Load schema + all theory + papers"
    )
    parser.add_argument(
        "--schema-only", action="store_true", help="Load constraints and indexes only"
    )
    parser.add_argument(
        "--theory",
        action="store_true",
        help="Load mathematical theory (groups, graphs, functions, operators, theorems)",
    )
    parser.add_argument(
        "--papers", action="store_true", help="Load papers, researchers, AI approaches"
    )
    parser.add_argument(
        "--graphs",
        action="store_true",
        help="Load graph constructions (base + extended)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print queries without executing"
    )
    args = parser.parse_args()

    if not any([args.all, args.schema_only, args.theory, args.papers, args.graphs]):
        parser.print_help()
        sys.exit(1)

    files_to_load = []
    if args.all:
        files_to_load = list(CYPHER_FILES.keys())
    elif args.schema_only:
        files_to_load = ["schema"]
    elif args.theory:
        files_to_load = ["schema"] + THEORY_FILES
    elif args.papers:
        files_to_load = ["schema"] + PAPERS_FILES
    elif args.graphs:
        files_to_load = ["schema"] + GRAPH_FILES

    driver = get_driver()
    try:
        ingest(driver, files_to_load, dry_run=args.dry_run)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
