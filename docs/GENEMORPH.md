# Gene2Morph LOO Reference Morphology Retrieval

## 1. Scientific Overview
Gene2Morph is a bidirectional retrieval engine that maps transcriptomic gene-expression profiles to representative, real histology patches extracted from an internal Whole-Slide Image (WSI) reference bank.

---

## 2. Leave-One-Patient-Out (LOO) Policy
To prevent patient-level retrieval leakage during scientific evaluation, Gene2Morph enforces strict query-patient self-exclusion (`exclude_query_patient=True`, `strict_loo=True`):
- Both the query patient ID and source slide patient IDs are normalized to canonical TCGA case format (`TCGA-XX-YYYY`).
- All whole-slide images and patch candidates originating from the query patient are excluded before similarity calculation.
- Exactly 300 reference patches are retrieved per query case.

---

## 3. Results Summary (6-Query Pilot Rerun)

| Query Index | Query Case | Query Class | Old Peak | LOO Peak | Old Top-300 | LOO Top-300 | Top Source Slide | Excluded Self Patches |
|---|---|---|---|---|---|---|---|---|
| 0 | TCGA-02-0003 | GBM | 0.8884 | 0.8884 | 0.8582 | 0.8582 | TCGA-06-5856 | 0 |
| 1 | TCGA-02-0016 | GBM | 0.8861 | 0.8861 | 0.8552 | 0.8552 | TCGA-DU-5847 | 0 |
| 2 | TCGA-02-0026 | GBM | 0.8820 | 0.8820 | 0.8546 | 0.8545 | TCGA-06-0743 | 3 |
| 3 | TCGA-CS-4938 | LGG | 0.9293 | 0.9293 | 0.9061 | 0.9061 | TCGA-FG-A70Z | 3 |
| 4 | TCGA-CS-4941 | LGG | 0.9081 | 0.9081 | 0.8819 | 0.8819 | TCGA-DU-7011 | 0 |
| 5 | TCGA-CS-4942 | LGG | 0.8978 | 0.8978 | 0.8738 | 0.8738 | TCGA-S9-A7QW | 0 |

---

## 4. Key Scientific Findings
1. **Peak Cosine Unchanged**: Peak cosine similarity ($0.8986$ mean) remained identical because rank #1 was non-self for all 6 queries.
2. **Diagnosis Agreement Maintained**: Top source slide matched query diagnosis in $5/6$ (83.3%) cases.
3. **Self Patches Removed**: 6 self-patient patches in baseline top-300 results were cleanly eliminated without affecting diagnosis agreement or top source slide identities.
