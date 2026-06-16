"use client";

import type { RnaApiResponse, PredictionRow, CanvasFile, ClinicalRelevance } from "./RnaUpload";
import DeepZoomViewer from "./DeepZoomViewer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function absUrl(rel?: string | null): string | null {
  if (!rel) return null;
  return `${API_BASE}${rel}`;
}

// ── Prob bar ──────────────────────────────────────────────────────────────

function probBar(prob: number) {
  const pct = Math.round(prob * 100);
  const color = prob >= 0.5 ? "var(--amber-500)" : "var(--teal-400)";
  return (
    <div style={{ marginTop: 6 }}>
      <div
        style={{
          height: 5,
          borderRadius: 99,
          background: "var(--bg-base)",
          overflow: "hidden",
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
          fontSize: "0.66rem",
          color: "var(--text-muted)",
          marginTop: 3,
        }}
      >
        <span>LGG-like ◀</span>
        <span>▶ GBM-like</span>
      </div>
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────────────

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <div className="report-section-header">
      <div className="report-section-num">{num}</div>
      <div className="report-section-title">{title}</div>
    </div>
  );
}

// ── Full prediction table ─────────────────────────────────────────────────

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
                <span
                  className={
                    row.predicted_class?.toLowerCase().includes("gbm")
                      ? "class-gbm"
                      : "class-lgg"
                  }
                >
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

// ── Clinical / Research Relevance ─────────────────────────────────────────

function ClinicalRelevancePanel({ cr }: { cr: ClinicalRelevance }) {
  const isGbm = cr.predicted_class?.toLowerCase().includes("gbm");
  const dirColor = isGbm ? "var(--amber-500)" : "var(--teal-400)";

  return (
    <div className="report-section">
      <SectionHeader num="2" title="Clinical / Research Relevance" />

      {cr.research_direction && (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 7,
            background: isGbm ? "var(--amber-bg)" : "var(--teal-glow)",
            border: `1px solid ${isGbm ? "rgba(245,158,11,0.28)" : "rgba(20,184,166,0.28)"}`,
            borderRadius: "var(--r-sm)",
            padding: "5px 12px",
            fontSize: "0.80rem",
            fontWeight: 600,
            color: dirColor,
            marginBottom: 10,
          }}
        >
          {isGbm ? "⚡" : "🧠"} {cr.research_direction}
        </div>
      )}

      {cr.research_summary && (
        <p
          style={{
            fontSize: "0.79rem",
            color: "var(--text-secondary)",
            lineHeight: 1.65,
            marginBottom: 10,
          }}
        >
          {cr.research_summary}
        </p>
      )}

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-start" }}>
        {cr.model_scope && (
          <span
            style={{
              fontSize: "0.70rem",
              color: "var(--text-muted)",
              background: "rgba(148,163,184,0.06)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-sm)",
              padding: "2px 8px",
              flexShrink: 0,
            }}
          >
            Scope: {cr.model_scope}
          </span>
        )}
        {cr.caution && (
          <div
            className="caution-strip"
            style={{ flex: 1, marginBottom: 0 }}
          >
            ⚠ {cr.caution}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Reference Morphology Retrieval ────────────────────────────────────────

function ReferenceMorphologyPanel({
  refMorph,
  files,
}: {
  refMorph: NonNullable<RnaApiResponse["reference_morphology"]>;
  files: NonNullable<RnaApiResponse["result_files"]>;
}) {
  return (
    <div className="report-section">
      <SectionHeader num="3" title="Advanced Reference Morphology Retrieval" />
      <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 10 }}>
        RNA-guided retrieval of reference histology patches with known WSI coordinates.
      </p>

      <div className="info-box" role="alert" style={{ marginBottom: 14, backgroundColor: "rgba(245, 158, 11, 0.1)", borderLeft: "4px solid var(--amber-500)" }}>
        ⚠ <strong>Warning:</strong> Reference retrieval only. This is not RNA-to-WSI reconstruction. Coordinates belong to retrieved reference WSIs from the internal patch bank.
      </div>

      <div className="result-grid" style={{ marginBottom: 16 }}>
        <div className="stat-block">
          <div className="stat-label">Best Similarity</div>
          <div className="stat-value">{refMorph.best_similarity_score?.toFixed(4) || "—"}</div>
        </div>
        <div className="stat-block">
          <div className="stat-label">Mean Top Similarity</div>
          <div className="stat-value">{refMorph.mean_top_similarity_score?.toFixed(4) || "—"}</div>
        </div>
        <div className="stat-block">
          <div className="stat-label">Patches Extracted</div>
          <div className="stat-value">{refMorph.patch_images_extracted || 0}</div>
        </div>
        <div className="stat-block">
          <div className="stat-label">Source Slides</div>
          <div className="stat-value">{refMorph.unique_source_slides || 0}</div>
        </div>
      </div>

      {/* Visual Cards */}
      <div style={{ display: "flex", gap: 16, overflowX: "auto", paddingBottom: 10, marginBottom: 16 }}>
        {files.reference_morphology_top_panel_url && (
          <div style={{ flex: "0 0 400px", border: "1px solid var(--border)", borderRadius: "var(--r-md)", padding: 8, background: "var(--bg-base)" }}>
            {files.reference_morphology_top_panel_dzi_url ? (
              <DeepZoomViewer title="Top retrieved morphology patches" dziUrl={absUrl(files.reference_morphology_top_panel_dzi_url)!} height="300px" />
            ) : (
              <>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 6 }}>Top retrieved morphology patches</div>
                <img src={absUrl(files.reference_morphology_top_panel_url) || ""} alt="Top Patches" style={{ width: "100%", borderRadius: 4 }} />
              </>
            )}
            <a href={absUrl(files.reference_morphology_top_panel_url) || "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "block", textAlign: "center", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
          </div>
        )}
        {files.reference_morphology_source_panel_url && (
          <div style={{ flex: "0 0 400px", border: "1px solid var(--border)", borderRadius: "var(--r-md)", padding: 8, background: "var(--bg-base)" }}>
            {files.reference_morphology_source_panel_dzi_url ? (
              <DeepZoomViewer title="Source-grouped reference patches" dziUrl={absUrl(files.reference_morphology_source_panel_dzi_url)!} height="300px" />
            ) : (
              <>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 6 }}>Source-grouped reference patches</div>
                <img src={absUrl(files.reference_morphology_source_panel_url) || ""} alt="Source Grouped Patches" style={{ width: "100%", borderRadius: 4 }} />
              </>
            )}
            <a href={absUrl(files.reference_morphology_source_panel_url) || "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "block", textAlign: "center", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
          </div>
        )}
        {files.reference_morphology_coordinate_layout_url && (
          <div style={{ flex: "0 0 400px", border: "1px solid var(--border)", borderRadius: "var(--r-md)", padding: 8, background: "var(--bg-base)" }}>
            {files.reference_morphology_coordinate_layout_dzi_url ? (
              <DeepZoomViewer title="Reference-coordinate layout" dziUrl={absUrl(files.reference_morphology_coordinate_layout_dzi_url)!} height="300px" />
            ) : (
              <>
                <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 6 }}>Reference-coordinate layout</div>
                <img src={absUrl(files.reference_morphology_coordinate_layout_url) || ""} alt="Coordinate Layout" style={{ width: "100%", borderRadius: 4 }} />
              </>
            )}
            <a href={absUrl(files.reference_morphology_coordinate_layout_url) || "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "block", textAlign: "center", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
          </div>
        )}
      </div>


    </div>
  );
}

