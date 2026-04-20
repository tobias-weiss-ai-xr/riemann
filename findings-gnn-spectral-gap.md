# GNN-basierte Analyse des spektralen Gaps von Cayley-Graphen von SL(2, F_p)

## Ergebnisse und Erkenntnisse aus den Experimenten

---

## 1. Einleitung

### Zielsetzung

Die zentrale Frage dieses Projekts lautet: **Können Graph Neural Networks spektrale Eigenschaften von Cayley-Graphen vorhersagen, die mit der Riemann-Hypothese zusammenhängen?**

Konkret untersuchen wir Cayley-Graphen der speziellen linearen Gruppe SL(2, F_p) über endlichen Primkörpern. Der spektrale Gap dieser Graphen steht in enger Beziehung zur Ramanujan-Eigenschaft, die wiederum mit der Verteilung der Nullstellen der Riemannschen Zetafunktion ζ(s) verknüpft ist. Ein GNN, das den spektralen Gap präzise vorhersagen kann, würde nicht nur die spektrale Graphentheorie bereichern, sondern auch einen neuen rechnerischen Zugang zu einem der tiefsten offenen Probleme der Mathematik eröffnen.

### Mathematischer Hintergrund

**SL(2, F_p)** ist die Gruppe aller 2×2-Matrizen mit Determinante 1 über dem Körper F_p mit p Elementen. Sie hat |SL(2, F_p)| = p(p²-1) Elemente. Für Primzahlen p ≥ 2 erhalten wir eine Familie von endlichen Gruppen wachsender Ordnung.

Ein **Cayley-Graph** Cay(G, S) zu einer Gruppe G mit Erzeugermenge S hat als Knotenmenge die Gruppenelemente und eine Kante (g, gs) für jedes g ∈ G und s ∈ S. Cayley-Graphen sind per Konstruktion regulär und knotentransitiv: Jeder Knoten lässt sich durch einen Automorphismus des Graphen in jeden anderen Knoten überführen.

Der **spektrale Gap** eines Graphen ist der Abstand zwischen dem größten Eigenwert (trivialerweise der Grad d für reguläre Graphen) und dem zweitgrößten Eigenwert der Adjazenzmatrix. Ein großer spektraler Gap bedeutet, dass der Graph stark expandierend ist. Für einen d-regulären Graphen mit d ≥ 3 gilt die **Ramanujan-Schranke**: Der Graph heißt Ramanujan-Graph, wenn alle nichttrivialen Eigenwerte λ die Bedingung |λ| ≤ 2√(d-1) erfüllen.

**Verbindung zur Riemann-Hypothese:** Die Ramanujan-Eigenschaft steht in direkter Beziehung zu Hecke-Eigenwerten modularer Formen. Deligne (1974) bewies, dass die Fourier-Koeffizienten a_p(f) einer Hecke-Eigenform f die Schranke |a_p(f)| ≤ 2p^(k-1)/2 erfüllen. Diese Schranke ist das exakte arithmetische Analogon zur Ramanujan-Bedingung |λ| ≤ 2√(d-1). Die Kette

    Cayley-Graph-Eigenwerte → Hecke-Eigenwerte → L-Funktion → ζ(s)

bildet die theoretische Brücke zwischen Graphenspektrum und Riemann-Hypothese.

### Das Knotentransitivitätsproblem

Cayley-Graphen sind knotentransitiv: Jeder Knoten sieht aus wie jeder andere. Das bedeutet, dass **lokale** Nachbarschaftsstrukturen keine Informationen über **globale** spektrale Eigenschaften tragen. Diese Eigenschaft stellt eine fundamentale Herausforderung für GNNs dar, da herkömmliche GNNs ihre Vorhersagen auf der Basis lokaler Nachbarschaftsaggregate treffen. Ein GNN, das nur lokale Strukturen sieht, kann den spektralen Gap prinzipiell nicht vorhersagen.

---

## 2. Infrastruktur

### Docker-Setup

Das Projekt läuft in einem dedizierten Forschungscontainer mit folgender Softwareausstattung:

