"use client";

/** WarningBanner — pinned research-prototype disclaimer. */
export default function WarningBanner() {
  return (
    <div className="warning-banner" role="alert" aria-label="Research prototype warning">
      <span className="warning-icon">⚠️</span>
      <p className="warning-text">
        <strong>Research prototype only.</strong> This tool outputs GBM-like vs LGG-like
        similarity for academic thesis demonstration. It is not a pan-CNS classifier
        and not intended for clinical diagnosis. Results must not be used for patient
        management or medical decision-making.
      </p>
    </div>
  );
}
