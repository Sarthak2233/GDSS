import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";
import { Navigation } from "@/components/navigation";
import { RepoRefPicker } from "@/components/repo-ref-picker";

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
      <body className="flex h-screen w-screen overflow-hidden bg-background text-foreground font-sans">
        <Providers>
          <Navigation />
          <div className="flex flex-col flex-1 h-full relative">
            <RepoRefPicker />
            <main className="flex-1 overflow-auto p-6 relative z-0">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