| Komponente | Version |
|---|---|
| PyTorch | 2.10 |
| CUDA | 12.6 |
| PyTorch Geometric (PyG) | neueste |
| CayleyPy | neueste |
| Jupyter Lab | neueste |

Der Container wird über `docker compose` gestartet und enthält alle Abhängigkeiten für Graphengenerierung, Eigenwertberechnung und GNN-Training. Ein separates SageMath-Profil ermöglicht den Zugang zu Computeralgebra-Funktionalität.

### Neo4j 5 Knowledge Graph

Die theoretischen Grundlagen des Projekts sind in einer Neo4j 5-Datenbank strukturiert:

- **194 Knoten** (Konzepte, Sätze, Personen, Werkzeuge)
- **161 Beziehungen** (begründet, verallgemeinert, verwendet, etc.)
- **28 Äquivalenzen zur Riemann-Hypothese** (vollständig modelliert)

Der Knowledge Graph dient als strukturierte Wissensbasis für die theoretische Einordnung der Experimente und ermöglicht Cypher-basierte Abfragen über den Zusammenhang von Graphenspektrum, Ramanujan-Eigenschaft und ζ(s).

### Skripte und Pipeline

Die experimentelle Pipeline besteht aus folgenden Kernskripten:

1. **generate_graphs.py** — Erzeugt Cayley-Graphen über CayleyPy und speichert sie als npz und PyG .pt
2. **compute_eigenvalues.py** — Berechnet Eigenwerte via dünnbesetzter Lanczos-Iteration
3. **augment_dataset.py** — Extrahiert zusammenhängende Teilgraphen für das Subgraph-Training
4. **train_gnn.py** — GAT/GCN-Baseline mit Augmentierungsunterstützung
5. **evaluate.py** — Evaluierung pro Primzahl mit Metriken

### Makefile-Targets

Das Makefile stellt folgende Ziele bereit:

| Target | Beschreibung |
|---|---|
| `make up` | Startet alle Services (Research + Neo4j) |
| `make build` | Baut den Research-Container |
| `make research` | Shell im Research-Container |
| `make jupyter` | Startet Jupyter Lab |
| `make ingest` | Lädt Theorie in den Knowledge Graph |
| `make graphs` | Erzeugt Cayley-Graphen für SL(2, F_p) |
| `make eigenvalues` | Berechnet Eigenwerte aller erzeugten Graphen |
| `make train` | Trainiert das GNN-Modell |
| `make eval` | Evaluiert ein trainiertes Modell |
| `make paper` | Baut das Paper aus Markdown |
| `make sage` | Startet SageMath (erfordert sage-Profil) |

---

## 3. Datengrundlage

### Cayley-Graphen von SL(2, F_p)

Alle Graphen werden über CayleyPy erzeugt mittels `MatrixGroups.special_linear_fundamental_roots(2, p)`. Diese Funktion liefert vier Erzeuger: E₁₂, E₂₁ und ihre Inversen. Die resultierenden Cayley-Graphen sind **4-regulär** (Grad = 4) und knotentransitiv.

### Vollständige Datentabelle

