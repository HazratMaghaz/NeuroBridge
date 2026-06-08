# GitHub Repository Setup Card

## Recommended repository name

`CNS-MultiModalAI`

Alternative names:

- `glioma-multimodal-missing-modality`
- `wsi-transcriptome-glioma-ai`
- `CNS-PathOmics-MissingModality`

## Short GitHub description

Bidirectional WSI–transcriptome multimodal AI framework for GBM/LGG glioma analysis, missing-modality inference, image-to-biology prediction, and molecular-to-morphology real-patch retrieval.

## GitHub topics

multimodal-ai, computational-pathology, glioblastoma, low-grade-glioma, cns-tumors, whole-slide-images, gene-expression, missing-modality, ctranspath, resnet50, transcriptomics, pathomics, bioinformatics, precision-oncology, medical-ai, deep-learning

## Recommended visibility

Start as **private** until:

1. external validation is cleaned,
2. data paths are sanitized,
3. no patient-level restricted metadata is exposed,
4. notebooks are polished,
5. large data is confirmed ignored.

Then optionally publish the code-only version.

## First commit message

`chore: initialize CNS-MultiModalAI repository structure`

## Suggested commit sequence

1. `chore: initialize repository metadata and README`
2. `docs: add project scope and data policy`
3. `chore: add gitignore for WSI and omics artifacts`
4. `notebooks: add internal phase notebooks`
5. `notebooks: add external validation templates`
6. `scripts: add data preparation utilities`
7. `docs: add CPTAC-GBM external validation notes`
8. `feat: add inference pipeline scaffold`
9. `feat: add morphology canvas generation module`
10. `docs: add thesis workflow summary`