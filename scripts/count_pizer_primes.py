"""Count primes with sufficient S_2 dimension for Pizer graphs."""

from cypari2 import Pari
import time

pari = Pari()


def is_prime(n):
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True


primes = [p for p in range(11, 2000) if is_prime(p)]
print(f"Checking {len(primes)} primes...")

eligible = []
t0 = time.time()
for p in primes:
    dim = int(pari(f"mfdim([{p},2], 1)"))
    if dim >= 4:
        eligible.append((p, dim))

elapsed = time.time() - t0
print(f"\nPrimes < 2000 with dim S_2 >= 4: {len(eligible)}")
print(f"  dim range: {min(d[1] for d in eligible)} to {max(d[1] for d in eligible)}")
print(f"  Computation time: {elapsed:.1f}s")
print(f"\nFirst 20:")
for p, d in eligible[:20]:
    print(f"  p={p:5d} dim={d:3d}")
print(f"\nLast 10:")
for p, d in eligible[-10:]:
    print(f"  p={p:5d} dim={d:3d}")
