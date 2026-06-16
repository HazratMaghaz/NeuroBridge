"use client";

import type {
  PatchApiResponse,
  PatchResultFiles,
  PatchClinicalRelevance,
  PatchMolecularOutput,
    PatchTopFeature,
} from "./PatchUpload";
import DeepZoomViewer from "./DeepZoomViewer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function absUrl(rel?: string | null): string | null {
  if (!rel) return null;
  return `${API_BASE}${rel}`;
}

// ── Probability bar ───────────────────────────────────────────────────────

function ProbBar({ prob }: { prob: number }) {
  const pct = Math.round(prob * 100);
  const isGbm = prob >= 0.5;
  const color = isGbm ? "var(--amber-500)" : "var(--teal-400)";
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ height: 5, borderRadius: 99, background: "var(--bg-base)", overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: 99,
            transition: "width 0.5s ease",
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

// ── Section header helper ─────────────────────────────────────────────────

function SectionHeader({ num, title, subtitle }: { num: string; title: string; subtitle?: string }) {
  return (
    <div className="report-section-header">
      <div className="report-section-num">{num}</div>
      <div className="report-section-title">{title}</div>
      {subtitle && <div className="report-section-subtitle">{subtitle}</div>}
    </div>
  );
}

// ── 1. Executive Summary ──────────────────────────────────────────────────

function ExecutiveSummary({ data }: { data: PatchApiResponse }) {
  const preview = data.prediction_preview;
  const isGbm = preview?.predicted_class?.toLowerCase().includes("gbm");

  return (
    <div className="report-section">
      <SectionHeader num="1" title="Executive Summary" />

      {preview ? (
        <div className="result-grid">
          {/* Predicted class */}
          <div className="stat-block">
            <div className="stat-label">Predicted Class</div>
            <div className={`stat-value large ${isGbm ? "class-gbm" : "class-lgg"}`}>
              {preview.predicted_class ?? "—"}
            </div>
            <div className="stat-sub">image-based classification</div>
          </div>

          {/* Probability */}
          <div className="stat-block">
            <div className="stat-label">P(GBM-like)</div>
            <div className={`stat-value large ${isGbm ? "class-gbm" : "class-lgg"}`}>
              {preview.prob_GBM_like != null
                ? preview.prob_GBM_like.toFixed(4)
                : "—"}
            </div>
            {preview.prob_GBM_like != null && <ProbBar prob={preview.prob_GBM_like} />}
          </div>

          {/* Patches */}
          <div className="stat-block">
            <div className="stat-label">Patches Used</div>
            <div className="stat-value">{preview.n_patches ?? "—"}</div>
            {preview.train_accuracy_internal != null && (
              <div className="stat-sub">
                internal acc: {(preview.train_accuracy_internal * 100).toFixed(1)}%
              </div>
            )}
          </div>

          {/* Images found */}
          <div className="stat-block">
            <div className="stat-label">{data.wsi_extraction ? "Patches Extracted" : "Images Found"}</div>
            <div className="stat-value">{data.wsi_extraction?.n_patches_saved ?? data.n_images_found ?? "—"}</div>
            <div className="stat-sub">{data.wsi_extraction ? "from WSI" : "in uploaded ZIP"}</div>
          </div>
        </div>
      ) : (
        <div className="info-box info">No prediction data returned.</div>
      )}

      {/* Error / note */}
      {data.status === "failed" && data.error && (
        <div className="info-box" style={{ marginTop: 12 }} role="alert">
          {data.error}
        </div>
      )}
      {data.status === "uploaded" && data.note && (
        <div className="info-box info" style={{ marginTop: 12 }}>
          {data.note}
        </div>
      )}
    </div>
  );
}

// ── 2. Spatial WSI Patch Visualization ────────────────────────────────────

function SpatialWsiVisualization({ files }: { files: PatchResultFiles }) {
  if (!files.wsi_patch_overlay_url && !files.wsi_coordinate_mosaic_url) return null;

  return (
    <div className="report-section">
      <SectionHeader num="2" title="Spatial WSI Patch Visualization" />
      
      <p style={{ fontSize: "0.79rem", color: "var(--text-secondary)", lineHeight: 1.65, marginBottom: 14 }}>
        These visualizations preserve approximate patch coordinates from the original WSI. This is different from the RNA retrieval canvas, which does not reconstruct WSI spatial layout.
      </p>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 20 }}>
        {files.wsi_thumbnail_url && (
          <div style={{ flex: "1 1 240px", minWidth: 200 }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>WSI overview</div>
            <a href={absUrl(files.wsi_thumbnail_url) ?? "#"} target="_blank" rel="noopener noreferrer">
              <img
                src={absUrl(files.wsi_thumbnail_url) ?? ""}
                alt="WSI Overview"
                style={{ width: "100%", borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }}
              />
            </a>
          </div>
        )}
        {files.wsi_patch_overlay_url && (
          <div style={{ flex: "1 1 400px", minWidth: 240 }}>
            {files.wsi_patch_overlay_dzi_url ? (
              <>
                <DeepZoomViewer title="Patch locations" dziUrl={absUrl(files.wsi_patch_overlay_dzi_url)!} height="350px" />
                <a href={absUrl(files.wsi_patch_overlay_url) ?? "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "inline-block", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
              </>
            ) : (
              <>
                <div className="stat-label" style={{ marginBottom: 6 }}>Patch locations</div>
                <a href={absUrl(files.wsi_patch_overlay_url) ?? "#"} target="_blank" rel="noopener noreferrer">
                  <img
                    src={absUrl(files.wsi_patch_overlay_url) ?? ""}
                    alt="WSI Patch Overlay"
                    style={{ width: "100%", borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }}
                  />
                </a>
              </>
            )}
          </div>
        )}
        {files.wsi_coordinate_mosaic_url && (
          <div style={{ flex: "1 1 400px", minWidth: 240 }}>
            {files.wsi_coordinate_mosaic_dzi_url ? (
              <>
                <DeepZoomViewer title="Coordinate-aware patch mosaic" dziUrl={absUrl(files.wsi_coordinate_mosaic_dzi_url)!} height="350px" />
                <a href={absUrl(files.wsi_coordinate_mosaic_url) ?? "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "inline-block", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
              </>
            ) : (
              <>
                <div className="stat-label" style={{ marginBottom: 6 }}>Coordinate-aware patch mosaic</div>
                <a href={absUrl(files.wsi_coordinate_mosaic_url) ?? "#"} target="_blank" rel="noopener noreferrer">
                  <img
                    src={absUrl(files.wsi_coordinate_mosaic_url) ?? ""}
                    alt="WSI Coordinate Mosaic"
                    style={{ width: "100%", borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }}
                  />
                </a>
              </>
            )}
          </div>
        )}
      </div>

      {(files.wsi_tissue_mask_url || files.wsi_spatial_contact_sheet_url || files.wsi_visualization_summary_url) && (
        <details>
          <summary style={{ cursor: "pointer", fontSize: "0.73rem", color: "var(--text-muted)", userSelect: "none", marginBottom: 8 }}>
            ▸ Advanced visual outputs
          </summary>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 15, marginTop: 10 }}>
            {files.wsi_tissue_mask_url && (
              <div style={{ flex: "1 1 200px" }}>
                <div className="stat-label" style={{ marginBottom: 6 }}>Tissue Mask</div>
                <a href={absUrl(files.wsi_tissue_mask_url) ?? "#"} target="_blank" rel="noopener noreferrer">
                  <img src={absUrl(files.wsi_tissue_mask_url) ?? ""} alt="Mask" style={{ width: "100%", borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }} />
                </a>
              </div>
            )}
            {files.wsi_spatial_contact_sheet_url && (
              <div style={{ flex: "1 1 400px", minWidth: 240 }}>
                {files.wsi_spatial_contact_sheet_dzi_url ? (
                  <>
                    <DeepZoomViewer title="Spatial Contact Sheet" dziUrl={absUrl(files.wsi_spatial_contact_sheet_dzi_url)!} height="350px" />
                    <a href={absUrl(files.wsi_spatial_contact_sheet_url) ?? "#"} target="_blank" rel="noopener noreferrer" className="btn btn-ghost" style={{ display: "inline-block", marginTop: 8, fontSize: "0.75rem" }}>⬇ Download Image</a>
                  </>
                ) : (
                  <>
                    <div className="stat-label" style={{ marginBottom: 6 }}>Spatial Contact Sheet</div>
                    <a href={absUrl(files.wsi_spatial_contact_sheet_url) ?? "#"} target="_blank" rel="noopener noreferrer">
                      <img src={absUrl(files.wsi_spatial_contact_sheet_url) ?? ""} alt="Contact Sheet" style={{ width: "100%", borderRadius: "var(--r-sm)", border: "1px solid var(--border)" }} />
                    </a>
                  </>
                )}
              </div>
            )}
          </div>
          {files.wsi_visualization_summary_url && (
            <div style={{ marginTop: 10 }}>
              <a className="dl-link" href={absUrl(files.wsi_visualization_summary_url) ?? "#"} target="_blank" rel="noopener noreferrer">
                📋 Visualization Summary JSON
              </a>
            </div>
          )}
        </details>
      )}
    </div>
  );
}