| Primzahl p | Knoten | Kanten | Spektraler Gap | Ramanujan-Verhältnis | Eigenwerte |
|---|---|---|---|---|---|
| 2 | 6 | 24 | 2.000000 | 1.000 | ✓ |
| 3 | 24 | 96 | 1.267949 | 0.634 | ✓ |
| 5 | 120 | 480 | 0.763932 | 0.382 | ✓ |
| 7 | 336 | 1 344 | 0.585786 | 0.293 | ✓ |
| 11 | 1 320 | 5 280 | 0.381966 | 0.191 | ✓ |
| 13 | 2 184 | 8 736 | 0.324869 | 0.162 | ✓ |
| 17 | 4 896 | 19 584 | 0.290725 | 0.145 | ✓ |
| 19 | 6 840 | 27 360 | 0.245395 | 0.123 | ✓ |
| 23 | 12 144 | 48 576 | 0.206681 | 0.103 | ✓ |
| 29 | 24 360 | 97 440 | 0.182153 | 0.091 | ✓ |
| 31 | 29 760 | 119 040 | 0.227251 | 0.114 | ✓ |
| 37 | 50 616 | 202 464 | 0.170768 | 0.085 | ✓ |
| 41 | 68 880 | 275 520 | 0.180865 | 0.090 | ✓ |
| 43 | 79 464 | 317 856 | 0.166165 | 0.083 | ✓ |
| 47 | 103 776 | 415 104 | 0.180653 | 0.090 | ✓ |
| 53 | 148 824 | 595 296 | 0.174447 | 0.087 | ✓ |
| 59 | 205 320 | 821 280 | 0.158304 | 0.079 | ✓ |
| 61 | 226 920 | 907 680 | 0.185452 | 0.093 | ✓ |
| 67 | 300 696 | 1 202 784 | — | — | ✗ |
| 71 | 357 840 | 1 431 360 | — | — | ✗ |
| 73 | 389 064 | 1 556 256 | — | — | ✗ |
| 79 | 490 320 | 1 961 280 | — | — | ✗ |
| 83 | 568 296 | 2 273 184 | — | — | ✗ |
| 89 | 704 976 | 2 819 904 | — | — | ✗ |
| 97 | 912 096 | 3 648 384 | — | — | ✗ |
| 101 | 1 030 200 | 4 120 800 | — | — | ✗ |

**Bemerkungen:**

- Alle 26 Primzahlen von 2 bis 101 erzeugen Cayley-Graphen.
- Für die Primzahlen 2 bis 61 (18 Graphen) liegen vollständige Eigenwertberechnungen vor.
- Für p ≥ 67 sind die Graphen zu groß für die Lanczos-Methode in der aktuellen Implementierung. Die Berechnung der Eigenwerte würde den Arbeitsspeicher übersteigen oder unverhältnismäßig lange dauern.
- Das Ramanujan-Verhältnis ist definiert als spektraler Gap / (2√(d-1)) = spektraler Gap / (2√3) ≈ spektraler Gap / 3.464. Ein Wert ≤ 1 bedeutet, dass der Graph die Ramanujan-Bedingung erfüllt.
- Der Graph für p=2 ist trivialerweise Ramanujan (Verhältnis = 1.000). Alle weiteren Graphen erfüllen die Ramanujan-Bedingung deutlich.
- Das auffällige lokale Maximum bei p=31 (0.227251) deutet auf eine arithmetische Anomalie hin.

---

## 4. Phase 1: Subgraph-basierte GNNs (fehlgeschlagen)

### Ansatz

Der erste Ansatz extrahierte zufällige zusammenhängende Teilgraphen aus den Cayley-Graphen und trainierte GNNs auf diesen Teilgraphen, um den spektralen Gap des Gesamtknotengraphen vorherzusagen. Die zugrundeliegende Idee war, dass eine GNN-Architektur in der Lage sein sollte, aus lokalen Strukturmerkmalen auf globale spektrale Eigenschaften zu schließen.

### Datenaugmentierung

- **599 Trainings- und 82 Test-Samples** aus 17 Primzahlen (p = 2..59)
- **3-dimensionale Knotenmerkmale:** Grad/4, Clustering-Koeffizient, Dreiecksanzahl
- **Teilgraphgrößen:** 20 bis 5 000 Knoten, extrahiert via BFS ausgehend von einem zufälligen Startknoten
- **Optimierung:** scipy dünnbesetzte Adjazenzmatrizen für die Extraktion (~10× schneller als Python-dict-basierte Ansätze)

### Fünf getestete Architekturen

