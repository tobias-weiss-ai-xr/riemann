import json, sys

with open("/workspace/data/farey-graphs/manifest.json") as f:
    m = json.load(f)
print("Total:", len(m["graphs"]))
for g in m["graphs"]:
    n = g["level"]
    v = g["num_vertices"]
    e = g["num_edges"]
    sg = g.get("spectral_gap", 0)
    ad = g.get("avg_degree", 0)
    print("n=%4d V=%6d E=%6d gap=%.6f deg=%.2f" % (n, v, e, sg, ad))
