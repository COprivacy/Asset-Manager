import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Settings, Save, Trash2, ShieldAlert } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useMutation } from "@tanstack/react-query";

export default function SettingsPage() {
  const { toast } = useToast();

  const clearMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("DELETE", "/api/signals");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/signals"] });
      toast({
        title: "Histórico limpo",
        description: "Todos os sinais foram removidos com sucesso.",
      });
    },
  });

  return (
    <div className="p-6 space-y-6 bg-background min-h-screen">
      <div className="flex items-center gap-2 mb-8">
        <Settings className="w-8 h-8 text-primary" />
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground">Configure as preferências do bot e do dashboard.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Bot Configuration</CardTitle>
            <CardDescription>
              Essas configurações afetam como o bot processa as análises.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto-Trade</Label>
                <p className="text-xs text-muted-foreground">Executar ordens automaticamente na IQ Option.</p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="space-y-2">
              <Label htmlFor="min-conf">Confiança Mínima (%)</Label>
              <Input id="min-conf" type="number" defaultValue="75" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="stake">Stake Padrão ($)</Label>
              <Input id="stake" type="number" defaultValue="2.00" />
            </div>
            <Button className="w-full gap-2">
              <Save className="w-4 h-4" /> Salvar Configurações
            </Button>
          </CardContent>
        </Card>

        <Card className="border-destructive/20">
          <CardHeader>
            <CardTitle className="text-destructive flex items-center gap-2">
              <ShieldAlert className="w-5 h-5" /> Danger Zone
            </CardTitle>
            <CardDescription>
              Ações irreversíveis para limpeza de dados.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
              <p className="text-sm text-destructive font-medium mb-4">
                Limpar todo o histórico de sinais e análises da IA. Esta ação não pode ser desfeita.
              </p>
              <Button 
                variant="destructive" 
                className="w-full gap-2"
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
              >
                <Trash2 className="w-4 h-4" /> {clearMutation.isPending ? "Limpando..." : "Limpar Todo Histórico"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
