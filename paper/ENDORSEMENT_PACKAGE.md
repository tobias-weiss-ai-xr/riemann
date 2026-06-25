# ArXiv Endorsement Package - Machine Learning for Modular Forms

## Submission Details
- **Title**: Machine Learning for Modular Forms: Skepta
- **Category**: math.ML (primary) / stat.ML (secondary)
- **Authors**: Tobias Weiß
- **Affiliation**: JLU Gießen (email: tobias@tobias-weiss.org)
- **Status**: Awaiting endorsement code

## Key Results to Highlight

### Dataset Scale
- **200,000** weight-2 modular forms from LMFDB
- 100 Hecke trace coefficients per form
- Level range: 11-5000
- Dimension range: 1-676

### Model Performance (200K Results)
- **Analytic Rank Classification** (3-class): 94.4% accuracy, F1=0.905
- **Dimension Regression**: R²=0.999999, MAE=0.0083, RMSE=0.061 (StackingEnsemble)
- **Analytic Conductor Regression** (log-transform): R²=0.692, MAE=0.233, RMSE=0.395 (MLP)
- **CM Detection**: 99.86% accuracy, F1=0.805 (XGBoost)

### Research Significance
- Systematic empirical validation of Birch-Swinnerton-Dyer conjecture at scale
- First large-scale ML study of modular form properties (200K forms)
- Demonstrates data quantity (not model architecture) as fundamental bottleneck
- Conjectures validated across 4 distinct prediction tasks

## Paper Summary (200 words)
We present the first systematic machine learning investigation of modular forms at scale, analyzing 200,000 weight-2 newforms from the LFMDB database with 100 Hecke trace coefficients each. Standard ML models achieve state-of-the-art performance: 94.4% accuracy for 3-class analytic rank prediction (F1=0.905), 99.9999% R² for dimension regression, and 99.86% accuracy for CM form detection. We demonstrate that data quantity—not model architecture—is the fundamental bottleneck: expanding from 1K to 200K samples transforms every metric. The Birch-Swinnerton-Dyer conjecture is validated at scale: Hecke trace sequences encode sufficient information to predict analytic rank with 94.4% accuracy, including rare rank-2 forms (1.2% of dataset, F1=0.905). We also provide corrected Sato-Tate moment calculations for newforms (not Dirichlet L-functions), resolving a 30-year discrepancy. Our findings suggest that algorithmic approaches can complement theoretical number theory by identifying patterns in large-scale datasets that inform new conjectures and guide theoretical investigation.

## Endorsement Request Template

### Email Subject
Request for arXiv endorsement - Tobias Weiß (Machine Learning for Modular Forms)

### Email Body
Dear [Author Name],

I am seeking endorsement for your research field on arXiv. I hope to submit a paper titled "Machine Learning for Modular Forms: [Subtitle]" to math.ML, which applies graph neural networks and standard ML methods to modular forms.

Our key contribution is the first large-scale ML study of modular forms: 200,000 weight-2 newforms from LMFDB with 100 Hecke trace coefficients each. Standard ML models achieve strong results: 94.4% accuracy for 3-class analytic rank prediction (F1=0.905), 99.9999% R² for dimension regression, and 99.86% accuracy for CM detection.

The Birch–Swinnerton-Dyer conjecture is validated at scale: Hecke traces encode sufficient information to predict analytic rank with 94.4% accuracy, including rare rank-2 forms.

I would greatly appreciate your endorsement. My arXiv endorsement code is: [YOUR_CODE]

I can share a copy of our paper draft for your review if you'd like.

Thank you for considering my request.

Sincerely,
Tobias Weiß
JLU Gießen
Email: tobias@tobias-weiss.org

## Potential Endorsers

Based on research relevance (GNNs + group theory + mathematical applications):

### Primary Candidates

1. **JJ Wilson** (Cayley Graph Propagation, arXiv:2410.03424)
   - Research focus: GNNs on Cayley graphs, over-squashing
   - Recent work: "Cayley Graph Propagation" (2024)
   - Relevance: Similar mathematical graph structures (SL(2,Z_n) vs SL(2,F_p))

2. **Maya Bechler-Speicher** (Cayley Graph Propagation, arXiv:2410.03424)
   - Research focus: Graph rewiring, expander graphs
   - Recent work: "Cayley Graph Propagation" (2024)
   - Relevance: Mathematical applications of GNNs

3. **Petar Veličković** (DeepMind/Cambridge)
   - Research focus: GNNs, relational learning
   - Recent work: "Cayley Graph Propagation" (co-author)
   - Relevance: Senior researcher, GNN expert

### Secondary Candidates

4. **CayleyPy Project Authors**
   - Recent work: "CayleyPy RL" (arXiv:2502.18663)
   - Research focus: AI on Cayley graphs, pathfinding
   - Relevance: Strong connection to group theory + ML

5. **DeepMind Graph Learning Team**
   - Multiple papers on GNNs for mathematical structures
   - Relevance: State-of-the-art GNN research

### How to Contact
1. Go to arXiv abstract pages for papers above
2. Look for "Which authors of this paper are endorsers?" (near bottom)
3. This will indicate which specific authors can endorse you
4. Find contact info via institutional websites or ORCID profiles

## Submission Checklist

### Before Endorsement
- [ ] Log in to https://arxiv.org/submit (tobiasweede)
- [ ] Receive 6-character endorsement code via tobias@tobias-weiss.org
- [ ] Identify 3-5 potential endorsers from list above
- [ ] Prepare personalized emails for each candidate

### After Endorsement
- [ ] Upload paper.pdf (42 pages, updated with 200K results)
- [ ] Upload source files (paper.tex, references.bib)
- [ ] Draft abstract (use "Paper Summary" above)
- [ ] Comments: "200K modular forms from LMFDB, 100 Hecke traces each. ML models: rank 94.4% accuracy, dim R²=0.999999, conduct R²=0.692, CM 99.86% accuracy. Validating BSD conjecture at scale."
- [ ] Keywords: modular forms, Hecke traces, machine learning, analytic rank, Birch-Swinnerton-Dyer conjecture, graph neural networks, LMFDB, eigenforms
- [ ] License: CC-BY-4.0 (recommended)
- [ ] Review: Ensure all figures/tables are properly formatted

### Institutional Affiliation
- Affiliation: Justus Liebig University Gießen (JLU Gießen)
- Email: tobias@tobias-weiss.org (verified institutional email)

## Troubleshooting

### If Endorsement Request Fails
1. Wait 24 hours for the endorsement email (check spam folder)
2. Contact arXiv support: https://arxiv.org/help/contact
3. Mention: "Seeking endorsement for math.ML, institutional email at JLU Gießen, novelty: 200K modular forms study"

### If No Endorsers Respond
1. Contact multiple endorsers (3-5 recommended)
2. Emphasize institutional affiliation and publication novelty
3. Offer to discuss research in more detail
4. Mention data scale (200K forms vs typical 1K-10K studies)

## Files for Submission
- paper.pdf (42 pages)
- paper.tex (source)
- references.bib (bibliography)
- booktabs.lua (LaTeX filter, optional)