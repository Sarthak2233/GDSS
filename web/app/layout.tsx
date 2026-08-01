import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";

export const metadata: Metadata = {
  title: "GDSS - Geometric Distributed Software Synchronizer",
  description:
    "A semantic intelligence layer above Git. Treat software development as a continuous geometric-semantic dynamical system.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="h-screen w-screen overflow-hidden bg-bg text-text font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
