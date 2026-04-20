# GNN-basierte Analyse des Farey-Graphen — Pfad B Ergebnisse

## Zusammenfassung

**Ergebnis: Farey Spectral Gap Prediction ist ein triviales Problem.**

Der spektrale Gap des Farey-Graphen folgt einer perfekten Potenzgesetz-Beziehung:
```
gap ≈ 2.65 · n^(-0.999) ≈ 2.65/n
```
Ein einfacher linearer Baseline (log-log Regression) erreicht **R² = 0.9999** mit MedRelErr = 0.07%. Die GNN (Full-Graph ChebConv, K=3, hidden=64) erreicht auf dem Standard-Split R² = -7.57 — sie **kann nicht einmal den trivialen Baseline schlagen**.

---

## 1. Experimentelles Setup

### Farey-Graph-Generierung
- **Methode:** Stern-Brocot BFS (O(|F_n|) Zeit)
- **23 Graphen:** n = 10, 20, 30, ..., 230
- **Größen:** V = 33 (n=10) bis V = 16,155 (n=230)
- **Kanten:** E = 63 bis E = 32,307
- **Nicht knotentransitiv:** min_deg = 2, max_deg = n, avg_deg → 4.0

### Datenformat
- `data/farey-graphs/farey_n{nnnn}.npz` — Adjazenzmatrix (scipy sparse CSR)
- `data/farey-graphs/farey_n{nnnn}_spectrum.npz` — Eigenwerte, spectral_gap
- `data/farey-graphs/manifest.json` — 23 Graph-Metadaten

### GNN-Architektur
- **Modell:** Full-Graph ChebConv (adaptiert von train_fullgraph_cheb.py)
- **Knoten-Features (5-dim):** degree_raw/N, degree/max_degree, clustering, triangles, PageRank
- **Kein RPE** (Farey-Graphen sind nicht knotentransitiv — Grad ist informativ)
- **Chebyshev K=3:** 20-dim Features (5 × 4)
- **Graph-Stats (7-dim):** log(V), log(E), density, diameter_est, degree_std, max_deg, avg_deg
- **Target:** log(1/spectral_gap) — transformiert Potenzgesetz-Zerfall in linearen Raum

---

## 2. Ergebnisse

### Baseline-Vergleich

| Modell | MAE (gap) | RMSE (gap) | R² (gap) | MedRelErr |
|--------|-----------|------------|----------|-----------|
| Linear (log-log) | 0.00000084 | 0.00000085 | **0.9999** | 0.0007 |
| Power-law (a·n^-b) | 0.00000084 | 0.00000085 | **0.9999** | 0.0007 |
| GNN (Standard-Split) | 0.00031302 | 0.00032133 | -7.57 | 1.19 |

### Potenzgesetz-Analyse
```
gap ≈ 2.654694 · n^(-0.9989) ≈ 2.65/n
```
Der Exponent b ≈ 1.0 bestätigt die theoretische Vorhersage (spectral gap des Farey-Graphen skaliert als 1/n).

### GNN-Fehlermuster (Standard-Split: train n≤120, test n>120)
- n=130: rel_err = 0.32
- n=160: rel_err = 0.82
- n=200: rel_err = 1.68
- n=230: rel_err = 2.41

→ GNN lernt nicht, sie extrapoliert konstant auf den Mittelwert des Trainingsbereichs.

---

## 3. Warum die GNN scheitert

**Hauptursache:** Der spektrale Gap des Farey-Graphen ist **rein skalenabhängig** — er wird vollständig durch die Knotenanzahl determiniert. Die lokale Graphstruktur (die beim Farey-Graphen ja variiert!) liefert **keine zusätzliche Information** über den spectral gap, die über log(V) hinausgeht.

Im Gegensatz zu den Cayley-Graphen von SL(2,F_p), wo der spectral gap von der Primzahl abhängt und nicht trivial aus der Knotenanzahl ableitbar ist (dort schlug die GNN den Baseline um ΔR²=+0.042), ist der Farey-Graph spectral gap ein exaktes Potenzgesetz.

---

## 4. Vergleich: Cayley vs. Farey

| Aspekt | Cayley SL(2,F_p) | Farey F_n |
|--------|-------------------|-----------|
| Datenpunkte | 18 (p=2..61) | 23 (n=10..230) |
| Knotentransitiv | Ja (alle Grad 4) | Nein (Grad 2..n) |
| Baseline R² (spectral gap) | 0.782 | 0.9999 |
| GNN R² (spectral gap) | 0.824 (LOO-CV) | -7.57 |
| GNN schlägt Baseline? | **Ja** (ΔR²=+0.042) | **Nein** |
| RH-Relevanz | Mittel (Hecke, LPS-Brücke) | Hoch (Mayer-Operator) |
| Daten-Augmentierung möglich | Ja (andere Generatoren) | Nein (ein Graph pro n) |

**Fazit:** Die Cayley-Graphen sind das bessere Testbett für GNN-Spectral-Analyse, weil:
1. Der spectral gap nicht-trivial ist (R²=0.782 Baseline, Raum für GNN-Verbesserung)
2. Daten-Augmentierung möglich ist (mehrere Generator-Sätze pro Gruppe)
3. RH-Relevanz über Hecke-Eigenwerte und LPS-Brücke

---

## 5. Pfad B Gesamtbewertung

### Was funktioniert hat
- Farey-Graph-Generierung via Stern-Brocot BFS (schnell, korrekt)
- Spectral gap Berechnung für alle 23 Graphen
- GNN-Architektur-Adaption (kein RPE, reichhaltigere Knoten-Features)

### Was nicht funktioniert hat
- Spectral gap Prediction: trivial (R²=0.9999 Baseline)
- Keine RH-relevanten Vorhersagen möglich über spectral gap

### Nächster Schritt (empfohlen)
**Pfad A.2: Cayley + Multi-Generator Daten-Augmentierung**
- Für jede Primzahl p: ~10 verschiedene 4-Element-Generatoren → ~130 Graphen
- Ziel: Hecke-Eigenwerte (bereits berechnet via PARI, 17 Eigenformen)
- Bewährte Full-Graph ChebConv-Architektur
- Zero veröffentlichte Arbeiten → hohe Novelität
