"use client";

import { useState, useEffect, useCallback } from "react";
import WarningBanner from "@/components/WarningBanner";
import RnaUpload, { type RnaApiResponse } from "@/components/RnaUpload";
import ResultCard from "@/components/ResultCard";
import CanvasViewer from "@/components/CanvasViewer";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// ── Backend health types ──────────────────────────────────────────────────

type HealthState = "checking" | "connected" | "offline";

interface HealthInfo {
  state: HealthState;
  label: string;
  detail?: string;
}

// ── Backend status indicator component ────────────────────────────────────

function BackendStatus({ health, onRefresh }: { health: HealthInfo; onRefresh: () => void }) {
  const color =
    health.state === "connected" ? "var(--green-500)"
    : health.state === "offline"  ? "var(--red-500)"
    : "var(--amber-500)";

  return (
    <div className={`status-bar ${health.state}`} role="status" aria-live="polite">
      <span className={`status-dot ${health.state}`} aria-hidden="true" />
      <span style={{ color }}>{health.label}</span>
      {health.detail && (
        <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
          &mdash; {health.detail}
        </span>
      )}
      <button
        onClick={onRefresh}
        style={{
          marginLeft: "auto",
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "0.70rem",
          color: "var(--text-muted)",
          padding: "0 2px",
          lineHeight: 1,
        }}
        aria-label="Re-check backend connection"
        title="Re-check backend"
      >
        ↺
      </button>
    </div>
  );
}

// ── Patch upload placeholder card ─────────────────────────────────────────

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
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          borderRadius: "var(--r-lg)",
          background: "rgba(11,15,26,0.50)",
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
            fontSize: "0.80rem",
            color: "var(--text-secondary)",
            fontWeight: 600,
          }}
        >
          🔒 Coming next: patch ZIP inference
        </span>
        <span style={{ fontSize: "0.70rem", color: "var(--text-muted)" }}>
          CTransPath feature extraction not yet wired
        </span>
      </div>

      {/* Card body (visually dimmed) */}
      <div
        className="card"
        style={{ opacity: 0.38, pointerEvents: "none", filter: "grayscale(0.4)" }}
      >
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

// ── Home page ─────────────────────────────────────────────────────────────

export default function HomePage() {
  const [result, setResult] = useState<RnaApiResponse | null>(null);
  const [health, setHealth] = useState<HealthInfo>({
    state: "checking",
    label: "Checking backend…",
  });

  /** Ping GET /api/health and update the status indicator. */
  const checkHealth = useCallback(async () => {
    setHealth((h) => ({ ...h, state: "checking", label: "Checking backend…" }));
    try {
      const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setHealth({
        state: "connected",
        label: "Backend connected",
        detail: `${data.project ?? "CNS-MultiModalAI"} v${data.version ?? "?"}`,
      });
    } catch {
      setHealth({
        state: "offline",
        label: "Backend offline",
        detail: "Start uvicorn on port 8000",
      });
    }
  }, []);

  // Auto-check on mount; re-check every 30 s.
  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 30_000);
    return () => clearInterval(id);
  }, [checkHealth]);

  /** Called by RnaUpload on success — also confirms backend is alive. */
  function handleResult(data: RnaApiResponse) {
    setResult(data);
    setHealth({ state: "connected", label: "Backend connected", detail: "Inference completed" });
  }

  const canvasFiles = result?.result_files?.canvas_files ?? [];
  const hasCanvas = canvasFiles.length > 0;
  const hasResult = result !== null;

  return (
    <main className="page-wrapper">

      {/* ── Topbar ──────────────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-dot" aria-hidden="true" />
          <div>
            <div className="topbar-title">CNS-MultiModalAI</div>
            <div className="topbar-subtitle">PhD thesis GUI · research prototype</div>
          </div>
        </div>
        <span className="topbar-badge">MVP v0.1</span>
      </header>

      {/* ── Backend status indicator (auto-polls every 30 s) ─────────────── */}
      <BackendStatus health={health} onRefresh={checkHealth} />

      {/* ── Research warning banner ──────────────────────────────────────── */}
      <WarningBanner />

      {/* ── Upload panels ────────────────────────────────────────────────── */}
      <div className="section-label">Upload &amp; Analyse</div>
      <div className="dash-grid">
        <RnaUpload onResult={handleResult} />
        <PatchUploadPlaceholder />
      </div>

      {/* ── Results section ──────────────────────────────────────────────── */}
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
              <div className="card" style={{ padding: "20px 24px 24px" }}>
                <CanvasViewer canvasFiles={canvasFiles} />
              </div>
            </>
          )}

          {/* Canvas enabled but no files returned */}
          {!hasCanvas && result.status === "completed" && result.canvas_enabled && (
            <>
              <div className="section-label" style={{ marginTop: 24 }}>
                Morphology Canvas
              </div>
              <div className="info-box info">
                Canvas was enabled but no canvas files were returned. Check
                backend logs for errors in the morphology retrieval step.
              </div>
            </>
          )}

          {/* Raw run metadata — collapsible */}
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

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="footer-note">
        <div>
          CNS-MultiModalAI GUI MVP &nbsp;·&nbsp;{" "}
          <a href={`${API_BASE}/docs`} target="_blank" rel="noopener noreferrer">
            API Docs ↗
          </a>
          &nbsp;·&nbsp;{" "}
          <a href={`${API_BASE}/api/health`} target="_blank" rel="noopener noreferrer">
            Health ↗
          </a>
        </div>
        <div className="footer-prototype-badge">
          Research prototype · GBM/LGG-like similarity only · Not for clinical use
        </div>
      </footer>

    </main>
  );
}
