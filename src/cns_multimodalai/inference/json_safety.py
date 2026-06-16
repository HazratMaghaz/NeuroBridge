from pathlib import Path
import json

try:
    import numpy as np
except Exception:
    np = None


_ORIGINAL_JSON_DEFAULT = json.JSONEncoder.default


def make_json_safe(obj):
    """
    Convert common scientific Python objects into JSON-safe objects.
    Large arrays are summarized, not exposed to frontend.
    """
    if np is not None:
        if isinstance(obj, np.ndarray):
            return {
                "omitted": "ndarray omitted from API response",
                "shape": list(obj.shape),
                "dtype": str(obj.dtype),
            }

        if isinstance(obj, np.integer):
            return int(obj)

        if isinstance(obj, np.floating):
            return float(obj)

        if isinstance(obj, np.bool_):
            return bool(obj)

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]

    try:
        if hasattr(obj, "item"):
            return obj.item()
    except Exception:
        pass

    return obj


def remove_internal_arrays(obj):
    """
    Remove internal vectors/embeddings recursively before API response.
    """
    internal_terms = [
        "embedding",
        "embeddings",
        "vector",
        "vectors",
        "ctranspath",
        "query_vector",
        "query_vectors",
    ]

    if isinstance(obj, dict):
        cleaned = {}

        for k, v in obj.items():
            key = str(k)
            key_lower = key.lower()

            is_internal_key = (
                key_lower.startswith("_")
                and any(term in key_lower for term in internal_terms)
            ) or key_lower in {
                "predicted_image_embedding",
                "predicted_image_embeddings",
                "predicted_ctranspath_embedding",
                "predicted_ctranspath_embeddings",
                "query_vector",
                "query_vectors",
            }

            if is_internal_key:
                shape = None
                dtype = None
                try:
                    shape = list(v.shape)
                    dtype = str(v.dtype)
                except Exception:
                    pass

                cleaned[f"{key}_omitted"] = "Internal vector omitted from API response."
                if shape is not None:
                    cleaned[f"{key}_shape"] = shape
                if dtype is not None:
                    cleaned[f"{key}_dtype"] = dtype
                continue

            cleaned[key] = remove_internal_arrays(v)

        return cleaned

    if isinstance(obj, list):
        return [remove_internal_arrays(v) for v in obj]

    if isinstance(obj, tuple):
        return [remove_internal_arrays(v) for v in obj]

    return obj


def _safe_json_default(self, obj):
    safe = make_json_safe(obj)

    # If converted, return it.
    if safe is not obj:
        return safe

    # Last fallback: if original encoder cannot handle it, stringify it.
    try:
        return _ORIGINAL_JSON_DEFAULT(self, obj)
    except TypeError:
        return str(obj)


def patch_json_encoder():
    """
    Globally patch standard json.dumps/json.dump so ndarray cannot crash backend.
    Safe to call multiple times.
    """
    if getattr(json.JSONEncoder.default, "_cns_json_safe_patched", False):
        return

    _safe_json_default._cns_json_safe_patched = True
    json.JSONEncoder.default = _safe_json_default
