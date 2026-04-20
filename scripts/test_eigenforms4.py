"""Compute Hecke eigenvalues using mfeigenbasis + polmod evaluation."""

from cypari2 import Pari
import numpy as np

pari = Pari()


def eval_polmod_to_float(polmod_val):
    """Evaluate a PARI polmod Mod(a, f) by substituting the real root of f.

    Returns (real_value, is_rational).
    """
    s = str(polmod_val)
    if not s.startswith("Mod("):
        # It's already a plain number
        try:
            return float(polmod_val), True
        except:
            return None, False

    # Extract the polynomial and modulus from "Mod(poly, modulus)"
    # Use PARI's subst to evaluate at the real root
    # polmod_to_float approach: lift and evaluate at real root
    try:
        # Get the modulus (minimal polynomial) and the polynomial
        # Use PARI's polmod to evaluate at real root of modulus
        result = pari(
            "subst(lift(%s), varnp(%s), real(polroots(%s)[1]))"
            % (polmod_val, polmod_val, polmod_val)
        )
        return float(result), False
    except:
        pass

    try:
        # Alternative: use nfroots to find real root
        result = pari(
            "my(m=polmodtoden(%s));"
            "my(r=nfroots(m));"
            "subst(lift(%s), varnp(%s), real(r[#r > 1 ? 2 : 1]))"
            % (polmod_val, polmod_val, polmod_val, polmod_val)
        )
        return float(result), False
    except:
        pass

    return None, False


for N in [11, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61]:
    result = pari(
        "my(mf=mfinit([%d,2],1));"
        "my(B=mfeigenbasis(mf));"
        "my(d=#B);"
        "vector(d, k, mfcoefs(B[k], 100))" % N
    )

    nforms = len(result)
    print("N=%d: %d eigenforms" % (N, nforms))

    for k in range(nforms):
        coeffs_vec = result[k]

        # Check if rational (first coeff converts to float)
        try:
            a1 = float(coeffs_vec[1])
            is_rational = True
        except:
            is_rational = False

        if is_rational:
            # All coefficients should be rational
            vals = []
            for n in range(1, 21):
                vals.append(float(coeffs_vec[n]))
            # Normalize by a_1
            a1 = vals[0]
            if abs(a1) < 1e-10:
                print("  Form %d: a_1=0, skipping" % (k + 1))
                continue
            normalized = [v / a1 for v in vals]
            print(
                "  Form %d (rational, Q): a=[%s]"
                % (k + 1, ", ".join("%.0f" % x for x in normalized[:10]))
            )
        else:
            # Non-rational: need to evaluate polmod at real root
            print("  Form %d (non-rational): polmod detected" % (k + 1))

            # Get the modulus polynomial
            mod_str = str(coeffs_vec[1])
            print("    modulus: %s" % mod_str[:80])

            # Use PARI to evaluate at real root of minimal polynomial
            try:
                # Build PARI expression to evaluate all coefficients
                eval_result = pari(
                    "my(mf=mfinit([%d,2],1));"
                    "my(B=mfeigenbasis(mf));"
                    "my(c=mfcoefs(B[%d], 100));"
                    "my(f=c[2]);"  # a_1 as polmod, extract modulus
                    "my(T=polmodtofunction(f));"  # not right
                    "my(r=polroots(lift(f)));"  # roots of the modulus
                    "r" % (N, k + 1)
                )
                print("    roots: %s" % str(eval_result)[:200])
            except Exception as ex:
                print("    root extraction failed: %s" % ex)
    print()
