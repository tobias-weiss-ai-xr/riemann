# Wenn Maschinen Algorithmen erfinden — und warum P vs. NP trotzdem ungelöst bleibt

> *Von AlphaTensor bis AlphaEvolve: Wie KI neue Algorithmen entdeckt, formale Beweise auf Olympiad-Niveau führt — und warum das Millennium-Problem P-vs-NP davon trotzdem unberührt bleibt.*

---

## Einleitung

Im Oktober 2022 veröffentlichte Google DeepMind einen Algorithmus für die Matrixmultiplikation, der zum ersten Mal seit 1969 — seit Strassens Durchbruch — die obere Schranke für 4×4-Matrizen verbesserte. Der Algorithmus wurde nicht von einem Mathematiker entdeckt, sondern von einem Reinforcement-Learning-Agenten namens **AlphaTensor**.

Innerhalb von drei Jahren folgten: neue Sortieralgorithmen (**AlphaDev**), verbesserte Lösungen für das Cap-Set-Problem (**FunSearch**), IMO-Silbermedaillen-Niveau bei formalen Beweisen (**AlphaProof**), und produktive Optimierungen in Googles Rechenzentren (**AlphaEvolve**).

Die Frage drängt sich auf: Wenn KI Algorithmen erfinden und Mathematik auf Wettkampfniveau beweisen kann — könnte sie auch **P-vs-NP** lösen und damit ein Million-Dollar-Problem der Clay Foundation knacken?

Die Antwort ist komplexer, als sie scheint.

---

## Die Durchbruchserie: KI als Algorithmus-Erfinder

### AlphaTensor — Die erste KI-Entdeckung in der Algorithmentheorie

**Oktober 2022 | Nature 610, 47–53**

AlphaTensor formuliert die Suche nach Matrixmultiplikations-Algorithmen als ein Spiel: das *TensorGame*. Die Matrixmultiplikation zweier n×n-Matrizen kann als Tensor 𝒯_n dargestellt werden. Ein effizienter Algorithmus entspricht einer Rang-R-Zerlegung dieses Tensors — je niedriger der Rang, desto weniger Multiplikationen werden benötigt.

Das System basiert auf AlphaZero (dem Schach-/Go-Programm) und nutzt Deep Reinforcement Learning mit Monte-Carlo-Baumsuche (MCTS). Der Aktionsraum ist riesig: >10¹² mögliche Züge für die meisten interessanten Fälle — deutlich mehr als beim Schach (~10⁴⁰) oder Go (~10¹⁷⁰).

**Die Ergebnisse:**

| Problem | Bisheriger bester Rang | AlphaTensor | Verbesserung |
|---------|------------------------|-------------|--------------|
| 4×4 Matrizen (ℤ₂) | 49 (Strassen²) | **47** | Erste Verbesserung seit 1969 |
| 4×5×5 Matrizen | 80 | **76** | −5% |
| 5×5 Matrizen | 98 | **96** | −2% |

AlphaTensor entdeckte über **14.000 nicht-äquivalente Faktorisierungen** für den 4×4-Tensor — ein Zeichen dafür, dass der Raum effizienter Algorithmen deutlich größer ist, als bisher angenommen.

### AlphaDev — KI-entdeckte Sortieralgorithmen in der Standardbibliothek

**Juni 2023 | Nature 618, 257–263**

AlphaDev wendet dieselbe RL-Methode auf Assembly-Level-Sortieralgorithmen an. Der Agent entdeckte Routinen für Sequenzen der Länge 3–5, die weniger Instruktionen benötigen als die bisher besten bekannten Algorithmen.

- **70% Speedup** für kurze Sequenzen (3–5 Elemente)
- Die Algorithmen wurden in die **LLVM libc++ Standardbibliothek** aufgenommen — das erste Mal, dass ein KI-entdeckter Algorithmus Teil einer Haupt-C++-Standardbibliothek wurde

### FunSearch — Evolutionäre Suche im Programmbereich

**Dezember 2023 | Nature**

