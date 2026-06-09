import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CNS-MultiModalAI | Research Prototype",
  description:
    "CNS-MultiModalAI GUI MVP — GBM/LGG-like similarity inference. " +
    "Research prototype for academic thesis demonstration only. " +
    "Not a clinical diagnostic tool.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="robots" content="noindex, nofollow" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>{children}</body>
    </html>
  );
}
