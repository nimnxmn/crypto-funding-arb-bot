"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { Toaster } from "sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 5_000, refetchInterval: 10_000 } },
  }));

  return (
    <QueryClientProvider client={client}>
      {children}
      <Toaster theme="dark" richColors position="top-right" />
    </QueryClientProvider>
  );
}
