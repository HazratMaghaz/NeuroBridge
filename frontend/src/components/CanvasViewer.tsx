"use client";

import { useState } from "react";
import type { CanvasFile } from "./RnaUpload";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function absUrl(rel?: string | null): string | null {
  if (!rel) return null;
  return `${API_BASE}${rel}`;
}

interface Props {
  canvasFiles: CanvasFile[];
}

export default function CanvasViewer({ canvasFiles }: Props) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (!canvasFiles || canvasFiles.length === 0) {
    return (
      <div className="info-box info">
        No morphology canvas was generated for this run.
        Enable &ldquo;Generate morphology canvas&rdquo; in the upload panel and re-run.
      </div>
    );
  }

  const active = canvasFiles[activeIdx];
  const imgUrl = absUrl(active.canvas_url);

  return (
    <div>
      {/* Patient selector (if multiple) */}
      {canvasFiles.length > 1 && (
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          {canvasFiles.map((cf, i) => (
            <button
              key={i}
              className={`btn ${i === activeIdx ? "btn-primary" : "btn-ghost"}`}
              style={{ padding: "5px 12px", fontSize: "0.78rem" }}
              onClick={() => setActiveIdx(i)}
              id={`canvas-tab-${i}`}
            >
              {cf.patient_id ?? `Canvas ${i + 1}`}
            </button>
          ))}
        </div>
      )}

      <div className="canvas-viewer" id="morphology-canvas-viewer">
        {/* Canvas header */}
        <div className="canvas-header">
          <div>
            <div style={{ fontSize: "0.80rem", fontWeight: 600, color: "var(--text-primary)" }}>
              Morphology Canvas
            </div>
            <div className="canvas-pid">
              Patient: {active.patient_id ?? "unknown"}
            </div>
          </div>
          {active.retrieval_csv_url && (
            <a
              className="dl-link"
              href={absUrl(active.retrieval_csv_url) ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              id="dl-retrieval-canvas"
              style={{ flexShrink: 0 }}
            >
              🔍 Retrieval CSV
            </a>
          )}
        </div>

        {/* Canvas image */}
        <div className="canvas-img-wrap">
          {imgUrl ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={imgUrl}
              alt={`Morphology canvas for patient ${active.patient_id ?? "unknown"}`}
              style={{ maxWidth: "100%", height: "auto" }}
              loading="lazy"
            />
          ) : (
            <div style={{ padding: 40, color: "var(--text-muted)", fontSize: "0.82rem" }}>
              Canvas image URL is unavailable.
            </div>
          )}
        </div>

        {/* Retrieval note */}
        {active.note && (
          <div className="canvas-note">{active.note}</div>
        )}
      </div>
    </div>
  );
}
