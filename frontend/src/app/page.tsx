"use client";

import { useState } from "react";
import WarningBanner from "@/components/WarningBanner";
import RnaUpload, { type RnaApiResponse } from "@/components/RnaUpload";
import ResultCard from "@/components/ResultCard";
import CanvasViewer from "@/components/CanvasViewer";

/** Patch upload placeholder — heavy model is NOT connected. */
function PatchUploadPlaceholder() {
  return (
    <div style={{ position: "relative" }}>
      {/* Disabled overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "var(--r-lg)",
          background: "rgba(11,15,26,0.45)",
          backdropFilter: "blur(2px)",
          cursor: "not-allowed",
        }}
        title="Patch model inference is not yet enabled"
        aria-disabled="true"
      >
        <span
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-bright)",
            borderRadius: "var(--r-sm)",
            padding: "6px 14px",
            fontSize: "0.78rem",
            color: "var(--text-muted)",
            fontWeight: 500,
          }}
        >
          🔒 Patch model — coming in next step
        </span>
      </div>

      {/* Card body (visually dimmed) */}
      <div className="card" style={{ opacity: 0.45, pointerEvents: "none", filter: "grayscale(0.3)" }}>
        <div className="card-title">🔬 Patch Image Inference</div>
        <p className="card-desc">
          Upload a ZIP archive of histology patch images (224×224 px).
          The backend will extract features using CTransPath and classify
          GBM-like vs LGG-like morphology.
        </p>
        <div className="upload-zone">
          <div className="upload-icon">🗜️</div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Drag &amp; drop or browse for a ZIP
          </div>
          <div className="upload-hint">.jpg/.png patches · max 2 GB</div>
        </div>
        <div className="btn-row">
          <button className="btn btn-primary" disabled>
            ▶ Run Patch Analysis
          </button>
        </div>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [result, setResult] = useState<RnaApiResponse | null>(null);
  const [healthStatus, setHealthStatus] = useState<string | null>(null);

  /** Ping the backend health endpoint */
  async function checkHealth() {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}/api/health`
      );
      const data = await res.json();
      setHealthStatus(
        data.status === "ok"
          ? `✓ Backend OK — ${data.project ?? "CNS-MultiModalAI"} v${data.version ?? "?"}`
          : "Backend returned unexpected status"
      );
    } catch {
      setHealthStatus("✗ Backend unreachable — is uvicorn running on port 8000?");
    }
  }

  const canvasFiles = result?.result_files?.canvas_files ?? [];
  const hasCanvas = canvasFiles.length > 0;
  const hasResult = result !== null;

  return (
    <main className="page-wrapper">
      {/* ── Topbar ─────────────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-dot" aria-hidden="true" />
          <div>
            <div className="topbar-title">CNS-MultiModalAI</div>
            <div className="topbar-subtitle">PhD thesis GUI · research prototype</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span className="topbar-badge">MVP v0.1</span>
          <button
            id="btn-health-check"
            className="btn btn-ghost"
            style={{ padding: "5px 12px", fontSize: "0.75rem" }}
            onClick={checkHealth}
          >
            Ping API
          </button>
        </div>
      </header>

      {/* Health status toast */}
      {healthStatus && (
        <div
          className="info-box info"
          style={{ marginBottom: 16, fontSize: "0.78rem" }}
          role="status"
        >
          {healthStatus}
        </div>
      )}

      {/* ── Warning banner ─────────────────────────────────────────────── */}
      <WarningBanner />

      {/* ── Upload panels (2-col grid) ──────────────────────────────────── */}
      <div className="section-label">Upload &amp; Analyse</div>
      <div className="dash-grid">
        <RnaUpload onResult={setResult} />
        <PatchUploadPlaceholder />
      </div>

      {/* ── Results section ─────────────────────────────────────────────── */}
      {hasResult && (
        <>
          <div className="divider" />
          <div className="section-label">Inference Results</div>
          <ResultCard data={result!} />

          {/* Morphology canvas */}
          {hasCanvas && (
            <>
              <div className="section-label" style={{ marginTop: 24 }}>
                Morphology Canvas
              </div>
              <div className="card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "16px 24px 0" }}>
                  <p style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginBottom: 12 }}>
                    The canvas below shows real histology patches retrieved from the
                    internal training cohort that are most morphologically similar to
                    this patient's predicted image embedding. It is retrieval-based —
                    not the patient's own WSI.
                  </p>
                </div>
                <div style={{ padding: "0 24px 24px" }}>
                  <CanvasViewer canvasFiles={canvasFiles} />
                </div>
              </div>
            </>
          )}

          {/* No canvas message */}
          {!hasCanvas && result.status === "completed" && result.canvas_enabled && (
            <>
              <div className="section-label" style={{ marginTop: 24 }}>Morphology Canvas</div>
              <div className="info-box info">
                Canvas was enabled but no canvas files were returned. Check backend logs.
              </div>
            </>
          )}

          {/* Run metadata */}
          <details style={{ marginTop: 20 }}>
            <summary
              style={{
                cursor: "pointer",
                fontSize: "0.78rem",
                color: "var(--text-muted)",
                userSelect: "none",
                padding: "4px 0",
              }}
            >
              ▸ Raw run metadata
            </summary>
            <pre
              style={{
                marginTop: 8,
                padding: 14,
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-md)",
                fontSize: "0.72rem",
                color: "var(--text-secondary)",
                fontFamily: "var(--font-mono)",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                maxHeight: 400,
                overflowY: "auto",
              }}
            >
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </>
      )}

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer
        style={{
          marginTop: 48,
          paddingTop: 20,
          borderTop: "1px solid var(--border)",
          fontSize: "0.72rem",
          color: "var(--text-muted)",
          textAlign: "center",
        }}
      >
        CNS-MultiModalAI GUI MVP · Research prototype · Not for clinical use ·{" "}
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "var(--teal-400)", textDecoration: "none" }}
        >
          API Docs ↗
        </a>
      </footer>
    </main>
  );
}
