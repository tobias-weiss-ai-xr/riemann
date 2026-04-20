"""Test PARI eigenform extraction - mfcoefs approach."""

from cypari2 import Pari

pari = Pari()

# mfeigenbasis returns vector of mf structs
# mfcoefs(mf_struct, n) returns vector of coefficients [a_0, a_1, ..., a_n]
# For rational forms: integer coefficients
# For non-rational forms: polmod coefficients

# Test with single expression per prime
for N in [23, 37, 43]:
    # Get eigenbasis coefficients
    # mfcoefs(B[k], n) returns a vector
    result = pari(
        "my(mf=mfinit([%d,2],1));"
        "my(B=mfeigenbasis(mf));"
        "my(d=#B);"
        "vector(d, k, mfcoefs(B[k], 10))" % N
    )

    nforms = len(result)
    print("=== N=%d: %d eigenforms ===" % (N, nforms))

    for k in range(nforms):
        coeffs_vec = result[k]
        print("  Form %d: type=%s, len=%d" % (k + 1, type(coeffs_vec), len(coeffs_vec)))
        for n in range(1, min(6, len(coeffs_vec))):
            c = coeffs_vec[n]
            try:
                val = float(c)
                print("    a_%d = %.4f" % (n, val))
            except:
                print("    a_%d = %s (non-float)" % (n, str(c)[:80]))
    print()

# For non-rational forms, use mfembed to get numerical approximations
# mfembed(mf, k) gives the k-th complex embedding of all forms
print("=== mfembed test ===")
for N in [23]:
    # mfembed on mfinit gives a matrix: rows = embeddings, cols = form coefficients
    try:
        emb = pari("my(mf=mfinit([%d,2],1));mfembed(mf)" % N)
        print("N=%d: type=%s" % (N, type(emb)))
        if hasattr(emb, "__len__"):
            print("  len=%d" % len(emb))
            for i in range(min(2, len(emb))):
                row = emb[i]
                print(
                    "  row %d: type=%s, len=%d"
                    % (i, type(row), len(row) if hasattr(row, "__len__") else "?")
                )
                if hasattr(row, "__len__"):
                    for j in range(min(10, len(row))):
                        try:
                            print("    [%d] = %.6f" % (j, float(row[j])))
                        except:
                            print("    [%d] = %s" % (j, str(row[j])[:50]))
    except Exception as ex:
        print("N=%d error: %s" % (N, ex))