// ── Grouped downloads ─────────────────────────────────────────────────────

function DownloadsSection({
  files,
  hasRefMorph,
}: {
  files: NonNullable<RnaApiResponse["result_files"]>;
  hasRefMorph: boolean;
}) {
  const sectionNum = hasRefMorph ? "4" : (files.canvas_files && files.canvas_files.length > 0 ? "3" : "3");
  return (
    <div className="report-section">
      <SectionHeader num={sectionNum} title="Downloads" />

      {/* Main downloads */}
      <div className="dl-group" style={{ marginBottom: 14 }}>
        <div className="dl-group-label">Main results</div>
        <div className="dl-group-links">
          {files.report_url && (
            <a
              className="dl-link dl-link-primary"
              href={absUrl(files.report_url) ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              id="dl-report"
            >
              📄 Inference Report
            </a>
          )}
          {files.predictions_url && (
            <a
              className="dl-link dl-link-primary"
              href={absUrl(files.predictions_url) ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              id="dl-predictions"
            >
              ⬇ Predictions CSV
            </a>
          )}
          {hasRefMorph && files.reference_morphology_retrieval_csv_url && (
            <a className="dl-link" href={absUrl(files.reference_morphology_retrieval_csv_url) || "#"} target="_blank" rel="noopener noreferrer">
              ⬇ Ref. Morphology Retrieval CSV
            </a>
          )}
          {hasRefMorph && files.reference_morphology_summary_url && (
            <a className="dl-link" href={absUrl(files.reference_morphology_summary_url) || "#"} target="_blank" rel="noopener noreferrer">
              📄 Ref. Morphology Summary JSON
            </a>
          )}
          {hasRefMorph && files.reference_morphology_top_panel_url && (
            <a className="dl-link" href={absUrl(files.reference_morphology_top_panel_url) || "#"} target="_blank" rel="noopener noreferrer">
              🖼️ Top Patch Panel
            </a>
          )}
          {hasRefMorph && files.reference_morphology_source_panel_url && (
            <a className="dl-link" href={absUrl(files.reference_morphology_source_panel_url) || "#"} target="_blank" rel="noopener noreferrer">
              🖼️ Source-Grouped Panel
            </a>
          )}
          {hasRefMorph && files.reference_morphology_coordinate_layout_url && (
            <a className="dl-link" href={absUrl(files.reference_morphology_coordinate_layout_url) || "#"} target="_blank" rel="noopener noreferrer">
              🖼️ Coordinate Layout
            </a>
          )}
        </div>
      </div>

      {/* Canvas / advanced */}
      {(files.canvas_index_url ||
        (files.canvas_files && files.canvas_files.length > 0)) && (
        <details>
          <summary
            style={{
              cursor: "pointer",
              fontSize: "0.73rem",
              color: "var(--text-muted)",
              userSelect: "none",
              marginBottom: 8,
            }}
          >
            ▸ Advanced / Legacy Outputs
          </summary>
          <div className="dl-group-links" style={{ marginTop: 8 }}>
            <a className="dl-link" href={`data:application/json,${encodeURIComponent(JSON.stringify(files, null, 2))}`} download="raw_api_response.json">
              📄 Raw API Response JSON
            </a>
            {files.canvas_index_url && (
              <a
                className="dl-link"
                href={absUrl(files.canvas_index_url) ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                id="dl-canvas-index"
              >
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
                  🔍 Retrieval CSV{" "}
                  {cf.patient_id ? `(${cf.patient_id})` : `#${i + 1}`}
                </a>
              ) : null
            )}
          </div>
        </details>
      )}
    </div>
  );
}

// ── Main ResultCard ───────────────────────────────────────────────────────

interface Props {
  data: RnaApiResponse;
}

export default function ResultCard({ data }: Props) {
  const preview = data.prediction_preview ?? [];
  const files = data.result_files;
  const firstRow: PredictionRow | undefined = preview[0];
  const isGbm = firstRow?.predicted_class?.toLowerCase().includes("gbm");

  return (
    <div className="report-card" id="result-card">

      {/* ── 1. Prediction Summary ────────────────────────────────────────── */}
      <div className="report-section">
        <SectionHeader num="1" title="Prediction Summary" />

        {/* Status pills row */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          <span
            className={`pill ${
              data.status === "completed"
                ? "pill-success"
                : data.status === "failed"
                ? "pill-error"
                : "pill-running"
            }`}
          >
            {data.status === "completed"
              ? "✓ Completed"
              : data.status === "failed"
              ? "✗ Failed"
              : "⟳ Uploaded"}
          </span>
          {data.inference_enabled && (
            <span className="pill pill-dim">Phase 14 RNA model</span>
          )}
          {data.canvas_enabled && (
            <span className="pill pill-dim">Canvas enabled</span>
          )}
        </div>

        {/* Error */}
        {data.status === "failed" && data.error && (
          <div className="info-box" role="alert" style={{ marginBottom: 12 }}>
            {data.error}
          </div>
        )}

        {/* Stat grid — first row */}
        {firstRow && (
          <div className="result-grid">
            <div className="stat-block">
              <div className="stat-label">Patient ID</div>
              <div
                className="stat-value"
                style={{ fontSize: "1rem", fontFamily: "var(--font-mono)" }}
              >
                {firstRow.patient_id ?? "—"}
              </div>
            </div>
            <div className="stat-block">
              <div className="stat-label">GBM/LGG Similarity</div>
              <div
                className={`stat-value large ${
                  isGbm ? "class-gbm" : "class-lgg"
                }`}
              >
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
              {firstRow.prob_GBM_like != null &&
                probBar(firstRow.prob_GBM_like)}
            </div>
            <div className="stat-block">
              <div className="stat-label">Shared Genes</div>
              <div className="stat-value">
                {firstRow.shared_gene_count ?? "—"}
              </div>
              <div className="stat-sub">
                of {firstRow.selected_gene_count ?? "?"} selected
              </div>
            </div>
          </div>
        )}

        {/* Multi-row table */}
        {preview.length > 1 && (
          <>
            <div
              style={{
                fontSize: "0.70rem",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginTop: 18,
                marginBottom: 4,
              }}
            >
              All predictions ({preview.length} cases)
            </div>
            <PredictionTable rows={preview} />
          </>
        )}
      </div>

      {/* ── 2. Clinical / Research Relevance ─────────────────────────────── */}
      {data.clinical_relevance && (
        <ClinicalRelevancePanel cr={data.clinical_relevance} />
      )}

      {/* ── 3. Reference Morphology ──────────────────────────────────────── */}
      {data.reference_morphology && files && (
        <ReferenceMorphologyPanel refMorph={data.reference_morphology} files={files} />
      )}

      {/* ── 4. Downloads ─────────────────────────────────────────────────── */}
      {files && <DownloadsSection files={files} hasRefMorph={!!data.reference_morphology} />}

      {/* ── Developer details ─────────────────────────────────────────────── */}
      <details className="dev-details">
        <summary>Developer details — raw API response</summary>
        <div className="dev-details-body">
          <pre
            style={{
              padding: 12,
              background: "var(--bg-base)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-sm)",
              fontSize: "0.70rem",
              color: "var(--text-muted)",
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
        </div>
      </details>
    </div>
  );
}