FunSearch (*Function Space Search*) kombiniert ein Large Language Model (Codey, basierend auf PaLM 2) mit einem evolutionären Algorithmus:

1. Das LLM generiert Programm-Mutationen als Python-Code
2. Ein Evaluator prüft Korrektheit und bewertet Qualität
3. Die besten Programme dienen als Kontext für die nächste Generation

**Cap-Set-Problem:** FunSearch fand eine Cap-Set-Konstruktion der Größe **512** für Dimension 8 (bisheriger Bestwert: 496) — die größte Verbesserung seit 20 Jahren. Die neue asymptotische untere Schranke stieg von 2.2180 auf **2.2184**.

**Online Bin Packing:** Verbesserung um ~5,3% gegenüber den bisher besten Heuristiken.

Was FunSearch von AlphaTensor unterscheidet: Es sucht nicht nur *innerhalb* einer formalen Sprache (Tensorzerlegungen, Assembly), sondern erfindet *neue Prioritätsfunktionen* — kreative Komponenten, die vorher nicht existierten.

### AlphaEvolve — Produktive Optimierung bei Google

**Mai 2025 | DeepMind White Paper**

AlphaEvolve kombiniert Gemini Flash (breite Exploration) und Gemini Pro (tiefe Analyse) mit automatisierten Evaluatoren und wird **produktiv bei Google** eingesetzt:

- **0,7% der weltweiten Google-Compute-Ressourcen** werden kontinuierlich zurückgewonnen (Borg Data Center Scheduling)
- **23% Speedup** eines kritischen Matrixmultiplikations-Kernels in der Gemini-Training-Pipeline
- **32,5% Speedup** für FlashAttention-Kernel
- Neue untere Schranke für das Kissing-Number-Problem in 11 Dimensionen: **593**
- 4×4 komplexe Matrizen: **48 Skalarmultiplikationen** (verbessert Strassen)

AlphaEvolve wurde auf über 50 offene mathematische Probleme getestet: in ~75% der Fälle wurde der State-of-the-Art wiedergefunden, in ~20% verbessert.

---

## Formale Beweise: Von der IMO zur Forschung

### AlphaProof — Silbermedaille bei der Internationalen Mathematik-Olympiade

**Juli 2024 | Nature 651, 607–613 (2026)**

AlphaProof ist der wohl bedeutendste Durchbruch im automatischen Theorembeweisen:

- **3-Milliarden-Parameter** Transformer, trainiert mit AlphaZero-inspiriertem Reinforcement Learning
- Beweise werden in **Lean 4** geführt — jeder Beweis wird vom Lean-Kernel verifiziert (garantierte Korrektheit)
- Training: ~300 Milliarden Tokens Pretraining → ~300.000 Zustand-Taktik-Paare aus Mathlib → RL auf ~80 Millionen autoformalisierten Problemen
- **~80.000 TPU-Tage** Rechenzeit für das RL-Training

**IMO 2024 Ergebnis: 28 von 42 Punkten** (Silbermedaille)

| Problem | Typ | Ergebnis |
|---------|-----|----------|
| Problem 1 | Algebra | ✅ AlphaProof (7/7) |
| Problem 2 | Algebra | ✅ AlphaProof (7/7) |
| Problem 4 | Geometrie | ✅ AlphaGeometry 2 (7/7, in 19 Sekunden) |
| Problem 5 | Zahlentheorie | ✅ AlphaProof (7/7) |
| Problem 6 | Kombinatorik | ❌ (nur 5 von 609 Teilnehmern lösten es) |

Problem 6 — das schwerste der IMO 2024 — wurde von AlphaProof **gelöst**. Nur 5 menschliche Teilnehmer schafften es ebenfalls.

Die Schlüsseltechnologie: **Test-Time Reinforcement Learning (TTRL)**. Für schwierige Probleme generiert das System Millionen von Varianten und trainiert gezielt darauf — eine Art „tiefe Anpassung" an das konkrete Problem.

### Gemini Deep Think & Aletheia — Der nächste Schritt