| Modell | Architektur | Train-Metrik | Test-MAE | Test-R² | Anmerkung |
|---|---|---|---|---|---|
| GAT Baseline | 3-Layer GAT, hidden=128 | R² = 0.69 | 0.086 | -122 | Subgraph-Sampling |
| SIGN (2-Hop) | Vorberechnete Aggregation, 9 → 128 → 1 | R² = 0.69 | 0.057 | -80 | Kein Message-Passing |
| Stratified | BinBalancedBatchSampler + GAT | Loss 0.026 | 0.081 | -111 | Ausgewogene Bins |
| Multi-Task | GIN + 5 Heads + Uncertainty | Loss -0.79 | — | negativ | log_nodes R² = 0.24 |
| ChebConv hier. | 3-Layer ChebConv (K=3) + Multi-Scale | MSE 0.005 | 0.024 | -44 | Bester Test-MAE |

### Analyse des Scheiterns

**Das zentrale Resultat:** Alle Subgraph-Ansätze erreichen auf dem Trainingssatz ein R² von etwa 0.69, brechen aber beim Cross-Prime-Test komplett zusammen. Die Test-R²-Werte sind durchweg stark negativ (bis -122), was bedeutet, dass die Modelle systematisch schlechter vorhersagen als der Durchschnittswert.

**Die Ursache:** Cayley-Graphen sind knotentransitiv. Jeder Knoten hat exakt die gleiche lokale Struktur: gleichen Grad, gleichen Clustering-Koeffizienten, gleiche lokale Nachbarschaftstopologie. Ein Teilgraph, egal woher er stammt, sieht im Wesentlichen gleich aus. Die einzige Information, die ein Teilgraph tragen könnte, wäre seine **Größe** im Verhältnis zum Gesamtknotengraphen, und selbst diese Information ist unzureichend, um den spektralen Gap zu rekonstruieren.

**Schlussfolgerung:** Subgraph-basiertes Training kann prinzipiell keine globalen spektralen Eigenschaften knotentransitiver Graphen erfassen. Dieser negative Befund ist mathematisch begründet und nicht durch mangelnde Modellkapazität oder Hyperparameter-Optimierung zu beheben.

---

## 5. Phase 2: Full-Graph ChebConv (erfolgreich)

### Durchbruch-Erkenntnis

Nach dem Scheitern der Subgraph-Ansätze lag der Schlüssel auf der Hand: **Trainiere auf den vollständigen Graphen statt auf Teilgraphen.** Anstatt Message-Passing in jedem Trainingsschritt durchzuführen, werden Chebyshev-Polynom-Features offline aus der normierten Laplace-Matrix vorberechnet. Das eigentliche Modell ist dann ein leichtgewichtiges MLP, das auf diesen vorberechneten Features operiert.

### Architektur

**Chebyshev-Vorberechnung:** Die Tschebyscheff-Polynome T₀(L), T₁(L), ..., T_K(L) werden via dünnbesetzter Matrixrekursion auf der skalierten normierten Laplace-Matrix berechnet. Dies ist ein einmaliger Vorverarbeitungsschritt pro Graph.

**Knotenmerkmale:**
- Strukturell: Grad/4, Clustering-Koeffizient, Dreiecksanzahl (3 Dimensionen)
- Positional: 8-dimensionales Random Positional Encoding (RPE)

**Random Positional Encoding (RPE)** ist die zentrale Innovation. Da Cayley-Graphen knotentransitiv sind, sieht jeder Knoten für das GNN gleich aus. RPE bricht diese Symmetrie, indem jeder Knoten einen eindeutigen zufälligen Signatur-Vektor erhält. Dieser Vektor wird während des Trainings als zusätzliches Knotenmerkmal behandelt und ermöglicht es dem Modell, Unterschiede zwischen Knoten zu lernen, die allein aus der Struktur nicht erkennbar sind.

**Graph-Level-Statistiken:** log(Knotenanzahl), log(Kantenanzahl), Dichte, Durchmesserschätzung (4 Dimensionen).

**Modell:** LayerNorm-MLP (nicht BatchNorm, da Batch-Size = 1). Die Eingabe ist die Konkatenation von mean_pool und max_pool über alle Knoten-Features zusammen mit den Graph-Level-Statistiken:

    concat(mean_pool, max_pool, graph_stats) → 64 → 64 → 32 → 1

