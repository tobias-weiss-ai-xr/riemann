"""KG query utilities — common queries against the Riemann knowledge graph."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


class RiemannKG:
    """Query interface for the Riemann Hypothesis knowledge graph."""

    def __init__(self) -> None:
        uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        user = os.environ.get("NEO4J_USER", "neo4j")
        password = os.environ.get("NEO4J_PASSWORD", "riemann-research")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def rh_equivalence_class(self) -> list[dict[str, Any]]:
        """Find all statements equivalent to the Riemann Hypothesis."""
        query = """
        MATCH path = (rh:Theorem {name: 'Riemann Hypothesis'})-[:EQUIVALENT_TO*1..3]-(equiv:Theorem)
        RETURN DISTINCT equiv.name AS name, equiv.proof_status AS status, equiv.description AS description
        ORDER BY equiv.name
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def graphs_to_zeta_bridges(self) -> list[dict[str, Any]]:
        """Find all graph → ζ(s) bridge paths."""
        query = """
        MATCH path = (g:Graph)-[*1..4]-(zeta:MathFunction {name: 'ζ(s)'})
        RETURN g.name AS graph,
               [r IN relationships(path) | type(r)] AS relationship_chain,
               length(path) AS distance
        ORDER BY distance
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def ai_approaches_ranked(self) -> list[dict[str, Any]]:
        """List all AI approaches ranked by confidence."""
        query = """
        MATCH (a:AIApproach)
        OPTIONAL MATCH (a)-[:TARGETS]->(t:Theorem)
        RETURN a.name AS approach, a.approach_type AS type, a.confidence AS confidence,
               a.status AS status, collect(t.name) AS targets
        ORDER BY a.confidence DESC
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def theory_chain_sl2z_to_zeta(self) -> list[dict[str, Any]]:
        """Trace the complete SL(2,Z) → ζ(s) mathematical chain."""
        query = """
        MATCH path = (g:Group {name: 'SL(2,Z)'})-[*1..6]-(z:MathFunction {name: 'ζ(s)'})
        UNWIND nodes(path) AS n
        UNWIND relationships(path) AS r
        WITH collect(DISTINCT {name: n.name, type: labels(n)[0], description: n.description}) AS nodes,
             collect(DISTINCT {type: type(r), from: startNode(r).name, to: endNode(r).name}) AS rels
        RETURN nodes, rels
        """
        with self.driver.session() as session:
            results = session.run(query)
            return [dict(r) for r in results]

    def ramanujan_graphs(self) -> list[dict[str, Any]]:
        """Find all graphs with Ramanujan property info."""
        query = """
        MATCH (g:Graph)
        WHERE g.is_ramanujan IS NOT NULL
        RETURN g.name AS name, g.is_ramanujan AS ramanujan, g.degree AS degree,
               g.type AS graph_type, g.description AS description
        ORDER BY g.degree
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def researcher_contributions(self, name: str) -> list[dict[str, Any]]:
        """Map a researcher's contributions."""
        query = """
        MATCH (r:Researcher {name: $name})-[:AUTHORED]->(p:Paper)
        OPTIONAL MATCH (p)-[:PROVES]->(t:Theorem)
        OPTIONAL MATCH (p)-[:INTRODUCES]->(obj)
        RETURN p.title AS paper, p.year AS year,
               collect(DISTINCT t.name) AS proved_theorems,
               collect(DISTINCT labels(obj)[0] + ':' + obj.name) AS introduced_objects
        ORDER BY p.year DESC
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query, name=name)]

    def stats(self) -> dict[str, int]:
        """Count nodes and relationships by type."""
        query = """
        MATCH (n)
        WITH labels(n)[0] AS label, count(*) AS count
        RETURN label, count ORDER BY count DESC
        """
        rel_query = """
        MATCH ()-[r]->()
        WITH type(r) AS rel_type, count(*) AS count
        RETURN rel_type, count ORDER BY count DESC
        """
        with self.driver.session() as session:
            nodes = {r["label"]: r["count"] for r in session.run(query)}
            rels = {r["rel_type"]: r["count"] for r in session.run(rel_query)}
            return {"nodes": nodes, "relationships": rels}

    def research_gaps(self) -> list[dict[str, Any]]:
        """Find all graph constructions with documented research gaps."""
        query = """
        MATCH (g:Graph)
        WHERE g.research_gap IS NOT NULL
        RETURN g.name AS name, g.type AS type, g.research_gap AS gap, g.feasibility AS feasibility
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def proof_status_summary(self) -> list[dict[str, Any]]:
        """Summarize proof status of all theorems/conjectures."""
        query = """
        MATCH (t:Theorem)
        WITH t.proof_status AS status, count(*) AS count
        RETURN status, count ORDER BY count DESC
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def operator_correspondences(self) -> list[dict[str, Any]]:
        """Find all operator ↔ operator correspondences (Hecke ↔ Adjacency etc.)."""
        query = """
        MATCH (o1:Operator)-[c:CORRESPONDS_TO]->(o2:Operator)
        RETURN o1.name AS from_op, o2.name AS to_op,
               c.description AS description, c.via AS via, c.precision AS precision
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def citation_network(
        self, paper_name: str, max_depth: int = 3
    ) -> list[dict[str, Any]]:
        """Get citation ancestry of a paper."""
        query = (
            """
        MATCH (p:Paper)-[:CITES*1.."""
            + str(max_depth)
            + """]->(ancestor:Paper)
        WHERE p.title CONTAINS $paper_name
        RETURN DISTINCT ancestor.title AS title, ancestor.year AS year,
               ancestor.bibtex_key AS key
        ORDER BY ancestor.year
        """
        )
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query, paper_name=paper_name)]

    def approach_dependencies(self) -> list[dict[str, Any]]:
        """For each AI approach, find the theorems and mathematical objects it depends on."""
        query = """
        MATCH (a:AIApproach)
        OPTIONAL MATCH (a)-[:BASED_ON_THEOREM]->(t:Theorem)
        OPTIONAL MATCH (a)-[:USES_OBJECT]->(obj)
        RETURN a.name AS approach, a.confidence AS confidence,
               collect(DISTINCT t.name) AS theorems,
               collect(DISTINCT labels(obj)[0] + ':' + obj.name) AS objects
        ORDER BY a.confidence DESC
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]

    def hecke_graph_path(self) -> list[dict[str, Any]]:
        """Trace the Hecke ↔ Graph correspondence path."""
        query = """
        MATCH path = (hecke:Operator {name: 'Hecke T_p'})-[*1..3]-(adj:Operator {name: 'Adjacency Matrix A'})
        RETURN [n IN nodes(path) | labels(n)[0] + ':' + n.name] AS path_nodes,
               [r IN relationships(path) | type(r)] AS path_rels
        """
        with self.driver.session() as session:
            return [dict(r) for r in session.run(query)]
