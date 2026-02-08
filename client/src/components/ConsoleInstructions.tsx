import { Terminal, Copy, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

export function ConsoleInstructions() {
  const [copied, setCopied] = useState(false);
  const command = "python trading_bot.py";

  const handleCopy = () => {
    navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card rounded-xl p-0 overflow-hidden border-l-4 border-l-primary/50">
      <div className="bg-white/[0.03] p-4 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-2 text-primary">
          <Terminal className="w-5 h-5" />
          <h3 className="font-semibold">Bot Control Center</h3>
        </div>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/50" />
          <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/50" />
          <div className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/50" />
        </div>
      </div>
      
      <div className="p-6 space-y-4">
        <p className="text-muted-foreground text-sm">
          To start receiving live market signals, you need to run the Python trading bot engine. 
          Open the <span className="text-white font-medium">Shell</span> tab in Replit and execute:
        </p>
        
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/10 to-transparent blur opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative bg-black/40 rounded-lg p-4 font-mono text-sm border border-white/10 flex items-center justify-between">
            <span className="text-emerald-400 flex items-center gap-2">
              <span className="text-white/40">$</span> {command}
            </span>
            <button 
              onClick={handleCopy}
              className="p-2 hover:bg-white/10 rounded-md transition-colors text-muted-foreground hover:text-white"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground border-t border-white/5 pt-4">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          System ready to accept signals
        </div>
      </div>
    </div>
  );
}