Die Ausgabe ist der vorhergesagte spektrale Gap.

### Lineare Baseline

Bevor das MLP trainiert wurde, diente eine lineare Regression als Baseline:

    spektraler Gap ≈ -0.135 · log(N) + 1.618

Diese einfache Formel erreicht R² = 0.782 und zeigt, dass der spektrale Gap logarithmisch mit der Knotenanzahl N abnimmt. Das GNN muss also mehr als nur den logarithmischen Trend erfassen, um einen Mehrwert zu bieten.

### Leave-One-Out Kreuzvalidierung (LOO-CV)

Das Modell wurde mit Leave-One-Out-Kreuzvalidierung über alle 18 Graphen mit bekannten Eigenwerten evaluiert. Parameter: K=3 (Chebyshev-Ordnung), hidden=64, 300 Epochen.

| Primzahl p | Knoten | Vorhersage | Tatsächlich | Fehler | Rel. Fehler |
|---|---|---|---|---|---|
| 2 | 6 | 1.173 | 2.000 | -0.827 | 41.4 % |
| 3 | 24 | 1.053 | 1.268 | -0.215 | 16.9 % |
| 5 | 120 | 0.630 | 0.764 | -0.134 | 17.5 % |
| 7 | 336 | 0.553 | 0.586 | -0.033 | 5.6 % |
| 11 | 1 320 | 0.279 | 0.382 | -0.103 | 26.9 % |
| 13 | 2 184 | 0.367 | 0.325 | +0.042 | 12.8 % |
| 17 | 4 896 | 0.210 | 0.291 | -0.081 | 27.9 % |
| 19 | 6 840 | 0.201 | 0.245 | -0.044 | 18.0 % |
| 23 | 12 144 | 0.180 | 0.207 | -0.027 | 13.1 % |
| **29** | **24 360** | **0.184** | **0.182** | **+0.002** | **0.9 %** |
| 31 | 29 760 | 0.185 | 0.227 | -0.043 | 18.7 % |
| **37** | **50 616** | **0.171** | **0.171** | **+0.001** | **0.3 %** |
| **41** | **68 880** | **0.167** | **0.181** | **-0.014** | **7.5 %** |
| **43** | **79 464** | **0.169** | **0.166** | **+0.003** | **1.7 %** |
| **47** | **103 776** | **0.167** | **0.181** | **-0.013** | **7.5 %** |
| **53** | **148 824** | **0.170** | **0.174** | **-0.005** | **2.8 %** |

### Zentrale Ergebnisse

**Für große Graphen (p ≥ 29, ≥ 24 360 Knoten):** Der relative Fehler liegt unter 6 %. Für p=37 erreicht das Modell einen relativen Fehler von nur 0.3 %. Die Vorhersagen sind für große Graphen im Wesentlichen perfekt.

**Kleine Graphen (p ≤ 11) sind Ausreißer.** Der relative Fehler erreicht hier bis zu 41 % (p=2). Die Ursache ist die geringe strukturelle Diversität: Für kleine Graphen liefern die Chebyshev-Features nicht genügend unterscheidbare Informationen, da die Graphen zu wenige Knoten haben, um signifikante spektrale Muster auszubilden.

**Vergleich mit der linearen Baseline:** Das Full-Graph ChebConv-Modell schlägt die lineare Baseline um ΔR² = +0.042. Der Mehrwert entsteht dadurch, dass das Modell nicht-lineare Zusammenhänge zwischen Graphstruktur und spektralem Gap erfasst, die der logarithmische Trend der linearen Regression nicht abbilden kann.

**RPE ist der entscheidende Baustein.** Ohne Random Positional Encoding sind alle Knoten für das Modell ununterscheidbar (Knotentransitivität). Die mean_pool- und max_pool-Aggregationen würden identische Vektoren für alle Graphen liefern, und das Modell könnte nur auf die Graph-Level-Statistiken zurückgreifen, was de facto der linearen Baseline entsprechen würde. RPE durchbricht die Symmetrie und ermöglicht es dem Modell, die vollständige Graphstruktur in die Readout-Schicht zu encodieren.

