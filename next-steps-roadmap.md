# Nächste Schritte: Von Graph-Spektren zur Riemann-Hypothese

> **Stand:** 18. April 2026
> **Voraussetzung:** Full-Graph ChebConv erreicht <6% relativen Fehler beim spektralen Gap für p≥29

---

## Pfad A: LPS-Brücke — Hecke-Eigenwerte vorhersagen

### Mathematische Grundlage

Die LPS-Konstruktion (Lubotzky-Phillips-Sarnak 1988) verbindet drei Welten:

```
Quaternionenalgebren → Cayley-Graphen → Modulare Formen
```

**Der zentrale Satz (Pizer 1990, Jacquet-Langlands-Korrespondenz):**

Die Eigenwerte der Brandt-Matrix B(ℓ) (außer ℓ+1 vom Eisenstein-Vektor) sind **präzise** die Eigenwerte des Hecke-Operators T_ℓ auf S₂(Γ₀(p)) — den Spitzenformen vom Gewicht 2, Level p.

**Walk-Counting-Formel:**

Für den LPS-Graphen X^{p,q} ist die Anzahl der Pfade der Länge m von Knoten i nach Knoten j:

```
(A^m)_{ij} = δ(p^m) + a(p^m)
```

wobei:
- `δ(p^m)` = Fourier-Koeffizient der Eisenstein-Reihe (Gewicht 2)
- `a(p^m)` = Fourier-Koeffizient der Spitzenform auf Γ(16q²)

**Exakte Entsprechung (Gewicht k=2):**

| Graph-Seite | Modulforme-Seite |
|---|---|
| Adjazenz-Eigenwert λ von X^{p,q} | Hecke-Eigenwert a_ℓ(f) von T_ℓ auf S₂(Γ₀(q)) |
| Grad d = p + 1 | (kommt von Quaternion-Norm) |
| Ramanujan-Schranke: \|λ\| ≤ 2√p | Deligne-Schranke: \|a_ℓ\| ≤ 2√ℓ |

### Konkrete Pipeline

#### Schritt 1: Hecke-Eigenwerte berechnen (SageMath)

```python
# Methode 1: Newforms (höchste Abstraktion)
sage: newforms = Newforms(37, 2, names='a')  # Gewicht 2, Level 37
sage: f = newforms[0]
sage: f.hecke_eigenvalue(2)   # → -2
sage: f.hecke_eigenvalue(3)   # → -3
sage: f.hecke_eigenvalue(5)   # → -2

# Methode 2: Numerische Eigenformen (schnell, approximativ)
sage: n = numerical_eigenforms(61)
sage: n.ap(2)  # Eigenwerte von T_2 auf allen Eigenformen

# Methode 3: Modular Symbols
sage: M = ModularSymbols(89, 2, sign=1)
sage: S = M.cuspidal_submodule().new_submodule()
sage: D = S.decomposition()
sage: [d.q_eigenform(50) for d in D]  # q-Entwicklung aller Newforms
```

**Relevante Modulform-Räume für unsere Graphen:**

| Graph-Parameter | Relevanter Raum |
|---|---|
| Level N = p | S₂(Γ₀(p)) — Spitzenformen Gewicht 2, Level p |
| LPS-Parameter q | S₂(Γ₀(q)) — Spitzenformen Gewicht 2, Level q |
| Pizer-Konstruktion | S₂(Γ₀(N)) mit N = q²M |

#### Schritt 2: L-Funktion konstruieren

```python
# Euler-Produkt (für normalisierte Newform f = Σ a_n q^n)
# L(s,f) = ∏_p (1 - a_p p^{-s} + χ(p) p^{k-1-2s})^{-1}

# SageMath: Direkte L-Reihe
sage: f = CuspForms(37, 2).newforms()[0]
sage: L = f.lseries()  # Dokchitser L-Reihe
sage: L(1)
sage: L.check_functional_equation()

# Alternative: Über Dokchitser (allgemein)
from sage.lfunctions.dokchitser import Dokchitser
L = Dokchitser(conductor=37, gammaV=[0], weight=2, eps=-1,
               poles=[], residues=[], init_coeffs=coeffs, prec=53)
```

#### Schritt 3: LMFDB API abfragen

