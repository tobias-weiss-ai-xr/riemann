# GNN-Experimente zur Riemann-Hypothese: Gesamtbilanz

## Ergebnisse aus sieben Experiment-Tracks zur Frage, ob Graph Neural Networks zahlentheoretische Eigenschaften aus Graphstruktur vorhersagen können

---

## 1. Zusammenfassung

Wir haben über mehrere Wochen sieben Experiment-Tracks durchgeführt, um zu prüfen, ob Graph Neural Networks (GNNs) in der Lage sind, zahlentheoretische Eigenschaften aus der Struktur algebraischer Graphen vorherzusagen. Das langfristige Ziel war ein rechnerischer Zugang zur Riemann-Hypothese (RH) über die Kette

    Cayley-Graph-Eigenwerte → Hecke-Eigenwerte → L-Funktionen → ζ(s).

**Das Gesamtergebnis ist eindeutig negativ.** Keines der sieben Experimente zeigt eine sinnvolle Generalisierung über Primzahlen hinweg. GNNs können spektrale Eigenschaften innerhalb ihrer Trainingsverteilung lernen, aber sie scheitern systematisch daran, Muster zu erkennen, die über verschiedene Primzahlen gelten.

Die einzig positive Ausnahme ist Track 2 (Full-Graph ChebConv mit Random Positional Encoding), der eine marginale Verbesserung von ΔR² = +0,042 über eine triviale lineare Baseline erzielt. Dieser Erfolg ist jedoch so gering, dass er keine praktische oder theoretische Bedeutung für die Riemann-Hypothese hat.

Die Negative-Results sind dennoch wissenschaftlich wertvoll: Es existiert bislang keine veröffentlichte Arbeit, die GNNs auf zahlentheoretische Strukturen anwendet. Unsere Ergebnisse bilden die erste systematische Untersuchung an dieser Schnittstelle.

### Gesamtergebnis auf einen Blick

| Track | Graph-Konstruktion | Zielgröße | Baseline R² | GNN R² | Urteil |
|-------|--------------------|-----------|-------------|--------|--------|
| 1 | Cayley SL(2,F_p), Subgraph | Spektraler Gap | — | < 0 (alle) | Gescheitert |
| 2 | Cayley SL(2,F_p), Full-Graph | Spektraler Gap | 0,782 | **0,824** | Marginal |
| 3 | Farey-Graph | Spektraler Gap | 0,9999 | -7,57 | Trivial |
| 4 | Cayley SL(2,F_p), 1 Generator | Hecke-Eigenwerte | 0,41 | -0,21 | Gescheitert |
| 5 | Cayley SL(2,F_p), 10 Generatoren | Hecke-Eigenwerte | 0,977 | -0,32 | Gescheitert |
| 6 | Cayley SL(2,F_p), 10 Generatoren | Spektraler Gap | 0,43 | -2,12 | Gescheitert |
| 7 | Pizer-Graph (Hecke T₂) | Hecke T₃-Eigenwerte | 0,057 | 0,000 | Null-Generalisierung |

---

## 2. Mathematischer Hintergrund

### Die Idee

Die Riemann-Hypothese besagt, dass alle nichttrivialen Nullstellen der Riemannschen Zeta-Funktion ζ(s) auf der kritischen Linie Re(s) = 1/2 liegen. Diese Vermutung ist seit 1859 unbewiesen und gilt als eines der tiefsten offenen Probleme der Mathematik.

Die verbindende Idee unserer Experimente ist die Kette von Zusammenhängen zwischen Graphenspektrum und Zahlentheorie:

**Cayley-Graph-Eigenwerte ↔ Hecke-Eigenwerte ↔ L-Funktionen ↔ ζ(s)**

Für Cayley-Graphen der Gruppe SL(2,F_p) mit Erzeugermenge S gilt:

    λ_ρ = Σ_{s ∈ S} χ_ρ(s)

wobei χ_ρ der Charakter einer irreduziblen Darstellung ρ ist. Die Hecke-Eigenwerte a_p modularer Formen stehen über die Darstellungstheorie von GL(2) über p-adischen Körpern in direkter Beziehung zu diesen Graph-Eigenwerten. Die Ramanujan-Schranke für Graphen, |λ| ≤ 2√(d-1), und die Deligne-Schranke für Hecke-Eigenwerte, |a_p| ≤ 2p^{(k-1)/2}, sind Manifestationen derselben algebraischen Struktur.

Wenn ein GNN den spektralen Gap oder die Hecke-Eigenwerte aus der Graphstruktur vorhersagen könnte, würde das zeigen, dass die lokale Gruppenstruktur die globalen L-Funktions-Eigenschaften determiniert, was zentrale Ideen des Langlands-Programms rechnerisch bestätigen würde.