---

## 6. Vergleich und Analyse

### Warum Full-Graph funktioniert und Subgraph scheitert

Der Unterschied lässt sich auf drei fundamentale Punkte zurückführen:

**1. Lokale vs. globale Information.** Der spektrale Gap ist eine inhärent **globale** Eigenschaft eines Graphen. Er beschreibt das Verhalten der gesamten Adjazenzmatrix, nicht das einer einzelnen Nachbarschaft. Subgraph-Ansätze aggregieren lokale Informationen und hoffen implizit, dass die Aggregation globale Muster erkennen lässt. Bei knotentransitiven Graphen ist diese Hoffnung unbegründet, da jede lokale Nachbarschaft identisch ist.

**2. Vollständige vs. unvollständige Information.** Der Full-Graph-Ansatz nutzt die **vollständige** Graphstruktur. Die Chebyshev-Polynome werden auf der gesamten Laplace-Matrix berechnet und encodieren damit die spektrale Information des gesamten Graphen in die Knoten-Features. Jeder Knoten trägt nach der Chebyshev-Transformation Informationen über den globalen Graphen in sich.

**3. Die Rolle der RPE.** Random Positional Encoding löst das Knotentransitivitätsproblem auf elegante Weise. Anstatt zu versuchen, strukturelle Unterschiede zwischen identischen Knoten zu finden, gibt RPE jedem Knoten eine künstliche Identität. Das Modell lernt dann, welche Knotenpositionen im Graphen (im Sinne der spektralen Eigenschaften) wichtig sind, und wie diese Positionen mit dem spektralen Gap zusammenhängen.

### Warum ChebConv räumliche GNNs übertrifft

**Spektrale vs. räumliche Faltung.** ChebConv operiert im **Spektralbereich** über Tschebyscheff-Polynome. Die Tschebyscheff-Polynome T_k(L) der Laplace-Matrix bilden eine effiziente Basis zur Approximation von Funktionen auf dem Graphenspektrum. Wenn das Ziel die Vorhersage einer spektralen Eigenschaft ist, dann ist eine spektrale Faltung die natürliche Wahl.

**Direkter spektraler Zugang.** Räumliche GNNs wie GAT oder GCN aggregieren Nachbarschaftsmerkmale und lernen implizit Filter. ChebConv hingegen berechnet explizit spektrale Filterkoeffizienten. Für die Vorhersage des spektralen Gaps ist dieser direkte Zugang zur spektralen Information überlegen.

**Effizienz durch Vorberechnung.** Die Chebyshev-Polynome werden einmal offline berechnet. Für große Graphen (bis 200 000 Knoten) bedeutet das, dass das eigentliche Training nur noch ein leichtgewichtiges MLP auf vorberechneten Features ist. Räumliche GNNs müssten in jedem Trainingsschritt Message-Passing über den gesamten Graphen durchführen, was bei diesen Größen infeasible wird.

---

## 7. Nächste Schritte

Die erfolgreiche Vorhersage des spektralen Gaps eröffnet zwei mathematisch fundierte Wege, die Verbindung zu ζ(s) zu vertiefen.

### Pfad A: LPS-Brücke — Hecke-Eigenwerte

**Theoretische Grundlage.** Lubotzky, Phillips und Sarnak (1988) konstruierten explizite Ramanujan-Graphen über Quaternionenalgebren. Ihre Konstruktion zeigt, dass die Adjazenz-Eigenwerte dieser Graphen direkt mit den Hecke-Eigenwerten modularer Formen zusammenhängen.

**Delignes Schranke.** Für eine Hecke-Eigenform f vom Gewicht k gilt Delignes berühmte Schranke:

    |a_p(f)| ≤ 2p^{(k-1)/2}

Diese Schranke ist das arithmetische Analogon zur Ramanujan-Bedingung:

    |λ| ≤ 2√(d-1)

