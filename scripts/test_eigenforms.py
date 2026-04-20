"""Test PARI eigenform extraction for non-rational newforms."""

from cypari2 import Pari

pari = Pari()

for N in [23, 37, 43, 47, 53, 59, 61]:
    pari("my(M=mfinit([%d,2],1))" % N)
    pari("my(B=mfeigenbasis(M))")
    nforms = int(pari("#B"))
    print("=== N=%d: %d eigenforms ===" % (N, nforms))

    for k in range(1, nforms + 1):
        try:
            coeffs = []
            is_rational = True
            for n in range(1, 11):
                an = pari("polcoeff(mfeigenbasis(M)[%d], %d)" % (k, n))
                try:
                    val = float(an)
                    coeffs.append(val)
                except (ValueError, TypeError, OverflowError):
                    is_rational = False
                    coeffs.append(None)

            if is_rational:
                print("  Form %d (rational): %s" % (k, [round(c, 4) for c in coeffs]))
            else:
                print("  Form %d (non-rational)" % k)
                # For non-rational forms, get complex embeddings via mfembed
                # mfembed takes a mf struct, not a polynomial
                try:
                    # Reinit and get embedding
                    pari("my(Emf=mfinit([%d,2],1))" % N)
                    pari("my(Eb=mfeigenbasis(Emf))")
                    # mfembed on the eigenform vector
                    emb = pari("mfembed(Eb[%d])" % k)
                    print("    mfembed type: %s" % pari("type(mfembed(Eb[%d]))" % k))
                    print("    mfembed: %s" % str(emb)[:200])
                    # Extract first embedding values
                    if hasattr(emb, "__len__") and len(emb) > 0:
                        first_emb = emb[0]
                        vals = []
                        for n in range(1, 11):
                            try:
                                vals.append(float(first_emb[n]))
                            except:
                                vals.append(None)
                        print("    emb1: %s" % vals)
                except Exception as ex:
                    print("    mfembed error: %s" % ex)
        except Exception as ex:
            print("  Form %d error: %s" % (k, ex))
    print()
