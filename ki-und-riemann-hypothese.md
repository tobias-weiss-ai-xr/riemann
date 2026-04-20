# KI und die Riemann-Hypothese: Wo Maschinen auf die tiefste offene Frage der Mathematik treffen

> *Die Riemann-Hypothese ist seit 167 Jahren ungelöst. Aber KI hat begonnen, an den Rändern zu nagen — von neuronalen Netzen, die die Struktur von Nullstellen erkennen, bis hin zu formalisierten Beweisen in Lean, bei denen Terence Tao selbst Claude Code einsetzt. Dieser Artikel vertieft jeden konkreten KI-Ansatz.*

---

## Die Ausgangslage

Die Riemann-Hypothese (RH) besagt, dass alle nichttrivialen Nullstellen der Riemannschen Zeta-Funktion ζ(s) auf der kritischen Linie Re(s) = ½ liegen. 20 Billionen Nullstellen wurden verifiziert — alle auf der Linie. Aber das beweist nichts über die unendlich vielen, die noch unerreicht sind.

Die Frage ist nicht, ob KI die RH morgen beweist. Die Frage ist: **Wo kann KI konkret nützen?** Die Antwort überrascht — es gibt deutlich mehr Ansätze, als man erwarten würde.

---

## I. Der tiefste theoretische Ansatz: RH als Aussage über neuronale Netze

### Das Nyman-Beurling-Kriterium

Die Riemann-Hypothese hat über 20 bekannte äquivalente Formulierungen. Eine davon — das **Nyman-Beurling-Kriterium** — besagt, dass die RH genau dann gilt, wenn eine bestimmte Klasse von Funktionen in L²(0,1) dicht ist.

**Soufiane Hayou** (UC Berkeley, 2023, arXiv: 2309.09171) hat gezeigt, dass diese Funktionenklasse sich als **Einzelschicht-Neuronale Netze** auffassen lässt:

```
f(x) = Σ cᵢ · ρ(βᵢ / x)
```

wobei ρ die Bruchteil-Funktion ist und die Gewichte die Bedingung cᵀβ = 0 erfüllen.

Die RH ist äquivalent zur Aussage: **Die Klasse N_d dieser neuronalen Netze ist dicht in L²((0,1)ᵈ) für jedes d ≥ 2.**

Das ist bemerkenswert. Zum ersten Mal gibt es eine **direkte mathematische Verbindung** zwischen der Riemann-Hypothese und einer Optimierungsaufgabe über neuronale Netze. Hayou erweitert dies auf mehrdimensionale Netze und zeigt, dass die RH eine Dichteaussage über eine spezifische Architektur impliziert.

**Bedeutung:** Wenn man beweisen könnte, dass diese neuronale Netz-Klasse dicht ist — etwa durch Approximationstheorie oder konstruktive Verfahren — hätte man die RH bewiesen. Umgekehrt: Wenn ein Gegenbeispiel existiert (eine Funktion, die nicht approximiert werden kann), wäre die RH widerlegt.

**Limitation:** Die Äquivalenz allein löst nichts. Die Dichte zu beweisen ist genauso schwer wie die RH selbst. Aber sie öffnet einen **neuen Zugangsweg** — und die Approximationstheorie neuronaler Netze (Universal Approximation Theorem) ist ein Gebiet, in dem KI-Forschung extrem aktiv ist.

---

## II. Empirische ML-Ansätze: Nullstellen lesen lernen

### Transformer für die Nullstellenverteilung

**Om Shankar** (2024) trainierte eine Transformer-Architektur (PyTorch) zur Vorhersage der Verteilung von Nullstellenanzahlen auf konsekutiven Gram-Intervallen. Ergebnis: **Genauigkeit 0,998** für Sequenzen von 10 aufeinanderfolgenden Nullstellenanzahlen.

**Jennifer Kampe & Artem Vysogorets** (SDSU REU, 2018) verglichen SVR, MLP und RNN zur Approximation der imaginären Teile nichttrivialer Nullstellen. Mit 80.000 Beobachtungen und 50 Features (Werte der Hardy Z-Funktion an 21 Gram-Punkten) erreichten sie **>99% erklärte Varianz**.

### Widerspruchsmethodik: ML als Falsifikationsversuch

