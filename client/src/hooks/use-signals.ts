import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@shared/routes";
import { z } from "zod";

export function useSignals() {
  return useQuery({
    queryKey: [api.signals.list.path],
    queryFn: async () => {
      const res = await fetch(api.signals.list.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch signals");
      return api.signals.list.responses[200].parse(await res.json());
    },
    refetchInterval: 5000, // Poll every 5s for new signals
  });
}

export function useClearSignals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch(api.signals.clear.path, {
        method: api.signals.clear.method,
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to clear signals");
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [api.signals.list.path] }),
  });
}

// Helper hook for signal stats
export function useSignalStats() {
  const { data: signals } = useSignals();
  
  if (!signals) return { winRate: 0, total: 0, profit: 0 };

  const finished = signals.filter(s => s.result === "WIN" || s.result === "LOSS");
  const wins = finished.filter(s => s.result === "WIN").length;
  const total = finished.length;
  
  return {
    winRate: total > 0 ? Math.round((wins / total) * 100) : 0,
    total: signals.length,
    active: signals.filter(s => s.result === "PENDING").length,
    wins,
    losses: total - wins
  };
}
