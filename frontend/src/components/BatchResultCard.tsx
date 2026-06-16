"use client";

import React from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

function absUrl(path?: string | null): string {
  if (!path) return "#";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}


export interface BatchApiResponse {
  status: "uploaded" | "completed" | "completed_with_errors" | "failed";
  batch_mode: boolean;
  batch_type: "rna" | "patch" | "wsi";
  run_dir: string;
  error?: string;
  n_samples_total: number;
  n_samples_completed: number;
  n_samples_failed: number;
  reference_morphology_samples_completed?: number;
  result_files: {
    batch_summary_url?: string;
    batch_errors_url?: string;
    batch_report_url?: string;
    batch_manifest_url?: string;
    batch_reference_morphology_summary_url?: string;
    batch_gene_expression_url?: string;
    batch_gene_pathway_url?: string;
  };
}

function SectionHeader({ num, title }: { num: string; title: string }) {
  return (
    <h3 className="section-title">
      <span className="section-num">{num}</span>
      {title}
    </h3>
  );
}

export default function BatchResultCard({ data }: { data: BatchApiResponse }) {
  const isError = data.status === "failed";
  const isPartial = data.status === "completed_with_errors";
  const files = data.result_files || {};

  // Simple absUrl helper locally in case it's not exported globally
  const getAbsUrl = (url?: string) => {
    if (!url) return "#";
    if (url.startsWith("http")) return url;
    const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
    return `${base}${url}`;
  };

  return (
    <div className="report-card">
      <div className="report-section">
        <SectionHeader num="1" title="Batch Processing Summary" />
        
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
          <span className={`pill ${isError ? "pill-error" : isPartial ? "pill-warning" : "pill-success"}`}>
            {data.status === "completed" ? "✓ Completed" : 
             isPartial ? "⚠ Completed with Errors" : 
             isError ? "✗ Failed" : "⟳ Processing"}
          </span>
          <span className="pill pill-dim">Batch Type: {data.batch_type.toUpperCase()}</span>
        </div>

        {(isError || isPartial) && (
          <div className="info-box" role="alert" style={{ marginBottom: 14, backgroundColor: "rgba(245, 158, 11, 0.1)", borderLeft: "4px solid var(--amber-500)" }}>
            ⚠ <strong>{isError ? "Error:" : "Warning:"}</strong> {data.error || "Some samples failed to process. Check the batch errors CSV for details."}
          </div>
        )}

        <div className="result-grid" style={{ marginBottom: 16 }}>
          <div className="stat-block">
            <div className="stat-label">Total Samples</div>
            <div className="stat-value large">{data.n_samples_total}</div>
          </div>
          <div className="stat-block">
            <div className="stat-label">Completed</div>
            <div className="stat-value large" style={{ color: "var(--green-400)" }}>{data.n_samples_completed}</div>
          </div>
          <div className="stat-block">
            <div className="stat-label">Failed</div>
            <div className="stat-value large" style={{ color: data.n_samples_failed > 0 ? "var(--red-400)" : "inherit" }}>
              {data.n_samples_failed}
            </div>
          </div>
          {data.batch_type === "rna" && data.reference_morphology_samples_completed !== undefined && (
            <div className="stat-block">
              <div className="stat-label">Ref. Morph. Completed</div>
              <div className="stat-value">{data.reference_morphology_samples_completed}</div>
            </div>
          )}
        </div>
      </div>

      <div className="report-section">
        <SectionHeader num="2" title="Batch Downloads" />
        <div className="dl-group" style={{ marginBottom: 14 }}>
          <div className="dl-group-label">Summary & Metrics</div>
          <div className="dl-group-links">
            {files.batch_report_url && (
              <a className="dl-link dl-link-primary" href={getAbsUrl(files.batch_report_url)} target="_blank" rel="noopener noreferrer">
                📄 Batch Report MD
              </a>
            )}
            {files.batch_summary_url && (
              <a className="dl-link dl-link-primary" href={getAbsUrl(files.batch_summary_url)} target="_blank" rel="noopener noreferrer">
                ⬇ Batch Predictions CSV
              </a>
            )}
            {files.batch_gene_expression_url && (
              <a className="dl-link" href={getAbsUrl(files.batch_gene_expression_url)} target="_blank" rel="noopener noreferrer">
                ⬇ Gene Expression Matrix CSV
              </a>
            )}
            {files.batch_gene_pathway_url && (
              <a className="dl-link" href={getAbsUrl(files.batch_gene_pathway_url)} target="_blank" rel="noopener noreferrer">
                ⬇ Gene Pathway Matrix CSV
              </a>
            )}
            {files.batch_reference_morphology_summary_url && (
              <a className="dl-link" href={getAbsUrl(files.batch_reference_morphology_summary_url)} target="_blank" rel="noopener noreferrer">
                ⬇ Reference Morphology Summary CSV
              </a>
            )}
          </div>
        </div>

        {(files.batch_errors_url || files.batch_manifest_url) && (
          <div className="dl-group" style={{ marginBottom: 0 }}>
            <div className="dl-group-label">Logs & Inputs</div>
            <div className="dl-group-links">
              {files.batch_errors_url && (
                <a className="dl-link" style={{ color: "var(--red-400)", borderColor: "var(--red-400)" }} href={getAbsUrl(files.batch_errors_url)} target="_blank" rel="noopener noreferrer">
                  ⚠ Batch Errors CSV
                </a>
              )}
              {files.batch_manifest_url && (
                <a className="dl-link" href={getAbsUrl(files.batch_manifest_url)} target="_blank" rel="noopener noreferrer">
                  🗂 Used Manifest CSV
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
