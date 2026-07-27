import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GDSS",
  description:
    "Geometric Distributed Software Synchronizer - a semantic intelligence layer above Git.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
