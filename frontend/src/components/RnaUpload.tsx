"use client";

import { useState, useCallback } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

/** Shape returned by POST /api/infer/rna */
export interface RnaApiResponse {
  status: "uploaded" | "completed" | "failed";
  run_dir?: string;
  bytes_saved?: number;
  warning?: string;
  inference_enabled?: boolean;
  canvas_enabled?: boolean;
  inference_result?: Record<string, unknown> | null;
  prediction_preview?: PredictionRow[];
  result_files?: ResultFiles;
  clinical_relevance?: ClinicalRelevance | null;
  reference_morphology?: ReferenceMorphology | null;
  error?: string;
}

export interface ReferenceMorphology {
  status: string;
  method: string;
  top_k: number;
  patch_images_extracted: number;
  unique_source_slides: number;
  best_similarity_score: number;
  mean_top_similarity_score: number;
  warning: string;
}

export interface ClinicalRelevance {
  workflow?: string;
  predicted_class?: string;
  prob_GBM_like?: string;
  research_summary?: string;
  research_direction?: string;
  model_scope?: string;
  caution?: string;
}

export interface PredictionRow {
  patient_id?: string;
  prob_GBM_like?: number;
  predicted_label?: number;
  predicted_class?: string;
  expression_strategy?: string;
  shared_gene_count?: number;
  selected_gene_count?: number;
}

export interface ResultFiles {
  predictions_url?: string | null;
  report_url?: string | null;
  canvas_index_url?: string | null;
  canvas_files?: CanvasFile[];
  reference_morphology_top_panel_url?: string | null;
  reference_morphology_source_panel_url?: string | null;
  reference_morphology_coordinate_layout_url?: string | null;
  reference_morphology_retrieval_csv_url?: string | null;
  reference_morphology_summary_url?: string | null;
}

export interface CanvasFile {
  patient_id?: string;
  canvas_url?: string | null;
  retrieval_csv_url?: string | null;
  note?: string;
}

interface Props {
  onResult: (data: RnaApiResponse) => void;
  onRunStart?: (filename: string) => void;
}

/** Returns true if the message looks like a network/CORS failure rather than
 *  a backend application error. */
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

export default function RnaUpload({ onResult, onRunStart }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [runModel, setRunModel] = useState(true);
  const [makeCanvas, setMakeCanvas] = useState(true);
  const [runReferenceMorphology, setRunReferenceMorphology] = useState(true);
  const [maxCases, setMaxCases] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback((f: File | null) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a .csv file.");
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const dropped = e.dataTransfer.files[0] ?? null;
      handleFile(dropped);
    },
    [handleFile]
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) { setError("No file selected."); return; }

    setLoading(true);
    setError(null);
    onRunStart?.(file.name);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("run_model", String(runModel));
    fd.append("make_canvas", String(makeCanvas));
    fd.append("run_reference_morphology", String(runReferenceMorphology));
    fd.append("max_cases", String(maxCases));

    try {
      const res = await fetch(`${API_BASE}/api/infer/rna`, {
        method: "POST",
        body: fd,
      });

      const data: RnaApiResponse = await res.json();

      if (!res.ok) {
        const detail = (data as unknown as { detail?: string }).detail;
        throw new Error(detail ?? `HTTP ${res.status}`);
      }

      onResult(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="card-title">🧬 RNA-seq Inference</div>
      <p className="card-desc">
        Upload a patient-level expression CSV (rows = patients, columns = gene IDs /
        patient_id). The system accepts multi-row CSVs for batch processing.
        The backend runs the frozen Phase&nbsp;14 GBM/LGG-like model.
      </p>

      <form onSubmit={submit}>
        {/* Drop zone */}
        <div
          className={`upload-zone${dragOver ? " drag-over" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            id="rna-file-input"
            type="file"
            accept=".csv"
            onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
            disabled={loading}
            aria-label="Select RNA-seq CSV file"
          />
          <div className="upload-icon">📄</div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Drag &amp; drop or <strong style={{ color: "var(--teal-400)" }}>browse</strong> for a CSV
          </div>
          <div className="upload-hint">patient_id + Ensembl gene columns · max 500 MB</div>
          {file && <div className="upload-filename">✓ {file.name}</div>}
        </div>

        {/* Options */}
        <div className="option-row">
          <label className="option-item" htmlFor="cb-run-model">
            <input
              id="cb-run-model"
              type="checkbox"
              checked={runModel}
              onChange={(e) => setRunModel(e.target.checked)}
              disabled={loading}
            />
            Run inference
          </label>
          <label className="option-item" htmlFor="cb-run-ref-morph">
            <input
              id="cb-run-ref-morph"
              type="checkbox"
              checked={runReferenceMorphology}
              onChange={(e) => setRunReferenceMorphology(e.target.checked)}
              disabled={loading}
            />
            Run reference morphology retrieval
          </label>
          <label className="option-item option-item-disabled" htmlFor="cb-batch-mode" style={{ opacity: 0.6 }}>
            <input
              id="cb-batch-mode"
              type="checkbox"
              checked={true}
              disabled={true}
            />
            Batch mode: process multiple rows/samples from one RNA CSV
          </label>
        </div>
        
        <details style={{ marginBottom: 14, marginTop: -4 }}>
          <summary style={{ cursor: "pointer", fontSize: "0.75rem", color: "var(--text-muted)" }}>Legacy Options</summary>
          <div className="option-row" style={{ marginTop: 8 }}>
            <label className="option-item" htmlFor="cb-make-canvas">
              <input
                id="cb-make-canvas"
                type="checkbox"
                checked={makeCanvas}
                onChange={(e) => setMakeCanvas(e.target.checked)}
                disabled={loading}
              />
              Generate legacy morphology canvas
            </label>
            <label className="option-item" htmlFor="sel-max-cases">
            Max cases&nbsp;
            <select
              id="sel-max-cases"
              value={maxCases}
              onChange={(e) => setMaxCases(Number(e.target.value))}
              disabled={loading}
            >
              <option value={1}>1</option>
              <option value={3}>3</option>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </label>
          </div>
        </details>

        {/* Submit */}
        <div className="btn-row">
          <button
            id="btn-run-rna"
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
              <>▶ Run Analysis</>
            )}
          </button>
          {file && !loading && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => { setFile(null); setError(null); }}
            >
              ✕ Clear
            </button>
          )}
        </div>
      </form>

      {/* Loading progress banner */}
      {loading && (
        <div className="loading-banner" role="status" aria-live="polite">
          <span className="spinner" style={{ marginTop: 2, flexShrink: 0 }} />
          <div className="loading-banner-body">
            <div className="loading-banner-title">Running RNA inference…</div>
            <div className="loading-banner-sub">
              Running RNA inference and morphology retrieval. This may take
              1–3&nbsp;minutes depending on canvas generation. Please keep
              this tab open.
            </div>
          </div>
        </div>
      )}

      {/* Clean error card — technical detail hidden in collapsible */}
      {error && !loading && (
        <div className="error-card" role="alert">
          <div className="error-card-title">⚠ Request failed</div>
          <div className="error-card-hint">
            {isNetworkError(error)
              ? "Could not reach the backend. Make sure uvicorn is running on port 8000 and CORS is enabled."
              : "The backend returned an error. See technical details below."}
          </div>
          <details>
            <summary>Technical details</summary>
            <pre>{error}</pre>
          </details>
        </div>
      )}
    </div>
  );
}
