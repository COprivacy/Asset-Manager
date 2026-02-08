import { useSignals, useClearSignals, useSignalStats } from "@/hooks/use-signals";
import { SignalRow } from "@/components/SignalRow";
import { MetricCard } from "@/components/MetricCard";
import { ConsoleInstructions } from "@/components/ConsoleInstructions";
import { Loader2, RefreshCw, Trash2, Activity, Zap, BarChart3, Wallet } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const { data: signals, isLoading, refetch, isRefetching } = useSignals();
  const { mutate: clearSignals, isPending: isClearing } = useClearSignals();
  const stats = useSignalStats();

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/5 bg-background/80 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white">Quantum Signals</h1>
              <p className="text-xs text-emerald-500 font-medium">LIVE MARKET DATA</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => refetch()}
              disabled={isRefetching}
              className="border-white/10 hover:bg-white/5 hover:text-white"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${isRefetching ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button 
              variant="destructive" 
              size="sm"
              onClick={() => clearSignals()}
              disabled={isClearing || !signals?.length}
              className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear History
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <MetricCard 
            label="Win Rate" 
            value={`${stats.winRate}%`} 
            icon={<Zap className="w-5 h-5 text-yellow-400" />}
            glowColor="green"
            trend={stats.winRate > 50 ? "up" : "down"}
            trendValue="2.4%"
          />
          <MetricCard 
            label="Total Signals" 
            value={stats.total} 
            icon={<BarChart3 className="w-5 h-5 text-blue-400" />}
            glowColor="blue"
          />
          <MetricCard 
            label="Active Trades" 
            value={stats.active} 
            icon={<Activity className="w-5 h-5 text-emerald-400" />}
            className="border-emerald-500/20"
          />
          <MetricCard 
            label="Net Profit (Est)" 
            value={`$${(stats.wins * 85) - (stats.losses * 100)}`} 
            icon={<Wallet className="w-5 h-5 text-purple-400" />}
            trend="up"
            trendValue="+12%"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Signals Table */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">Recent Signals</h2>
              <div className="flex gap-2">
                <span className="flex items-center gap-1.5 text-xs text-muted-foreground px-2 py-1 rounded-full bg-white/5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Connected
                </span>
              </div>
            </div>

            <div className="glass-card rounded-xl overflow-hidden min-h-[400px] border border-white/5">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-4 p-4 bg-white/[0.02] border-b border-white/5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <div className="col-span-2">Time</div>
                <div className="col-span-2">Asset</div>
                <div className="col-span-2">Action</div>
                <div className="col-span-2">Price</div>
                <div className="col-span-2">Strategy</div>
                <div className="col-span-2 text-right">Result</div>
              </div>

              {/* Table Body */}
              <div className="divide-y divide-white/5">
                {isLoading ? (
                  <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                    <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
                    <p>Scanning markets...</p>
                  </div>
                ) : signals?.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
                    <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
                      <Activity className="w-8 h-8 opacity-20" />
                    </div>
                    <p>No signals detected yet</p>
                    <p className="text-xs mt-2 opacity-50">Wait for the bot to identify opportunities</p>
                  </div>
                ) : (
                  signals?.map((signal, idx) => (
                    <SignalRow key={signal.id} signal={signal} index={idx} />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <ConsoleInstructions />
            
            {/* Market Status Card */}
            <div className="glass-card rounded-xl p-6 border border-white/5">
              <h3 className="font-semibold text-white mb-4">Market Volatility</h3>
              <div className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">EUR/USD</span>
                    <span className="text-emerald-500">High</span>
                  </div>
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-500 w-[85%] rounded-full animate-pulse" />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">GBP/JPY</span>
                    <span className="text-yellow-500">Medium</span>
                  </div>
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-yellow-500 w-[45%] rounded-full" />
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">BTC/USD</span>
                    <span className="text-rose-500">Extreme</span>
                  </div>
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-rose-500 w-[92%] rounded-full animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