// ── 3. Predicted Molecular Output table ──────────────────────────────────

function MolecularTable({ mol, isWsi }: { mol: PatchMolecularOutput; isWsi: boolean }) {
  const features: PatchTopFeature[] = mol.top_features ?? [];

  return (
    <div className="report-section">
      <SectionHeader
        num="3"
        title={isWsi ? "Predicted Gene / Pathway Expression Output from WSI" : "Predicted Gene / Pathway Expression Output from Image"}
        subtitle="gene-expression-like signature — not measured RNA-seq"
      />

      <p style={{ fontSize: "0.79rem", color: "var(--text-secondary)", lineHeight: 1.65, marginBottom: 14 }}>
        These are predicted gene/program/pathway scores inferred from histology image embeddings using the frozen Phase 15G Ridge model. They are not measured RNA-seq counts and not a full transcriptome.
      </p>

      <div
        className="caution-strip"
        style={{ marginBottom: 14 }}
      >
        ⚠ Computational prediction from image embeddings; <strong>not measured RNA-seq</strong>.
      </div>

      {features.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table className="prediction-table" style={{ fontSize: "0.75rem" }}>
            <thead>
              <tr>
                <th>Gene / program / pathway</th>
                <th>Type</th>
                <th>Direction</th>
                <th>Predicted score</th>
                <th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {features.map((f, i) => {
                const isHigh = f.predicted_direction === "high";
                return (
                  <tr key={i}>
                    <td style={{ fontWeight: 500, color: "var(--text-primary)", fontFamily: "var(--font-sans)" }}>
                      {f.feature_name ?? "—"}
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "0.67rem",
                          background: "rgba(148,163,184,0.08)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--r-sm)",
                          padding: "1px 6px",
                          color: "var(--text-secondary)",
                          fontFamily: "var(--font-sans)",
                        }}
                      >
                        {f.feature_type ?? "—"}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: "0.72rem",
                          color: isHigh ? "var(--amber-500)" : "var(--teal-400)",
                        }}
                      >
                        {f.predicted_direction ?? "—"}
                      </span>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--teal-300)" }}>
                      {f.relative_score != null ? f.relative_score.toFixed(4) : "—"}
                    </td>
                    <td style={{ fontSize: "0.72rem", color: "var(--text-secondary)", maxWidth: 260, fontFamily: "var(--font-sans)" }}>
                      {f.interpretation ?? "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="info-box info">No top features returned.</div>
      )}
    </div>
  );
}