```python
import requests
BASE = "https://www.lmfdb.org/api"

# Hecke-Eigenwerte für eine Newform
resp = requests.get(f"{BASE}/mf_hecke_cc/?label=37.2.a.a&_format=json&n=pyrange(1,100)")
eigenvalues = {d['n']: complex(d['an']) for d in resp.json()}

# L-Funktion mit Nullstellen
resp = requests.get(f"{BASE}/lfunc_lfunctions/?conductor=i37&_format=json")
zeros = resp.json()[0]['positive_zeros']  # Imaginärteile auf Re(s)=1/2

# L-Funktion nach Conductor suchen
resp = requests.get(f"{BASE}/mf_newforms/?level=i37&weight=i2&_format=json")
```

**LMFDB Datenbank:**
- 1.1M+ klassische Newforms
- 14M+ Hecke-Eigenwerte (als komplexe Zahlen)
- 24M+ L-Funktionen mit Nullstellen

#### Schritt 4: Brücke zu ζ(s) via Eisenstein-Reihen

```
G_k(z) = Σ*_{m,n∈Z} (mz + n)^{-k}  (nicht-normalisierte Eisenstein-Reihe)
G_k(z) = 2ζ(k) + 2·(2πi)^k/(k-1)! · Σ σ_{k-1}(n) q^n

Zentrale Beziehung: ζ(k) = -(2πi)^k · B_k / (2 · k!)
```

Für Gewicht k=2 über Rankin-Selberg:
```
⟨E_k, f⟩_RS ∝ L(s, f ⊗ E_k) = L(s, f) · ζ(s - k + 1)
```

### Was das GNN vorhersagen kann

| Ziel | Mathematische Bedeutung | Berechenbar? |
|---|---|---|
| Hecke-Eigenwerte a_p(f) | Fourier-Koeffizienten von Spitzenformen | ✅ SageMath `Newforms` |
| Wurzelzahl ε | Vorzeichen der funktionalen Gleichung | ✅ SageMath `root_number()` |
| Analytischer Rang | Ordnung der Nullstelle bei s=k/2 | ✅ LMFDB |
| Erste Nullstelle γ₁ | Lage der ersten nichttrivialen Nullstelle | ✅ LMFDB API |
| Sato-Tate-Verteilung | Verteilung der normierten Eigenwerte | ✅ Statistischer Test |

### Empfohlenes Experiment

**GNN vorhersagt Hecke-Eigenwerte a_p(f) aus Cayley-Graph-Struktur:**

1. Für jede Primzahl p: Berechne Cayley(SL(2,F_p), S) — **bereits vorhanden**
2. Berechne Hecke-Eigenwerte via SageMath `Newforms(p, 2)` — **Ground Truth**
3. Konstruiere PyG-Datensatz: Graph → Hecke-Eigenwerte als Target
4. Trainiere Full-Graph ChebConv (bewährte Architektur)
5. Validiere: Deligne-Schranke |a_p| ≤ 2√p muss für Vorhersagen gelten

**Erweiterung:** Konstruiere L(s,f) aus vorhergesagten Koeffizienten → berechne vorhergesagte Nullstellen → vergleiche mit LMFDB.

---

## Pfad B: Farey-Graph + Transfer-Operatoren

### Mathematische Grundlage

**WICHTIGE Unterscheidung:** Es gibt zwei verschiedene „Farey"-Objekte:
1. **Die Farey-Abbildung** F: [0,1] → [0,1] (dynamisches System, Kettenbrüche)
2. **Der Farey-Graph** (Graphentheorie) — unendlicher Graph mit Knoten = reduzierte Brüche

Die Brücke zu ζ(s) verläuft über **Transfer-Operatoren → Selberg-Zetafunktion → ζ(s)**.

### Der Mayer-Transfer-Operator

**Definition** (Mayer 1990/1991):

```
L_s φ(z) = Σ_{n=1}^{∞} (z+n)^{-2s} φ(1/(z+n))
```

wobei φ holomorph auf der Scheibe D = {z ∈ ℂ : |z-1| < 3/2}.

**Der zentrale Satz (Mayer 1991, Theorem 2):**

```
Z_{Selberg}(s) = det(1 - L_s) · det(1 + L_s)
```

Und die Selberg-Zetafunktion für SL(2,ℤ):
```
Z_{Selberg}(s) = Π_{k=0}^{∞} ζ(s+k)^{-1}
```

**Konsequenz:**
- **Eigenwerte +1** von L_s ↔ diskretes Spektrum des Laplace-Operators (Maass-Formen)
- **Eigenwerte -1** von L_s ↔ **Nullstellen von ζ(s)**

**RH als lineares Algebra-Problem (Bonanno 2023, Theorem 2.1):**

