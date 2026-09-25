import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Pencil, Plus, Tags, Trash2, X } from 'lucide-react'
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
import { Badge } from '@/components/ui/badge'
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
import { api } from '@/lib/api'
import { SectionCard } from '@/components/SectionCard'
import { fmtCopDecimals } from '@/lib/money'
import { monthLabel, useMonth } from '@/hooks/useMonth'
import type { Category, CategoryType } from '@/lib/types'

const COLORS = ['#EF4444', '#F97316', '#EAB308', '#10B981', '#14B8A6', '#3B82F6', '#8B5CF6', '#EC4899', '#F43F5E', '#6366F1']

const ICONS = [
  '📁', '🏠', '🍕', '🚌', '⚡', '🎮', '🏥', '📚', '🛍️', '📦',
  '💰', '💻', '📈', '💵', '🐷', '🪙', '🙏', '🎁', '🐾', '✈️', '📱', '🔒',
]

interface CategoryFormProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  category: Category | null
  defaultType: CategoryType
}

function CategoryForm({ open, onOpenChange, category, defaultType }: CategoryFormProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {open && (
          <CategoryFormBody
            category={category}
            defaultType={defaultType}
            onOpenChange={onOpenChange}
          />
        )}
      </DialogContent>
    </Dialog>
  )
}