// ── 3. Clinical / Research Relevance ─────────────────────────────────────

function ClinicalRelevanceSection({ cr }: { cr: PatchClinicalRelevance }) {
  const isGbm = cr.predicted_class?.toLowerCase().includes("gbm");
  const dirColor = isGbm ? "var(--amber-500)" : "var(--teal-400)";

  return (
    <div className="report-section">
      <SectionHeader num="4" title="Clinical / Research Relevance" />

      {/* Direction badge */}
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

      {/* Summary */}
      {cr.research_summary && (
        <p style={{ fontSize: "0.79rem", color: "var(--text-secondary)", lineHeight: 1.65, marginBottom: 10 }}>
          {cr.research_summary}
        </p>
      )}

      {/* Scope + caution row */}
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
          <div className="caution-strip" style={{ flex: 1, marginBottom: 0 }}>
            ⚠ {cr.caution}
          </div>
        )}
      </div>
    </div>
  );
}

// ── 4. Downloads ──────────────────────────────────────────────────────────

function DownloadsSection({ files }: { files: PatchResultFiles }) {
  return (
    <div className="report-section">
      <SectionHeader num="5" title="Downloads" />

      {/* Main downloads */}
      <div className="dl-group" style={{ marginBottom: 14 }}>
        <div className="dl-group-label">Main results</div>
        <div className="dl-group-links">
          {files.gene_expression_matrix_url && (
            <a className="dl-link dl-link-primary" href={absUrl(files.gene_expression_matrix_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-gene-matrix">
              ⬇ Full Predicted Gene Expression Matrix
            </a>
          )}
          {files.gene_pathway_matrix_url && (
            <a className="dl-link dl-link-primary" href={absUrl(files.gene_pathway_matrix_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-pathway-matrix">
              ⬇ Full Gene/Program/Pathway Matrix
            </a>
          )}
          {files.gene_pathway_top_features_url && (
            <a className="dl-link dl-link-primary" href={absUrl(files.gene_pathway_top_features_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-gene-top-features">
              ⬇ Top Features CSV
            </a>
          )}
          {files.gene_pathway_report_url && (
            <a className="dl-link dl-link-primary" href={absUrl(files.gene_pathway_report_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-gene-report">
              📋 Gene/Pathway Report
            </a>
          )}
          {files.clinical_relevance_report_url && (
            <a className="dl-link dl-link-primary" href={absUrl(files.clinical_relevance_report_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-clin-relevance-report">
              📋 Clinical Relevance Report
            </a>
          )}
        </div>
      </div>



      {/* Advanced / developer downloads */}
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
          ▸ Advanced downloads
        </summary>
        <div className="dl-group-links" style={{ marginTop: 8 }}>
          {files.prediction_url && (
            <a className="dl-link" href={absUrl(files.prediction_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-patch-prediction">
              ⬇ Patch Prediction CSV
            </a>
          )}
          {files.embedding_url && (
            <a className="dl-link" href={absUrl(files.embedding_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-patch-embedding">
              ⬇ Mean Embedding CSV
            </a>
          )}
          {files.molecular_json_url && (
            <a className="dl-link" href={absUrl(files.molecular_json_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-molecular-json">
              🧬 Molecular JSON
            </a>
          )}
          {files.molecular_report_url && (
            <a className="dl-link" href={absUrl(files.molecular_report_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-molecular-report">
              📋 Molecular Report
            </a>
          )}
          {files.wsi_thumbnail_url && (
            <a className="dl-link" href={absUrl(files.wsi_thumbnail_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-thumb">
              🖼️ WSI Thumbnail
            </a>
          )}
          {files.wsi_tissue_mask_url && (
            <a className="dl-link" href={absUrl(files.wsi_tissue_mask_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-mask">
              🖼️ Tissue Mask
            </a>
          )}
          {files.wsi_patch_overlay_url && (
            <a className="dl-link" href={absUrl(files.wsi_patch_overlay_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-overlay">
              🖼️ Patch Overlay
            </a>
          )}
          {files.wsi_coordinate_mosaic_url && (
            <a className="dl-link" href={absUrl(files.wsi_coordinate_mosaic_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-mosaic">
              🖼️ Coordinate Mosaic
            </a>
          )}
          {files.wsi_spatial_contact_sheet_url && (
            <a className="dl-link" href={absUrl(files.wsi_spatial_contact_sheet_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-contact-sheet">
              🖼️ Spatial Contact Sheet
            </a>
          )}
          {files.wsi_visualization_summary_url && (
            <a className="dl-link" href={absUrl(files.wsi_visualization_summary_url) ?? "#"} target="_blank" rel="noopener noreferrer" id="dl-wsi-vis-summary">
              📋 Visualization Summary JSON
            </a>
          )}
        </div>
      </details>
    </div>
  );
}

// ── Main PatchResultReport ─────────────────────────────────────────────────

interface Props {
  data: PatchApiResponse;
}

export default function PatchResultReport({ data }: Props) {
  const mol = data.image_to_molecular?.predicted_molecular_output;
  const cr = data.clinical_relevance;
  const files = data.result_files;

  return (
    <div>
      {/* Single global caution — only if backend returns one */}
      {data.warning && (
        <div className="caution-strip" style={{ marginBottom: 14 }}>
          ⚠️ {data.warning}
        </div>
      )}

      <div className="report-card">
        {/* 1 — Executive Summary */}
        <ExecutiveSummary data={data} />

        {/* 2 — Spatial WSI Visualization */}
        {files && <SpatialWsiVisualization files={files} />}

        {/* 3 — Molecular Output Table */}
        {mol && <MolecularTable mol={mol} isWsi={!!data.wsi_extraction} />}

        {/* 4 — Clinical / Research Relevance */}
        {cr && <ClinicalRelevanceSection cr={cr} />}

        {/* 5 — Downloads */}
        {files && <DownloadsSection files={files} />}

        {/* Developer details — collapsible at bottom */}
        <details className="dev-details">
          <summary>Developer details</summary>
          <div className="dev-details-body">
            {/* Phase 11A context */}
            {data.image_to_molecular?.phase11a_context &&
              data.image_to_molecular.phase11a_context.length > 0 && (
                <div style={{ marginBottom: 14 }}>
                  <div
                    style={{
                      fontSize: "0.70rem",
                      color: "var(--text-muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      marginBottom: 6,
                    }}
                  >
                    Phase 11A context
                  </div>
                  <ul
                    style={{
                      margin: 0,
                      paddingLeft: 0,
                      listStyle: "none",
                      display: "flex",
                      flexDirection: "column",
                      gap: 4,
                    }}
                  >
                    {data.image_to_molecular.phase11a_context.map((ctx, i) => (
                      <li
                        key={i}
                        style={{
                          fontSize: "0.72rem",
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
                </div>
              )}

            {/* Raw JSON */}
            <div
              style={{
                fontSize: "0.70rem",
                color: "var(--text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                marginBottom: 6,
              }}
            >
              Raw API response
            </div>
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
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        </details>
      </div>
    </div>
  );
}