**Shianghau Wu** (2025, Mathematics 13(17), 2824) unternahm den bislang umfassendsten ML-basierten Falsifikationsversuch:

- **Random Forest Classifier**, **Naive Bayes**, **GANs**, **Mixture-Density VAEs**, und **SHAP Explainability** in einem einheitlichen Framework
- Trainiert auf Nullstellen auf der kritischen Linie, getestet auf Off-Line-Punkten
- MDN-VAE trainiert auf 10.000 Nullstellenabständen erzeugt synthetische Verteilungen, die mit echten Nullstellenabständen praktisch **ununterscheidbar** sind
- SHAP-Analyse bestätigt: Real- und Imaginärteil von ζ(s) dominieren die Klassifikation
- **Ergebnis:** Kein Hinweis auf Nullstellen abseits der kritischen Linie

### Was diese Arbeiten wirklich zeigen

Diese empirischen Studien demonstrieren, dass die Nullstellenstruktur hochgradig regulär ist — ML-Modelle lernen die Muster mühelos. Aber sie liefern **keine Beweise**. Ein ML-Modell, das Nullstellen vorhersagt, sagt nichts darüber aus, ob *alle* Nullstellen auf der Linie liegen. Es ist Kurvenanpassung, keine Mathematik.

---

## III. Random Matrix Theory: Die Brücke zwischen Physik und Zahlentheorie

### Die Montgomery-Odlyzko-Übereinstimmung

1973 bemerkte Hugh Montgomery, dass die Paarkorrelation der Riemann-Nullstellen exakt der Paarkorrelation der Eigenwerte großer zufälliger hermitescher Matrizen entspricht — der sogenannten **GUE** (Gaussian Unitary Ensemble) Verteilung.

Andrew Odlyzko verifizierte dies 1987 numerisch mit Milliarden von Nullstellen nahe der Nullstelle mit der imaginären Höhe 10²⁰. Die Übereinstimmung war verblüffend.

### Keating-Snaith: Momente aus zufälligen Matrizen

**Jon Keating & Nina Snaith** (2000, Commun. Math. Phys. 214, 57–89) gingen weiter: Sie berechneten die Momente charakteristischer Polynome von CUE-Matrizen (Circular Unitary Ensemble) und erhielten Vorhersagen für die Momente von |ζ(½ + it)|:

```
M_k(T) = (1/T) ∫₀ᵀ |ζ(½ + it)|²ᵏ dt ≈ c_k · (log T)^{k²}
```

mit der Keating-Snaith-Konstante:

```
c_β = G²(1 + β) / G(1 + 2β)
```

wobei G die Barnes G-Funktion ist. Diese Vorhersagen stimmen mit Selbergs Theorem und Odlyzkos Daten überein.

### RMT trifft Deep Learning

Hier wird es besonders interessant: **Jon Keating** arbeitet gleichzeitig an zwei Fronten:

- **RMT für die Riemann-Hypothese** — Momente, Paarkorrelation, Dichtevermutungen
- **RMT für Deep Learning** — Analyse der Loss-Landschaft neuronaler Netze

Mit Nick Baskerville (Sibylla AI) und Kollegen veröffentlichte Keating:

- *"Appearance of Random Matrix Theory in deep learning"* (Physica A, 2022) — Die Hessian-Matrix der Loss-Funktion neuronaler Netze zeigt **„banded structure"**, die GUE-Spektra ähnelt
- *"Universal characteristics of deep neural network loss surfaces from random matrix theory"* (J. Phys. A, 2022) — Kac-Rice-Formeln analysieren kritische Punkte

**Die Konsequenz:** Die gleiche mathematische Struktur (Zufallsmatrizen) beschreibt sowohl die Riemann-Nullstellen als auch die Optimierungslandschaft neuronaler Netze. Das bedeutet nicht, dass Deep Learning die RH löst — aber es bedeutet, dass Fortschritte im Verständnis der einen Seite die andere befruchten könnten.

---

## IV. Formalisierung: Die Riemann-Hypothese in Lean

### Die RH als Lean-Proposition

Die Riemann-Hypothese ist in **Mathlib** (der kollaborativen Mathematikbibliothek für Lean 4) als Proposition definiert:

