"use client";

import { useState, useCallback } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// ── Response types ────────────────────────────────────────────────────────

export interface PatchPredictionPreview {
  predicted_class?: string | null;
  prob_GBM_like?: number | null;
  predicted_label?: number | null;
  n_patches?: number | null;
  train_accuracy_internal?: number | null;
  train_balanced_accuracy_internal?: number | null;
}

export interface PatchResultFiles {
  prediction_url?: string | null;
  embedding_url?: string | null;
  report_url?: string | null;
  molecular_json_url?: string | null;
  molecular_report_url?: string | null;
  molecular_top_features_url?: string | null;
  clinical_relevance_json_url?: string | null;
  clinical_relevance_report_url?: string | null;
  gene_expression_matrix_url?: string | null;
  gene_pathway_matrix_url?: string | null;
  gene_pathway_predictions_url?: string | null;
  gene_pathway_top_features_url?: string | null;
  gene_pathway_report_url?: string | null;
  wsi_thumbnail_url?: string | null;
  wsi_tissue_mask_url?: string | null;
  wsi_patch_overlay_url?: string | null;
  wsi_patch_overlay_dzi_url?: string | null;
  wsi_coordinate_mosaic_url?: string | null;
  wsi_coordinate_mosaic_dzi_url?: string | null;
  wsi_spatial_contact_sheet_url?: string | null;
  wsi_spatial_contact_sheet_dzi_url?: string | null;
  wsi_visualization_summary_url?: string | null;
}

export interface PatchTopFeature {
  feature_name?: string;
  feature_type?: string;
  predicted_direction?: string;
  relative_score?: number | null;
  interpretation?: string;
  evidence_basis?: string;
}

export interface PatchMolecularOutput {
  output_type?: string;
  top_features?: PatchTopFeature[];
  caution?: string;
}

export interface PatchClinicalRelevance {
  workflow?: string;
  predicted_class?: string;
  prob_GBM_like?: string;
  research_summary?: string;
  research_direction?: string;
  model_scope?: string;
  caution?: string;
}

export interface ImageToMolecular {
  primary_interpretation_category?: string | null;
  candidate_molecular_signals?: string[];
  interpretation?: string | null;
  predicted_molecular_output?: PatchMolecularOutput | null;
  caution?: string | null;
  phase11a_context?: string[];
}

export interface PatchApiResponse {
  status: "uploaded" | "completed" | "failed";
  run_dir?: string;
  n_images_found?: number;
  wsi_extraction?: { n_patches_saved?: number };
  bytes_saved?: number;
  warning?: string;
  inference_enabled?: boolean;
  inference_result?: Record<string, unknown> | null;
  prediction_preview?: PatchPredictionPreview | null;
  image_to_molecular?: ImageToMolecular | null;
  clinical_relevance?: PatchClinicalRelevance | null;
  result_files?: PatchResultFiles | null;
  error?: string;
  note?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function absUrl(rel?: string | null): string | null {
  if (!rel) return null;
  return `${API_BASE}${rel}`;
}

function isNetworkError(msg: string): boolean {
  const lower = msg.toLowerCase();
  return (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("cors") ||
    lower.includes("econnrefused") ||
    lower.includes("load failed")
  );
}

function probBar(prob: number) {
  const pct = Math.round(prob * 100);
  const color = prob >= 0.5 ? "var(--amber-500)" : "var(--teal-400)";
  return (
    <div style={{ marginTop: 6 }}>
      <div
        style={{
          height: 6,
          borderRadius: 99,
          background: "var(--bg-surface)",
          overflow: "hidden",
          border: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            transition: "width 0.5s ease",
            borderRadius: 99,
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "0.68rem",
          color: "var(--text-muted)",
          marginTop: 3,
        }}
      >
        <span>LGG-like</span>
        <span>GBM-like</span>
      </div>
    </div>
  );
}

// ── Molecular output table ────────────────────────────────────────────────

function MolecularOutputTable({ mol }: { mol: PatchMolecularOutput }) {
  const features = mol.top_features ?? [];
  if (features.length === 0) return null;

  return (
    <div>
      {/* Safe wording disclaimer */}
      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--text-muted)",
          fontStyle: "italic",
          marginBottom: 10,
          lineHeight: 1.5,
        }}
      >
        Gene-expression-like molecular profile inferred from histology embeddings.
        Computational prediction; not measured RNA-seq.
        Relative scores are derived from image embedding similarity, not expression counts.
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="prediction-table" style={{ fontSize: "0.76rem" }}>
          <thead>
            <tr>
              <th>Feature / pathway / program</th>
              <th>Type</th>
              <th>Direction</th>
              <th>Relative score</th>
              <th>Interpretation</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f, i) => {
              const isHigh = f.predicted_direction === "high";
              return (
                <tr key={i}>
                  <td style={{ fontFamily: "var(--font-sans)", fontWeight: 500, color: "var(--text-primary)" }}>
                    {f.feature_name ?? "—"}
                  </td>
                  <td>
                    <span
                      style={{
                        fontSize: "0.68rem",
                        background: "rgba(148,163,184,0.08)",
                        border: "1px solid var(--border)",
                        borderRadius: "var(--r-sm)",
                        padding: "1px 6px",
                        color: "var(--text-secondary)",
                      }}
                    >
                      {f.feature_type ?? "—"}
                    </span>
                  </td>
                  <td>
                    <span
                      style={{
                        fontWeight: 600,
                        color: isHigh ? "var(--amber-500)" : "var(--teal-400)",
                        fontSize: "0.72rem",
                      }}
                    >
                      {f.predicted_direction ?? "—"}
                    </span>
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", color: "var(--teal-300)" }}>
                    {f.relative_score != null ? f.relative_score.toFixed(4) : "—"}
                  </td>
                  <td style={{ fontSize: "0.73rem", color: "var(--text-secondary)", maxWidth: 260 }}>
                    {f.interpretation ?? "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {mol.caution && (
        <div
          style={{
            marginTop: 8,
            fontSize: "0.70rem",
            color: "var(--text-muted)",
            fontStyle: "italic",
          }}
        >
          ⚠ {mol.caution}
        </div>
      )}
    </div>
  );
}

