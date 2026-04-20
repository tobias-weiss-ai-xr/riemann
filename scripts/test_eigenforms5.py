"""Compute Hecke eigenvalues with proper polmod evaluation for non-rational forms."""

from cypari2 import Pari
import numpy as np

pari = Pari()


def get_eigenvalues(pari_result, n_eigenvalues=100):
    """Extract numerical eigenvalues from PARI mfcoefs result.

    For rational forms: direct float conversion.
    For non-rational forms: evaluate polmod at largest real root of minimal polynomial.
    """
    coeffs = pari_result  # vector [a_0, a_1, ..., a_n]

    # Check if rational
    try:
        a1 = float(coeffs[1])
        is_rational = True
    except:
        is_rational = False

    if is_rational:
        vals = [float(coeffs[n]) for n in range(1, n_eigenvalues + 1)]
        a1 = vals[0]
        if abs(a1) < 1e-10:
            return None  # Eisenstein component
        return np.array([v / a1 for v in vals])

    # Non-rational: evaluate polmod at real roots of minimal polynomial
    # Get the modulus from a_1 (which is Mod(1, minpoly))
    a1_str = str(coeffs[1])  # e.g. "Mod(1, y^2 - y - 1)"

    # Extract modulus: everything after the last comma
    # "Mod(1, y^2 - y - 1)" -> "y^2 - y - 1)"
    mod_part = a1_str.split(",")[-1].strip().rstrip(")")

    # Use PARI to find real roots and evaluate all coefficients
    try:
        eval_result = pari(
            "my(f=%s);"
            "my(R=polroots(f));"
            "my(r=vecsort(R,,4)[1]);"  # largest real root
            "r" % mod_part
        )
        real_root = float(eval_result)
    except Exception as ex:
        print("    root finding failed for %s: %s" % (mod_part[:60], ex))
        return None

    # Evaluate each coefficient at the real root
    vals = []
    for n in range(1, n_eigenvalues + 1):
        try:
            c_str = str(coeffs[n])
            if c_str.startswith("Mod("):
                # Extract polynomial part: "Mod(poly, mod)" -> poly
                poly_part = c_str[c_str.index("(") + 1 : c_str.index(",")].strip()
                # Evaluate poly at real_root
                val = pari(
                    "subst(%s, %s, %f)"
                    % (
                        poly_part,
                        mod_part.split("^")[0].strip(),  # variable name
                        real_root,
                    )
                )
                vals.append(float(val))
            else:
                vals.append(float(coeffs[n]))
        except Exception as ex:
            vals.append(0.0)

    a1 = vals[0]
    if abs(a1) < 1e-10:
        return None
    return np.array([v / a1 for v in vals])


# Test on all primes
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
        eigenvalues = get_eigenvalues(result[k])
        if eigenvalues is not None:
            print(
                "  Form %d: a=[%s]"
                % (k + 1, ", ".join("%.4f" % x for x in eigenvalues[:10]))
            )
            # Check Deligne bound at prime indices
            primes = [
                2,
                3,
                5,
                7,
                11,
                13,
                17,
                19,
                23,
                29,
                31,
                37,
                41,
                43,
                47,
                53,
                59,
                61,
                67,
                71,
                73,
                79,
                83,
                89,
                97,
            ]
            violations = 0
            for q in primes:
                if q - 1 < len(eigenvalues):
                    bound = 2 * q**0.5
                    if abs(eigenvalues[q - 1]) > bound + 0.01:
                        violations += 1
            if violations > 0:
                print("    WARNING: %d Deligne bound violations" % violations)
            else:
                print("    OK: Deligne bound satisfied")
        else:
            print("  Form %d: skipped (a_1=0 or error)" % (k + 1))
    print()
