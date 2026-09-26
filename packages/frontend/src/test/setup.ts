import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Polyfill for IntersectionObserver (used by framer-motion's useInView)
// Must be defined before any modules that use it are imported
const mockIntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
  takeRecords: () => [],
  root: null,
  rootMargin: '',
  thresholds: [],
}));

global.IntersectionObserver = mockIntersectionObserver;