"""Assess LMFDB data scope for scale-up (Thread A).

Queries:
1. Count of weight-2 newforms with trivial character by dimension
2. How many have Hecke trace entries in mf_hecke_nf
3. For d>1 forms, how many have complete trace data
4. Sample individual eigenvalue data to assess Thread P feasibility
"""
from __future__ import annotations
import json, sys, os
from loguru import logger

def main():
    import psycopg2
    
    conn = psycopg2.connect(
        host="devmirror.lmfdb.xyz", port=5432,
        dbname="lmfdb",
        user="lmfdb", password="lmfdb",
    )
    cur = conn.cursor()
    
    # 1. Weight-2 newforms with trivial character
    logger.info("Query 1: weight-2 trivial-char newforms...")
    cur.execute("""
        SELECT dim, COUNT(*) 
        FROM mf_newforms 
        WHERE weight = 2 AND conrey_index = 1 
        GROUP BY dim 
        ORDER BY dim
    """)
    rows = cur.fetchall()
    total = sum(r[1] for r in rows)
    print(f"\n=== Weight-2 trivial character newforms (total: {total:,}) ===")
    for dim, cnt in rows:
        print(f"  dim={dim}: {cnt:,}")
    
    # 2. How many have Hecke trace entries
    logger.info("Query 2: forms with Hecke traces...")
    cur.execute("""
        SELECT COUNT(DISTINCT nf.label)
        FROM mf_newforms nf
        JOIN mf_hecke_nf h ON h.label = nf.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1
    """)
    with_traces = cur.fetchone()[0]
    print(f"\nForms with Hecke traces: {with_traces:,} / {total:,} ({100*with_traces/total:.1f}%)")
    
    # 3. By dimension with traces
    cur.execute("""
        SELECT nf.dim, COUNT(DISTINCT nf.label)
        FROM mf_newforms nf
        JOIN mf_hecke_nf h ON h.label = nf.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1
        GROUP BY nf.dim
        ORDER BY nf.dim
    """)
    print("\n=== Forms with Hecke traces by dim ===")
    for dim, cnt in cur.fetchall():
        print(f"  dim={dim}: {cnt:,}")
    
    # 4. Check what the 'an' field looks like (sample)
    logger.info("Query 3: sample individual eigenvalue data...")
    cur.execute("""
        SELECT nf.dim, h.n, h.an
        FROM mf_hecke_nf h
        JOIN mf_newforms nf ON nf.label = h.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1 AND nf.dim >= 2
        LIMIT 5
    """)
    print("\n=== Sample individual eigenvalue data (dim>=2) ===")
    for dim, n, an_str in cur.fetchall():
        an = json.loads(an_str) if isinstance(an_str, str) else an_str
        print(f"  dim={dim}, n={n}, an type={type(an).__name__}, len={len(an) if hasattr(an,'__len__') else '?'}, first={an[:3] if hasattr(an,'__getitem__') else '?'}")
    
    # 5. For d=1 forms: trace = eigenvalue, check how many have complete data
    cur.execute("""
        SELECT h.n, h.an
        FROM mf_hecke_nf h
        JOIN mf_newforms nf ON nf.label = h.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1 AND nf.dim = 1
        LIMIT 3
    """)
    print("\n=== Sample d=1 eigenvalue data ===")
    for n, an_str in cur.fetchall():
        an = json.loads(an_str) if isinstance(an_str, str) else an_str
        print(f"  n={n}, an={str(an)[:120]}")
    
    # 6. Count traces per form for the current 63K dataset
    cur.execute("""
        SELECT COUNT(DISTINCT h.label)
        FROM mf_hecke_nf h
        JOIN mf_newforms nf ON nf.label = h.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1
        AND nf.dim = 1
    """)
    d1_with_traces = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(DISTINCT h.label)
        FROM mf_hecke_nf h
        JOIN mf_newforms nf ON nf.label = h.label
        WHERE nf.weight = 2 AND nf.conrey_index = 1
        AND nf.dim >= 2
    """)
    d2plus_with_traces = cur.fetchone()[0]
    
    print(f"\nd=1 forms with traces: {d1_with_traces:,}")
    print(f"dim>=2 forms with traces: {d2plus_with_traces:,}")
    print(f"Total: {d1_with_traces + d2plus_with_traces:,}")
    
    # 7. Average number of trace coefficients per form
    cur.execute("""
        SELECT AVG(cnt) FROM (
            SELECT h.label, COUNT(*) as cnt
            FROM mf_hecke_nf h
            JOIN mf_newforms nf ON nf.label = h.label
            WHERE nf.weight = 2 AND nf.conrey_index = 1
            GROUP BY h.label
        ) sub
    """)
    avg_traces = cur.fetchone()[0]
    print(f"Average trace coefficients per form: {avg_traces:.1f}")
    
    cur.close()
    conn.close()
    logger.success("Done")

if __name__ == "__main__":
    main()
