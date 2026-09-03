// ---------------------------------------------------------------------------
// research-data.js
//
// Research findings from the GNN × Number Theory investigation of the
// Riemann Hypothesis, embedded for the three.js visualisation.
// All numbers are pulled directly from the project's data/ JSON outputs.
// ---------------------------------------------------------------------------

const RESEARCH = {
  // ----- The headline finding: the dimension split in L-function zero stats
  // 63,844 weight-2 newforms from the LMFDB → 568,708 nearest-neighbour
  // spacings, fitted to the Brody distribution (β interpolates Poisson↔GUE).
  dimensionSplit: {
    totalForms: 63844,
    totalSpacings: 568708,
    // Hecke-field degree / group
    groups: [
      { label: "dim = 1  (CM forms)",  beta: 1.879, n: 34628, ci: [1.870, 1.888], ksGue: 0.0165, regime: "GUE" },
      { label: "dim = 2",               beta: 0.494, n: 8263,  ci: [0.484, 0.503], ksGue: 0.180, regime: "Poisson" },
      { label: "dim = 3",               beta: 0.316, n: 4319,  ci: [0.304, 0.326], ksGue: 0.220, regime: "Poisson" },
      { label: "dim = 4",               beta: 0.213, n: 3157,  ci: [0.202, 0.224], ksGue: 0.247, regime: "Poisson" },
      { label: "dim ≥ 5",               beta: 0.128, n: 13477, ci: [0.123, 0.133], ksGue: 0.266, regime: "Poisson" },
      { label: "all (aggregate)",       beta: 0.620, n: 63844, ci: [0.615, 0.624], ksGue: 0.125, regime: "mixed" },
    ],
    // Reference repulsion levels
    references: [
      { label: "Poisson (β = 0)", beta: 0, color: 0x4f8ef7 },
      { label: "GOE (β = 1)",     beta: 1, color: 0xf0a020 },
      { label: "GUE (β = 2)",     beta: 2, color: 0x33d6a6 },
    ],
    cohensD: 8.808,
    zScore: 101.6,
  },

  // ----- Machine learning on L-function zeros (from multi_task results)
  ml: {
    singleTaskZ1R2: 0.714,
    multiTaskPerZeroR2: {
      z1: 0.704, z2: 0.709, z3: 0.724, z4: 0.735, z5: 0.741,
      z6: 0.745, z7: 0.744, z8: 0.749, z9: 0.710, z10: 0.340,
    },
    benchmark: {
      tracesOnly: 0.962,
      tracesPlusZeros: 0.985,
    },
    note: "sklearn on 53k–63k LMFDB Hecke traces: R² 0.73–0.99. GNNs on Cayley graphs failed (R² < 0).",
  },

  // ----- Cayley graphs of SL(2,F_p) → Ramanujan / spectral gap connection
  cayley: {
    regularity: 4,
    ramanujanBound: 2 * Math.sqrt(3), // ≈ 3.464 for 4-regular
    ramanujanBoundStr: "2√3 ≈ 3.464",
    primes: [
      { p: 3,  ramanujan: true,  order: 24,    lambda2: null },
      { p: 5,  ramanujan: true,  order: 120,   lambda2: null },
      { p: 7,  ramanujan: false, order: 336 },
      { p: 11, ramanujan: false, order: 1320 },
      { p: 13, ramanujan: false, order: 2184 },
    ],
    pThreeIsRamanujan: true,
    pFiveIsRamanujan: true,
    note: "LPS 1988: p=3,5 are Ramanujan. Hecke eigenvalues ↔ graph eigenvalues ↔ L-functions ↔ ζ(s).",
  },

  // ----- Farey graph (Pollicott–Ruelle transfer operator bridge to RH)
  farey: {
    gapLaw: "gap ≈ 2.6547 · n^(-0.9989) ≈ 2.65 / n",
    baselineR2: 0.9999,
    gnnR2: -7.57,
    note: "Pollicott 2022: RH ⇔ spectral gap of the Farey transfer operator. Gap scales as 1/n.",
  },

  // ----- Zeta-landscape facts (shown in the hero scene)
  zeta: {
    criticalLine: "Re(s) = 1/2",
    firstZerosImag: [
      14.134725141734693, 21.022039638771555, 25.010857580145690,
      30.424876125859513, 32.935061587739190, 37.586178158825671,
      40.918719012147495, 43.327073280914999, 48.005150881167159,
      49.773832477672302, 52.970321477714460, 56.446247697063948,
      59.347044002602353, 60.831778524609810, 65.112544048081652,
      67.079810529494174, 69.546401711173979, 72.067157674481908,
      75.704690699083933, 77.144840068874805, 79.337375020249068,
      82.910380854086031, 84.735493977550075, 87.425274626125575,
      88.809111207634466, 92.491899455460041, 94.651344040519886,
      95.870634228245573, 98.831191881207210, 101.317851005931262,
    ],
    poleAt: "s = 1",
  },

  // ----- Provenance
  provenance: {
    zenodo: "https://doi.org/10.5281/zenodo.21974748",
    repo: "https://github.com/tobias-weiss-ai-xr/riemann",
    headline:
      "The Montgomery–Odlyzko law is NOT universal: CM forms (dim = 1) are GUE-like (β ≈ 1.88), " +
      "generic non-CM forms (dim ≥ 2) are near-Poisson (β ≈ 0.24). The aggregate β ≈ 0.62 is a mixing artifact.",
  },
};

