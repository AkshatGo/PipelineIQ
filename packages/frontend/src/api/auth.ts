import type { UserResponse } from "@pipelineiq/shared";
import axios from "axios";

import { api } from "./client";

export const githubLoginUrl = `${api.defaults.baseURL ?? "/api"}/auth/github`;

export async function getCurrentUser(): Promise<UserResponse | null> {
  try {
    const response = await api.get<UserResponse>("/auth/me");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) return null;
    throw error;
  }
}