```lean
/-- A formal statement of the Riemann hypothesis –
    constructing a term of this type is worth a million dollars. -/
def RiemannHypothesis : Prop :=
  ∀ (s : ℂ) (_ : riemannZeta s = 0)
      (_ : ¬∃ n : ℕ, s = -2 * (n + 1)) (_ : s ≠ 1),
    s.re = 1 / 2
```

Einen Term dieses Typs zu konstruieren, wäre ein Beweis der RH. Der Kommentar spricht Bände.

### Was bereits formalisiert ist

**David Loeffler & Michael Stoll** (2025, Annals of Formalized Mathematics) haben die Riemann-Zeta-Funktion umfassend formalisiert:

| Komponente | Status | Lean-Code |
|------------|--------|-----------|
| ζ(s) Definition | ✅ | `def riemannZeta := hurwitzZetaEven 0` |
| Analytische Fortsetzung | ✅ | `differentiableAt_riemannZeta` |
| Funktionale Gleichung | ✅ | `riemannZeta_one_sub` |
| Triviale Nullstellen | ✅ | `riemannZeta_neg_two_mul_nat_add_one` |
| Residuum bei s=1 | ✅ | `riemannZeta_residue_one` |
| ζ(2) = π²/6 | ✅ | explizit bewiesen |
| Nichttriviale Nullstellen sind diskret | ✅ | `isDiscrete_riemannZetaZeros` (2026!) |
| Dirichlet-Primzahlsatz | ✅ | Voll formalisiert |

### Was noch fehlt

| Lücke | Bedeutung für RH | Schwierigkeit |
|-------|-------------------|---------------|
| **Hadamard-Produktzerlegung** | Verbindet Nullstellenverteilung mit Wachstum | Hoch — braucht Weierstraß-Produkte |
| Nullstellenfreie Region | Grundlage für jeden analytischen PNT-Beweis | Hoch |
| Explizite Formel (von Mangoldt) | Verbindet Nullstellen mit Primzahlen | Sehr hoch |
| Residuensatz (allgemein) | Fundament für Konturintegration | Mittel-Hoch |
| Argumentprinzip | Zentrales Werkzeug | Mittel |
| Logarithmische Ableitung von ζ | Für explizite Formeln nötig | Mittel |
| N(T)-Zählfunktion | Nullstellen zählende Funktion | Hoch |

**Einschätzung:** Etwa **60–70%** des benötigten Formalismus existieren. Die größte einzelne Lücke ist der Hadamard-Zerlegungssatz.

### Der Primzahlsatz in Lean

Der Primzahlsatz wurde **fünfmal** in verschiedenen Systemen formalisiert. Das aktuellste Projekt: **PNT+** (Kontorovich, Tao et al., 2025–26) formalisiert den PNT über den **Wiener-Ikehara-Satz** in Lean. Die Roadmap:

1. ~~PNT via Wiener-Ikehara~~ ✅ (abgeschlossen)
2. PNT via Perron-Formel mit explizitem Fehlerterm (in Arbeit)
3. PNT mit klassischem exp(√log x)-Fehler via Hadamard + nullstellenfreie Region (Zukunft)

Schritt 3 würde die RH-benachbarte Mathematik formalisieren.

### Terence Tao und Claude Code

**März 2026** demonstrierte Terence Tao öffentlich die Nutzung von **Claude Code zur Formalisierung von Beweisen in Lean**:

> „Current models are now ready for primetime."
> „AI spart mehr Zeit als sie verschwendet."
> „AI lets me try crazier things."

Tao nutzt KI für Literatursuche, Code-Schreibung, Plots, Berechnungen und Testen von Ansätzen. Aber er warnt:

> „Nützliche Assistenten, aber keine Peers" — weniger hilfreich für tiefe originelle Einsichten.
> „KI kann polierte Argumente mit verstecktem schwachen Schritt erzeugen."

Seine Lösung: **Formale Verifikation mit Lean** — jeder Schritt wird vom Kernel geprüft.

---

## V. L-Funktionen und ML: Murmurations

### Murmuration: Ein neues Phänomen

