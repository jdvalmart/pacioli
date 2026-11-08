import { useMutation } from '@tanstack/react-query'
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
import { api } from '@/lib/api'
import { fmtCopDecimals } from '@/lib/money'
import { useInvalidate } from '@/lib/queries'
import type { Transaction } from '@/lib/types'

/** Confirms and deletes a movement (all its installments for a card purchase). */
export function DeleteTransactionDialog({
  transaction,
  onClose,
}: {
  transaction: Transaction | null
  onClose: () => void
}) {
  const invalidate = useInvalidate()
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteTransaction(id),
    onSuccess: () => {
      toast.success('Movimiento eliminado')
      onClose()
      void invalidate('movement')
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <AlertDialog open={!!transaction} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>¿Eliminar movimiento?</AlertDialogTitle>
          <AlertDialogDescription>
            Se eliminará &quot;{transaction?.description || 'este movimiento'}&quot; por{' '}
            {transaction ? fmtCopDecimals(transaction.amount) : ''}
            {transaction && transaction.installments > 1
              ? `, con sus ${transaction.installments} cuotas en todos los meses`
              : ''}
            . Esta acción no se puede deshacer.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            onClick={() => transaction && deleteMutation.mutate(transaction.id)}
            className="bg-red-600 hover:bg-red-700"
          >
            Eliminar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