function CategoryFormBody({
  category,
  defaultType,
  onOpenChange,
}: {
  category: Category | null
  defaultType: CategoryType
  onOpenChange: (open: boolean) => void
}) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(category?.name ?? '')
  const [type, setType] = useState<CategoryType>(category?.type ?? defaultType)
  const [color, setColor] = useState(category?.color || COLORS[0])
  const [icon, setIcon] = useState(category?.icon || ICONS[0])

  const mutation = useMutation({
    mutationFn: async () => {
      if (category) {
        await api.updateCategory(category.id, { name, color, icon })
      } else {
        await api.createCategory({ name, type, color, icon })
      }
    },
    onSuccess: () => {
      toast.success(category ? 'Category updated' : 'Category created')
      onOpenChange(false)
      void queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    mutation.mutate()
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{category ? 'Edit category' : 'New category'}</DialogTitle>
        <DialogDescription>
          {category
            ? 'Type cannot be changed once created.'
            : 'Organize your transactions into categories.'}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="cat-name">Name</Label>
          <Input id="cat-name" required value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        {!category && (
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select value={type} onValueChange={(v) => setType((v ?? 'expense') as CategoryType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="expense">Expense</SelectItem>
                <SelectItem value="income">Income</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}
        <div className="space-y-1.5">
          <Label>Color</Label>
          <div className="flex flex-wrap gap-2">
            {COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`size-7 rounded-full border ${
                  color === c ? 'border-foreground' : 'border-transparent'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Icon</Label>
          <div className="flex flex-wrap gap-1">
            {ICONS.map((i) => (
              <button
                key={i}
                type="button"
                onClick={() => setIcon(i)}
                className={`rounded-md border p-1.5 text-lg ${
                  icon === i ? 'border-foreground bg-accent' : 'border-transparent'
                }`}
              >
                {i}
              </button>
            ))}
          </div>
        </div>
        <Button type="submit" className="w-full" disabled={mutation.isPending}>
          {mutation.isPending ? 'Saving…' : 'Save'}
        </Button>
      </form>
    </>
  )
}

function CategoryRow({ category, total }: { category: Category; total: number }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [newSub, setNewSub] = useState('')
  const [subToDelete, setSubToDelete] = useState<number | null>(null)

  const subcategories = useQuery({
    queryKey: ['subcategories', category.id],
    queryFn: () => api.listSubcategories(category.id),
  })

  const addSub = useMutation({
    mutationFn: () => api.createSubcategory(category.id, { name: newSub, icon: '📁' }),
    onSuccess: () => {
      toast.success('Subcategory created')
      setNewSub('')
      void queryClient.invalidateQueries({ queryKey: ['subcategories', category.id] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const deleteSub = useMutation({
    mutationFn: (id: number) => api.deleteSubcategory(id),
    onSuccess: () => {
      toast.success('Subcategory deleted')
      void queryClient.invalidateQueries({ queryKey: ['subcategories', category.id] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  const deleteCat = useMutation({
    mutationFn: () => api.deleteCategory(category.id),
    onSuccess: () => {
      toast.success('Category deleted')
      void queryClient.invalidateQueries({ queryKey: ['categories'] })
    },
    onError: (error: Error) => toast.error(error.message),
  })

  return (
    <div className="rounded-2xl border border-border bg-card p-3 shadow-[0_4px_0_0_rgba(0,0,0,0.05)]">
      <div className="flex items-center gap-2.5">
        <div
          className="flex size-9 shrink-0 items-center justify-center rounded-lg text-base text-white shadow-[0_2px_0_0_rgba(0,0,0,0.25)]"
          style={{ backgroundColor: category.color || '#888' }}
        >
          {category.icon}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold">{category.name}</p>
          <p className="truncate text-xs font-bold text-muted-foreground">
            {total > 0 ? `This month: ${fmtCopDecimals(total)}` : 'No transactions'}
          </p>
        </div>
        <Button variant="ghost" size="icon-xs" onClick={() => setEditing(true)}>
          <Pencil className="size-3.5" />
        </Button>
        <Button variant="ghost" size="icon-xs" onClick={() => setDeleting(true)}>
          <Trash2 className="size-3.5 text-red-500" />
        </Button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {subcategories.data?.map((sub) => (
          <Badge key={sub.id} variant="secondary" className="gap-1 text-[11px]">
            {sub.icon} {sub.name}
            <button
              onClick={() => setSubToDelete(sub.id)}
              className="ml-0.5 text-muted-foreground hover:text-red-500"
              aria-label={`Delete ${sub.name}`}
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <form
          className="flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault()
            if (newSub.trim()) addSub.mutate()
          }}
        >
          <Input
            className="h-7 w-24 text-xs"
            placeholder="New sub…"
            value={newSub}
            onChange={(e) => setNewSub(e.target.value)}
          />
          <Button type="submit" variant="ghost" size="icon" className="size-7">
            <Plus />
          </Button>
        </form>
      </div>

      <CategoryForm open={editing} onOpenChange={setEditing} category={category} defaultType={category.type} />

      <AlertDialog open={deleting} onOpenChange={setDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete category?</AlertDialogTitle>
            <AlertDialogDescription>
              {category.name} will be deleted. Cannot delete if it has transactions or
              budgets.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteCat.mutate()}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={subToDelete !== null} onOpenChange={(open) => !open && setSubToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete subcategory?</AlertDialogTitle>
            <AlertDialogDescription>
              Transactions using it will be left without a subcategory.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => subToDelete && deleteSub.mutate(subToDelete)}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export function CategoriesSection() {
  const { month } = useMonth()
  const categories = useQuery({ queryKey: ['categories'], queryFn: () => api.listCategories() })
  const spendingExpense = useQuery({
    queryKey: ['categorySpending', month, 'expense'],
    queryFn: () => api.categorySpending(month.month, month.year, 'expense'),
  })
  const spendingIncome = useQuery({
    queryKey: ['categorySpending', month, 'income'],
    queryFn: () => api.categorySpending(month.month, month.year, 'income'),
  })
  const [formOpen, setFormOpen] = useState(false)
  const [formType, setFormType] = useState<CategoryType>('expense')

  const totals = new Map<string, number>([
    ...(spendingExpense.data ?? []).map((row) => [row.name, Number(row.total)] as const),
    ...(spendingIncome.data ?? []).map((row) => [row.name, Number(row.total)] as const),
  ])

  const sortByUsage = (a: Category, b: Category) => {
    const totalA = totals.get(a.name) ?? 0
    const totalB = totals.get(b.name) ?? 0
    if (totalA !== totalB) return totalB - totalA
    return a.name.localeCompare(b.name)
  }

  const income = (categories.data?.filter((c) => c.type === 'income') ?? []).sort(sortByUsage)
  const expense = (categories.data?.filter((c) => c.type === 'expense') ?? []).sort(sortByUsage)

  return (
    <>
      <SectionCard
        icon={Tags}
        title="Categories"
        subtitle={`Organize your ${monthLabel(month)} transactions with categories and subcategories`}
        action={
          <Button
            onClick={() => {
              setFormType('expense')
              setFormOpen(true)
            }}
          >
            <Plus /> New category
          </Button>
        }
      >
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-emerald-600">Income</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {income.map((cat) => (
                <CategoryRow key={cat.id} category={cat} total={totals.get(cat.name) ?? 0} />
              ))}
            </div>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                setFormType('income')
                setFormOpen(true)
              }}
            >
              <Plus /> Add income
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-red-600">Expenses</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {expense.map((cat) => (
                <CategoryRow key={cat.id} category={cat} total={totals.get(cat.name) ?? 0} />
              ))}
            </div>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                setFormType('expense')
                setFormOpen(true)
              }}
            >
              <Plus /> Add expense
            </Button>
          </CardContent>
        </Card>
      </div>
      </SectionCard>

      <CategoryForm
        open={formOpen}
        onOpenChange={setFormOpen}
        category={null}
        defaultType={formType}
      />
    </>
  )
}
