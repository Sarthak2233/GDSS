import { describe, it, expect } from "vitest";
import { GDSS_API_BASE_URL } from "@/lib/api";

describe("GDSS API Client configuration", () => {
  it("defaults to http://127.0.0.1:8787 local API server", () => {
    expect(GDSS_API_BASE_URL).toBe("http://127.0.0.1:8787");
  });
});