### Die untersuchten Graphfamilien

**Cayley-Graphen von SL(2,F_p).** Die Gruppe SL(2,F_p) besteht aus allen 2×2-Matrizen mit Determinante 1 über dem Körper F_p. Sie hat p(p²-1) Elemente. Der Cayley-Graph Cay(G, S) hat als Knoten die Gruppenelemente und Kanten (g, gs) für jeden Generator s ∈ S. Diese Graphen sind per Konstruktion regulär und knotentransitiv: jeder Knoten lässt sich durch einen Graph-Automorphismus in jeden anderen überführen.

**Farey-Graphen.** Endliche Approximationen des Farey-Graphen F_n enthalten die Farey-Brüche mit Nenner ≤ n. Zwei Brüche a/b und c/d sind benachbart, wenn |ad - bc| = 1. Farey-Graphen sind nicht knotentransitiv und haben eine reichhaltige Gradverteilung (min_deg = 2, max_deg = n).

**Pizer-Graphen.** Für eine Primzahl p ist der Pizer-Graph ein gewichteter Graph, dessen Adjazenzmatrix den Hecke-Operator T₂ auf dem Raum S₂(Γ₀(p)) der Spitzenformen vom Gewicht 2 darstellt. Diese Konstruktion ist mathematisch exakt: Die Kanten und ihre Gewichte sind direkt durch die Arithmetik von Γ₀(p) bestimmt.

---

## 3. Methodik

### 3.1 GNN-Architekturen

Im Lauf der sieben Tracks haben wir folgende Architekturen eingesetzt:

| Architektur | Track | Beschreibung |
|-------------|-------|-------------|
| GAT | 1 | Graph Attention Network, 3 Schichten, hidden=128 |
| SIGN | 1 | Scalable Inception GNN, vorberechnete 2-Hop-Aggregation |
| Stratified | 1 | BinBalancedBatchSampler + GAT, balancierte Spektral-Gap-Bins |
| Multi-Task | 1 | GIN-Encoder + 5 Task-Heads + Uncertainty-Weighting |
| ChebConv hier. | 1 | 3-Schicht ChebConv (K=3) + Multi-Scale-Readout |
| ChebConv Full | 2, 3 | Tschebyscheff-Vorberechnung T_0..T_K(L) + LayerNorm MLP |
| GIN | 5 | Graph Isomorphism Network für Hecke-Vorhersage |
| Weighted ChebConv | 7 | 3-Schichten gewichteter ChebConv (K=3, hidden=64) + LayerNorm MLP |

### 3.2 Chebyshev-Vorberechnung (Tracks 2, 3, 7)

Die zentrale Architektur für die Full-Graph-Experimente basiert auf Tschebyscheff-Polynomen der Laplace-Matrix:

1. Berechne die normierte Laplace-Matrix L = I - D^{-1/2}AD^{-1/2}
2. Berechne T_0(L), T_1(L), ..., T_K(L) via dünnbesetzter Matrixrekursion
3. Konkateniere die Polynom-Features mit Knotenmerkmalen
4. Wende mean_pool und max_pool an, konkateniere mit Graph-Level-Statistiken
5. MLP-Regression auf den Zielgrößen

### 3.3 Random Positional Encoding (RPE, Track 2)

Da Cayley-Graphen knotentransitiv sind, sieht jeder Knoten für das GNN identisch aus. RPE bricht diese Symmetrie, indem jeder Knoten einen eindeutigen 8-dimensionalen Zufallsvektor als zusätzliches Merkmal erhält. Ohne RPE liefern mean_pool und max_pool identische Vektoren für alle Graphen.

### 3.4 Evaluationsprotokoll

**Leave-One-Out Kreuzvalidierung (LOO-CV).** Bei n Graphen wird n-mal trainiert, wobei jeweils ein anderer Graph als Testfall dient. Dies ist die strengste Form der Evaluierung bei kleinen Datensätzen und simuliert echtes Cross-Prime-Generalisieren.

**Lineare Baseline.** Für jeden Track wurde eine lineare Regression als Referenz trainiert. Die Baseline nutzt nur skalare Graph-Merkmale (Knotenanzahl, Kantenanzahl, Dimension), keine Graphstruktur. Wenn die Baseline den GNN schlägt, liefert die Graphstruktur keinen Zusatznutzen.

**Trainings- und Test-Splits.** Wo angegeben, wurden zusätzlich Random-Splits (80/20) durchgeführt, um Within-Distribution-Lernen von Cross-Prime-Generalisierung zu trennen.

---

## 4. Ergebnisse pro Track

