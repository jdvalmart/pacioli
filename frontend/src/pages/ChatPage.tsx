import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Landmark, Loader2, Send, Settings2, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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
import { useMonth, monthLabel } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import type { AIConfig } from '@/lib/types'

function AISettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const config = useQuery({ queryKey: ['aiConfig'], queryFn: api.getAIConfig, enabled: open })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Configuración del asistente</DialogTitle>
          <DialogDescription>
            Conexión con Ollama para el asistente financiero.
          </DialogDescription>
        </DialogHeader>
        {config.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : config.data && open ? (
          <AISettingsForm initial={config.data} onOpenChange={onOpenChange} />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

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
    <div className="space-y-4">
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

export function ChatPage() {
  const { month } = useMonth()
  const queryClient = useQueryClient()
  const [question, setQuestion] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [confirmClear, setConfirmClear] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const history = useQuery({
    queryKey: ['chatHistory', month],
    queryFn: () => api.chatHistory(month.month, month.year),
  })

  const send = useMutation({
    mutationFn: (text: string) => api.sendChat(text, month.month, month.year),
    onSuccess: (reply) => {
      if (reply.error) {
        toast.error(reply.error)
      }
      void queryClient.invalidateQueries({ queryKey: ['chatHistory', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const clear = useMutation({
    mutationFn: () => api.clearChat(month.month, month.year),
    onSuccess: () => {
      toast.success('Conversación eliminada')
      setConfirmClear(false)
      void queryClient.invalidateQueries({ queryKey: ['chatHistory', month] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history.data, send.isPending])

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault()
    const text = question.trim()
    if (!text) return
    setQuestion('')
    send.mutate(text)
  }

  const messages = history.data ?? []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Asistente financiero</h1>
          <p className="text-sm text-muted-foreground">
            Pregunta sobre tus finanzas de {monthLabel(month)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => setConfirmClear(true)}>
            <Trash2 className="text-red-500" />
          </Button>
          <Button variant="outline" size="icon" onClick={() => setSettingsOpen(true)}>
            <Settings2 />
          </Button>
        </div>
      </div>

      <Card className="flex h-[65vh] flex-col">
        <CardHeader className="border-b pb-3">
          <CardTitle className="text-sm font-medium">
            Conversación de {monthLabel(month)}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 space-y-4 overflow-y-auto pt-4">
          {history.isLoading ? (
            <>
              <Skeleton className="h-12 w-3/4" />
              <Skeleton className="ml-auto h-12 w-2/3" />
            </>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <Landmark className="size-8" />
              <p>Pregúntame sobre tus gastos, presupuestos o ingresos.</p>
              <p className="text-xs">Ej. «¿En qué categoría me pasé del presupuesto?»</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-accent text-accent-foreground'
                  }`}
                >
                  {message.message}
                </div>
              </div>
            ))
          )}
          {send.isPending && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl bg-accent px-4 py-2 text-sm text-muted-foreground">
                <Loader2 className="size-4 animate-spin" /> Pensando…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </CardContent>
        <form onSubmit={handleSend} className="flex gap-2 border-t p-3">
          <Input
            placeholder="Escribe tu pregunta…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={send.isPending}
          />
          <Button type="submit" disabled={send.isPending || !question.trim()}>
            <Send />
          </Button>
        </form>
      </Card>

      <AISettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />

      <AlertDialog open={confirmClear} onOpenChange={setConfirmClear}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Borrar la conversación?</AlertDialogTitle>
            <AlertDialogDescription>
              Se eliminará todo el historial del chat de {monthLabel(month)}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => clear.mutate()}
              className="bg-red-600 hover:bg-red-700"
            >
              Borrar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
