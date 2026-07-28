"use client";

import { useEffect } from "react";
import { AlertCircle } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[400px] p-6 text-center border border-destructive/20 rounded-xl bg-destructive/5 m-4">
      <AlertCircle className="w-12 h-12 text-destructive mb-4" />
      <h2 className="text-xl font-semibold mb-2">Something went wrong!</h2>
      <p className="text-muted-foreground mb-6 max-w-md">
        {error.message || "An unexpected layout rendering error occurred while loading this view."}
      </p>
      <button
        onClick={() => reset()}
        className="px-4 py-2 bg-destructive text-destructive-foreground font-medium rounded-md hover:bg-destructive/90 transition-colors shadow-sm"
      >
        Try again
      </button>
    </div>
  );
}