if (typeof window !== "undefined") window.RESEARCH = RESEARCH;
if (typeof module !== "undefined") module.exports = { RESEARCH };

// ---------------------------------------------------------------------------
// Strategy map: the approaches (Herangehensweisen) to the Riemann hypothesis.
// Text in German — documents the strategic discussion; status colour is set
// in viz.js (proven / partial / numerical / proposed / tool).
// ---------------------------------------------------------------------------
RESEARCH.approaches = {
  target: { label: "RH", detail: "Riemann-Hypothese: alle nichttrivialen Nullstellen von ζ(s) auf Re(s) = ½" },
  groups: [
    {
      name: "A · Transferoperator (EPIC-4)",
      color: "#3fe0ff",
      items: [
        {
          label: "Mayer-Äquivalenz",
          status: "proven",
          title: "Mayer-Äquivalenz — RH ⟺ 1 ∉ Spec(L_s)",
          detail: `
            <p>Operatorkern des Hauptstrangs (Mayer 1990, Bonanno 2022, Möller–Pohl 2011):</p>
            <p><code>L_s f(x) = Σ (n+1+x)^{−2s} f(1/(n+1+x))</code> — Transferoperator der Gauß-Abbildung,</p>
            <p><code>RH ⟺ det(I − L_s) ≠ 0</code> für alle <strong>Re(s) &gt; ½</strong> ⟺ <span class="stat">1 ∉ Spec(L_s)</span>.</p>
            <p>„ρ(L_s) &lt; 1“ ist <strong>strikt stärker</strong> als RH und am Streifenrand numerisch falsch (die volle Operator hat ρ &gt; 1 durch den ζ(2σ)-Mode). Das Numerik-Programm misst deshalb <span class="stat">m(s) = min_j |1 − λ_j(s)|</span> (Exp 19k).</p>
          `,
        },
        {
          label: "Ruelle-Domination",
          status: "proven",
          title: "Ruelle-Domination — Re(s) &gt; 1 uniform geschlossen",
          detail: `
            <p>Elementarer Beweis (2026, in Lean formalisiert): die Gewichte majorisieren punktweise,</p>
            <p><code>|L_{σ+it} f| ≤ L_σ |f|</code> &nbsp;⇒&nbsp; <code>ρ(L_{σ+it}) ≤ ρ(L_σ) = λ₁(σ)</code>.</p>
            <p>Zusammen mit <span class="stat">λ₁'(1) = −π²/(6·ln 2) &lt; 0</span> folgt <strong>ρ(L_s) &lt; 1 für alle Re(s) &gt; 1, uniform in t</strong> — quantitativ, ohne Maximumsprinzip.</p>
            <p class="cite">Grenze: die <em>Envelope-Obstruction</em> — am Rand degeneriert es zu |λ₁(1+it)| ≤ 1, der Streifen (½, 1] braucht echte t-Abhängigkeit.</p>
          `,
        },
        {
          label: "Spektrum bei s = 1",
          status: "proven",
          title: "Spektralanalyse bei s = 1 (in Lean bewiesen, `sorry` entfernt)",
          detail: `
            <ul>
              <li><span class="stat">λ₁'(1) = −π²/(6·ln 2) ≈ −2.373</span> — exakt <strong>−2 × Lévy-Konstante</strong> (Feynman–Hellmann-Verifikation, Commit 3dd41dd)</li>
              <li><span class="stat green">ρ(L_r) &lt; 1</span> lokal rechts von s = 1 (∃ε&gt;0, Commit 6671a13)</li>
              <li>Spektrallücke bei s = 1: zweiter Eigenwert = Gauss–Kuzmin–Wirsing-Konstante</li>
            </ul>
            <p>Schließt den Perturbations-Schritt „λ₁ aus dem Einheitskreis heraus“ — der erste rigorose Baustein in Richtung Streifen.</p>
          `,
        },
        {
          label: "Certified Numerics",
          status: "numerical",
          title: "Falsifikations-Hebel — certified zero-free sliver",
          detail: `
            <p>Ziel: maschinengeprüfte (Nisoli/DFLY-Intervallarithmetik) untere Schranke <span class="stat">m(s) ≥ c &gt; 0</span> im engsten Schlitz.</p>
            <p>Nyström-konvergiert (N=256, n_max=8000):</p>
            <ul>
              <li><strong>Ecke</strong> [0.505, 0.56] × [75, 200]: |λ₂| → 1 mit σ → ½⁺ (0.919 @ 0.55, 0.999 @ 0.51)</li>
              <li><strong>High-t-Strang</strong> t ≈ 900–1200: |λ₂| ≈ 0.98–1.01 (N ≥ 512 nötig)</li>
              <li><span class="stat">m ≥ 0.011</span> bei σ = 0.51 über alle getesteten t — kein Eigenwert je = 1 (RH-konsistent)</li>
            </ul>
            <p>Außerhalb der beiden Regionen ist der Abstand ≥ 0.15.</p>
          `,
        },
        {
          label: "t-Dynamik",
          status: "numerical",
          title: "t-Dynamik — der Schlüssel um die Envelope-Obstruction",
          detail: `
            <p>σ-only-Schranken können den Streifen nicht öffnen. Nötig ist echte t-Abhängigkeit (Exp 19h–19l):</p>
            <ul>
              <li>Kleines t: Abfall exakt mit CLT-Rate <span class="stat">−P''/2 · t²</span> (bei σ = 1.0 auf 4 Nachkommastellen)</li>
              <li>Großes t: Plateau strikt &lt; 1 (0.86 / 0.64 / 0.49 / 0.35 für σ = 0.6 / 0.8 / 1.0 / 1.25)</li>
              <li>An Nullstellenhöhen: <span class="stat">m(σ+iγ) ≈ c·(σ−½)</span>, c ≈ 2–3 — messbarer Slope (γ₄₁: 0.117@0.55 → 0.083@0.51)</li>
            </ul>
            <p>Koppelbar an <code>Z_S'(½+iγ)</code> / Hardy-Z-Funktion → RH wird zu „die Rate verschwindet nie“ — anschluss an die rigoros verifizierten Nullstellen.</p>
          `,
        },
        {
          label: "Lean: Axiome → Theoreme",
          status: "proposed",
          title: "Lean-Formalisierung — die Axiome zu Theoremen machen",
          detail: `
            <p>Nach der Umkorrektur auf <span class="stat">1 ∉ Spec</span> (19k) bleibt als Formalisierungs-Schrank:</p>
            <ul>
              <li><span class="stat gold">Nuklearität</span>/Spurklasse von L_s auf C¹-Hölder-Räumen — mathlib hat die Transferoperator-Theorie noch gar nicht (eigener Beitrag!)</li>
              <li>Mayer-Identität, Fredholm-Determinante ganz, analytische Fortsetzung</li>
              <li>125 verbleibende <code>sorry</code>s, Kern-Theoreme stehen noch als <code>axiom</code></li>
            </ul>
            <p class="cite">Selbst die nukleare Spektraltheorie von L_s wäre ein veröffentlichbarer mathlib-Beitrag — unabhängig vom RH-Beweis.</p>
          `,
        },
      ],
    },
    {
      name: "B · andere RH-Äquivalente",
      color: "#7ea8ff",
      items: [
        {
          label: "Nyman–Beurling–Báez-Duarte",
          status: "proposed",
          title: "Nyman–Beurling–Báez-Duarte — ℓ²-Abschluss",
          detail: `
            <p>RH ⟺ der Abschluss der Funktionen <code>{ρ_k(x/k)}</code> ist L²(0,1); Báez-Duarte: RH ⟺ <span class="stat">d_n → 0</span>.</p>
            <p>Anderes funktionalanalytisches Gepäck als Mayer, nur elementare harmonische Analysis + ⌊x⌋; klare Falsifikationsstruktur; gut formalisierbar.</p>
            <p class="cite">Im Projekt noch unberührt — Kandidat für die zweite, unabhängige Angriffsachse.</p>
          `,
        },
        {
          label: "Li-Kriterium",
          status: "proposed",
          title: "Li-Kriterium — λ_n ≥ 0",
          detail: `
            <p>RH ⟺ alle Li-Koeffizienten <code>λ_n = Σ_ρ (1 − (1 − 1/ρ)^n)</code> sind <strong>≥ 0</strong> (Li 1997, Bombieri–Lagarias 1999).</p>
            <p>Konkret berechenbar — Zugriff über die ζ-/LMFDB-Pipelines; formalisierbar als Implikationskette „λ_n ≥ 0 ∀ n ⇒ RH“.</p>
            <p class="cite">Offen; numerisch starke Evidenz.</p>
          `,
        },
        {
          label: "Lagarias–Robin",
          status: "proposed",
          title: "Lagarias / Robinsche Ungleichung — die elementare Äquivalenz",
          detail: `
            <p>RH ⟺ für alle n ≥ 1: <span class="stat">σ₁(n) ≤ Hₙ + e^{Hₙ}·log Hₙ</span> (Lagarias 2002) — die einzige <strong>rein arithmetische</strong> Äquivalenz.</p>
            <p>Reduktions-Programm: ungleichung genügt es, für (endlich viele bis zur expliziten Schranke) <strong>kolossal-abundante Zahlen</strong> zu prüfen + analytischer Tail.</p>
            <p>Maschinell bis 10⁹+ verifiziert; passt auf unsere Rechen-Pipelines und auf Lean (elementare Zahlentheorie).</p>
          `,
        },
        {
          label: "de Bruijn–Newman Λ",
          status: "partial",
          title: "de Bruijn–Newman-Konstante Λ",
          detail: `
            <p>Λ ≤ 0 ⇒ RH; <span class="stat">Λ = 0 ⟺ RH</span>. Rodgers–Tao (2018): <span class="stat">Λ ≤ ½</span> (Theorem).</p>
            <p>Numerisch: untere Schranke <span class="stat">Λ &gt; −1.1·10⁻¹²</span>. Jede Verbesserung Λ &lt; c ist publizierbar; der Schritt zu Λ &lt; 0 rigoros ist hart.</p>
            <p class="cite">Verbindbar mit der vorhandenen Nulllinien-Computation.</p>
          `,
        },
        {
          label: "explizite Regionen",
          status: "partial",
          title: "Explizite nullstellenfreie Regionen + explizite Formeln",
          detail: `
            <p>„Nahe-RH“ mit expliziten Konstanten (Platt, Trudgian, Mossinghoff–Trudgian) + rigoros verifizierte Nullstellen (Odlyzko bis 10¹³, Hiary ~10¹⁴) → starke explizite Fehlerschranken für Primzahlsummen.</p>
            <p>Der einzige Pfad mit <strong>quantitativen, zitterbaren</strong> Fortschritten; schließt direkt an <code>PrimeNumberTheorem.lean</code> an.</p>
          `,
        },
      ],
    },
    {
      name: "C · Graphentheorie",
      color: "#33d6a6",
      items: [
        {
          label: "Ihara / Hashimoto-Zeta",
          status: "proposed",
          title: "Ihara-RH ⟺ Ramanujan ⟺ L-Funktionen",
          detail: `
            <p>Für Graphen: <span class="stat">Ihara-RH</span> (alle |α| = 1/√q) ⟺ Graph ist <strong>Ramanujan</strong> ⟺ (Sunada / Hashimoto / Bass) <strong>Produkt von Modulform-L-Funktionen</strong>.</p>
            <p>Verheiratet die zwei fertigen Projekt-Zweige: <code>CayleyGraphs.lean</code> + <code>RamanujanProperty.lean</code> mit <code>LMFDBConjectures.lean</code>.</p>
            <p class="cite">Fehlendes Werkzeug: Ihara-Zeta in Lean + Lemma „Zeta_G(u) = ∏ L-Funktionen“. Für geeignete arithmetische Graphen ist Ihara-RH äquivalent zur klassischen RH.</p>
          `,
        },
      ],
    },
    {
      name: "D · Projekt-Werkzeuge",
      color: "#b08cff",
      items: [
        {
          label: "FunSearch",
          status: "tool",
          title: "FunSearch — die fehlende Ungleichung suchen",
          detail: `
            <p>Die Envelope-Obstruction sagt exakt, was fehlt: eine explizite t-abhängige Majorante <code>|λ₂(σ+it)| ≤ φ(σ,t) &lt; 1</code> im Streifen.</p>
            <p>FunSearch (Programm-Synthese) genau darauf ansetzen; ein Kandidat wird dann von Mensch/Lean verifiziert.</p>
            <p class="cite">Erzeugt Hypothesen, keine Beweise — aber das fehlende Lemma hat eine präzise Syntax.</p>
          `,
        },
        {
          label: "ML / LMFDB",
          status: "tool",
          title: "ML auf LMFDB — Conjecture-Generator",
          detail: `
            <p>sklearn auf 53k–63k Hecke-Spuren: <span class="stat">R² 0.73–0.99</span> (GNNs auf Cayley-Graphen scheitern, R² &lt; 0).</p>
            <p>Fand empirische Strukturen: Friedli-Konstante <span class="stat">1.1367</span>, Brody-Split β 1.88 vs 0.24, Murmurations.</p>
            <p class="cite">Mustererkennung ≠ Beweis — dient der Hypothesenbildung für die Achsen A–C.</p>
          `,
        },
      ],
    },
  ],
};

