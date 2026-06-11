"use client";

import type { RnaApiResponse, PredictionRow, CanvasFile, ClinicalRelevance } from "./RnaUpload";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

/** Prefix a backend-relative URL with the API base. */
function absUrl(rel?: string | null): string | null {
  if (!rel) return null;
  return `${API_BASE}${rel}`;
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
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.68rem", color: "var(--text-muted)", marginTop: 3 }}>
        <span>LGG-like</span>
        <span>GBM-like</span>
      </div>
    </div>
  );
}

function PredictionTable({ rows }: { rows: PredictionRow[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="prediction-table">
        <thead>
          <tr>
            <th>Patient ID</th>
            <th>Predicted Class</th>
            <th>P(GBM-like)</th>
            <th>Shared Genes</th>
            <th>Selected Genes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              <td>{row.patient_id ?? "—"}</td>
              <td>
                <span className={row.predicted_class?.toLowerCase().includes("gbm") ? "class-gbm" : "class-lgg"}>
                  {row.predicted_class ?? "—"}
                </span>
              </td>
              <td>
                {row.prob_GBM_like != null
                  ? row.prob_GBM_like.toFixed(4)
                  : "—"}
              </td>
              <td>{row.shared_gene_count ?? "—"}</td>
              <td>{row.selected_gene_count ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ClinicalRelevancePanel({ cr, label }: { cr: ClinicalRelevance; label?: string }) {
  const isGbm = cr.predicted_class?.toLowerCase().includes("gbm");
  const dirColor = isGbm ? "var(--amber-500)" : "var(--teal-400)";
  return (
    <div
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--r-md)",
        padding: "14px 18px",
        marginTop: 16,
      }}
    >
      <div className="stat-label" style={{ marginBottom: 10, fontSize: "0.72rem" }}>
        {label ?? "Clinical / Research Relevance"}
      </div>

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
        <p style={{ fontSize: "0.79rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: 8 }}>
          {cr.research_summary}
        </p>
      )}

      {/* Model scope + caution */}
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
          <span style={{ fontSize: "0.70rem", color: "var(--text-muted)", fontStyle: "italic", flex: 1 }}>
            ⚠ {cr.caution}
          </span>
        )}
      </div>
    </div>
  );
}

interface Props {
  data: RnaApiResponse;
}

export default function ResultCard({ data }: Props) {
  const preview = data.prediction_preview ?? [];
  const files = data.result_files;
  const firstRow: PredictionRow | undefined = preview[0];

  const statusClass =
    data.status === "completed" ? "pill-success"
    : data.status === "failed"   ? "pill-error"
    : "pill-running";

  const statusLabel =
    data.status === "completed" ? "✓ Completed"
    : data.status === "failed"   ? "✗ Failed"
    : "⟳ Uploaded";

  return (
    <div className="card" id="result-card">
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
        <span className={`pill ${statusClass}`}>{statusLabel}</span>
        {data.canvas_enabled && (
          <span className="pill pill-dim">Canvas enabled</span>
        )}
        {data.inference_enabled && (
          <span className="pill pill-dim">Model: Phase 14 RNA</span>
        )}
      </div>

      {/* Error box */}
      {data.status === "failed" && data.error && (
        <div className="info-box" style={{ marginBottom: 14 }} role="alert">
          {data.error}
        </div>
      )}

      {/* Warning from backend */}
      {data.warning && (
        <div className="warning-banner" style={{ marginBottom: 16 }}>
          <span className="warning-icon">⚠️</span>
          <p className="warning-text" style={{ fontSize: "0.75rem" }}>{data.warning}</p>
        </div>
      )}

      {/* Summary stat blocks — first row */}
      {firstRow && (
        <>
          <div className="result-grid">
            <div className="stat-block">
              <div className="stat-label">Patient ID</div>
              <div className="stat-value" style={{ fontSize: "1rem", fontFamily: "var(--font-mono)" }}>
                {firstRow.patient_id ?? "—"}
              </div>
            </div>
            <div className="stat-block">
              <div className="stat-label">Predicted Class</div>
              <div className={`stat-value large ${firstRow.predicted_class?.toLowerCase().includes("gbm") ? "class-gbm" : "class-lgg"}`}>
                {firstRow.predicted_class ?? "—"}
              </div>
            </div>
            <div className="stat-block">
              <div className="stat-label">P(GBM-like)</div>
              <div className="stat-value large">
                {firstRow.prob_GBM_like != null
                  ? firstRow.prob_GBM_like.toFixed(4)
                  : "—"}
              </div>
              {firstRow.prob_GBM_like != null && probBar(firstRow.prob_GBM_like)}
            </div>
            <div className="stat-block">
              <div className="stat-label">Shared Genes</div>
              <div className="stat-value">{firstRow.shared_gene_count ?? "—"}</div>
              <div className="stat-sub">of {firstRow.selected_gene_count ?? "?"} selected</div>
            </div>
          </div>
        </>
      )}

      {/* Full prediction table (if >1 row) */}
      {preview.length > 1 && (
        <>
          <div className="section-label" style={{ marginTop: 20 }}>All predictions</div>
          <PredictionTable rows={preview} />
        </>
      )}

      {/* Download links */}
      {files && (
        <>
          <div className="section-label" style={{ marginTop: 20 }}>Result files</div>
          <div className="download-links">
            {files.predictions_url && (
              <a className="dl-link" href={absUrl(files.predictions_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-predictions">
                ⬇ Predictions CSV
              </a>
            )}
            {files.report_url && (
              <a className="dl-link" href={absUrl(files.report_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-report">
                📄 Inference Report
              </a>
            )}
            {files.canvas_index_url && (
              <a className="dl-link" href={absUrl(files.canvas_index_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-canvas-index">
                🗂 Canvas Index CSV
              </a>
            )}
            {files.canvas_files?.map((cf: CanvasFile, i: number) =>
              cf.retrieval_csv_url ? (
                <a
                  key={i}
                  className="dl-link"
                  href={absUrl(cf.retrieval_csv_url) ?? "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  id={`dl-retrieval-${i}`}
                >
                  🔍 Retrieval CSV {cf.patient_id ? `(${cf.patient_id})` : `#${i + 1}`}
                </a>
              ) : null
            )}
          </div>
        </>
      )}

      {/* ── Clinical / Research Relevance ─────────────────────────────── */}
      {data.clinical_relevance && (
        <>
          <div className="section-label" style={{ marginTop: 20 }}>
            Clinical / Research Relevance
          </div>
          <ClinicalRelevancePanel
            cr={data.clinical_relevance}
            label="RNA-seq workflow · Phase 14 model"
          />
        </>
      )}
    </div>
  );
}
