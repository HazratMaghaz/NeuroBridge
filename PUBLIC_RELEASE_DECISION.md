# Public Release Decision & Status

## Status: READY_FOR_PUBLIC

### Scientific & Release Audit Summary:
1. **Scientific Validation**: Gene2Morph Leave-One-Patient-Out (LOO) final scientific rerun completed with zero errors ($1800/1800$ rows, $0$ self-patches, $0.8986$ mean peak cosine, $5/6$ diagnosis match). All 16 unit tests PASSING.
2. **Secrets & Security Audit**: PASS. Zero API keys, passwords, or credentials present.
3. **Path Portability**: Refactored `config.py` for dynamic root resolution. Public package code uses portable project-root resolution and contains no developer-specific workstation defaults.
4. **Data Sanitization**: `.gitignore` excludes WSIs, H5 banks, model weights, FASTQ/STAR raw counts.
5. **Sanitized Results**: Public reproducibility summaries stored in `results/public_summary/` using portable identifiers (`source_patient_id`, `source_slide_id`, `patch_index`, `x`, `y`, `score`).
6. **Documentation & Licensing**: Added `THIRD_PARTY_NOTICES.md`, updated `CITATION.cff`, `README.md`, and `PUBLIC_RELEASE_AUDIT.md`.

---

### Release Branch Information:
- **Clean Release Branch**: `release/neurobridge-public-v1`
- **Visibility Recommendation**: Keep GitHub repository PRIVATE until final review ZIP is inspected and confirmed.