**2025–2026**

Google DeepMinds Gemini Deep Think erreichte **Goldmedaillen-Niveau** bei der IMO (Juli 2025) und beim ICPC (September 2025).

**Aletheia** (Februar 2026) ist ein Mathematik-Forschungs-Agent:

- 90% auf IMO-ProofBench Advanced
- **4 offene Probleme** aus Erdős' Problem-Datenbank autonom gelöst (aus 700 evaluierten)
- **Feng26**: Erste vollständig autonome KI-Mathematik-Arbeit (Eigenweights in arithmetischer Geometrie)
- 18 Forschungsprobleme gelöst, darunter eine decade-old Vermutung in der Online-Submodular-Optimierung

Aletheia definiert eine **Taxonomie für KI-Mathematik** mit 5 Stufen:

| Stufe | Beschreibung | Aktueller Stand |
|-------|-------------|-----------------|
| Level 0 | Reproduktion bekannter Resultate | ✅ |
| Level 1 | Lösung von Wettkampfproblemen (IMO, Putnam) | ✅ |
| Level 2 | Assistierte Lösung offener Forschungsprobleme | ✅ (4 Erdős-Probleme) |
| Level 3 | Größere Fortschritte („Major Advance") | ❌ |
| Level 4 | Durchbrüche („Landmark Breakthrough") | ❌ |

Die Stufen 3 und 4 sind **bewusst leer gelassen**. Die Autoren machen keine Anmaßung, in absehbarer Zeit fundamentale Durchbrüche zu erzielen.

---

## P-vs-NP: Warum KI (noch) nicht reicht

### Was ist P-vs-NP?

Die Frage, ob **P = NP**, ist das bekannteste offene Problem der theoretischen Informatik:

- **P**: Die Klasse aller Probleme, die von einem Computer **effizient** (in polynomieller Zeit) gelöst werden können
- **NP**: Die Klasse aller Probleme, bei denen eine gegebene Lösung **effizient überprüft** werden kann

P-vs-NP fragt: *Ist jedes Problem, dessen Lösung sich effizient überprüfen lässt, auch effizient lösbar?*

Die überwältigende Mehrheit der Experten glaubt: **P ≠ NP**. Aber niemand kann es beweisen. Der Beweis würde bedeuten, dass es für viele wichtige Probleme (Reisenverkäuferproblem, Faktorisierung, Protein-Faltung) grundsätzlich keine effizienten Algorithmen gibt.

### Warum die bisherigen KI-Durchbrüche nicht ausreichen

Jeder der bisherigen KI-Durchbrüche hat eine **strukturelle Begrenzung**, die ihn für P-vs-NP untauglich macht:

| System | Was es kann | Warum es P-vs-NP nicht löst |
|--------|------------|---------------------------|
| **AlphaTensor** | Findet neue Tensorzerlegungen | Arbeitet in einem formalen Suchraum mit effizienter Evaluation — P-vs-NP hat keine effiziente Evaluation |
| **FunSearch** | Findet neue Prioritätsfunktionen | Generiert Heuristiken, keine formalen Beweise. Das FunSearch-Papier selbst stellt fest, dass es „keinen Grund gibt zu glauben, dass FunSearch bei P-vs-NP helfen könnte" |
| **AlphaProof** | Formale Beweise auf IMO-Niveau | IMO-Probleme sind für Forschungsprobleme der Komplexitätstheorie trivial. P-vs-NP ist **viele Größenordnungen schwerer** |
| **AlphaEvolve** | Optimiert reale Systeme | Heuristische Optimierung — kein formaler Beweis |
| **Aletheia** | Löst offene Forschungsprobleme | Level 2 (assistiert), nicht Level 3/4 (autonomer Durchbruch) |

### Die fundamentale Barriere

P-vs-NP erfordert einen **formalen Unmöglichkeitsbeweis** — die Demonstration, dass *kein* polynomieller Algorithmus für ein NP-vollständiges Problem existiert. Das ist strukturell anders als:

- **Algorithmus finden** (obere Schranke) → „Hier ist ein Algorithmus, der funktioniert"
- **Konstruktion verbessern** (untere Schranke) → „Hier ist eine größere Cap-Set"
- **Wettkampfproblem lösen** → „Hier ist ein Beweis für einen Satz, von dem wir wissen, dass er beweisbar ist"

P-vs-NP erfordert: „Hier ist ein Beweis, dass *alle möglichen* Algorithmen einer bestimmten Klasse nicht ausreichen" — eine **universelle negative Aussage** über unendlich viele mögliche Algorithmen.

### Was Experten sagen

**Scott Aaronson** (UT Austin), einer der prominentesten Komplexitätstheoretiker:

> „The history of complexity theory suggests that any proof of P≠NP would need to be something fundamentally different from anything we've seen before."

In seinem Aufsatz „Five Worlds of AI" (2023, mit Boaz Barak) argumentiert Aaronson, dass selbst in den optimistischsten KI-Szenarien ein P≠NP-Beweis unwahrscheinlich ist, weil er eine *qualitativ neue Beweistechnik* erfordert — nicht brute-force Suche oder Mustererkennung.

**Avi Wigderson** (IAS, Turing Award 2021):

KI ist ein mächtiges Werkzeug für Mathematiker, besonders für Autoformalisierung und Beweisassistenz. Aber ein KI-Beweis von P≠NP würde ein „qualitativ neues Verständnis von Berechnung" erfordern, das über Mustererkennung hinausgeht.

**Ryan Williams** (MIT), der mit seiner ACC⁰-Separation (2011) einen der größten Fortschritte der letzten Jahrzehnte in der Komplexitätstheorie erzielte:

Die entscheidenden Durchbrüche kommen von „conceptual leaps", die nicht aus Daten extrahiert werden können. Er nutzt keine ML-Methoden.

### Die drei potenziellen KI-Pfade zu P-vs-NP

Trotz der Barriere gibt es drei plausible Pfade, wie KI **beitragen** könnte:

#### 1. Autoformalisierung

Die Formalisierung komplexer Komplexitätsbeweise in Lean 4 / Coq. AlphaProof hat gezeigt, dass Autoformalisierung machbar ist (~1 Million informelle Probleme → 80 Millionen formale Lean-Probleme). Wenn die Komplexitätstheorie-Community ihre Beweise formalisiert, könnte KI helfen, **Lücken zu finden** und **neue Beweisstrategien** zu explorieren.

#### 2. Beweisassistenz mit TTRL

Test-Time Reinforcement Learning — die Schlüsseltechnologie von AlphaProof — könnte auf Forschungsniveau skaliert werden. Statt IMO-Probleme könnte ein ähnliches System auf offene Probleme der Komplexitätstheorie trainiert werden. Die Hürde: Es gibt keine 1 Million „einfache" Komplexitätsprobleme zum Vortraining.

#### 3. Algorithmische Neuheit

Wenn P = NP (was fast niemand erwartet), müsste ein polynomieller Algorithmus für ein NP-vollständiges Problem gefunden werden. Genau hier sind KI-Systeme wie AlphaTensor und FunSearch stark: Sie finden Algorithmen, die Menschen nie probieren würden. Aber selbst wenn KI einen überraschend effizienten Algorithmus fände, wäre das ein empirischer Befund, kein formaler Beweis.

---

## Chronologie: Die KI-Algorithmus-Revolution

| Datum | System | Durchbruch | Venue |
|-------|--------|-----------|-------|
| Okt 2022 | AlphaTensor | Erste RL-basierte Matrixmult.-Algorithmen | Nature |
| Jun 2023 | AlphaDev | Neue Assembly-Sortierroutinen | Nature |
| Dez 2023 | FunSearch | Cap-Set n=8: 496 → 512 | Nature |
| Jan 2024 | AlphaGeometry | 25/30 IMO-Geometrie-Probleme | Nature |
| Jul 2024 | AlphaProof + AG2 | IMO 2024: 28/42 (Silber) | Blog / Nature |
| Mai 2025 | AlphaEvolve | Produktive Optimierung bei Google | White Paper |
| Jul 2025 | Gemini Deep Think | IMO Gold-Niveau | Blog |
| Aug 2025 | Goedel-Prover-V2 | Open-Source ATP SOTA (8B > 671B) | arXiv |
| Sep 2025 | Gemini Deep Think | ICPC Gold-Niveau | Blog |
| Feb 2026 | Aletheia | Autonome Mathematik-Forschung | arXiv |
| Mär 2026 | Algorithmist | Beweisbare Algorithmensynthese | arXiv |

---

## Fazit

Die KI-Algorithmus-Revolution ist real und beeindruckend. Innerhalb von vier Jahren hat KI gezeigt, dass sie:

- **Neue Algorithmen erfinden** kann (AlphaTensor, AlphaDev)
- **Offene mathematische Probleme verbessern** kann (FunSearch, AlphaEvolve)
- **Formale Beweise auf Wettkampfniveau** führen kann (AlphaProof, AlphaGeometry)
- **Produktive Systeme optimieren** kann (AlphaEvolve in Googles Rechenzentren)
- **Forschungsprobleme assistiert lösen** kann (Aletheia, Level 2)

Aber P-vs-NP bleibt außer Reichweite. Das Problem ist nicht nur schwer — es ist **strukturell anders** als alles, was KI bisher angegangen ist. Es erfordert einen Beweis über *alle möglichen* Algorithmen, nicht nur die Suche nach *einem* guten Algorithmus.

Die wahrscheinlichste Rolle von KI bei P-vs-NP ist nicht die des alleinigen Beweisers, sondern die des **Werkzeugs** — formalisierte Beweise, Muster in bestehender Literatur, und vielleicht eines Tages die Assistenz bei dem kreativen Sprung, den Scott Aaronson als „etwas fundamental Neues" beschreibt.

Bis dahin: 6 der 7 Millennium-Probleme bleiben ungelöst. Die Million Dollar wartet.

---

## Quellen

- Fawzi, A. et al. „Discovering faster matrix multiplication algorithms with reinforcement learning." *Nature* **610**, 47–53 (2022). [DOI](https://doi.org/10.1038/s41586-022-05172-4)
- Mankowitz, D.J. et al. „Faster sorting algorithms discovered using deep reinforcement learning." *Nature* **618**, 257–263 (2023). [DOI](https://doi.org/10.1038/s41586-023-06004-9)
- Romera-Paredes, B. et al. „Mathematical discoveries from program search with large language models." *Nature* (2023). [DOI](https://doi.org/10.1038/s41586-023-06924-6)
- Trinh, T.H. et al. „Solving olympiad geometry without human demonstrations." *Nature* **611**, 448–453 (2024). [DOI](https://doi.org/10.1038/s41586-023-06747-5)
- Hubert, T. et al. „Olympiad-level formal mathematical reasoning with reinforcement learning." *Nature* **651**, 607–613 (2026). [DOI](https://doi.org/10.1038/s41586-025-09833-y)
- Oh, J. et al. „Discovering State-of-the-art Reinforcement Learning Algorithms." *Nature* (2025).
- Clay Mathematics Institute: [claymath.org/millennium-problems](https://www.claymath.org/millennium-problems/)
- Aaronson, S. „Five Worlds of AI" (2023). [scottaaronson.blog](https://scottaaronson.blog)
- AlphaEvolve White Paper: [PDF](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf)
- Goedel-Prover-V2: [arXiv:2508.03613](https://arxiv.org/abs/2508.03613)
- LeanDojo: [leandojo.org](https://leandojo.org/)
- Aletheia: [arXiv:2602.10177](https://arxiv.org/abs/2602.10177), [arXiv:2602.03837](https://arxiv.org/abs/2602.03837)
- Algorithmist: [arXiv:2603.22363](https://arxiv.org/abs/2603.22363)