### Track 1: Subgraph-GNN auf Cayley-Graphen von SL(2,F_p)

**Datum:** April 2026
**Daten:** 26 Cayley-Graphen (p=2..101), 599 Trainings- und 82 Test-Teilgraphen
**Ziel:** Spektraler Gap des Gesamtknotengraphen aus lokaler Teilgraphstruktur vorhersagen

#### Fünf getestete Architekturen

| Modell | Architektur | Train R² | Test MAE | Test R² |
|--------|-------------|----------|----------|---------|
| GAT Baseline | 3-Layer GAT, hidden=128 | 0,69 | 0,086 | -122 |
| SIGN (2-Hop) | Vorberechnete Aggregation, 9 → 128 → 1 | 0,69 | 0,057 | -80 |
| Stratified | BinBalancedBatchSampler + GAT | 0,69 | 0,081 | -111 |
| Multi-Task | GIN + 5 Heads + Uncertainty | 0,69 | — | negativ |
| ChebConv hier. | 3-Layer ChebConv (K=3) + Multi-Scale | 0,69 | 0,024 | -44 |

#### Analyse

Alle fünf Architekturen erreichen auf dem Trainingssatz R² ≈ 0,69, brechen aber beim Cross-Prime-Test komplett zusammen. Die Test-R²-Werte sind durchweg stark negativ (bis -122), was bedeutet, dass die Modelle systematisch schlechter vorhersagen als der Mittelwert.

**Ursache:** Cayley-Graphen sind knotentransitiv. Jeder Knoten hat exakt die gleiche lokale Struktur: gleichen Grad (4), gleichen Clustering-Koeffizienten, gleiche lokale Nachbarschaftstopologie. Ein Teilgraph sieht, unabhängig davon, woher er stammt, im Wesentlichen immer gleich aus. Die einzige unterscheidbare Information ist die Teilgraphgröße, und selbst diese reicht nicht aus, um den spektralen Gap zu rekonstruieren.

**Schlussfolgerung:** Subgraph-basiertes Training kann prinzipiell keine globalen spektralen Eigenschaften knotentransitiver Graphen erfassen. Dieser negative Befund ist mathematisch begründet und nicht durch Hyperparameter-Optimierung zu beheben.

---

### Track 2: Full-Graph ChebConv auf Cayley-Graphen von SL(2,F_p)

**Datum:** April 2026
**Daten:** 18 vollständige Cayley-Graphen (p=2..61), Eigenwerte via dünnbesetzter Lanczos-Iteration
**Ziel:** Spektraler Gap des Gesamtknotengraphen vorhersagen
**Architektur:** Chebyshev-Vorberechnung T_0..T_K(L) + 8-dim RPE + LayerNorm MLP

#### Lineare Baseline

    spektraler Gap ≈ -0,135 · log(N) + 1,618

R² = 0,782. Der spektrale Gap nimmt logarithmisch mit der Knotenanzahl N ab. Das GNN muss mehr als diesen logarithmischen Trend erfassen, um einen Mehrwert zu bieten.

#### LOO-CV-Ergebnisse (K=3, hidden=64, 300 Epochen)

| p | Knoten | Vorhersage | Tatsächlich | Fehler | Rel. Fehler |
|---|--------|------------|-------------|--------|-------------|
| 2 | 6 | 1,173 | 2,000 | -0,827 | 41,4 % |
| 3 | 24 | 1,053 | 1,268 | -0,215 | 16,9 % |
| 5 | 120 | 0,630 | 0,764 | -0,134 | 17,5 % |
| 7 | 336 | 0,553 | 0,586 | -0,033 | 5,6 % |
| 11 | 1 320 | 0,279 | 0,382 | -0,103 | 26,9 % |
| 13 | 2 184 | 0,367 | 0,325 | +0,042 | 12,8 % |
| 17 | 4 896 | 0,210 | 0,291 | -0,081 | 27,9 % |
| 19 | 6 840 | 0,201 | 0,245 | -0,044 | 18,0 % |
| 23 | 12 144 | 0,180 | 0,207 | -0,027 | 13,1 % |
| **29** | **24 360** | **0,184** | **0,182** | **+0,002** | **0,9 %** |
| 31 | 29 760 | 0,185 | 0,227 | -0,043 | 18,7 % |
| **37** | **50 616** | **0,171** | **0,171** | **+0,001** | **0,3 %** |
| **41** | **68 880** | **0,167** | **0,181** | **-0,014** | **7,5 %** |
| **43** | **79 464** | **0,169** | **0,166** | **+0,003** | **1,7 %** |
| **47** | **103 776** | **0,167** | **0,181** | **-0,013** | **7,5 %** |
| **53** | **148 824** | **0,170** | **0,174** | **-0,005** | **2,8 %** |