// ── Patch clinical relevance panel ────────────────────────────────────────

function PatchClinicalRelevancePanel({ cr }: { cr: PatchClinicalRelevance }) {
  const isGbm = cr.predicted_class?.toLowerCase().includes("gbm");
  const dirColor = isGbm ? "var(--amber-500)" : "var(--teal-400)";

  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-md)",
        padding: "14px 18px",
      }}
    >
      {/* Direction badge */}
      {cr.research_direction && (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            background: isGbm ? "var(--amber-bg)" : "var(--teal-glow)",
            border: `1px solid ${isGbm ? "rgba(245,158,11,0.30)" : "rgba(20,184,166,0.30)"}`,
            borderRadius: "var(--r-sm)",
            padding: "4px 10px",
            fontSize: "0.78rem",
            fontWeight: 600,
            color: dirColor,
            marginBottom: 10,
          }}
        >
          {isGbm ? "⚡" : "🧠"} {cr.research_direction}
        </div>
      )}

      {/* Research summary */}
      {cr.research_summary && (
        <p
          style={{
            fontSize: "0.79rem",
            color: "var(--text-secondary)",
            lineHeight: 1.6,
            marginBottom: 8,
          }}
        >
          {cr.research_summary}
        </p>
      )}

      {/* Scope + caution row */}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 6 }}>
        {cr.model_scope && (
          <span
            style={{
              fontSize: "0.70rem",
              color: "var(--text-muted)",
              background: "rgba(148,163,184,0.06)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-sm)",
              padding: "2px 8px",
            }}
          >
            Scope: {cr.model_scope}
          </span>
        )}
        {cr.caution && (
          <span
            style={{
              fontSize: "0.70rem",
              color: "var(--text-muted)",
              fontStyle: "italic",
              flex: 1,
            }}
          >
            ⚠ {cr.caution}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Patch result sub-component ────────────────────────────────────────────

function PatchResultCard({ data }: { data: PatchApiResponse }) {
  const preview = data.prediction_preview;
  const files = data.result_files;


  const statusClass =
    data.status === "completed"
      ? "pill-success"
      : data.status === "failed"
      ? "pill-error"
      : "pill-dim";

  const statusLabel =
    data.status === "completed"
      ? "✓ Completed"
      : data.status === "failed"
      ? "✗ Failed"
      : "⟳ Uploaded";

  return (
    <div className="card" id="patch-result-card" style={{ marginTop: 20 }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 14,
          flexWrap: "wrap",
        }}
      >
        <span className={`pill ${statusClass}`}>{statusLabel}</span>
        {data.inference_enabled && (
          <span className="pill pill-dim">Model: Phase 14 Patch</span>
        )}
        {data.n_images_found != null && (
          <span className="pill pill-dim">{data.n_images_found} images found</span>
        )}
      </div>

      {/* Research disclaimer */}
      <div className="canvas-retrieval-note" style={{ marginBottom: 14 }}>
        <span style={{ fontSize: "1rem", flexShrink: 0 }}>🔬</span>
        <span>
          <strong>Image-to-report output:</strong> this is a research
          interpretation from histology patch embeddings, not a clinical
          diagnosis. Results are GBM-like vs LGG-like similarity only.
        </span>
      </div>

      {/* Error */}
      {data.status === "failed" && data.error && (
        <div className="info-box" style={{ marginBottom: 14 }} role="alert">
          {data.error}
        </div>
      )}

      {/* Stat blocks */}
      {preview && (
        <div className="result-grid">
          <div className="stat-block">
            <div className="stat-label">Predicted Class</div>
            <div
              className={`stat-value large ${
                preview.predicted_class?.toLowerCase().includes("gbm")
                  ? "class-gbm"
                  : "class-lgg"
              }`}
            >
              {preview.predicted_class ?? "—"}
            </div>
          </div>

          <div className="stat-block">
            <div className="stat-label">P(GBM-like)</div>
            <div className="stat-value large">
              {preview.prob_GBM_like != null
                ? preview.prob_GBM_like.toFixed(4)
                : "—"}
            </div>
            {preview.prob_GBM_like != null && probBar(preview.prob_GBM_like)}
          </div>

          <div className="stat-block">
            <div className="stat-label">Images Found</div>
            <div className="stat-value">{data.n_images_found ?? "—"}</div>
            <div className="stat-sub">in uploaded ZIP</div>
          </div>

          <div className="stat-block">
            <div className="stat-label">Patches Used</div>
            <div className="stat-value">{preview.n_patches ?? "—"}</div>
            <div className="stat-sub">
              {preview.train_accuracy_internal != null
                ? `internal acc: ${(preview.train_accuracy_internal * 100).toFixed(1)}%`
                : "by model"}
            </div>
          </div>
        </div>
      )}

      {/* Upload-only note (run_model=false) */}
      {data.status === "uploaded" && data.note && (
        <div className="info-box info" style={{ marginTop: 12 }}>
          {data.note}
        </div>
      )}

      {/* ── Predicted Molecular Signature from Image ───────────────────── */}
      {data.image_to_molecular && (
        <>
          <div className="section-label" style={{ marginTop: 24 }}>
            Predicted Molecular Signature from Image
          </div>

          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-md)",
              padding: "18px 20px",
            }}
          >
            {/* Primary category badge */}
            {data.image_to_molecular.primary_interpretation_category && (
              <div style={{ marginBottom: 14 }}>
                <div className="stat-label" style={{ marginBottom: 5 }}>
                  Primary Interpretation Category
                </div>
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    background: "var(--teal-glow)",
                    border: "1px solid rgba(20,184,166,0.30)",
                    borderRadius: "var(--r-sm)",
                    padding: "5px 12px",
                    fontSize: "0.84rem",
                    fontWeight: 600,
                    color: "var(--teal-300)",
                  }}
                >
                  🧬 {data.image_to_molecular.primary_interpretation_category}
                </div>
              </div>
            )}

            {/* Interpretation paragraph */}
            {data.image_to_molecular.interpretation && (
              <div style={{ marginBottom: 14 }}>
                <div className="stat-label" style={{ marginBottom: 5 }}>Interpretation</div>
                <p
                  style={{
                    fontSize: "0.82rem",
                    color: "var(--text-secondary)",
                    lineHeight: 1.65,
                  }}
                >
                  {data.image_to_molecular.interpretation}
                </p>
              </div>
            )}

            {/* Candidate molecular signals */}
            {data.image_to_molecular.candidate_molecular_signals &&
              data.image_to_molecular.candidate_molecular_signals.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div className="stat-label" style={{ marginBottom: 6 }}>
                  Candidate Molecular / Signature Signals
                </div>
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 20,
                    listStyle: "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: 5,
                  }}
                >
                  {data.image_to_molecular.candidate_molecular_signals.map(
                    (sig, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: "0.80rem",
                          color: "var(--text-primary)",
                          display: "flex",
                          alignItems: "flex-start",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            color: "var(--teal-400)",
                            flexShrink: 0,
                            fontWeight: 700,
                            fontSize: "0.75rem",
                            marginTop: 2,
                          }}
                        >
                          ▸
                        </span>
                        {sig}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}

            {/* Research caution */}
            {data.image_to_molecular.caution && (
              <div className="warning-banner" style={{ marginBottom: 0, marginTop: 4 }}>
                <span className="warning-icon">⚠️</span>
                <p className="warning-text" style={{ fontSize: "0.74rem" }}>
                  {data.image_to_molecular.caution}
                </p>
              </div>
            )}
          </div>

          {/* Phase 11A context — collapsible */}
          {data.image_to_molecular.phase11a_context &&
            data.image_to_molecular.phase11a_context.length > 0 && (
            <details style={{ marginTop: 10 }}>
              <summary
                style={{
                  cursor: "pointer",
                  fontSize: "0.73rem",
                  color: "var(--text-muted)",
                  userSelect: "none",
                  padding: "2px 0",
                }}
              >
                ▸ Phase 11A context
              </summary>
              <ul
                style={{
                  margin: "8px 0 0",
                  paddingLeft: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                  listStyle: "none",
                }}
              >
                {data.image_to_molecular.phase11a_context.map((ctx, i) => (
                  <li
                    key={i}
                    style={{
                      fontSize: "0.73rem",
                      color: "var(--text-muted)",
                      display: "flex",
                      gap: 7,
                    }}
                  >
                    <span style={{ color: "var(--border-bright)", flexShrink: 0 }}>—</span>
                    {ctx}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}

      {/* ── Predicted Molecular Output from Image (table) ────────────── */}
      {data.image_to_molecular?.predicted_molecular_output && (
        <>
          <div className="section-label" style={{ marginTop: 22 }}>
            Predicted Molecular Output from Image
          </div>
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-md)",
              padding: "16px 18px",
            }}
          >
            <MolecularOutputTable mol={data.image_to_molecular.predicted_molecular_output} />
          </div>
        </>
      )}

      {/* ── Clinical / Research Relevance ─────────────────────────────── */}
      {data.clinical_relevance && (
        <>
          <div className="section-label" style={{ marginTop: 22 }}>
            Clinical / Research Relevance
          </div>
          <PatchClinicalRelevancePanel cr={data.clinical_relevance} />
        </>
      )}

      {/* ── Download links ─────────────────────────────────────────────── */}
      {files && (
        <>
          <div className="section-label" style={{ marginTop: 20 }}>
            Result files
          </div>
          <div className="download-links">
            {files.prediction_url && (
              <a
                className="dl-link"
                href={absUrl(files.prediction_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-patch-prediction"
              >
                ⬇ Prediction CSV
              </a>
            )}
            {files.embedding_url && (
              <a
                className="dl-link"
                href={absUrl(files.embedding_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-patch-embedding"
              >
                ⬇ Mean Embedding CSV
              </a>
            )}
            {files.report_url && (
              <a
                className="dl-link"
                href={absUrl(files.report_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-patch-report"
              >
                📄 Inference Report
              </a>
            )}
            {files.molecular_json_url && (
              <a
                className="dl-link"
                href={absUrl(files.molecular_json_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-molecular-json"
              >
                🧬 Molecular JSON
              </a>
            )}
            {files.molecular_report_url && (
              <a
                className="dl-link"
                href={absUrl(files.molecular_report_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-molecular-report"
              >
                📋 Molecular Report
              </a>
            )}
            {files.molecular_top_features_url && (
              <a
                className="dl-link"
                href={absUrl(files.molecular_top_features_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-top-features"
              >
                ⬇ Top Features CSV
              </a>
            )}
            {files.clinical_relevance_json_url && (
              <a
                className="dl-link"
                href={absUrl(files.clinical_relevance_json_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-clin-relevance-json"
              >
                🏥 Clinical Relevance JSON
              </a>
            )}
            {files.clinical_relevance_report_url && (
              <a
                className="dl-link"
                href={absUrl(files.clinical_relevance_report_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-clin-relevance-report"
              >
                📋 Clinical Relevance Report
              </a>
            )}
          </div>
        </>
      )}

      {/* Raw metadata collapsible */}
      <details style={{ marginTop: 16 }}>
        <summary
          style={{
            cursor: "pointer",
            fontSize: "0.72rem",
            color: "var(--text-muted)",
            userSelect: "none",
            padding: "2px 0",
          }}
        >
          ▸ Raw run metadata
        </summary>
        <pre
          style={{
            marginTop: 6,
            padding: 12,
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--r-md)",
            fontSize: "0.70rem",
            color: "var(--text-secondary)",
            fontFamily: "var(--font-mono)",
            overflowX: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            maxHeight: 320,
            overflowY: "auto",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}

// ── Main PatchUpload component ────────────────────────────────────────────

interface Props {
  onResult?: (data: any) => void;
  onRunStart?: (filename: string) => void;
}

export default function PatchUpload({ onResult, onRunStart }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [isBatchMode, setIsBatchMode] = useState(false);

  const handleFiles = useCallback(
    (newFiles: FileList | File[] | null) => {
      if (!newFiles || newFiles.length === 0) return;
      const validFiles = Array.from(newFiles).filter((f) =>
        f.name.toLowerCase().endsWith(".zip")
      );
      
      if (validFiles.length === 0) {
        setError("Please select at least one .zip archive.");
        return;
      }
      
      setError(null);
      if (isBatchMode) {
        setFiles((prev) => [...prev, ...validFiles]);
      } else {
        setFiles([validFiles[0]]);
      }
    },
    [isBatchMode]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );
  
  const removeFile = (idx: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) {
      setError("No file selected.");
      return;
    }

    setLoading(true);
    setError(null);
    onRunStart?.(isBatchMode ? `Batch (${files.length} ZIPs)` : files[0].name);

    const fd = new FormData();
    files.forEach((f) => fd.append(isBatchMode ? "files" : "file", f));
    fd.append("run_model", "true");

    try {
      const endpoint = isBatchMode ? "/api/infer/patches/batch" : "/api/infer/patches";
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        body: fd,
      });

      const data = await res.json();

      if (!res.ok) {
        const detail = (data as unknown as { detail?: string }).detail;
        throw new Error(detail ?? `HTTP ${res.status}`);
      }

      onResult?.(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">🔬 Patch Image Inference</div>
        <p className="card-desc">
          Upload a ZIP archive of histology patch images (224×224 px, JPG/PNG/TIF).
          The backend extracts CTransPath embeddings and classifies GBM-like
          vs LGG-like morphology.
        </p>

        {/* Mode Selector */}
        <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
          <label className="option-item" style={{ cursor: "pointer" }}>
            <input type="radio" name="patchMode" checked={!isBatchMode} onChange={() => { setIsBatchMode(false); setFiles(files.slice(0, 1)); }} disabled={loading} />
            Single ZIP
          </label>
          <label className="option-item" style={{ cursor: "pointer" }}>
            <input type="radio" name="patchMode" checked={isBatchMode} onChange={() => setIsBatchMode(true)} disabled={loading} />
            Batch ZIP
          </label>
        </div>

        {isBatchMode && (
          <div className="info-box info" style={{ marginBottom: 16 }}>
            For batch mode, the ZIP must contain <strong>one folder per sample</strong>.<br/>
            Example: <code>sample_A/*.png</code>, <code>sample_B/*.png</code>.
          </div>
        )}

        <form onSubmit={submit}>
          {/* Drop zone */}
          <div
            className={`upload-zone${dragOver ? " drag-over" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              id="patch-file-input"
              type="file"
              accept=".zip"
              multiple={isBatchMode}
              onChange={(e) => handleFiles(e.target.files)}
              disabled={loading}
              aria-label="Select patch ZIP file"
            />
            <div className="upload-icon">🗜️</div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Drag &amp; drop or <strong style={{ color: "var(--teal-400)" }}>browse</strong> for {isBatchMode ? "ZIP archives" : "a ZIP archive"}
            </div>
            <div className="upload-hint">
              .jpg/.png/.tif patches · max 2 GB
            </div>
          </div>

          {/* Selected files list */}
          {files.length > 0 && (
            <div style={{ marginTop: 12, marginBottom: 16, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-sm)", padding: "10px 14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                  Selected ZIPs ({files.length})
                </div>
                {isBatchMode && files.length > 1 && (
                  <button type="button" onClick={() => setFiles([])} style={{ fontSize: "0.75rem", background: "none", border: "none", color: "var(--red-400)", cursor: "pointer", padding: 0 }}>
                    Clear All
                  </button>
                )}
              </div>
              <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 4 }}>
                {files.map((f, idx) => (
                  <li key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>✓ {f.name}</span>
                    <button type="button" onClick={() => removeFile(idx)} style={{ fontSize: "0.75rem", background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: "0 4px" }}>✕</button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Buttons */}
          <div className="btn-row">
            <button
              id="btn-run-patches"
              type="submit"
              className="btn btn-primary"
              disabled={loading || files.length === 0}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  Running…
                </>
              ) : (
                <>▶ Run Patch Analysis</>
              )}
            </button>
            {files.length > 0 && !loading && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => { setFiles([]); setError(null); }}
              >
                ✕ Clear
              </button>
            )}
          </div>
        </form>

        {/* Error card */}
        {error && !loading && (
          <div className="error-card" role="alert">
            <div className="error-card-title">⚠ Request failed</div>
            <div className="error-card-hint">
              {isNetworkError(error)
                ? "Could not reach the backend. Make sure uvicorn is running on port 8000."
                : "The backend returned an error. See technical details below."}
            </div>
            <details>
              <summary>Technical details</summary>
              <pre>{error}</pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
