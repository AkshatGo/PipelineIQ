
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { WorkspacePage } from './pages/WorkspacePage';
import { AutoFixReportPage } from './pages/AutoFixReportPage';
import { AutoFixFeedbackPage } from './pages/AutoFixFeedbackPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    mutations: { retry: 0 },
  },
});

export function RoutesApp() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/workspace/:workspaceId" element={<WorkspacePage />} />
        <Route path="/autofix/report" element={<AutoFixReportPage />} />
        <Route path="/autofix/feedback" element={<AutoFixFeedbackPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </QueryClientProvider>
  );
}

export function RootApp() {
  return (
    <React.StrictMode>
      <RoutesApp />
      {/* <ReactQueryDevtools initialIsOpen={false} /> */}
    </React.StrictMode>
  );
}