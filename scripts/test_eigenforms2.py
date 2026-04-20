"""Test PARI eigenform extraction - single expression approach."""

from cypari2 import Pari

pari = Pari()

for N in [23, 37, 43, 47, 53, 59, 61]:
    # Single PARI expression to avoid variable scope issues
    # mfeigenbasis returns vector of mf structs (polynomials in q)
    # For rational newforms, polcoeff gives integers
    # For non-rational, polcoeff gives polmod

    # Get eigenbasis and coefficients in one expression
    result = pari(
        "my(mf=mfinit([%d,2],1));"
        "my(B=mfeigenbasis(mf));"
        "my(d=#B);"
        "vector(d, k, vector(10, n, polcoeff(B[k], n)))" % N
    )

    nforms = len(result)
    print("=== N=%d: %d eigenforms ===" % (N, nforms))

    for k in range(nforms):
        form = result[k]
        coeffs = []
        is_rational = True
        for n in range(10):
            try:
                val = float(form[n])
                coeffs.append(val)
            except:
                is_rational = False
                coeffs.append(str(form[n])[:50])

        if is_rational:
            print("  Form %d: %s" % (k + 1, [round(c, 4) for c in coeffs]))
        else:
            print("  Form %d (non-rational): %s" % (k + 1, coeffs[:3]))
    print()

# Now test mfembed for non-rational forms
print("=== Testing mfembed ===")
for N in [23, 29]:
    try:
        # mfembed on the mfinit object returns matrix of embeddings
        # Rows = embeddings, each row = vector of a_1..a_n for all forms concatenated
        emb = pari("my(mf=mfinit([%d,2],1));my(B=mfeigenbasis(mf));mfembed(mf)" % N)
        print(
            "N=%d: mfembed type=%s, len=%d"
            % (N, type(emb), len(emb) if hasattr(emb, "__len__") else "?")
        )
        print("  content: %s" % str(emb)[:300])
    except Exception as ex:
        print("N=%d: mfembed failed: %s" % (N, ex))
