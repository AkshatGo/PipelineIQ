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

    expect(screen.getByRole("heading", { name: /turn pipeline failures/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in with github/i })).toHaveAttribute(
      "href",
      "/api/auth/github",
    );
    expect(screen.getByRole("button", { name: /assess risk/i })).toBeInTheDocument();
  });
});
