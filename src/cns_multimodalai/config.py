from pathlib import Path
import os

DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = Path(os.getenv("CNS_PROJECT_ROOT", os.getenv("PROJECT_ROOT", str(DEFAULT_ROOT))))

# Internal reference cohort
SELECTED_CSV = PROJECT_ROOT / "metadata" / "selected_best_slide_per_patient.csv"
INTERNAL_EXPRESSION_CSV = PROJECT_ROOT / "data" / "expression" / "processed" / "expression_matrix_log2_tpm_filtered.csv"
INTERNAL_CTRANSPATH_CSV = PROJECT_ROOT / "features" / "ctranspath_7B_wsi_streaming_full" / "patient_level_ctranspath_mean_embeddings.csv"

# Phase 11A WSI-to-biology targets
PHASE11A_TARGET_CSV = PROJECT_ROOT / "results" / "tables" / "phase11a_image_to_gene_pathway_prediction" / "phase11a_target_gene_pathway_matrix.csv"

# Patch bank for real-patch morphology retrieval
PATCH_ROOT = PROJECT_ROOT / "patches"

# CTransPath model
CTRANSPATH_REPO = PROJECT_ROOT / "models" / "external" / "TransPath"
CTRANSPATH_CKPT = PROJECT_ROOT / "models" / "weights" / "ctranspath" / "ctranspath.pth"

# Default output root for GUI/tool inference
INFERENCE_OUT_ROOT = PROJECT_ROOT / "results" / "tool_inference_outputs"

# Model/data defaults
RANDOM_STATE = 42
RNA_HVG_N = 5000
RNA_PCA_DIM = 128
PLS_COMPONENTS = 32
CTRANSPATH_DIM = 768
CTRANSPATH_INPUT_SIZE = 224

# Morphology canvas defaults
PATCHES_PER_CANVAS = 1000
CANVAS_TILE_SIZE = 96
CANVAS_COLUMNS = 40
PATCHES_PER_SOURCE_PATIENT = 80

# Report warnings
MODEL_SCOPE_NOTE = (
    "Research prototype. The model is GBM/LGG-focused and outputs GBM-like vs LGG-like similarity. "
    "It is not a pan-CNS classifier and is not intended for clinical diagnosis."
)

MORPHOLOGY_NOTE = (
    "The morphology canvas is retrieval-based and uses real histology patches from the internal patch bank. "
    "It is not a true reconstruction of the patient's WSI."
)