> Der verallgemeinerte Transfer-Operator Q_q hat einen Eigenwert 1 **genau dann**, wenn:
> - λ_q := q(1-q) im diskreten Spektrum des Laplace-Operators liegt, **ODER**
> - **2q eine nichttriviale Nullstelle der Riemannschen Zetafunktion ist.**

### Konkrete Berechnung: Mayer-Matrix

Die Matrixdarstellung von L_s in der Polynomialbasis {(z-1)^k}:

```
L_{mk}(s) = Γ(2s+m+k) / (Γ(2s) · m! · k!) · ζ(2s + m + k)
```

**Python-Implementierung:**

```python
import numpy as np
from scipy.special import gamma, zeta as scipy_zeta
from scipy.linalg import eigvals

def mayer_matrix(N, s):
    """N×N-Trunkierung des Mayer-Transfer-Operators L_s."""
    L = np.zeros((N, N), dtype=complex)
    for m in range(N):
        for k in range(N):
            coeff = gamma(2*s + m + k) / (gamma(2*s) * gamma(m+1) * gamma(k+1))
            L[m, k] = coeff * scipy_zeta(2*s + m + k)
    return L

def find_zeta_zeros(N, s_values):
    """Finde s-Werte, bei denen L_s Eigenwert ±1 hat."""
    zeros = []
    for s in s_values:
        eigs = eigvals(mayer_matrix(N, s))
        for lam in eigs:
            if abs(lam - 1) < 1e-4:
                zeros.append(('plus1', s, lam))
            if abs(lam + 1) < 1e-4:
                zeros.append(('minus1', s, lam))
    return zeros
```

### Farey-Graph-Konstruktion

```python
from fractions import Fraction

def farey_sequence(n):
    """Farey-Folge der Ordnung n — reduzierte Brüche in [0,1]."""
    seq = [Fraction(0, 1)]
    for d in range(1, n + 1):
        for num in range(d):
            f = Fraction(num, d)
            if f not in seq:
                seq.append(f)
    seq.sort()
    seq.append(Fraction(1, 1))
    return seq

def build_farey_graph(n):
    """Farey-Graph trunkiert bei Nenner ≤ n.
    |F_n| = 1 + Σ_{k=1}^{n} φ(k) ≈ 3n²/π² Knoten."""
    farey = farey_sequence(n)
    edges = []
    for i in range(len(farey) - 1):
        # Konsekutive Farey-Brüche erfüllen |ad-bc| = 1
        edges.append((i, i+1))
    return farey, edges
```

### GKW-Operator (Vepstas)

Der Gauss-Kuzmin-Wirsing-Operator in der Basis {x^k}:

```
H_{jk} = Σ_{n=0}^{∞} (-1)^{k-n} / (n+1)^{j+1} · C(k,n)
```

Beziehung zu ζ(s):
```
ζ(s) = s/(s-1) - s · ∫_0^1 x [G x^{s-1}](x) dx
```

### Verfügbare Software

| Werkzeug | Beschreibung | URL |
|---|---|---|
| **PyZeta** | Python-Bibliothek für Selberg-Zeta via Transfer-Operatoren | github.com/Spectral-Analysis-UPB/PyZeta |
| **Fraczek (2017)** | Numerische Methoden, Befehlszeilen-Tool `widmo` | Springer LNM 2259 |
| **SageMath** | Eingebaute `farey_sequence()`, Modulformen-Framework | sagemath.org |

### Empfohlenes Experiment

**Phase 1 — Transfer-Operator-Eigenwerte (direktester Weg):**
1. Baue N×N Mayer-Matrix L_{mk}(s) für verschiedene s auf der kritischen Linie
2. Berechne Eigenwerte → identifiziere welche nahe ±1 liegen
3. Trainiere GNN auf der Matrixstruktur, um vorherzusagen, welche s-Werte Eigenwert ±1 geben
4. Dies ist äquivalent zur Vorhersage von Nullstellen von Z(s) und damit ζ(s)

**Phase 2 — Farey-Graph + Transfer-Operator-Hybrid:**
1. Baue Farey-Graph F(N) als Graph für GNN
2. Knoten-Features = Tiefe im Stern-Brocot-Baum, Zähler, Nenner
3. Berechne Transfer-Operator-Matrixelemente aus der Graphstruktur
4. Trainiere GNN, den führenden Eigenwert von L_s aus Graph-Features vorherzusagen

