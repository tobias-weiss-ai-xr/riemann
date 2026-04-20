"""Compute Hecke eigenvalues - fix real root extraction."""

from cypari2 import Pari
import numpy as np

pari = Pari()


def get_eigenvalues(coeffs_vec, n_eigenvalues=100):
    """Extract numerical eigenvalues from PARI mfcoefs result."""
    try:
        a1 = float(coeffs_vec[1])
        is_rational = True
    except:
        is_rational = False

    if is_rational:
        vals = [float(coeffs_vec[n]) for n in range(1, n_eigenvalues + 1)]
        a1 = vals[0]
        if abs(a1) < 1e-10:
            return None
        return np.array([v / a1 for v in vals])

    # Non-rational: evaluate polmod at largest REAL root
    a1_str = str(coeffs_vec[1])
    mod_part = a1_str.split(",")[-1].strip().rstrip(")")

    # Find REAL roots only (imaginary part ~= 0)
    try:
        roots = pari(
            "my(f=%s); my(R=polroots(f)); my(rR=select(r->abs(imag(r))<1e-10, R)); rR"
            % mod_part
        )
        n_real = len(roots)
        if n_real == 0:
            return None

        # Pick the largest real root
        real_roots = sorted([float(roots[i]) for i in range(n_real)])
        real_root = real_roots[-1]
    except Exception as ex:
        print("    root finding failed: %s" % ex)
        return None

    # Evaluate each coefficient at the real root
    var_name = mod_part.split("^")[0].strip()
    vals = []
    for n in range(1, n_eigenvalues + 1):
        try:
            c_str = str(coeffs_vec[n])
            if c_str.startswith("Mod("):
                poly_part = c_str[c_str.index("(") + 1 : c_str.index(",")].strip()
                val = pari("subst(%s, %s, %.15f)" % (poly_part, var_name, real_root))
                vals.append(float(val))
            else:
                vals.append(float(coeffs_vec[n]))
        except:
            vals.append(0.0)

    a1 = vals[0]
    if abs(a1) < 1e-10:
        return None
    return np.array([v / a1 for v in vals])


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
            violations = sum(
                1
                for q in primes
                if q - 1 < len(eigenvalues)
                and abs(eigenvalues[q - 1]) > 2 * q**0.5 + 0.01
            )
            print(
                "    %s (Deligne: %d violations)"
                % ("OK" if violations == 0 else "WARN", violations)
            )
        else:
            print("  Form %d: skipped" % (k + 1))
    print()
