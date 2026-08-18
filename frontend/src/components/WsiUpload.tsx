"use client";

import { useState } from "react";
import type { PatchApiResponse } from "./PatchUpload";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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

interface Props {
  onResult?: (data: any) => void;
  onRunStart?: (filename: string) => void;
}

export default function WsiUpload({ onResult, onRunStart }: Props) {
  const [wsiPath, setWsiPath] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [maxPatches, setMaxPatches] = useState(300);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isBatchMode, setIsBatchMode] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (isBatchMode && !file) {
      setError("Please select a CSV manifest.");
      return;
    }
    if (!isBatchMode && !wsiPath.trim()) {
      setError("Please enter a local WSI path.");
      return;
    }

    setLoading(true);
    setError(null);
    
    // Extract just the filename for the UI summary
    const filename = isBatchMode ? file!.name : (wsiPath.split("/").pop() ?? wsiPath);
    onRunStart?.(filename);

    try {
      let res;
      if (isBatchMode) {
        const fd = new FormData();
        fd.append("file", file!);
        res = await fetch(`${API_BASE}/api/infer/wsi-path/batch`, {
          method: "POST",
          body: fd,
        });
      } else {
        res = await fetch(`${API_BASE}/api/infer/wsi-path`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            wsi_path: wsiPath.trim(),
            max_patches: maxPatches,
            run_model: true,
          }),
        });
      }

      const data = await res.json();

      if (!res.ok) {
        const detail = (data as unknown as { detail?: string }).detail;
        throw new Error(detail ?? `HTTP ${res.status}`);
      }

      onResult?.(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="card-title">🖼️ Local WSI Analysis</div>
      <p className="card-desc">
        Local WSI path mode is for .svs files already present on this workstation/server.
        Browser WSI upload is disabled in this MVP.
      </p>

      {/* Mode Selector */}
      <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <label className="option-item" style={{ cursor: "pointer" }}>
          <input type="radio" name="wsiMode" checked={!isBatchMode} onChange={() => setIsBatchMode(false)} disabled={loading} />
          Single WSI Path
        </label>
        <label className="option-item" style={{ cursor: "pointer" }}>
          <input type="radio" name="wsiMode" checked={isBatchMode} onChange={() => setIsBatchMode(true)} disabled={loading} />
          Batch Manifest
        </label>
      </div>

      <form onSubmit={submit}>
        {!isBatchMode ? (
          <div style={{ marginBottom: 16 }}>
            <label
              htmlFor="wsi-path"
              style={{
                display: "block",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
                marginBottom: 6,
              }}
            >
              Local WSI Path (absolute)
            </label>
            <input
              id="wsi-path"
              type="text"
              value={wsiPath}
              onChange={(e) => setWsiPath(e.target.value)}
              disabled={loading}
              placeholder="/path/to/data/example.svs"
              style={{
                width: "100%",
                padding: "10px 14px",
                background: "var(--bg-surface)",
                border: "1px solid var(--border)",
                borderRadius: "var(--r-sm)",
                color: "var(--text-primary)",
                fontFamily: "var(--font-mono)",
                fontSize: "0.85rem",
              }}
            />
          </div>
        ) : (
          <div style={{ marginBottom: 16 }}>
            <label
              htmlFor="wsi-manifest"
              style={{
                display: "block",
                fontSize: "0.85rem",
                fontWeight: 600,
                color: "var(--text-secondary)",
                marginBottom: 6,
              }}
            >
              CSV Manifest Upload
            </label>
            <div className="info-box info" style={{ marginBottom: 10 }}>
              Manifest must contain columns: <code>sample_id, wsi_path, max_patches</code>.<br/>
              <em>One manifest CSV can contain many WSI rows.</em>
            </div>
            <input
              id="wsi-manifest"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={loading}
              style={{ width: "100%", padding: "6px 0" }}
            />
          </div>
        )}

        <div style={{ marginBottom: 20 }}>
          <label
            htmlFor="wsi-max-patches"
            style={{
              display: "block",
              fontSize: "0.85rem",
              fontWeight: 600,
              color: "var(--text-secondary)",
              marginBottom: 6,
            }}
          >
            Max Patches to Extract
          </label>
          <input
            id="wsi-max-patches"
            type="number"
            min={1}
            max={500}
            value={maxPatches}
            onChange={(e) => setMaxPatches(parseInt(e.target.value) || 1)}
            disabled={loading}
            style={{
              width: "100%",
              padding: "10px 14px",
              background: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--r-sm)",
              color: "var(--text-primary)",
              fontSize: "0.85rem",
              marginBottom: 8,
            }}
          />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            {[
              { val: 20, label: "20 = Fast test" },
              { val: 100, label: "100 = Quick demo" },
              { val: 300, label: "300 = Recommended" },
              { val: 500, label: "500 = Extended" },
            ].map((preset) => (
              <button
                key={preset.val}
                type="button"
                className="btn btn-ghost"
                style={{
                  fontSize: "0.75rem",
                  padding: "4px 8px",
                  border: maxPatches === preset.val ? "1px solid var(--border-bright)" : "1px solid transparent",
                  background: maxPatches === preset.val ? "var(--bg-base)" : "transparent",
                }}
                onClick={() => setMaxPatches(preset.val)}
                disabled={loading}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", margin: "4px 0 0" }}>
            Recommended: 300 patches for supervisor demo. Higher values increase runtime and output size.
          </p>
          {maxPatches > 500 && (
            <div className="warning-banner" style={{ marginTop: 8 }}>
              <span className="warning-icon">⚠️</span>
              <p className="warning-text">
                Large patch counts may slow WSI extraction, embedding, and browser rendering. Use 100–300 for live demos.
              </p>
            </div>
          )}
        </div>

        <div className="btn-row">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading || (isBatchMode ? !file : !wsiPath.trim())}
          >
            {loading ? (
              <>
                <span className="spinner" />
                Extracting & Running…
              </>
            ) : (
              <>▶ Run WSI Analysis</>
            )}
          </button>
          {wsiPath && !loading && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setWsiPath("");
                setError(null);
              }}
            >
              ✕ Clear
            </button>
          )}
        </div>
      </form>

      {/* Error card */}
      {error && !loading && (
        <div className="error-card" role="alert" style={{ marginTop: 16 }}>
          <div className="error-card-title">⚠ Request failed</div>
          <div className="error-card-hint">
            {isNetworkError(error)
              ? "Could not reach the backend. Make sure uvicorn is running on port 8000."
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