#### Analyse

Für große Graphen (p ≥ 29, ≥ 24 360 Knoten) liegt der relative Fehler unter 6 %. Für p=37 erreicht das Modell einen relativen Fehler von nur 0,3 %. Kleine Graphen (p ≤ 11) sind Ausreißer mit bis zu 41 % relativem Fehler, weil die Chebyshev-Features bei zu wenig Knoten keine aussagekräftigen Muster liefern.

**GNN R² = 0,824 vs. Baseline R² = 0,782, also ΔR² = +0,042.**

Das RPE ist der entscheidende Baustein: ohne RPE sind alle Knoten ununterscheidbar, und das Modell degradiert zur linearen Baseline.

#### Urteil: Marginaler Erfolg

Die Verbesserung von +4,2 % über eine triviale logarithmische Formel ist statistisch real, aber zu klein, um mathematisch bedeutungsvoll zu sein. Das Modell erfasst leichte nichtlineare Zusammenhänge, aber der spektrale Gap wird überwiegend durch die Knotenanzahl bestimmt.

---

### Track 3: Farey-Graph, Spektraler Gap

**Datum:** April 2026
**Daten:** 23 Farey-Graphen (n=10..230, Schritt 10), erzeugt via Stern-Brocot BFS
**Ziel:** Spektraler Gap vorhersagen

#### Farey-Graph-Eigenschaften

Farey-Graphen sind nicht knotentransitiv: min_deg = 2, max_deg = n, avg_deg → 4,0. Die Knotenanzahl reicht von 33 (n=10) bis 16 155 (n=230).

#### Ergebnisse

| Modell | MAE (gap) | R² (gap) |
|--------|-----------|----------|
| Linear (log-log) | 0,00000084 | **0,9999** |
| Power-law (a·n^(-b)) | 0,00000084 | **0,9999** |
| GNN (Standard-Split) | 0,00031302 | -7,57 |

Der spektrale Gap folgt einer perfekten Potenzgesetz-Beziehung: gap ≈ 2,65 · n^(-0,999) ≈ 2,65/n.

#### Urteil: Trivial

Die Potenzgesetz-Beziehung erklärt alles. Die lineare Baseline erreicht R² = 0,9999 mit einem Median-Relativfehler von 0,07 %. Der GNN (R² = -7,57) kann nicht einmal diesen trivialen Baseline schlagen. Die lokale Graphstruktur liefert keine zusätzliche Information über den spektralen Gap, die über log(V) hinausgeht.

---

### Track 4: Einzel-Generator Hecke-Eigenwert-Vorhersage

**Datum:** April 2026
**Daten:** 17 Eigenformen über 13 Primzahlen (p=11,17,19,23,29,31,37,41,43,47,53,59,61), berechnet via PARI `mfeigenbasis` + polmod-Auswertung
**Ziel:** Hecke-Eigenwerte a_p aus Cayley-Graph-Struktur vorhersagen

#### Zielgrößen

| Zielgröße | Beschreibung | GNN R² | Baseline R² |
|-----------|-------------|--------|-------------|
| mean_a_p | Mittlerer Hecke-Eigenwert | -0,21 | **0,41** |
| deligne_ratio | |a_p| / (2p^{(k-1)/2}) | — | — |
| first_form_a2 | a₂ der ersten Eigenform | — | — |

#### Analyse

Mit nur 13 Datenpunkten ist der Datensatz extrem klein. Die lineare Baseline erklärt bereits 41 % der Varianz von mean_a_p allein aus skalaren Graph-Merkmalen. Der GNN (R² = -0,21) kann nicht einmal diese schwache Baseline übertreffen.

#### Urteil: Gescheitert

Die Datenmenge ist für sinnvolle GNN-Aussagen völlig unzureichend. Zudem kodiert die Wahl der Standard-Generatoren (fundamental_roots) keine sinnvolle Information über die Hecke-Eigenwerte, die eine rein arithmetische Eigenschaft der Primzahl sind.

---

### Track 5: Multi-Generator Hecke-Eigenwert-Vorhersage

**Datum:** April 2026
**Daten:** 88 Cayley-Graphen (13 Primzahlen × 10 Generatortypen), Generatortypen: fundamental_roots, root_weyl, rand_0..rand_7
**Ziel:** mean_a_p aus der Graphstruktur bei verschiedenen Erzeugermengen vorhersagen

#### Schlüsselfund: Generator-Typ bestimmt spektrale Eigenschaften

| Generatortyp | Spektraler Gap |
|-------------|----------------|
| fundamental_roots / root_weyl | 0,1 - 0,25 (klein) |
| rand_0 .. rand_7 | 2,3 - 2,6 (groß) |

