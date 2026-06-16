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
  onResult: (data: any) => void;
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
  const [files, setFiles] = useState<File[]>([]);
  const [runModel, setRunModel] = useState(true);
  const [makeCanvas, setMakeCanvas] = useState(false);
  const [runReferenceMorphology, setRunReferenceMorphology] = useState(false);
  const [maxCases, setMaxCases] = useState<number>(1);
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [batchRefMorphN, setBatchRefMorphN] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (newFiles: FileList | File[] | null) => {
      if (!newFiles || newFiles.length === 0) return;
      const validFiles = Array.from(newFiles).filter((f) =>
        f.name.toLowerCase().endsWith(".csv")
      );
      
      if (validFiles.length === 0) {
        setError("Please select at least one .csv file.");
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
    if (files.length === 0) { setError("No file selected."); return; }

    setLoading(true);
    setError(null);
    onRunStart?.(isBatchMode ? `Batch (${files.length} files)` : files[0].name);

    const fd = new FormData();
    files.forEach((f) => fd.append(isBatchMode ? "files" : "file", f));
    fd.append("run_model", String(runModel));
    fd.append("run_reference_morphology", String(runReferenceMorphology));
    
    if (isBatchMode) {
      fd.append("batch_ref_morph_n", String(batchRefMorphN));
    } else {
      fd.append("make_canvas", String(makeCanvas));
      if (maxCases > 0) fd.append("max_cases", String(maxCases));
    }

    try {
      const endpoint = isBatchMode ? "/api/infer/rna/batch" : "/api/infer/rna";
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        body: fd,
      });

      const data = await res.json();

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
        Upload a patient-level expression CSV. The backend runs the frozen Phase 14 GBM/LGG-like model.
      </p>

      {/* Mode Selector */}
      <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <label className="option-item" style={{ cursor: "pointer" }}>
          <input type="radio" name="rnaMode" checked={!isBatchMode} onChange={() => { setIsBatchMode(false); setFiles(files.slice(0, 1)); }} disabled={loading} />
          Single Sample
        </label>
        <label className="option-item" style={{ cursor: "pointer" }}>
          <input type="radio" name="rnaMode" checked={isBatchMode} onChange={() => setIsBatchMode(true)} disabled={loading} />
          Batch Mode
        </label>
      </div>

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
            multiple={isBatchMode}
            onChange={(e) => handleFiles(e.target.files)}
            disabled={loading}
            aria-label="Select RNA-seq CSV file"
          />
          <div className="upload-icon">📄</div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Drag &amp; drop or <strong style={{ color: "var(--teal-400)" }}>browse</strong> for {isBatchMode ? "CSV files" : "a CSV file"}
          </div>
          <div className="upload-hint">patient_id + Ensembl gene columns · max 500 MB</div>
        </div>

        {/* Selected files list */}
        {files.length > 0 && (
          <div style={{ marginTop: 12, marginBottom: 16, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: "var(--r-sm)", padding: "10px 14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Selected Files ({files.length})
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
          
          {isBatchMode && runReferenceMorphology && (
            <label className="option-item" htmlFor="num-batch-ref-n" style={{ marginLeft: 16 }}>
              for first&nbsp;
              <input 
                id="num-batch-ref-n"
                type="number"
                min={1}
                max={100}
                value={batchRefMorphN}
                onChange={(e) => setBatchRefMorphN(parseInt(e.target.value))}
                disabled={loading}
                style={{ width: 50, padding: "2px 4px" }}
              />
              &nbsp;samples
            </label>
          )}
        </div>
        
        {!isBatchMode && (
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
        )}

        {/* Submit */}
        <div className="btn-row">
          <button
            id="btn-run-rna"
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
              <>▶ Run Analysis</>
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
