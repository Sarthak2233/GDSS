import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";

export const metadata: Metadata = {
  title: "GDSS - Gate Distributive Semantic Synopsis",
  description:
    "Semantic Branch Intelligence and PR Collision Radar above Git.",
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