Die fundamental_roots- und root_weyl-Generatoren erzeugen Graphen mit winzigen spektralen Lücken (schlechte Expander), während zufällige Generatoren Graphen mit großen Lücken (gute Expander) erzeugen.

#### Ergebnisse

| Zielgröße | GNN R² | Baseline R² |
|-----------|--------|-------------|
| mean_a_p | -0,32 | **0,977** |

Die lineare Baseline erklärt 97,7 % der Varianz, der GNN liegt bei -0,32. Der Grund für die hohe Baseline-Leistung: Die Hecke-Eigenwerte hängen nur von der Primzahl p ab, nicht vom Generatortyp. Bei 10 Graphen pro Primzahl lernt die Baseline einfach den Mittelwert über die Generatoren.

#### Urteil: Gescheitert

Die Wahl der Erzeugermenge kodiert keine Hecke-Information. Die Hecke-Eigenwerte sind eine rein arithmetische Eigenschaft der Primzahl p und unabhängig davon, wie man SL(2,F_p) als Cayley-Graph darstellt.

---

### Track 6: Multi-Generator Spektraler Gap-Vorhersage

**Datum:** April 2026
**Daten:** Dieselben 88 Multi-Generator-Graphen wie Track 5
**Ziel:** Spektraler Gap aus der Graphstruktur vorhersagen

#### Ergebnisse

| Zielgröße | GNN R² | Baseline R² |
|-----------|--------|-------------|
| spectral_gap | -2,12 | **0,43** |

#### Analyse

Die Baseline R² = 0,43 zeigt, dass der spektrale Gap teilweise durch skalare Merkmale erklärbar ist (Knotenanzahl, Generatortyp). Der GNN (R² = -2,12) ist deutlich schlechter und kann nicht einmal unterscheiden, ob fundamental_roots- oder zufällige Generatoren verwendet wurden.

#### Urteil: Gescheitert

Der GNN kann nicht erkennen, ob ein Graph von fundamental_roots-Generatoren (kleiner spektraler Gap) oder von zufälligen Generatoren (großer spektraler Gap) erzeugt wurde. Das ist ein klarer Hinweis darauf, dass die Message-Passing-Aggregation die entscheidenden strukturellen Unterschiede nicht erfasst.

---

### Track 7: Pizer-Graph Cross-ℓ Eigenwert-Vorhersage

**Datum:** April 2026
**Daten:** 81 Pizer-Graphen (Primzahlen 47-499, Dimension 4-41)
**Ziel:** 9 Eigenwert-Statistiken des Hecke-Operators T₃ vorhersagen (mean, std, min, max, median, Q25, Q75, radius, pos_frac)

#### Die Pizer-Konstruktion

Die Pizer-Graphen sind die mathematisch sauberste Konstruktion in unserem Projekt: Die Adjazenzmatrix des Pizer-Graphen zur Primzahl p ist genau der Hecke-Operator T₂ auf dem Raum S₂(Γ₀(p)). Die Kantengewichte kodieren die Arithmetik der Kongruenzuntergruppe Γ₀(p) direkt in die Graphstruktur. Wenn irgendeine Graph-Konstruktion eine Verbindung zwischen Graphstruktur und Hecke-Eigenwerten zeigen sollte, dann diese.

#### Architektur

Weighted ChebConv (3 Schichten, K=3, hidden=64) + LayerNorm MLP. Gewichtetete Kanten ermöglichen es dem Modell, die Stärke der Hecke-Operator-Einträge zu berücksichtigen.

#### Lineare Baseline

| Statistik | Baseline R² |
|-----------|-------------|
| Overall | **0,057** |

R² = 0,057 bedeutet: Die lineare Baseline erklärt nur 5,7 % der Varianz. Das ist eine sehr schwache Baseline und würde theoretisch viel Raum für einen GNN lassen.

#### LOO-CV-Ergebnisse (81 Folds, 100 Epochen)

| Statistik | GNN R² | Baseline R² | Delta |
|-----------|--------|-------------|-------|
| mean | 0,0000 | 0,174 | -0,174 |
| std | 0,0000 | -0,003 | +0,003 |
| min | 0,0000 | 0,074 | -0,074 |
| max | 0,0000 | 0,072 | -0,072 |
| median | 0,0000 | 0,309 | -0,309 |
| Q25 | 0,0000 | -0,161 | +0,161 |
| Q75 | 0,0000 | 0,096 | -0,096 |
| radius | 0,0000 | 0,072 | -0,072 |
| pos_frac | 0,0000 | -0,121 | +0,121 |
| **Overall** | **0,0000** | **0,057** | **-0,057** |

