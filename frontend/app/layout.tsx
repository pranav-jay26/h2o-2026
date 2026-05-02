import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "H2O — Predictive Water Intelligence",
  description:
    "Early-warning water intelligence for Sacramento River / Shasta Lake",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
