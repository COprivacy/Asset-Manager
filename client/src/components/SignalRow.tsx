import { motion } from "framer-motion";
import { format } from "date-fns";
import { TrendingUp, TrendingDown, Clock, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Signal } from "@shared/schema";

interface SignalRowProps {
  signal: Signal;
  index: number;
}

export function SignalRow({ signal, index }: SignalRowProps) {
  const isCall = signal.action === "CALL";
  const isWin = signal.result === "WIN";
  const isLoss = signal.result === "LOSS";
  const isPending = signal.result === "PENDING" || !signal.result;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="group relative"
    >
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      
      <div className="grid grid-cols-12 gap-4 p-4 items-center border-b border-white/5 hover:bg-white/[0.02] transition-colors">
        {/* Time */}
        <div className="col-span-2 flex items-center gap-2 text-sm text-muted-foreground font-mono">
          <Clock className="w-3 h-3" />
          {signal.timestamp ? format(new Date(signal.timestamp), "HH:mm:ss") : "--:--:--"}
        </div>

        {/* Asset */}
        <div className="col-span-2">
          <span className="font-bold text-white tracking-wide">{signal.asset}</span>
        </div>

        {/* Action */}
        <div className="col-span-2">
          <div className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-bold border",
            isCall 
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
              : "bg-rose-500/10 border-rose-500/20 text-rose-400"
          )}>
            {isCall ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {signal.action}
          </div>
        </div>

        {/* Price */}
        <div className="col-span-2 font-mono text-sm text-white/80">
          {signal.price || "---"}
        </div>

        {/* Strategy */}
        <div className="col-span-2">
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-white/5 text-muted-foreground border border-white/5">
            {signal.strategy}
          </span>
        </div>

        {/* Confidence/Result */}
        <div className="col-span-2 flex items-center justify-end gap-4">
          <div className="flex flex-col items-end">
            <div className="h-1.5 w-16 bg-white/10 rounded-full overflow-hidden">
              <div 
                className={cn(
                  "h-full rounded-full transition-all duration-1000",
                  signal.confidence >= 80 ? "bg-emerald-500" : "bg-blue-500"
                )}
                style={{ width: `${signal.confidence}%` }}
              />
            </div>
            <span className="text-[10px] text-muted-foreground mt-1 font-mono">{signal.confidence}% Conf.</span>
          </div>

          <div className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center border",
            isWin && "bg-emerald-500/20 border-emerald-500 text-emerald-500",
            isLoss && "bg-rose-500/20 border-rose-500 text-rose-500",
            isPending && "bg-yellow-500/10 border-yellow-500/30 text-yellow-500"
          )}>
            {isWin && <CheckCircle2 className="w-4 h-4" />}
            {isLoss && <XCircle className="w-4 h-4" />}
            {isPending && <AlertCircle className="w-4 h-4" />}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
