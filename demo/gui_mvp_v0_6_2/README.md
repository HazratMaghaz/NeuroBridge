# CNS-MultiModalAI GUI MVP v0.6.2

## Purpose
The CNS-MultiModalAI GUI MVP provides a robust, user-friendly interface for researchers to interact with the trained Phase 14 and Phase 15G models. It translates complex machine learning inferences into clinically interpretable biological signatures, specifically focusing on the morpho-molecular landscape of adult-type diffuse gliomas.

## Supported Workflows
This prototype supports three primary multimodal workflows:
1. **RNA CSV → GBM/LGG-like Prediction → Morphology Canvas**
   - Ingests pre-processed RNA-seq count data to predict tumor similarity and retrieves top conceptually-aligned histological morphology.
2. **Patch ZIP → Image-to-Gene/Pathway Prediction**
   - Accepts pre-extracted histology patches, computes CTransPath embeddings, and generates a unified molecular program inference.
3. **Local WSI Path → Extracted Patches → Image-to-Gene/Pathway Prediction**
   - Directly processes raw Whole Slide Images (`.svs`), handling automated tissue masking and patch extraction, before feeding into the frozen Phase 15G Ridge models.

## Important Output Files
The WSI and Patch workflows generate several matrix-format tabular outputs suitable for downstream statistical aggregation or direct database ingestion:
- `image_to_gene_expression_matrix.csv`
- `image_to_gene_pathway_prediction_matrix.csv`
- `image_to_gene_pathway_top_features.csv`
- `image_to_gene_pathway_report.md`

## Important Notice
> **Research Warning:**
> This is a research prototype. Outputs are GBM/LGG-like similarity and predicted gene-expression-like signatures inferred from histology embeddings. They are not measured RNA-seq and not intended for clinical diagnosis.
