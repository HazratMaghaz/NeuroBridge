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
  error?: string;
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
}

export interface CanvasFile {
  patient_id?: string;
  canvas_url?: string | null;
  retrieval_csv_url?: string | null;
  note?: string;
}

interface Props {
  onResult: (data: RnaApiResponse) => void;
}

export default function RnaUpload({ onResult }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [runModel, setRunModel] = useState(true);
  const [makeCanvas, setMakeCanvas] = useState(true);
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

    const fd = new FormData();
    fd.append("file", file);
    fd.append("run_model", String(runModel));
    fd.append("make_canvas", String(makeCanvas));
    fd.append("max_cases", String(maxCases));

    try {
      const res = await fetch(`${API_BASE}/api/infer/rna`, {
        method: "POST",
        body: fd,
      });

      const data: RnaApiResponse = await res.json();

      if (!res.ok) {
        // FastAPI 400 etc — detail field
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
        patient_id). The backend runs the frozen Phase&nbsp;14 GBM/LGG-like model.
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
          <label className="option-item" htmlFor="cb-make-canvas">
            <input
              id="cb-make-canvas"
              type="checkbox"
              checked={makeCanvas}
              onChange={(e) => setMakeCanvas(e.target.checked)}
              disabled={loading}
            />
            Generate morphology canvas
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

      {error && (
        <div className="info-box" style={{ marginTop: 14 }} role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
