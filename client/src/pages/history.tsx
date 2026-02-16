import { useQuery } from "@tanstack/react-query";
import { type Signal } from "@shared/schema";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { History, TrendingUp, TrendingDown, CheckCircle2, XCircle, Clock } from "lucide-react";
import { format } from "date-fns";
import { motion } from "framer-motion";

export default function HistoryPage() {
  const { data: signals, isLoading } = useQuery<Signal[]>({
    queryKey: ["/api/signals"],
    refetchInterval: 5000,
  });

  const historySignals = signals?.filter(s => s.result !== "ANALYZING") || [];
  
  const stats = {
    total: historySignals.length,
    wins: historySignals.filter(s => s.result === "WIN").length,
    losses: historySignals.filter(s => s.result === "LOSS").length,
  };
  
  const winRate = stats.total > 0 ? (stats.wins / stats.total) * 100 : 0;

  return (
    <div className="p-6 space-y-6 bg-background min-h-screen">
      <div className="flex items-center gap-2 mb-8">
        <History className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trade History</h1>
          <p className="text-muted-foreground">Relatório completo de operações e performance.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Signals</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Win Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-primary">{winRate.toFixed(1)}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">W/L Ratio</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <span className="text-green-500">{stats.wins}W</span>
              <span className="mx-2">/</span>
              <span className="text-red-500">{stats.losses}L</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Asset</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Strategy</TableHead>
                <TableHead>Confidence</TableHead>
                <TableHead className="text-right">Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                [1, 2, 3].map(i => (
                  <TableRow key={i}>
                    {[1, 2, 3, 4, 5, 6].map(j => (
                      <TableCell key={j}><div className="h-4 w-full bg-muted animate-pulse rounded" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : historySignals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                    Nenhum sinal no histórico ainda.
                  </TableCell>
                </TableRow>
              ) : (
                historySignals.map((signal) => (
                  <TableRow key={signal.id}>
                    <TableCell className="text-xs text-muted-foreground">
                      {signal.timestamp ? format(new Date(signal.timestamp), "HH:mm:ss") : "--:--"}
                    </TableCell>
                    <TableCell className="font-medium">{signal.asset}</TableCell>
                    <TableCell>
                      <Badge variant={signal.action === "CALL" ? "default" : "destructive"} className="gap-1">
                        {signal.action === "CALL" ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {signal.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">{signal.strategy}</TableCell>
                    <TableCell>{signal.confidence}%</TableCell>
                    <TableCell className="text-right">
                      {signal.result === "WIN" && (
                        <div className="flex items-center justify-end gap-1 text-green-500 font-bold">
                          <CheckCircle2 className="w-4 h-4" /> WIN
                        </div>
                      )}
                      {signal.result === "LOSS" && (
                        <div className="flex items-center justify-end gap-1 text-red-500 font-bold">
                          <XCircle className="w-4 h-4" /> LOSS
                        </div>
                      )}
                      {signal.result === "PENDING" && (
                        <div className="flex items-center justify-end gap-1 text-yellow-500">
                          <Clock className="w-4 h-4" /> PENDING
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
