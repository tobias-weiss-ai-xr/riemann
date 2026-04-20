"""Test PARI-based Pizer graph construction via supersingular isogeny graphs."""

from cypari2 import Pari

pari = Pari()


# Step 1: Find supersingular j-invariants in F_p^2
# A j-invariant is supersingular iff ellap(E, p) = 0
def find_supersingular_j(p):
    """Find all supersingular j-invariants in F_{p^2}."""
    p2 = p * p
    ss = []
    # Check small j values (brute force for small p)
    for j in range(p2):
        try:
            E = pari(f"ellinit([0,0,0,0,{j}], Mod(1,{p2}))")
            ap = pari(f"ellap({E}, {p})")
            if str(ap) == "0":
                ss.append(j)
        except Exception:
            pass
    return ss


# Step 2: Build isogeny graph using modular polynomial
def build_isogeny_graph(p, ell, ss_j):
    """Build adjacency list for supersingular ell-isogeny graph."""
    p2 = p * p
    Phi = pari(f"polmodular({ell})")  # Phi_ell(x, y)

    adj = {j: set() for j in ss_j}
    for j in ss_j:
        # Evaluate Phi_ell(j, y) in F_{p^2}
        poly = pari(f"subst({Phi}, x, Mod({j}, {p2}))")
        # Find roots (neighbors)
        try:
            roots = pari(f"nfroots(Mod(1,{p2}), {poly})")
            # roots are Gen objects in F_{p^2}
            for r in roots:
                # Convert to integer representative
                r_int = int(pari(f"lift({r})"))
                if r_int != j:  # no self-loops
                    adj[j].add(r_int)
        except Exception as e:
            print(f"  Error finding roots for j={j}: {e}")

    return adj


# Test with p=11, ell=2
print("=== Testing Pizer graph for p=11, ell=2 ===")
print()

ss_j = find_supersingular_j(11)
print(f"Supersingular j-invariants in F_121: {len(ss_j)} found")
print(f"  Values: {ss_j[:10]}{'...' if len(ss_j) > 10 else ''}")
print()

if ss_j:
    adj = build_isogeny_graph(11, 2, ss_j)
    print("Adjacency list:")
    for j in sorted(adj.keys()):
        if adj[j]:
            print(f"  j={j} -> {sorted(adj[j])}")

    # Count vertices and edges
    n_verts = len(adj)
    n_edges = sum(len(v) for v in adj.values()) // 2  # undirected
    print(f"\nGraph: {n_verts} vertices, {n_edges} edges")
    print(f"Expected: ~{11 // 12} + epsilon = ~1 vertex (p=11 is small)")

    # Compare with Brandt module
    print("\nBrandt module comparison:")
    dim = int(pari("mfdim([11,2], 1)"))  # cusp forms
    print(f"  dim S_2(Gamma_0(11)) = {dim}")
    print(f"  class_number = {n_verts} (should be dim + 1)")

    # Verify: compute Hecke eigenvalues from modular forms
    print("\nHecke eigenvalues from modular forms:")
    if dim > 0:
        mf = pari("mfinit([11,2], 1)")
        eb = pari("mfeigenbasis(mf)")
        for k in range(len(eb)):
            coeffs = pari(f"mfcoefs({eb}[{k + 1}], 5)")
            print(f"  Form {k + 1}: a_2={coeffs[2]}, a_3={coeffs[3]}, a_5={coeffs[5]}")

# Test with p=37 (more interesting)
print("\n\n=== Testing Pizer graph for p=37, ell=2 ===")
ss_j_37 = find_supersingular_j(37)
print(f"Supersingular j-invariants in F_{37**2}: {len(ss_j_37)} found")
if len(ss_j_37) > 0:
    print(f"  First 10: {ss_j_37[:10]}")