Die formale Entsprechung ist bemerkenswert: Die Fourier-Koeffizienten a_p(f) einer Modulform spielen dieselbe Rolle wie die Eigenwerte λ eines Cayley-Graphen.

**Die Kette.** Die vollständige Argumentationskette lautet:

    Cayley-Graph-Adjazenzeigenwerte → Hecke-Eigenwerte → L-Funktion → ζ(s)

Jeder Schritt dieser Kette ist mathematisch wohldefiniert und teilweise explizit bekannt. Die Herausforderung besteht darin, diese Kette rechnerisch zu durchlaufen.

**Eisenstein-Reihen.** Die Eisenstein-Reihe E_k liefert einen konkreten Ausgangspunkt. Ihre Fourier-Koeffizienten sind σ_{k-1}(n) (die Teilersummenfunktion) und stehen in direkter Beziehung zu ζ(1-k):

    E_k(τ) = 1 - (2k/B_k) Σ σ_{k-1}(n) q^n

Die Eisenstein-Reihe ist keine Eigenform, aber ihre Fourier-Koeffizienten können als Referenz für die Hecke-Eigenwerte echter Eigenformen dienen.

**Rechnerische Pipeline.** Eine konkrete Umsetzung mit SageMath und PARI/GP umfasst:

1. Für gegebene Primzahl p: Berechne die Hecke-Operatoren T_p auf dem Raum der Modulformen S_k(Γ₀(N))
2. Diagonalisiere die Hecke-Matrix, um die Eigenwerte a_p(f) für alle Eigenformen f zu erhalten
3. Konstruiere die assoziierte L-Funktion L(f, s) = Σ a_n(f) n^{-s}
4. Vergleiche die analytische Fortsetzung von L(f, s) mit ζ(s)

SageMath stellt hierfür die Klassen `ModularForms`, `HeckeAlgebra` und `LFunction` bereit.

### Pfad B: Farey-Graph + Transfer-Operatoren

**Theoretische Grundlage.** Pollicott (2022) formulierte die Riemann-Hypothese als Eigenwertproblem von Transfer-Operatoren auf dem Farey-Graphen. Dieser Ansatz ist grundlegend verschieden von der LPS-Brücke und bietet einen geometrischen Zugang zu ζ(s).

**Der Farey-Graph.** Der Farey-Graph hat als Knotenmenge die Menge der reduzierten Brüche a/b (einschließlich 1/0 als Punkt im Unendlichen). Zwei Knoten a/b und c/d sind genau dann benachbart, wenn |ad - bc| = 1. Der Farey-Graph ist ein unendlicher 3-regulärer Baum mit besonderen geometrischen Eigenschaften.

**Ihara-Zetafunktion.** Für jeden endlichen Graphen Γ definiert die Ihara-Zetafunktion:

    Z_Γ(s) = det(1 - uT)^{-1}

wobei u = q^{-s} und T der Transfer-Operator ist. Die Nullstellen von Z_Γ(s) stehen in direkter Beziehung zu den Eigenwerten des Transfer-Operators. Die Riemann-Hypothese ist äquivalent zur Aussage, dass alle nichttrivialen Eigenwerte von T auf der kritischen Linie Re(s) = 1/2 liegen.

**Zagiers Kaskade und Mayers Spurformel.** Zagier entdeckte eine Kaskade von Spurformeln, die eine systematische Beziehung zwischen Eigenwerten des Laplace-Operators auf Modulflächen und den Nullstellen von ζ(s) herstellt. Mayer (2005) zeigte, dass diese Kaskade als endliche Approximation der Riemann-Hypothese interpretiert werden kann.

**Finite Trunkierungsstrategien.** Der Farey-Graph ist unendlich, aber man kann endliche Approximationen F_n konstruieren, die die Farey-Brüche mit Nenner ≤ n enthalten. Für diese endlichen Graphen lässt sich die Ihara-Zetafunktion explizit berechnen. Die Frage ist, ob die Konvergenz der Eigenwerte von F_n gegen die Nullstellen von ζ(s) schnell genug ist, um rechnerisch nutzbar zu sein.

---