**Phase 3 — Von Eigenwerten zu Zeta-Nullstellen:**
1. Für jedes s = 1/4 + it (t variierend), berechne trunkierte L_s-Matrix
2. Verfolge, wie sich Eigenwerte mit t bewegen (Spektralfluss)
3. Trainiere GNN: Gegeben Spektralfluss-Daten, wo überqueren Eigenwerte ±1?

---

## Strategische Empfehlung

### Pfad A (LPS/Hecke) ist der direktere Weg:

1. **Wir haben bereits die Cayley-Graphen** — kein neuer Graph nötig
2. **Hecke-Eigenwerte sind direkt berechenbar** via SageMath/PARI
3. **LMFDB bietet 14M+ vorgefertigte Eigenwerte** als Ground Truth
4. **Die mathematische Verbindung ist exakt** (Pizer-Theorem)
5. **Full-Graph ChebConv ist bereits bewährt** für spektrale Vorhersage

### Pfad B (Farey/Transfer) ist fundamentaler aber komplexer:

1. **Neuer Graph nötig** — Farey-Graph muss konstruiert werden
2. **Transfer-Operator ist unendlich-dimensional** — Trunkierung nötig
3. **Die Verbindung zu ζ(s) ist indirekter** — über Selberg-Zetafunktion
4. **Numerische Stabilität** der Mayer-Matrix-Trunkierung muss validiert werden
5. **Bietet aber einen direkteren Weg zu ζ(s)-Nullstellen**

### Empfohlene Reihenfolge

1. **Woche 1-2:** Pfad A Schritt 1-2 (Hecke-Eigenwerte berechnen + GNN trainieren)
2. **Woche 3-4:** Pfad A Schritt 3-4 (L-Funktion + LMFDB-Vergleich)
3. **Woche 5-6:** Pfad B Phase 1 (Mayer-Matrix + Farey-Graph)
4. **Woche 7+:** Entscheidung basierend auf Ergebnissen

---

## Referenzen

### Pfad A: LPS / Hecke

- Lubotzky, Phillips, Sarnak (1988). Ramanujan graphs. *Combinatorica* 8(3), 261-277.
- Pizer, A. (1990). Ramanujan graphs and Hecke operators. *Bull. AMS* 23(1), 127-137.
- Charles, et al. (2009). Ramanujan graphs from quaternion algebras. [McGill PDF](https://www.math.mcgill.ca/goren/PAPERSpublic/FinalRamanujan.pdf)
- Murty & Sinha. Ramanujan graphs. [Queens U PDF](https://mast.queensu.ca/~murty/RamanujanGraphs-IJDM.pdf)
- Deligne, P. (1974). La conjecture de Weil, I. *Publ. IHÉS* 43, 273-307.
- Winnie Li (1993). Ramanujan conjecture survey. [PMC](https://ncbi.nlm.nih.gov/pmc/articles/PMC6939229/)
- Zagier, D. Modular forms and their applications. [MPIM PDF](https://people.mpim-bonn.mpg.de/zagier/files/doi/10.1007/978-3-540-74119-0_1/fulltext.pdf)

### Pfad B: Farey / Transfer

- Mayer, D.H. (1991). The thermodynamic formalism approach to Selberg's zeta function for PSL(2,Z). *BAMS* 25(1), 55-60.
- Bonanno, C. (2023). On the generalized transfer operators of the Farey map with complex temperature. *Mathematics* 11(1), 134. [DOI](https://doi.org/10.3390/math11010134)
- Zagier, D. New points of view on the Selberg zeta function. [MPIM PDF](https://people.mpim-bonn.mpg.de/zagier/files/tex/NewPointsSelbergZeta/fulltext.pdf)
- Lewis & Zagier (2001). Period functions and the Selberg zeta function. *Invent. Math.*
- Fraczek, M.S. (2017). Selberg zeta functions and transfer operators. Springer LNM 2259.
- Vepstas, L. The Bernoulli operator, the GKW operator, and the Riemann zeta. [linas.org](http://linas.org/math/gkw.pdf)

### Software

- LMFDB API: [lmfdb.org/api](https://www.lmfdb.org/api/) — 14M+ Hecke-Eigenwerte, 24M+ L-Funktionen
- PyZeta: [github.com/Spectral-Analysis-UPB/PyZeta](https://github.com/Spectral-Analysis-UPB/PyZeta)
- SageMath: Modulformen, Hecke-Algebra, L-Reihen, Dokchitser
