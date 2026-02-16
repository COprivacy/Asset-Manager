import { useQuery } from "@tanstack/react-query";
import { type Signal } from "@shared/schema";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { format } from "date-fns";
import { motion, AnimatePresence } from "framer-motion";

export default function AIAnalysisPage() {
  const { data: signals, isLoading } = useQuery<Signal[]>({
    queryKey: ["/api/signals"],
    refetchInterval: 5000,
  });

  const analysisSignals = signals?.filter(s => s.result === "ANALYZING") || [];

  return (
    <div className="p-6 space-y-6 bg-background min-h-screen">
      <div className="flex items-center gap-2 mb-8">
        <Brain className="w-8 h-8 text-primary animate-pulse" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">IA Real-Time Analysis</h1>
          <p className="text-muted-foreground">Monitorando padrões e confluências em tempo real.</p>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-48 rounded-lg bg-card animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          <AnimatePresence mode="popLayout">
            {analysisSignals.length === 0 ? (
              <div className="col-span-full flex flex-col items-center justify-center h-64 border-2 border-dashed rounded-xl bg-card/50">
                <Brain className="w-12 h-12 text-muted-foreground/30 mb-4" />
                <p className="text-muted-foreground">Aguardando novo ciclo de análise da IA...</p>
              </div>
            ) : (
              analysisSignals.map((signal) => (
                <motion.div
                  key={signal.id}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.3 }}
                >
                  <Card className="overflow-hidden border-primary/20 bg-card/50 backdrop-blur-sm hover:border-primary/40 transition-all">
                    <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0 gap-2">
                      <CardTitle className="text-lg font-bold">
                        {signal.asset}
                      </CardTitle>
                      <Badge 
                        variant={signal.action === "CALL" ? "default" : signal.action === "PUT" ? "destructive" : "secondary"}
                        className="font-mono"
                      >
                        {signal.action === "CALL" && <TrendingUp className="w-3 h-3 mr-1" />}
                        {signal.action === "PUT" && <TrendingDown className="w-3 h-3 mr-1" />}
                        {signal.action === "WAIT" && <Minus className="w-3 h-3 mr-1" />}
                        {signal.action}
                      </Badge>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-muted-foreground">Confiança</span>
                        <span className="font-bold text-primary">{signal.confidence}%</span>
                      </div>
                      <div className="w-full bg-secondary/30 h-1.5 rounded-full overflow-hidden">
                        <motion.div 
                          className="bg-primary h-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${signal.confidence}%` }}
                        />
                      </div>
                      
                      <div className="bg-background/40 p-3 rounded-lg border border-border/50">
                        <p className="text-xs leading-relaxed italic text-foreground/90">
                          "{signal.reasoning}"
                        </p>
                      </div>

                      <div className="flex justify-between items-center text-[10px] uppercase tracking-wider text-muted-foreground pt-2 border-t border-border/20">
                        <span>{signal.strategy}</span>
                        <span>{signal.timestamp ? format(new Date(signal.timestamp), "HH:mm:ss") : "--:--:--"}</span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
