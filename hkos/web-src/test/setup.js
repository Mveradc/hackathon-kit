import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  delete window.matchMedia;
});