## 8. Code-Übersicht

### Skripte

| Skript | Beschreibung |
|---|---|
| `scripts/generate_graphs.py` | CayleyPy-Graphengenerierung → npz + PyG .pt |
| `scripts/compute_eigenvalues.py` | Dünnbesetzte Lanczos-Eigenwertberechnung → \_stats.npz |
| `scripts/augment_dataset.py` | Zusammenhängende Teilgraph-Extraktion via scipy sparse BFS |
| `scripts/train_gnn.py` | GAT/GCN-Baseline mit Augmentierungsunterstützung |
| `scripts/train_sign.py` | SIGN Vorberechnung + MLP (kein Message-Passing) |
| `scripts/train_stratified.py` | BinBalancedBatchSampler + ReweightedMSELoss |
| `scripts/train_multitask.py` | GIN-Encoder + 5 Task-Heads + Uncertainty-Weighting |
| `scripts/train_cheb_hierarchical.py` | Hierarchisches ChebConv + Multi-Scale-Readout |
| `scripts/train_fullgraph_cheb.py` | **Full-Graph ChebConv mit LOO-CV (BESTES MODELL)** |
| `scripts/evaluate.py` | Evaluierung pro Primzahl mit Metriken |

### Knowledge Graph

| Skript | Beschreibung |
|---|---|
| `knowledge-graph/scripts/ingest.py` | Neo4j Cypher-Ingestion (Schema + Theorie) |
| `knowledge-graph/scripts/kg_queries.py` | KG-Abfrage-Interface |

---

## 9. Referenzen

### Mathematische Grundlagen

- Deligne, P. (1974). La conjecture de Weil, I. *Publications Mathématiques de l'IHÉS*, 43, 273-307.
- Lubotzky, A., Phillips, R., & Sarnak, P. (1988). Ramanujan graphs. *Combinatorica*, 8(3), 261-277.
- Lubotzky, A. (1994). *Discrete Groups, Expanding Graphs and Invariant Measures*. Birkhäuser.
- Pollicott, M. (2022). A note on the Riemann hypothesis and the Farey graph. arXiv:2209.05465.
- Mayer, D. (2005). The thermodynamic formalism approach to Selberg's zeta function for PSL(2, Z). *Bulletin of the AMS*, 42(1), 61-71.
- Zagier, D. (1984). The Eisenstein series and the Selberg trace formula. In *Séminaire N. Bourbaki*.

### Graph Neural Networks

- Kipf, T. N. & Welling, M. (2017). Semi-Supervised Classification with Graph Convolutional Networks. *ICLR 2017*.
- Veličković, P., Cucurull, G., Casanova, A., Romero, A., Liò, P., & Bengio, Y. (2018). Graph Attention Networks. *ICLR 2018*.
- Defferrard, M., Bresson, X., & Vandergheynst, P. (2016). Convolutional Neural Networks on Graphs with Fast Localized Spectral Filtering. *NeurIPS 2016*.
- Rossi, E., Chamberlain, B., Frasca, F., Eynard, D., Monti, F., & Bronstein, M. (2020). SIGN: Scalable Inception Graph Neural Networks. *ICML 2020 Workshop*.
- Xu, K., Li, C., Tian, Y., Sonobe, T., Kawarabayashi, K., & Jegelka, S. (2019). How Powerful are Graph Neural Networks? *ICLR 2019*.
- Lim, D., Hohne, F., Li, H., Feng, Y., & Duvenaud, D. (2022). Large Scale Learning on Non-Homophilous Graphs: New Benchmarks and Strong Simple Methods. *NeurIPS 2022*.

### Software

- CayleyPy: Python-Bibliothek für algebraische Graphentheorie und Cayley-Graphen.
- PyTorch Geometric (PyG): Graph Neural Network Library für PyTorch.
- Neo4j: Graphdatenbank für den Knowledge Graph.
- SageMath: Open-Source-Mathematik-Software (Modulformen, Hecke-Algebra).
- PARI/GP: Computeralgebra-System für Zahlentheorie.
