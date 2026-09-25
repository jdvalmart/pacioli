import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Landmark, Loader2, MessageSquare, Send, Settings2, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
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
import { Input } from '@/components/ui/input'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

export function ChatBubble() {
  const { month } = useMonth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [confirmClear, setConfirmClear] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const history = useQuery({
    queryKey: ['chatHistory', month],
    queryFn: () => api.chatHistory(month.month, month.year),
    enabled: open,
  })

  const send = useMutation({
    mutationFn: (text: string) => api.sendChat(text, month.month, month.year),
    onSuccess: (reply) => {
      if (reply.error) toast.error(reply.error)
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
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history.data, send.isPending, open])

  const handleSend = (event: React.FormEvent) => {
    event.preventDefault()
    const text = question.trim()
    if (!text) return
    setQuestion('')
    send.mutate(text)
  }

  const messages = history.data ?? []

  return (
    <>
      {open && (
        <div className="fixed bottom-24 left-4 z-50 flex h-[30rem] w-[min(24rem,calc(100vw-2rem))] flex-col overflow-hidden rounded-3xl border-2 border-border bg-card shadow-[0_16px_50px_rgba(0,0,0,0.22)] md:left-64">
          <div className="flex items-center justify-between bg-primary px-4 py-3 text-primary-foreground">
            <div className="flex items-center gap-2.5">
              <Landmark className="size-5" />
              <div>
                <p className="text-sm leading-none font-black">Asistente</p>
                <p className="text-[11px] font-semibold opacity-80">{monthLabel(month)}</p>
              </div>
            </div>
            <div className="flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => {
                  setOpen(false)
                  navigate('/settings')
                }}
                className="rounded-lg p-1.5 transition-colors hover:bg-white/20"
                aria-label="Configuración"
              >
                <Settings2 className="size-4" />
              </button>
              <button
                type="button"
                onClick={() => setConfirmClear(true)}
                className="rounded-lg p-1.5 transition-colors hover:bg-white/20"
                aria-label="Borrar conversación"
              >
                <Trash2 className="size-4" />
              </button>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 transition-colors hover:bg-white/20"
                aria-label="Cerrar"
              >
                <X className="size-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto bg-muted/30 p-4">
            {history.isLoading ? (
              <>
                <div className="h-10 w-3/4 rounded-2xl bg-muted" />
                <div className="ml-auto h-10 w-2/3 rounded-2xl bg-muted" />
              </>
            ) : messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-muted-foreground">
                <Landmark className="size-7" />
                <p className="text-sm font-semibold">
                  Pregúntame sobre tus gastos, presupuestos o ingresos.
                </p>
                <p className="text-xs">Ej. «¿En qué categoría me pasé del presupuesto?»</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}
                >
                  <div
                    className={cn(
                      'max-w-[85%] rounded-2xl px-3.5 py-2 text-sm font-medium whitespace-pre-wrap shadow-sm',
                      message.role === 'user'
                        ? 'rounded-br-sm bg-primary text-primary-foreground'
                        : 'rounded-bl-sm border-2 border-border bg-card',
                    )}
                  >
                    {message.message}
                  </div>
                </div>
              ))
            )}
            {send.isPending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border-2 border-border bg-card px-3.5 py-2 text-sm font-medium text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Pensando…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSend} className="flex gap-2 border-t-2 border-border bg-card p-3">
            <Input
              placeholder="Escribe tu pregunta…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={send.isPending}
            />
            <Button type="submit" size="icon" disabled={send.isPending || !question.trim()}>
              <Send />
            </Button>
          </form>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 left-4 z-50 flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-[0_6px_0_0_color-mix(in_oklch,var(--primary),black_18%)] transition-transform hover:scale-105 active:translate-y-0.5 md:left-64"
        aria-label={open ? 'Cerrar asistente' : 'Abrir asistente'}
      >
        {open ? <X className="size-6" /> : <MessageSquare className="size-6" />}
      </button>

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
    </>
  )
}
