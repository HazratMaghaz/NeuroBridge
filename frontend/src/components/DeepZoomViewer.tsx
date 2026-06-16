"use client";

import React, { useEffect, useRef } from "react";

interface Props {
  dziUrl: string;
  height?: string;
  title?: string;
  description?: string;
}

export default function DeepZoomViewer({ dziUrl, height = "500px", title, description }: Props) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const osdRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !viewerRef.current) return;

    // Dynamically import OpenSeadragon to avoid SSR issues
    import("openseadragon").then((OpenSeadragon) => {
      osdRef.current = OpenSeadragon.default({
        element: viewerRef.current!,
        prefixUrl: "https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/images/",
        tileSources: dziUrl,
        showNavigationControl: true,
        showNavigator: true,
        navigatorPosition: "BOTTOM_RIGHT",
        animationTime: 0.5,
        blendTime: 0.1,
        constrainDuringPan: true,
        maxZoomPixelRatio: 2,
      });
    });

    return () => {
      if (osdRef.current) {
        try {
          osdRef.current.destroy();
          osdRef.current = null;
        } catch (e) {
          console.error("Failed to destroy OpenSeadragon instance", e);
        }
      }
    };
  }, [dziUrl]);

  return (
    <div style={{ marginBottom: 16 }}>
      {title && (
        <h4 style={{ margin: "0 0 4px 0", color: "var(--text-primary)" }}>
          {title}
        </h4>
      )}
      {description && (
        <p style={{ margin: "0 0 8px 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
          {description}
        </p>
      )}
      <div
        ref={viewerRef}
        style={{
          width: "100%",
          height,
          background: "#000",
          borderRadius: "var(--r-sm)",
          overflow: "hidden",
        }}
      />
      <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4, textAlign: "right" }}>
        Interactive zoom viewer for generated visualization output. Use scroll/pinch to zoom.
      </div>
    </div>
  );
}
