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
}

export interface PatchApiResponse {
  status: "uploaded" | "completed" | "failed";
  run_dir?: string;
  n_images_found?: number;
  bytes_saved?: number;
  warning?: string;
  inference_enabled?: boolean;
  inference_result?: Record<string, unknown> | null;
  prediction_preview?: PatchPredictionPreview | null;
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
        <div
          className="info-box info"
          style={{ marginTop: 12 }}
        >
          {data.note}
        </div>
      )}

      {/* Download links */}
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
  onResult?: (data: PatchApiResponse) => void;
}

export default function PatchUpload({ onResult }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PatchApiResponse | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback((f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".zip")) {
      setError("Please select a .zip archive.");
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      handleFile(e.dataTransfer.files[0] ?? null);
    },
    [handleFile]
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("No file selected.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("run_model", "true");

    try {
      const res = await fetch(`${API_BASE}/api/infer/patches`, {
        method: "POST",
        body: fd,
      });

      const data: PatchApiResponse = await res.json();

      if (!res.ok) {
        const detail = (data as unknown as { detail?: string }).detail;
        throw new Error(detail ?? `HTTP ${res.status}`);
      }

      setResult(data);
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
              onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
              disabled={loading}
              aria-label="Select patch ZIP file"
            />
            <div className="upload-icon">🗜️</div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              Drag &amp; drop or{" "}
              <strong style={{ color: "var(--teal-400)" }}>browse</strong> for a
              ZIP
            </div>
            <div className="upload-hint">
              .jpg/.png/.tif patches · max 2 GB
            </div>
            {file && (
              <div className="upload-filename">✓ {file.name}</div>
            )}
          </div>

          {/* Buttons */}
          <div className="btn-row">
            <button
              id="btn-run-patches"
              type="submit"
              className="btn btn-primary"
              disabled={loading || !file}
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
            {file && !loading && (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => {
                  setFile(null);
                  setError(null);
                  setResult(null);
                }}
              >
                ✕ Clear
              </button>
            )}
          </div>
        </form>

        {/* Loading banner */}
        {loading && (
          <div className="loading-banner" role="status" aria-live="polite">
            <span
              className="spinner"
              style={{ marginTop: 2, flexShrink: 0 }}
            />
            <div className="loading-banner-body">
              <div className="loading-banner-title">
                Running patch-based image inference…
              </div>
              <div className="loading-banner-sub">
                Running patch-based image inference. This may take 1–3&nbsp;minutes
                depending on patch count and GPU availability. Please keep this
                tab open.
              </div>
            </div>
          </div>
        )}

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

      {/* Result card — rendered below the upload card */}
      {result && !loading && <PatchResultCard data={result} />}
    </div>
  );
}
