"use client";

import { useState, useEffect, useCallback } from "react";
import WarningBanner from "@/components/WarningBanner";
import RnaUpload, { type RnaApiResponse } from "@/components/RnaUpload";
import ResultCard from "@/components/ResultCard";
import CanvasViewer from "@/components/CanvasViewer";
import PatchUpload, { type PatchApiResponse } from "@/components/PatchUpload";
import PatchResultReport from "@/components/PatchResultReport";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

// ── Types ─────────────────────────────────────────────────────────────────

type WorkflowTab = "rna" | "patch" | "wsi";
type RunState = "idle" | "running" | "done";

type HealthState = "checking" | "connected" | "offline";

interface HealthInfo {
  state: HealthState;
  label: string;
  detail?: string;
}

// ── Backend status ────────────────────────────────────────────────────────

function BackendStatus({
  health,
  onRefresh,
}: {
  health: HealthInfo;
  onRefresh: () => void;
}) {
  const color =
    health.state === "connected"
      ? "var(--green-500)"
      : health.state === "offline"
      ? "var(--red-500)"
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

// ── Input summary bar (shown after run) ───────────────────────────────────

function InputSummary({
  icon,
  filename,
  meta,
  statusPill,
  onRunAnother,
}: {
  icon: string;
  filename: string;
  meta: string;
  statusPill: React.ReactNode;
  onRunAnother: () => void;
}) {
  return (
    <div className="input-summary">
      <span className="input-summary-icon">{icon}</span>
      <div className="input-summary-body">
        <div className="input-summary-filename">{filename}</div>
        <div className="input-summary-meta">{meta}</div>
      </div>
      {statusPill}
      <button className="btn btn-ghost" style={{ fontSize: "0.78rem", padding: "6px 14px" }} onClick={onRunAnother}>
        ↩ Run another
      </button>
    </div>
  );
}

// ── Progress panel ────────────────────────────────────────────────────────

function ProgressPanel({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="progress-panel">
      <div className="progress-spinner-wrap">
        <span className="spinner" />
      </div>
      <div className="progress-body">
        <div className="progress-title">{title}</div>
        <div className="progress-sub">{sub}</div>
        <div className="progress-bar-track">
          <div className="progress-bar-fill" />
        </div>
      </div>
    </div>
  );
}

// ── Home page ─────────────────────────────────────────────────────────────

export default function HomePage() {
  const [tab, setTab] = useState<WorkflowTab>("rna");

  // RNA state
  const [rnaState, setRnaState] = useState<RunState>("idle");
  const [rnaResult, setRnaResult] = useState<RnaApiResponse | null>(null);
  const [rnaFilename, setRnaFilename] = useState<string>("");

  // Patch state
  const [patchState, setPatchState] = useState<RunState>("idle");
  const [patchResult, setPatchResult] = useState<PatchApiResponse | null>(null);
  const [patchFilename, setPatchFilename] = useState<string>("");
  const [patchImageCount, setPatchImageCount] = useState<number | null>(null);

  // Health
  const [health, setHealth] = useState<HealthInfo>({
    state: "checking",
    label: "Checking backend…",
  });

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

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 30_000);
    return () => clearInterval(id);
  }, [checkHealth]);

  // RNA callbacks
  function handleRnaRunStart(filename: string) {
    setRnaState("running");
    setRnaFilename(filename);
    setRnaResult(null);
  }

  function handleRnaResult(data: RnaApiResponse) {
    setRnaResult(data);
    setRnaState("done");
    setHealth({
      state: "connected",
      label: "Backend connected",
      detail: "RNA inference completed",
    });
  }

  function resetRna() {
    setRnaState("idle");
    setRnaResult(null);
    setRnaFilename("");
  }

  // Patch callbacks
  function handlePatchRunStart(filename: string) {
    setPatchState("running");
    setPatchFilename(filename);
    setPatchResult(null);
    setPatchImageCount(null);
  }

  function handlePatchResult(data: PatchApiResponse) {
    setPatchResult(data);
    setPatchState("done");
    setPatchImageCount(data.n_images_found ?? null);
    setHealth({
      state: "connected",
      label: "Backend connected",
      detail: "Patch inference completed",
    });
  }

  function resetPatch() {
    setPatchState("idle");
    setPatchResult(null);
    setPatchFilename("");
    setPatchImageCount(null);
  }

  const canvasFiles = rnaResult?.result_files?.canvas_files ?? [];
  const hasCanvas = canvasFiles.length > 0;

  return (
    <main className="page-wrapper">

      {/* ── Topbar ──────────────────────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="topbar-dot" aria-hidden="true" />
          <div>
            <div className="topbar-title">CNS-MultiModalAI</div>
            <div className="topbar-subtitle">MultimodalAI GUI · prototype</div>
          </div>
        </div>
        <span className="topbar-badge">MVP v0.4.1</span>
      </header>

      {/* ── Backend status ───────────────────────────────────────────────── */}
      <BackendStatus health={health} onRefresh={checkHealth} />

      {/* ── Research warning (one global) ───────────────────────────────── */}
      <WarningBanner />

      {/* ── Workflow tabs ────────────────────────────────────────────────── */}
      <div className="workflow-tabs" role="tablist">
        <button
          role="tab"
          className={`workflow-tab${tab === "rna" ? " active" : ""}`}
          onClick={() => setTab("rna")}
          aria-selected={tab === "rna"}
          id="tab-rna"
        >
          🧬 RNA → Morphology
        </button>
        <button
          role="tab"
          className={`workflow-tab${tab === "patch" ? " active" : ""}`}
          onClick={() => setTab("patch")}
          aria-selected={tab === "patch"}
          id="tab-patch"
        >
          🔬 Patch / Image → Molecular
        </button>
        <button
          role="tab"
          className="workflow-tab"
          disabled
          aria-disabled="true"
        >
          🖼️ WSI Analysis
          <span className="workflow-tab-soon">Soon</span>
        </button>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          RNA WORKFLOW
      ═══════════════════════════════════════════════════════════════════ */}
      {tab === "rna" && (
        <>
          {/* Upload form — only shown when idle */}
          {rnaState === "idle" && (
            <RnaUpload
              onResult={handleRnaResult}
              onRunStart={handleRnaRunStart}
            />
          )}

          {/* Progress panel during run */}
          {rnaState === "running" && (
            <>
              <InputSummary
                icon="📄"
                filename={rnaFilename}
                meta="RNA-seq CSV · Phase 14 model"
                statusPill={<span className="pill pill-running">⟳ Running</span>}
                onRunAnother={resetRna}
              />
              <ProgressPanel
                title="Running RNA inference…"
                sub="Phase 14 GBM/LGG-like model + optional morphology retrieval. This may take 1–3 minutes. Please keep this tab open."
              />
            </>
          )}

          {/* Compact input summary after completion */}
          {rnaState === "done" && rnaResult && (
            <InputSummary
              icon="📄"
              filename={rnaFilename}
              meta={`RNA-seq CSV · ${rnaResult.prediction_preview?.length ?? 0} case(s) · Phase 14 model`}
              statusPill={
                <span className={`pill ${rnaResult.status === "completed" ? "pill-success" : "pill-error"}`}>
                  {rnaResult.status === "completed" ? "✓ Completed" : "✗ Failed"}
                </span>
              }
              onRunAnother={resetRna}
            />
          )}

          {/* Results */}
          {rnaState === "done" && rnaResult && (
            <>
              <ResultCard data={rnaResult} />

              {hasCanvas && (
                <>
                  <div className="section-label" style={{ marginTop: 20 }}>
                    Morphology Canvas
                  </div>
                  <div className="card" style={{ padding: "20px 24px 24px" }}>
                    <CanvasViewer canvasFiles={canvasFiles} />
                  </div>
                </>
              )}

              {!hasCanvas &&
                rnaResult.status === "completed" &&
                rnaResult.canvas_enabled && (
                  <div className="info-box info" style={{ marginTop: 14 }}>
                    Canvas was enabled but no canvas files were returned. Check
                    backend logs for errors in the morphology retrieval step.
                  </div>
                )}
            </>
          )}
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          PATCH WORKFLOW
      ═══════════════════════════════════════════════════════════════════ */}
      {tab === "patch" && (
        <>
          {/* Upload form — only shown when idle */}
          {patchState === "idle" && (
            <PatchUpload
              onResult={handlePatchResult}
              onRunStart={handlePatchRunStart}
            />
          )}

          {/* Progress panel during run */}
          {patchState === "running" && (
            <>
              <InputSummary
                icon="🗜️"
                filename={patchFilename}
                meta="Patch ZIP · CTransPath embeddings · Phase 14 model"
                statusPill={<span className="pill pill-running">⟳ Running</span>}
                onRunAnother={resetPatch}
              />
              <ProgressPanel
                title="Running patch image inference…"
                sub="Extracting CTransPath embeddings and classifying GBM/LGG-like morphology. This may take 1–3 minutes depending on patch count and GPU availability."
              />
            </>
          )}

          {/* Compact input summary after completion */}
          {patchState === "done" && patchResult && (
            <InputSummary
              icon="🗜️"
              filename={patchFilename}
              meta={`Patch ZIP · ${patchImageCount ?? "?"} images found · Phase 14 model`}
              statusPill={
                <span className={`pill ${patchResult.status === "completed" ? "pill-success" : "pill-error"}`}>
                  {patchResult.status === "completed" ? "✓ Completed" : "✗ Failed"}
                </span>
              }
              onRunAnother={resetPatch}
            />
          )}

          {/* Patch result report */}
          {patchState === "done" && patchResult && (
            <PatchResultReport data={patchResult} />
          )}
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════════════
          WSI (Coming Soon)
      ═══════════════════════════════════════════════════════════════════ */}
      {tab === "wsi" && (
        <div
          style={{
            textAlign: "center",
            padding: "60px 24px",
            color: "var(--text-muted)",
          }}
        >
          <div style={{ fontSize: "2.5rem", marginBottom: 14 }}>🖼️</div>
          <div style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: 6 }}>
            Whole Slide Image Analysis
          </div>
          <div style={{ fontSize: "0.80rem" }}>Coming in a future version.</div>
        </div>
      )}

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="footer-note">
        <div>
          CNS-MultiModalAI GUI &nbsp;·&nbsp;{" "}
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
