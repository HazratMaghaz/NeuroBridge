# Supervisor Summary

## What is completed
- The **Phase 14** (GBM/LGG classification) and **Phase 15G** (Image-to-gene/pathway Ridge regression) models are fully frozen and integrated.
- The FastAPI backend successfully serves requests for both pre-processed CSV/ZIPs and raw local `.svs` files.
- The Next.js frontend GUI handles asynchronous progress updates, dynamically renders complex scientific tables, and serves downloadable matrix results securely.

## What is scientifically new/useful
- **Direct Image-to-Molecular Mapping:** The system establishes a direct, quantitative link from histology (via CTransPath) to 101 specific biological targets (genes, programs, and pathways).
- **Matrix Formatting:** The backend automatically parses predictions into an `image_to_gene_expression_matrix.csv`. This formatting makes it incredibly easy for biologists to treat image-inferred signatures exactly like traditional cohort data matrices for downstream analysis.

## What is still prototype
- The WSI workflow utilizes a relatively simple HSV-based tissue masking approach.
- The morphology retrieval (RNA → Image) relies on pre-computed feature similarity rather than a true generative network.
- The models focus entirely on distinguishing GBM-like vs. LGG-like states and associated pathways; it is not a pan-CNS classifier.

## Why WSI → Gene-Expression-Like Matrix Matters
Currently, predicting molecular traits from H&E is largely handled via black-box classification models. By forcing the model to output a structured **gene-expression-like matrix**, we allow pathologists and researchers to cross-reference predictions with established bioinformatics pipelines. It translates computer vision embeddings back into the universal language of molecular biology.

## What questions to ask supervisor
1. Do the UI warnings sufficiently convey that these are computational predictions and not actual RNA-seq measurements?
2. Are there specific additional gene targets we should include in the Phase 15G model before finalizing the thesis?
3. Should we prioritize integrating patient survival data (KM curves, c-index) into the report generation next?