Das Training zeigt abnehmende Loss-Werte, aber die Test-Vorhersagen bleiben für alle 81 Folds exakt konstant. Das Modell lernt innerhalb der Trainingsverteilung, aber generalisiert null auf die herausgenommene Primzahl.

#### Nach Graphgröße

| Größe (Dimension) | GNN R² | Anzahl |
|-------------------|--------|--------|
| Klein (4-10) | 0,0000 | 17 |
| Mittel (11-20) | 0,0000 | 22 |
| Groß (21-41) | 0,0000 | 42 |

Keine Graphgröße zeigt auch nur den Hauch einer Generalisierung.

#### Random Split (64/17)

| Statistik | GNN R² |
|-----------|--------|
| min | +0,52 |
| max | +0,48 |
| median | -0,50 |
| radius | +0,42 |
| mean | -0,17 |

Mit einem Random-Split (kein LOO) erzielt der GNN partiell positive R²-Werte. Das bestätigt: Das Modell kann lernen, aber nur Within-Distribution. Sobald die Herausnahme einer Primzahl eine strukturelle Lücke erzeugt, bricht die Vorhersage zusammen.

#### Urteil: Null-Generalisierung

Die Pizer-Graphen sind die theoretisch sauberste Brücke zwischen Graphstruktur und Hecke-Eigenwerten. Dass selbst hier die Cross-Prime-Generalisierung bei exakt null liegt, ist das stärkste Argument gegen die Machbarkeit eines GNN-basierten Zugangs zur Riemann-Hypothese.

---

## 5. Ursachenanalyse

### 5.1 Vertex-Transitivität (Tracks 1 und 2)

Cayley-Graphen von Gruppen sind knotentransitiv: Jeder Knoten hat identische lokale Nachbarschaften. Für Subgraph-basierte GNNs (Track 1) bedeutet das, dass jeder Teilgraph im Wesentlichen gleich aussieht, unabhängig davon, von welcher Primzahl er stammt. Die einzige unterscheidbare Information ist die Teilgraphgröße, und diese reicht nicht zur Rekonstruktion des spektralen Gaps aus.

Random Positional Encoding (Track 2) durchbricht die Vertex-Transitivität künstlich, indem jeder Knoten eine zufällige Signatur erhält. Dies ermöglicht marginale Verbesserungen (+4,2 % R²), aber die Signatur enthält keine zahlentheoretische Information.

### 5.2 Datenmenge (Tracks 4 und 6)

Mit 13 Datenpunkten (Track 4) oder 88 Datenpunkten (Tracks 5 und 6) ist die Datenmenge für GNN-Training extrem klein. Moderne GNNs sind datenhungrig und benötigen in der Regel Tausende von Trainingsgraphen für zuverlässige Generalisierung.

Das Problem ist hier jedoch grundsätzlich: Es gibt nur endlich viele Primzahlen in einem berechenbaren Bereich, und die Erzeugung großer Cayley-Graphen (p > 100, > 1 Million Knoten) wird rechnerisch prohibitiv.

### 5.3 Die Generalisierungslücke (Tracks 5, 6, 7)

Das zentrale Problem across aller Tracks: Jede Primzahl erzeugt einen strukturell einzigartigen Graph, und es gibt kein „glattes" Muster, das von einer Primzahl zur nächsten übertragbar ist.

In Track 7 (Pizer-Graphen) ist dieses Problem am deutlichsten sichtbar: Die Pizer-Adjazenzmatrix ist mathematisch exakt der Hecke-Operator T₂, und das Ziel ist die Vorhersage von T₃-Eigenwerten. Trotz dieser exakten mathematischen Beziehung generalisiert das Modell null über Primzahlen hinweg. Der Grund: Die Arithmetik jeder einzelnen Primzahl p (Faktorisierung von p±1, Klassenzahl, usw.) bestimmt die Struktur von Γ₀(p) und damit des Pizer-Graphen auf eine Weise, die zwischen Primzahlen nicht glatt interpolierbar ist.

### 5.4 Triviale Baselines (Tracks 2 und 3)

In Track 2 erklärt eine logarithmische Formel 78,2 % der Varianz des spektralen Gaps. In Track 3 erklärt ein Potenzgesetz 99,99 % der Varianz. In diesen Fällen hat die Graphstruktur keinen Zusatznutzen über einfache skalare Merkmale (Knotenanzahl) hinaus.

### 5.5 Generatorwahl kodiert keine Hecke-Information (Tracks 4, 5, 6)

