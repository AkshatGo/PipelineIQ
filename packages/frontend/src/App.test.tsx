import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "./App";

describe("App", () => {
  it("presents the PipelineIQ risk workflow", () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <App />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("heading", { name: /turn pipeline failures/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /assess risk/i })).toBeInTheDocument();
  });
});

