import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Bot, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { AccountsSection } from '@/components/AccountsSection'
import { CreditCardsSection } from '@/components/CreditCardsSection'
import { SavingsSection } from '@/components/SavingsSection'
import { CategoriesSection } from '@/pages/CategoriesPage'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import type { AIConfig } from '@/lib/types'

function AISettingsForm({
  initial,
  onOpenChange,
}: {
  initial: AIConfig
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [model, setModel] = useState(initial.model)
  const [url, setUrl] = useState(initial.url)
  const [timeout, setTimeoutValue] = useState(String(initial.timeout))
  const [temperature, setTemperature] = useState(String(initial.temperature))
  const [maxTokens, setMaxTokens] = useState(String(initial.max_tokens))
  const [think, setThink] = useState<AIConfig['think']>(initial.think)

  const save = useMutation({
    mutationFn: (payload: AIConfig) => api.updateAIConfig(payload),
    onSuccess: () => {
      toast.success('Configuración guardada')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['aiConfig'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const testConnection = useMutation({
    mutationFn: api.testAIConnection,
    onSuccess: (result) => {
      if (result.success) {
        toast.success(result.message)
      } else {
        toast.error(result.message)
      }
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSave = () => {
    save.mutate({
      model,
      url,
      timeout: Number(timeout),
      temperature: Number(temperature),
      max_tokens: Number(maxTokens),
      think,
    })
  }

  return (
    <div className="grid max-w-2xl gap-4">
      <div className="space-y-1.5">
        <Label htmlFor="ai-model">Modelo</Label>
        <Input id="ai-model" value={model} onChange={(e) => setModel(e.target.value)} />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="ai-url">URL de Ollama</Label>
        <Input id="ai-url" value={url} onChange={(e) => setUrl(e.target.value)} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="ai-timeout">Timeout (s)</Label>
          <Input
            id="ai-timeout"
            type="number"
            min={1}
            max={600}
            value={timeout}
            onChange={(e) => setTimeoutValue(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ai-temp">Temperatura</Label>
          <Input
            id="ai-temp"
            type="number"
            step={0.1}
            min={0}
            max={2}
            value={temperature}
            onChange={(e) => setTemperature(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ai-tokens">Max tokens</Label>
          <Input
            id="ai-tokens"
            type="number"
            min={16}
            max={8192}
            value={maxTokens}
            onChange={(e) => setMaxTokens(e.target.value)}
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>Razonamiento (think)</Label>
        <Select value={think} onValueChange={(v) => setThink((v ?? 'low') as AIConfig['think'])}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="off">Apagado (más rápido)</SelectItem>
            <SelectItem value="low">Bajo (recomendado)</SelectItem>
            <SelectItem value="medium">Medio</SelectItem>
            <SelectItem value="high">Alto (más lento)</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Solo aplica a modelos con razonamiento (Qwen3, DeepSeek-R1).
        </p>
      </div>
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={() => testConnection.mutate()}
          disabled={testConnection.isPending}
        >
          {testConnection.isPending && <Loader2 className="animate-spin" />}
          Probar conexión
        </Button>
        <Button className="flex-1" onClick={handleSave} disabled={save.isPending}>
          {save.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </div>
    </div>
  )
}

function AssistantSettings() {
  const config = useQuery({ queryKey: ['aiConfig'], queryFn: api.getAIConfig })
  return (
    <section className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-[0_3px_0_0_color-mix(in_oklch,var(--primary),black_18%)]">
          <Bot className="size-5" />
        </div>
        <div>
          <h2 className="text-lg font-extrabold">Asistente</h2>
          <p className="text-sm font-semibold text-muted-foreground">
            Conexión con Ollama para el asistente financiero
          </p>
        </div>
      </div>
      {config.isLoading ? (
        <div className="max-w-2xl space-y-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : config.data ? (
        <AISettingsForm initial={config.data} onOpenChange={() => {}} />
      ) : null}
    </section>
  )
}

export function SettingsPage() {
  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-xl font-extrabold">Configuración</h1>
        <p className="text-sm font-semibold text-muted-foreground">
          Crea y edita tus cuentas y tarjetas de crédito, y ajusta el asistente
        </p>
      </div>

      <AccountsSection />

      <CreditCardsSection />

      <SavingsSection />

      <CategoriesSection />

      <AssistantSettings />
    </div>
  )
}