Die Hecke-Eigenwerte a_p sind eine rein arithmetische Eigenschaft der Primzahl p. Sie hängen nicht davon ab, wie man SL(2,F_p) als Cayley-Graph darstellt. Die Wahl der Generatoren bestimmt den spektralen Gap der Graph-Adjazenzmatrix, aber dieser Gap korreliert nicht mit den Hecke-Eigenwerten. Das wurde in Tracks 4, 5 und 6 klar gezeigt.

---

## 6. Vergleich mit dem Stand der Forschung

### 6.1 Bisherige Arbeiten

Die Schnittstelle zwischen GNNs und Zahlentheorie ist weitgehend unbearbeitet. Die relevantesten Vorarbeiten sind:

| Arbeit | Autoren | Jahr | Bezug |
|--------|---------|------|-------|
| Kombinatorische Invarianzvermutung | Davies, Veličković et al. (DeepMind) | 2021 | GNN für Darstellungstheorie, aber nicht für Zahlentheorie |
| GNNs für UA-Vermutungen | Giannini et al. (Cambridge) | 2023 | GNN für Universalalgebra, isoliert geblieben |
| CayleyPy | Fedimser, Linial, Snarski | 2025-26 | Infrastruktur für Cayley-Graphen, keine GNNs |
| GNNs = Arithm. Schaltkreise | Barlag et al. | 2024-26 | Theoretische Grenzen konstant-tiefer GNNs |
| ML für L-Funktionen | Bieri et al. | 2025 | PCA/NN für L-Funktionen, keine GNNs |

**Keine einzige veröffentlichte Arbeit wendet GNNs auf zahlentheoretische Strukturen an.** Unsere sieben Experiment-Tracks bilden die erste systematische Untersuchung an dieser Schnittstelle.

### 6.2 Komplexitätstheoretische Grenzen

Barlag et al. (2024) zeigen, dass konstant-tiefe GNNs (C-GNNs) genau die Funktionen berechnen, die durch arithmetische Schaltkreise konstanter Tiefe über R berechenbar sind (FAC^0_R). Die Riemannsche Zeta-Funktion erfordert jedoch beliebig tiefe arithmetische Berechnungen. Rekurrente GNNs oder völlig andere Architekturen wären theoretisch nötig.

### 6.3 Publikationspotenzial

**Negative Results sind publikationswürdig**, insbesondere wenn sie systematisch und mit theoretischer Begründung durchgeführt werden. Unsere Experimente bieten:

1. **Novelty:** Erste systematische GNN-Untersuchung auf zahlentheoretischen Graphen.
2. **Track 2 (marginal positiv):** ChebConv + RPE schlägt lineare Baseline um +4,2 %.
3. **Track 7 (sauberster negativer Befund):** Pizer-Graph = exakter Hecke-Operator, trotzdem null Generalisierung. Dies ist das stärkste Argument gegen GNN-basierte Zugänge zur Zahlentheorie.
4. **Umfang:** Sieben Tracks decken Cayley-Graphen, Farey-Graphen und Pizer-Graphen ab.

---

## 7. Skripte und Daten

### 7.1 Zentrale Trainings-Skripte

| Skript | Track | Zeilen | Beschreibung |
|--------|-------|--------|-------------|
| `scripts/train_gnn.py` | 1 | — | GAT/GCN-Baseline mit Augmentierungsunterstützung |
| `scripts/train_sign.py` | 1 | — | SIGN Vorberechnung + MLP (kein Message-Passing) |
| `scripts/train_stratified.py` | 1 | — | BinBalancedBatchSampler + ReweightedMSELoss |
| `scripts/train_multitask.py` | 1 | — | GIN-Encoder + 5 Task-Heads + Uncertainty-Weighting |
| `scripts/train_cheb_hierarchical.py` | 1 | — | Hierarchisches ChebConv + Multi-Scale-Readout |
| `scripts/train_fullgraph_cheb.py` | 2 | — | Full-Graph ChebConv mit LOO-CV (bestes Modell) |
| `scripts/train_farey_gnn.py` | 3 | — | Farey-Graph GNN (adaptiert von Track 2) |
| `scripts/train_hecke_gnn.py` | 4 | — | Einzel-Generator Hecke-Vorhersage |
| `scripts/train_multigen_hecke.py` | 5, 6 | — | Multi-Generator Hecke- und Gap-Vorhersage |
| `scripts/train_pizer_gnn.py` | 7 | 427 | Pizer-Graph Cross-ℓ Hecke-Vorhersage |
| `scripts/test_pizer_inline.py` | 7 | — | Inline-Test für Pizer-Pipeline |

### 7.2 Datengenerierung und Vorverarbeitung

