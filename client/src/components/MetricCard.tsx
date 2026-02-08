import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  className?: string;
  glowColor?: "green" | "red" | "blue";
}

export function MetricCard({ 
  label, 
  value, 
  icon, 
  trend, 
  trendValue, 
  className,
  glowColor
}: MetricCardProps) {
  return (
    <div className={cn(
      "glass-card rounded-xl p-6 relative overflow-hidden group transition-all duration-300 hover:border-white/10",
      className
    )}>
      {glowColor && (
        <div className={cn(
          "absolute -top-10 -right-10 w-32 h-32 rounded-full blur-[80px] opacity-20 transition-opacity duration-500 group-hover:opacity-30",
          glowColor === "green" && "bg-emerald-500",
          glowColor === "red" && "bg-rose-500",
          glowColor === "blue" && "bg-blue-500"
        )} />
      )}
      
      <div className="relative z-10 flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-muted-foreground mb-1">{label}</p>
          <h3 className="text-3xl font-bold font-mono tracking-tight text-white">{value}</h3>
        </div>
        {icon && (
          <div className="p-3 rounded-lg bg-white/5 text-white/80">
            {icon}
          </div>
        )}
      </div>

      {trend && trendValue && (
        <div className="relative z-10 mt-4 flex items-center gap-2">
          <span className={cn(
            "text-xs font-bold px-2 py-0.5 rounded-full",
            trend === "up" && "bg-emerald-500/10 text-emerald-500",
            trend === "down" && "bg-rose-500/10 text-rose-500",
            trend === "neutral" && "bg-gray-500/10 text-gray-400",
          )}>
            {trend === "up" && "↑"}
            {trend === "down" && "↓"}
            {trendValue}
          </span>
          <span className="text-xs text-muted-foreground">vs last session</span>
        </div>
      )}
    </div>
  );
}
