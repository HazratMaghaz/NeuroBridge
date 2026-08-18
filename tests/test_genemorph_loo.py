import unittest
import numpy as np
import pandas as pd
import h5py
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from cns_multimodalai.inference.rna_reference_morphology_retrieval import (
    normalize_tcga_patient_id,
    canonicalize_diagnosis_label,
    assert_final_output_loo_clean,
    run_reference_morphology_retrieval,
)
from cns_multimodalai.inference.retrieve_morphology_canvas import (
    retrieve_real_patches_from_predicted_image_embedding,
)


class TestGene2MorphLOO(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_mock_h5(self, filename, patient_id, slide_id, features, coords=None, diagnosis="Glioblastoma"):
        h5_path = self.tmp_path / filename
        with h5py.File(h5_path, "w") as h:
            h.attrs["patient_id"] = patient_id
            h.attrs["slide_id"] = slide_id
            h.attrs["diagnosis_label"] = diagnosis
            h.create_dataset("features", data=np.asarray(features, dtype=np.float32))
            if coords is None:
                n_patches = len(features)
                coords = np.zeros((n_patches, 2), dtype=np.int32)
                coords[:, 0] = np.arange(n_patches) * 256
                coords[:, 1] = 100
            h.create_dataset("coords_level0", data=np.asarray(coords, dtype=np.int32))
        return h5_path

    # 1. Patient ID Normalization
    def test_01_normalize_tcga_patient_id(self):
        self.assertEqual(normalize_tcga_patient_id("TCGA-02-0003-01Z-00-DX1"), "TCGA-02-0003")
        self.assertEqual(normalize_tcga_patient_id("tcga-cs-4941-01a"), "TCGA-CS-4941")
        self.assertEqual(normalize_tcga_patient_id("C3N-00100-01"), "C3N-00100")
        self.assertIsNone(normalize_tcga_patient_id("SAMPLE_12345"))
        self.assertIsNone(normalize_tcga_patient_id(None))

    # 2. Canonical Diagnosis Normalization
    def test_02_canonicalize_diagnosis_label(self):
        self.assertEqual(canonicalize_diagnosis_label("Glioblastoma"), "GBM")
        self.assertEqual(canonicalize_diagnosis_label("GBM-like"), "GBM")
        self.assertEqual(canonicalize_diagnosis_label("TCGA-GBM"), "GBM")
        self.assertEqual(canonicalize_diagnosis_label("Lower Grade Glioma"), "LGG")
        self.assertEqual(canonicalize_diagnosis_label("LGG-like"), "LGG")
        self.assertEqual(canonicalize_diagnosis_label("TCGA-LGG"), "LGG")
        self.assertEqual(canonicalize_diagnosis_label("Medulloblastoma"), "UNKNOWN")
        self.assertEqual(canonicalize_diagnosis_label(None), "UNKNOWN")

    # 3. Same Patient Exclusion
    def test_03_same_patient_exclusion(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        # Query patient slide
        self._create_mock_h5("slide1.h5", "TCGA-02-0003-01A", "slide1", np.ones((5, 768)))
        # Other patient slide
        self._create_mock_h5("slide2.h5", "TCGA-02-0016-01A", "slide2", np.ones((5, 768)))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=True,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        retrieved_pids = set(df["source_patient_id"].tolist())
        self.assertNotIn("TCGA-02-0003", retrieved_pids)
        self.assertIn("TCGA-02-0016", retrieved_pids)

    # 4. Different Patient Eligible
    def test_04_different_patient_eligible(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        self._create_mock_h5("slide2.h5", "TCGA-02-0016-01A", "slide2", np.ones((5, 768)))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=True,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        self.assertEqual(len(df), 5)
        self.assertTrue((df["source_patient_id"] == "TCGA-02-0016").all())

    # 5. Multi-slide Same Patient All Excluded
    def test_05_multi_slide_same_patient_excluded(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        # Multiple slides for query patient
        self._create_mock_h5("slide1_a.h5", "TCGA-02-0003-01A", "slide1_a", np.ones((5, 768)))
        self._create_mock_h5("slide1_b.h5", "TCGA-02-0003-01Z", "slide1_b", np.ones((5, 768)))
        # Other patient slide
        self._create_mock_h5("slide2.h5", "TCGA-02-0026-01A", "slide2", np.ones((5, 768)))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=True,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        retrieved_pids = set(df["source_patient_id"].tolist())
        self.assertNotIn("TCGA-02-0003", retrieved_pids)
        self.assertEqual(summary["bank_audit"]["excluded_self_h5_files"], 2)

    # 6. Malformed Strict Query ID Fails
    def test_06_malformed_strict_query_id_fails(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        self._create_mock_h5("slide1.h5", "TCGA-02-0016-01A", "slide1", np.ones((5, 768)))

        with self.assertRaises(ValueError):
            run_reference_morphology_retrieval(
                query_embedding=q_vec,
                query_patient_id="INVALID_CASE_NAME",
                output_dir=self.tmp_path / "out",
                h5_dir=str(self.tmp_path),
                strict_loo=True,
            )

    # 7. Unresolvable Source Patient Skipped
    def test_07_unresolvable_source_patient_skipped(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        # Unresolvable patient slide
        self._create_mock_h5("unknown.h5", "UNKNOWN_PATIENT", "slide_unk", np.ones((5, 768)))
        # Valid patient slide
        self._create_mock_h5("slide2.h5", "TCGA-02-0016-01A", "slide2", np.ones((5, 768)))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=True,
        )

        audit = summary["bank_audit"]
        self.assertEqual(audit["skipped_unresolved_h5_files"], 1)
        df = pd.read_csv(summary["retrieval_csv"])
        self.assertTrue((df["source_patient_id"] == "TCGA-02-0016").all())

    # 8. Output Validation Catches Self-Patient Row
    def test_08_final_output_validation_catches_self_patient(self):
        bad_df = pd.DataFrame([
            {"query_patient_id": "TCGA-02-0003", "source_patient_id": "TCGA-02-0016"},
            {"query_patient_id": "TCGA-02-0003", "source_patient_id": "TCGA-02-0003"},
        ])
        with self.assertRaises(AssertionError):
            assert_final_output_loo_clean(bad_df, "TCGA-02-0003", strict_loo=True)

    # 9. Output Validation Catches Missing or Unresolved Source ID
    def test_09_final_output_validation_catches_missing_or_unresolved_source(self):
        missing_df = pd.DataFrame([
            {"query_patient_id": "TCGA-02-0003", "source_patient_id": None},
        ])
        with self.assertRaises(AssertionError):
            assert_final_output_loo_clean(missing_df, "TCGA-02-0003", strict_loo=True)

        unresolved_df = pd.DataFrame([
            {"query_patient_id": "TCGA-02-0003", "source_patient_id": "NON_TCGA_ID"},
        ])
        with self.assertRaises(AssertionError):
            assert_final_output_loo_clean(unresolved_df, "TCGA-02-0003", strict_loo=True)

    # 10. Top-K Count Preserved
    def test_10_top_k_count(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        self._create_mock_h5("slide1.h5", "TCGA-02-0016-01A", "slide1", np.random.randn(20, 768))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=7,
            exclude_query_patient=True,
            strict_loo=True,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        self.assertEqual(len(df), 7)

    # 11. Explicit Deterministic Ordering under Tied Cosine Scores (Requirement A & K)
    def test_11_explicit_deterministic_ordering_tied_scores(self):
        q_vec = np.zeros((1, 768), dtype=np.float32)
        q_vec[0, 0] = 1.0

        feats = np.zeros((3, 768), dtype=np.float32)
        feats[:, 0] = 1.0

        # Create 2 H5 files with IDENTICAL features (exact unit vectors -> identical cosine score 1.0)
        # slide_b.h5 named alphabetically after slide_a.h5
        self._create_mock_h5("slide_a.h5", "TCGA-02-0016", "slide_a", feats)
        self._create_mock_h5("slide_b.h5", "TCGA-02-0026", "slide_b", feats)

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=6,
            exclude_query_patient=True,
            strict_loo=True,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        self.assertEqual(len(df), 6)

        # Assert score DESC, h5_path ASC, patch_index ASC
        # slide_a.h5 (h5_path ASC) must precede slide_b.h5
        slide_a_rows = df[df["h5_path"].str.endswith("slide_a.h5")]
        slide_b_rows = df[df["h5_path"].str.endswith("slide_b.h5")]

        self.assertEqual(slide_a_rows.iloc[0]["rank"], 1)
        self.assertEqual(slide_b_rows.iloc[0]["rank"], 4)

        # Within slide_a and slide_b, patch_index must be ASC (0, 1, 2)
        self.assertEqual(list(slide_a_rows["patch_index"]), [0, 1, 2])
        self.assertEqual(list(slide_b_rows["patch_index"]), [0, 1, 2])

    # 12. H5 Bank Audit Accounting Invariants (Requirement F)
    def test_12_bank_audit_accounting_invariants(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        self._create_mock_h5("slide1.h5", "TCGA-02-0003", "slide1", np.ones((5, 768))) # self
        self._create_mock_h5("slide2.h5", "TCGA-02-0016", "slide2", np.ones((5, 768))) # eligible searched
        self._create_mock_h5("slide3.h5", "UNKNOWN_PATIENT", "slide3", np.ones((5, 768))) # invalid unresolvable

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=True,
        )

        audit = summary["bank_audit"]
        self.assertEqual(audit["total_h5_files"], 3)
        self.assertEqual(audit["invalid_h5_files"], 1)
        self.assertEqual(audit["eligible_h5_files"], 2)
        self.assertEqual(audit["excluded_self_h5_files"], 1)
        self.assertEqual(audit["searched_h5_files"], 1)
        self.assertEqual(audit["skipped_unresolved_h5_files"], 1)
        self.assertEqual(audit["excluded_self_patch_candidates"], 5)

        # Assert mathematical invariants
        self.assertEqual(audit["eligible_h5_files"], audit["total_h5_files"] - audit["invalid_h5_files"])
        self.assertEqual(audit["eligible_h5_files"], audit["excluded_self_h5_files"] + audit["searched_h5_files"])
        self.assertEqual(audit["total_h5_files"], audit["invalid_h5_files"] + audit["eligible_h5_files"])

    # 13. Real Fallback Canvas Patch Retrieval (Requirement J)
    def test_13_canvas_fallback_real_patch_retrieval(self):
        # Create synthetic internal database CSV & patch bank DataFrame
        db_df = pd.DataFrame([
            {"patient_id": "TCGA-02-0003", "feat_0": 1.0, "feat_1": 0.0}, # query patient
            {"patient_id": "TCGA-02-0016", "feat_0": 0.9, "feat_1": 0.1}, # other patient
        ])

        patch_df = pd.DataFrame([
            {"patient_id": "TCGA-02-0003", "patch_path": "/fake/TCGA-02-0003/patch1.jpg"},
            {"patient_id": "TCGA-02-0016", "patch_path": "/fake/TCGA-02-0016/patch1.jpg"},
            {"patient_id": "TCGA-02-0026", "patch_path": "/fake/TCGA-02-0026/patch1.jpg"},
            {"patient_id": "TCGA-02-0026", "patch_path": "/fake/TCGA-02-0026/patch2.jpg"},
        ])

        pred_vec = np.array([1.0, 0.0], dtype=np.float32)

        with patch("pandas.read_csv", return_value=db_df), \
             patch("cns_multimodalai.inference.retrieve_morphology_canvas.select_ctranspath_feature_cols", return_value=["feat_0", "feat_1"]), \
             patch("cns_multimodalai.inference.retrieve_morphology_canvas.build_clean_patch_bank", return_value=patch_df):

            paths, ret_df = retrieve_real_patches_from_predicted_image_embedding(
                pred_img_embedding=pred_vec,
                n_patches=3, # Request 3 patches: TCGA-02-0016 only has 1 patch, forcing fallback for remaining 2!
                query_patient_id="TCGA-02-0003",
                exclude_query_patient=True,
                strict_loo=True,
            )

            # Verify 3 patches retrieved
            self.assertEqual(len(paths), 3)
            # Verify ZERO patches belong to query patient TCGA-02-0003
            for p in paths:
                self.assertNotIn("TCGA-02-0003", p)
            # Verify ret_df source patient IDs
            self.assertNotIn("TCGA-02-0003", ret_df["source_patient_id"].tolist())

    # 14. Canvas Strict LOO Missing Query ID Fails (Requirement I)
    def test_14_canvas_strict_loo_missing_query_id_fails(self):
        with self.assertRaises(ValueError):
            retrieve_real_patches_from_predicted_image_embedding(
                pred_img_embedding=np.zeros(768),
                query_patient_id=None,
                strict_loo=True,
            )

    # 15. Generic Non-LOO Backward Compatibility (Requirement M)
    def test_15_generic_non_loo_backward_compatibility(self):
        q_vec = np.ones((1, 768), dtype=np.float32)
        self._create_mock_h5("slide1.h5", "TCGA-02-0003", "slide1", np.ones((5, 768)))

        # Default args: exclude_query_patient=False, strict_loo=False
        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
        )

        df = pd.read_csv(summary["retrieval_csv"])
        # Self patient retrieved under default non-LOO mode
        self.assertIn("TCGA-02-0003", df["source_patient_id"].tolist())

    # 16. H5 Processing Exception Accounting (Item 1 & 8)
    def test_16_h5_processing_exception_accounting(self):
        q_vec = np.ones((1, 768), dtype=np.float32)

        # Create H5 with feature dataset having WRONG feature dimension (512 vs expected 768)
        # This passes initial dataset presence check, but fails dimension validation inside loop!
        h5_path = self.tmp_path / "corrupted_dim.h5"
        with h5py.File(h5_path, "w") as h:
            h.attrs["patient_id"] = "TCGA-02-0016"
            h.attrs["slide_id"] = "slide_corrupt"
            h.create_dataset("features", data=np.ones((5, 512), dtype=np.float32))
            h.create_dataset("coords_level0", data=np.zeros((5, 2), dtype=np.int32))

        # Create 1 valid H5
        self._create_mock_h5("valid_slide.h5", "TCGA-02-0026", "valid_slide", np.ones((5, 768)))

        summary = run_reference_morphology_retrieval(
            query_embedding=q_vec,
            query_patient_id="TCGA-02-0003",
            output_dir=self.tmp_path / "out",
            h5_dir=str(self.tmp_path),
            top_k=5,
            exclude_query_patient=True,
            strict_loo=False,
        )

        audit = summary["bank_audit"]
        self.assertEqual(audit["total_h5_files"], 2)
        self.assertEqual(audit["invalid_h5_files"], 1)
        self.assertEqual(audit["searched_h5_files"], 1) # Corrupted H5 must NOT be counted as searched!
        self.assertEqual(audit["eligible_h5_files"], 1)

        # Assert accounting invariants
        self.assertEqual(audit["eligible_h5_files"], audit["total_h5_files"] - audit["invalid_h5_files"])
        self.assertEqual(audit["eligible_h5_files"], audit["excluded_self_h5_files"] + audit["searched_h5_files"])
        self.assertEqual(audit["total_h5_files"], audit["invalid_h5_files"] + audit["eligible_h5_files"])


if __name__ == "__main__":
    unittest.main()