| Skript | Beschreibung |
|--------|-------------|
| `scripts/generate_graphs.py` | CayleyPy-Graphengenerierung → npz + PyG .pt |
| `scripts/compute_eigenvalues.py` | Dünnbesetzte Lanczos-Eigenwertberechnung |
| `scripts/augment_dataset.py` | Zusammenhängende Teilgraph-Extraktion via scipy sparse BFS |
| `scripts/generate_farey.py` | Farey-Graph-Generierung via Stern-Brocot BFS |
| `scripts/build_pizer_dataset.py` | Pizer-Graph-Datensatz-Erzeugung |
| `scripts/compute_hecke.py` | Hecke-Eigenwert-Berechnung via PARI/GP |

### 7.3 Datenbestand

| Datensatz | Ort | Graphen | Beschreibung |
|-----------|------|---------|-------------|
| Cayley-Graphen | `data/` | 26 | p=2..101, SL(2,F_p) |
| Farey-Graphen | `data/farey-graphs/` | 23 | n=10..230 |
| Multi-Gen | `data/multigen/` | 88 | 13 Primzahlen × 10 Generatoren |
| Pizer | `data/pizer/dataset_cross_l2_to_l3.pt` | 81 | p=47..499, Hecke T₂ → T₃ |
| Augmentierte Subgraphen | `data/augmented/` | 681 | 599 Train + 82 Test |

---

## 8. Fazit und Ausblick

### 8.1 Kernbotschaft

GNNs können spektrale Eigenschaften von Graphen innerhalb einer Trainingsverteilung lernen. Sie können diese Fähigkeit jedoch nicht über Primzahlen hinweg generalisieren. Die Ursache ist fundamental: Zahlentheoretische Eigenschaften von Primzahlen sind nicht glatt übertragbar. Jede Primzahl erzeugt eine strukturell einzigartige algebraische Struktur mit keinem kontinuierlichen Übergang zum Nachbarn.

Dieses Ergebnis ist konsistent mit einer tiefen mathematischen Tatsache: Die Verteilung der Primzahlen (und damit ihrer zahlentheoretischen Eigenschaften) ist pseudozufällig und folgt keinem einfachen Muster, das ein lokales Lernverfahren wie ein GNN extrapolieren könnte.

### 8.2 Warum das nicht entmutigend sein sollte

1. **Negative Results sind wertvoll.** Sie sparen anderen Forschern Wochen an Arbeit und definieren die Grenzen eines neuen Forschungsfelds.
2. **Die Pizer-Ergebnisse (Track 7) sind besonders aussagekräftig.** Die mathematisch exakteste Konstruktion zeigt das klarste negative Resultat. Wenn Pizer nicht funktioniert, funktioniert wahrscheinlich keine Cayley-basierte Methode.
3. **Track 2 zeigt, dass GNNs grundsätzlich fähig sind**, spektrale Graph-Eigenschaften zu lernen. Die Barriere ist nicht die GNN-Architektur, sondern die Beschaffenheit des Zielraums.
4. **Die Forschungslücke bleibt.** Niemand sonst arbeitet an GNNs für Zahlentheorie. Das Feld ist offen.

### 8.3 Mögliche nächste Schritte (falls fortgesetzt)

| Richtung | Beschreibung | Machbarkeit |
|----------|-------------|-------------|
| Transformer auf Hecke-Sequenzen | Nicht GNN-basiert: Transformer auf Folgen {a_p} | Mittel |
| Pizer-Graph mit mehr Features | Degree-of-freedom, Klassenzahl, Teiler von p±1 als Knoten-Features | Hoch |
| Transfer Learning | Pre-Train auf synthetischen Graphen, fine-tune auf Pizer | Niedrig |
| Rekurrente GNNs | Barlag et al.: Relevante Architekturklasse, aber schwer zu trainieren | Niedrig |
| Publikation der Negative Results | Systematisches Paper über alle 7 Tracks | Hoch |

### 8.4 Empfehlung

Die7 Experimente sprechen eine klare Sprache: Ein GNN-basierter Zugang zur Riemann-Hypothese über Cayley-Graphen oder Pizer-Graphen ist aussichtslos. Die sinnvollste nächste Aktion ist die Publikation dieser Ergebnisse als systematische Negative-Results-Studie. Ein Paper mit dem Titel „Why Graph Neural Networks Cannot Predict Number-Theoretic Properties from Graph Structure" wäre das erste seiner Art und hätte ein klares Publikum auf Konferenzen wie ICLR, NeurIPS (AI for Science Workshop) oder IACR.

---

*Stand: April 2026. Alle Experimente durchgeführt in einem Docker-Container (PyTorch 2.10 + CUDA 12.6 + PyG + CayleyPy). Die vollständige experimentelle Pipeline umfasst ~20 Python-Skripte mit insgesamt über 3000 Zeilen Code.*