// Compact L-function correlation-spectrum data (data/phase_transition_spectral/spectral_analysis.json)
RESEARCH.spectral = [{"dim": 1, "n_forms": 57270, "effective_rank": 24.888, "spectral_entropy_norm": 0.9993, "top1_concentration": 0.0493, "top_eigs": [1.2331, 1.1262, 1.0837, 1.0519, 1.0344, 1.0282, 1.0238, 1.0159, 1.0031, 0.9989, 0.9925, 0.9877]}, {"dim": 2, "n_forms": 24377, "effective_rank": 24.27, "spectral_entropy_norm": 0.9958, "top1_concentration": 0.0656, "top_eigs": [1.64, 1.2977, 1.2156, 1.1279, 1.0872, 1.0623, 1.0402, 1.0353, 1.0033, 0.991, 0.9744, 0.9635]}, {"dim": 3, "n_forms": 11964, "effective_rank": 23.1, "spectral_entropy_norm": 0.9891, "top1_concentration": 0.0822, "top_eigs": [2.0546, 1.5768, 1.387, 1.1598, 1.0912, 1.0735, 1.0432, 1.0206, 0.9957, 0.9767, 0.931, 0.912]}, {"dim": 4, "n_forms": 9438, "effective_rank": 21.835, "spectral_entropy_norm": 0.9816, "top1_concentration": 0.0977, "top_eigs": [2.4429, 1.721, 1.4482, 1.2457, 1.101, 1.0948, 1.0833, 1.0191, 1.0083, 0.9714, 0.9208, 0.8992]}, {"dim": 5, "n_forms": 5704, "effective_rank": 19.444, "spectral_entropy_norm": 0.966, "top1_concentration": 0.1217, "top_eigs": [3.042, 2.0978, 1.599, 1.2758, 1.1392, 1.0949, 1.0313, 1.0187, 0.9832, 0.9499, 0.8715, 0.8578]}, {"dim": 6, "n_forms": 5895, "effective_rank": 18.677, "spectral_entropy_norm": 0.9606, "top1_concentration": 0.1304, "top_eigs": [3.2592, 2.1567, 1.6375, 1.2515, 1.1674, 1.1191, 1.0405, 1.0094, 0.9876, 0.9497, 0.8531, 0.8276]}, {"dim": 7, "n_forms": 3691, "effective_rank": 16.072, "spectral_entropy_norm": 0.9386, "top1_concentration": 0.1556, "top_eigs": [3.8912, 2.5685, 1.7506, 1.3614, 1.1267, 1.1236, 1.0164, 0.9981, 0.9752, 0.9046, 0.8054, 0.7812]}, {"dim": 8, "n_forms": 4282, "effective_rank": 15.878, "spectral_entropy_norm": 0.9369, "top1_concentration": 0.1598, "top_eigs": [3.9952, 2.4951, 1.7235, 1.4201, 1.1459, 1.0756, 1.0514, 1.0033, 0.9854, 0.921, 0.8373, 0.7567]}, {"dim": 9, "n_forms": 3020, "effective_rank": 13.629, "spectral_entropy_norm": 0.914, "top1_concentration": 0.1881, "top_eigs": [4.7021, 2.7483, 1.8593, 1.4186, 1.1204, 1.0507, 1.0052, 0.972, 0.9282, 0.8676, 0.767, 0.7104]}, {"dim": 10, "n_forms": 3178, "effective_rank": 13.601, "spectral_entropy_norm": 0.9124, "top1_concentration": 0.1874, "top_eigs": [4.6847, 2.7383, 1.8626, 1.495, 1.1493, 1.0469, 1.0245, 0.9927, 0.9708, 0.8558, 0.8213, 0.7109]}, {"dim": 11, "n_forms": 2316, "effective_rank": 11.92, "spectral_entropy_norm": 0.8901, "top1_concentration": 0.2103, "top_eigs": [5.2574, 3.0144, 1.9805, 1.4287, 1.0843, 1.0618, 1.004, 0.9572, 0.8885, 0.8749, 0.8136, 0.6597]}, {"dim": 12, "n_forms": 3005, "effective_rank": 12.461, "spectral_entropy_norm": 0.9009, "top1_concentration": 0.2095, "top_eigs": [5.2364, 2.636, 1.8627, 1.3801, 1.2051, 1.0413, 1.0022, 0.9522, 0.9234, 0.8484, 0.8024, 0.6935]}];