2022 entdeckten **Lee, Oliver und Pozdnyakov** ein überraschendes Phänomen: Die Fourier-Koeffizienten elliptischer Kurven zeigen systematische **Schwingungsmuster** („Murmurations"), wenn man sie nach der Diskriminante ordnet.

### ML auf L-Funktionen

Mehrere Arbeitsgruppen nutzen ML, um Muster in L-Funktionen zu finden:

| Arbeit | Methode | Ergebnis |
|--------|---------|----------|
| **Bieri et al.** (2025, arXiv: 2502.10360) | PCA, LDA, NNs | Vorhersage der Vanishing-Ordnung rationaler L-Funktionen; Murmuration-ähnliche Muster entdeckt |
| **Pozdnyakov** (2024, arXiv: 2403.14631) | Flache interpretierbare NNs | Root-Number-Vorhersage lernt Mestre-Nagao + Murmurations |
| **He, Lee, Oliver** (2023, JSC) | NNs auf Euler-Faktoren | Vorhersage von analytischem Rang, Root-Number, Sha-Ordnung |
| **Saraeb** (2025, arXiv: 2504.19451) | LLMs (Qwen2.5-Math) + LightGBM | ≥93,9% Accuracy bei Dirichlet-Zeichen-Erkennung aus Nullstellen |

**Für die RH relevant:** Murmurations wurden bislang auf elliptischen L-Funktionen und Dirichlet-L-Funktionen untersucht — **nicht auf ζ(s) selbst**. Das ist eine offene Forschungslücke.

---

## VI. Die Hilbert-Pólya-Vermutung: Operator-Suche mit KI?

### Die Idee

Die Hilbert-Pólya-Vermutung (1914/1950er) schlägt vor: Wenn es einen **selbstadjungierten Operator** gibt, dessen Eigenwerte genau den imaginären Teilen der nichttrivialen Nullstellen von ζ(s) entsprechen, dann folgt die RH daraus — weil selbstadjungierte Operatoren reelle Eigenwerte haben.

### Neuere Konstruktionen

**Enderalp Yakaboylu** (2023–2024, arXiv: 2309.00405, 2408.15135) konstruierte einen expliziten Hamiltonian:

```
Ĥ = Ŝ · Ĥ_BK · Ŝ⁻¹
```

mit Ŝ = t^N̂ · e^(αx̂)/(1+e^(x̂)). Er zeigte:
- Die Eigenfunktionen verschwinden am Ursprung durch nichttriviale Riemann-Nullstellen
- **Realität der Eigenwerte** unter bestimmten Bedingungen

**Wenn der Operator selbstadjungiert ist → die RH folgt.**

### Connes' Spurformel

**Alain Connes** (1998/2026, arXiv: 2602.04022) zeigte, dass seine Spurformel auf Adele-Klassen **äquivalent zur RH** ist. Seine 2026er Übersicht diskutiert Momente, unitäre Matrizen, Spektraltheorie und die Katz-Sarnak-Dichtevermutung in einem einheitlichen Rahmen.

### Wo KI hier passen könnte

**Bisher hat niemand ML systematisch eingesetzt, um einen geeigneten Operator für die Hilbert-Pólya-Vermutung zu finden.** Das ist eine offene Forschungslücke:

- ML könnte im riesigen Raum möglicher Operatoren nach Kandidaten suchen
- Reinforcement Learning könnte Operatoren optimieren, deren Spektrum die Nullstellen approximiert
- Physic-Informed Neural Networks könnten spektroskopische Bedingungen einbetten

Die Hürde: Der Operatorraum ist kontinuierlich und unendlichdimensional. Aber das Problem hat eine **klar evaluierbare Zielfunktion** — „Wie gut stimmen die Eigenwerte mit den Nullstellen überein?" — was es prinzipiell für Optimierungsverfahren zugänglich macht.

---

## VII. Numerische Verifikation: Warum ML hier (noch) nicht hilft

### Der aktuelle Rekord

**Platt & Trudgian** (2021, Bulletin LMS): **12,36 Billionen Nullstellen** rigoros verifiziert — alle auf Re(s) = ½. Benötigt: 7,5 Millionen Core-Stunden auf Intel Xeon.

### Warum keine GPU/ML-Beschleunigung?

Der **Riemann-Siegel-Algorithmus** — die Standardmethode zur Nullstellenberechnung — ist inhärent **sequenziell**. Jeder Schritt hängt vom vorherigen ab. Das macht GPU-Parallelisierung schwierig und ML-Beschleunigung unbewiesen.

**Potenziale:**
- ML könnte **Gram-Punkt-Berechnungen** beschleunigen
- ML könnte „suspicious regions" identifizieren — Intervalle, in denen Nullstellen nahe beieinander liegen (close pairs)
- Aber: Rigorose Verifikation erfordert **Intervallarithmetik** — und die ist nicht mit ML-Vorhersagen kompatibel

---

## VIII. Graph Neuronale Netze für Zahlentheorie

### Bestehende Arbeiten

**Giannini et al.** (NeurIPS Workshop, 2023, arXiv: 2307.11688) wandten GNNs erstmals auf **Universalalgebra-Vermutungen** an — mit interpretierbaren neuronalen Schichten, die neue Vermutungen identifizierten.

**Barlag et al.** (2024/2026, arXiv: 2402.17805, 2603.05140) zeigten eine **exakte Korrespondenz** zwischen GNNs und konstant-tiefen arithmetischen Schaltkreisen über ℝ — relevant für alle arithmetischen Anwendungen.

### Für die RH

GNNs wurden **noch nie direkt auf RH-relevanten Strukturen** angewendet. Denkbare Ansätze:

- **Nullstellen-Abstands-Graphen** — Knoten = Nullstellen, Kanten = Abstandsverhältnisse
- **Primzahl-Adjazenz-Graphen** — Struktur der Primzahlverteilung
- **Cayley-Graphen** von (ℤ/Nℤ)* — algebraische Struktur, die mit Dirichlet-Zeichen verbunden ist

---

## IX. Die sechs konkreten KI-Pfade zur RH

Basierend auf der aktuellen Forschung gibt es sechs plausible Pfade, wie KI zur RH beitragen könnte:

### Pfad 1: Nyman-Beurling + Approximationstheorie

**Reifegrad: Theoretisch**

Die RH als Dichteaussage über neuronale Netze (Hayou 2023). Wenn die Approximationstheorie Fortschritte macht — etwa Beweise für Dichte unter bestimmten Architekturbeschränkungen — könnte dies auf den Nyman-Beurling-Raum übertragen werden.

### Pfad 2: Hilbert-Pólya + Operator-Optimierung

**Reifegrad: Spekulativ**

Reinforcement Learning oder evolutionäre Suche im Raum selbstadjungierter Operatoren, deren Spektrum die Riemann-Nullstellen approximiert. Konkrete Konstruktionen existieren (Yakaboylu 2023), aber die Selbstadjungiertheit ist ungelöst.

### Pfad 3: Formale Verifikation + TTRL

**Reifegrad: Praktisch (mittelfristig)**

AlphaProofs Test-Time Reinforcement Learning auf RH-benachbarte Sätze. Der Formalsierungsstand in Lean erreicht ~70% — Hadamard-Produkt und nullstellenfreie Region wären die nächsten Meilensteine. Tao nutzt bereits Claude Code + Lean.

### Pfad 4: RMT-Verstärkung durch Deep Learning

**Reifegrad: Mittel**

Keatings parallele Arbeit an RMT für ζ-Momente und RMT für Deep Learning schafft eine einzigartige Brücke. ML-gestützte Entdeckung neuer RMT-Zusammenhänge könnte zu stärkeren heuristischen Argumenten für die RH führen.

### Pfad 5: Murmuration auf ζ(s)

**Reifegrad: Offen**

Murmuration-Muster wurden für elliptische und Dirichlet-L-Funktionen gefunden, aber **nicht für ζ(s) selbst**. Ein ML-gestützter Scan der Fourier-Koeffizienten-Struktur von ζ könnte unerwartete Regularitäten aufdecken.

### Pfad 6: Numerische Beschleunigung + Anomalie-Erkennung

**Reifegrad: Praktisch (kurzfristig)**

ML-gestützte Identifikation von „suspicious regions" in der Nullstellenverteilung. Kein Beweis, aber ein effizienteres Frühwarnsystem für potenzielle Widerlegungen.

---

## X. Was Experten sagen

### Terence Tao (UCLA)

> „AI lets me try crazier things."

Tao nutzt KI aktiv, sieht sie aber als Assistenten, nicht als Peer. Die Warnung vor „polierten Argumenten mit verstecktem schwachen Schritt" ist zentral — weshalb er formale Verifikation in Lean als Korrektiv einsetzt.

### Alain Connes (IHÉS, Fields-Medaillist)

Connes' 2026er Übersicht (arXiv: 2602.04022) diskutiert die RH umfassend, einschließlich neuer numerischer Annäherungen seiner Spurformel. Keine direkten KI-Aussagen, aber sein Operator-Ansatz ist der am stärksten formalisierte Weg zur RH.

### Jon Keating (Oxford)

Keating steht einzigartig an der Schnittstelle von RMT für Zahlentheorie und RMT für Deep Learning. Seine Arbeit mit Sibylla AI zeigt, dass die Verbindungen zwischen beiden Welten real und produktiv sind.

---

## Fazit

Die Riemann-Hypothese wird nicht morgen von KI bewiesen. Aber die Landschaft hat sich in den letzten drei Jahren dramatisch verändert:

1. **Die RH ist als Lean-Proposition definiert** — ein Beweis wäre maschinenverifizierbar
2. **Terence Tao nutzt Claude Code** — die produktive KI-Integration in die Zahlentheorie hat begonnen
3. **Hayou hat RH direkt mit neuronalen Netzen verknüpft** — der Nyman-Beurling-Ansatz ist mathematisch rigoros
4. **AlphaProof hat IMO-Niveau erreicht** — formale Beweise in Lean durch RL sind machbar
5. **Die Hilbert-Pólya-Operator-Suche bleibt unberührt von ML** — die größte offene Forschungslücke

Die wahrscheinlichste Rolle von KI: nicht als alleiniger Beweiser, sondern als **Katalysator** — der Mathematiker befähigt, schneller zu explorieren, Formales zu verifizieren, und Muster zu erkennen, die dem menschlichen Auge entgehen.

Die Million Dollar wartet. Aber zum ersten Mal seit 167 Jahren gibt es Werkzeuge, die das Warten erträglicher machen.

---

## Quellen

- Hayou, S. „On the Connection Between Riemann Hypothesis and a Special Class of Neural Networks." arXiv:2309.09171 (2023).
- Wu, S. „Empirical Investigation of the Riemann Hypothesis Using Machine Learning." Mathematics 13(17), 2824 (2025). DOI: 10.3390/math13172824
- Shanker, O. „Generative AI predicts the Riemann zeta zero distribution." TechRxiv (2024).
- Kampe, J. & Vysogorets, A. „Predicting Zeros of the Riemann Zeta Function Using Machine Learning." SDSU REU (2018).
- Keating, J.P. & Snaith, N.C. „Random Matrix Theory and ζ(½+it)." Commun. Math. Phys. 214, 57–89 (2000).
- Keating, J.P. et al. „Appearance of Random Matrix Theory in deep learning." Physica A 590, 126742 (2022).
- Rodgers, B. & Tao, T. „The De Bruijn-Newman Constant is Non-Negative." Forum of Mathematics, Pi 8, e6 (2020). arXiv:1801.05914.
- Connes, A. „The Riemann Hypothesis: Past, Present and a Letter Through Time." arXiv:2602.04022 (2026).
- Yakaboylu, E. „Hamiltonian for the Hilbert-Pólya Conjecture." arXiv:2309.00405 (2023).
- Loeffler, D. & Stoll, M. „Formalizing zeta and L-functions in Lean." Annals of Formalized Mathematics 1, afm:15328 (2025). arXiv:2503.00959.
- Platt, D. & Trudgian, T. „The Riemann hypothesis is true up to 3·10¹²." Bulletin LMS 53, 792–797 (2021). arXiv:2004.09765.
- Bieri, C. et al. „Machine learning the vanishing order of rational L-functions." arXiv:2502.10360 (2025).
- Pozdnyakov, A. „Predicting Root Numbers with Neural Networks." arXiv:2403.14631 (2024).
- He, Y., Lee, K.H. & Oliver, R. „Machine learning invariants of arithmetic curves." J. Symbolic Computation 115, 478–491 (2023).
- Giannini, G. et al. „Interpretable Graph Networks Formulate Universal Algebra Conjectures." arXiv:2307.11688 (2023).
- Barlag, C. et al. „Graph Neural Networks and Arithmetic Circuits." arXiv:2402.17805 (2024).
- PNT+ Project: github.com/AlexKontorovich/PrimeNumberTheoremAnd
- Tao, T. bei IPAM „Accelerating Math and Theoretical Physics with AI" (März 2026).
