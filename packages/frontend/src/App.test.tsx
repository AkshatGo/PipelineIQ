import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";

vi.mock("./api/auth", () => ({
  getCurrentUser: vi.fn().mockResolvedValue(null),
  githubLoginUrl: "/api/auth/github",
}));

describe("App", () => {
  it("presents the PipelineIQ risk workflow", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("heading", { name: /your build broke/i })).toBeTruthy();
    // Find the link with the specific href to avoid ambiguity
    const githubLinks = screen.getAllByRole("link", { name: /connect github/i });
    const githubLink = githubLinks.find((link) => link.getAttribute("href") === "/api/auth/github");
    expect(githubLink).toBeTruthy();
    expect(screen.getByRole("link", { name: /watch a real fix/i })).toBeTruthy();
  });
});
