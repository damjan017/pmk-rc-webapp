import { useState, useCallback, useRef } from 'react'

let _show = null

export function useToast() {
  const [toasts, setToasts] = useState([])
  const id = useRef(0)

  const show = useCallback((message, type = 'info') => {
    const key = ++id.current
    setToasts(p => [...p, { key, message, type }])
    setTimeout(() => setToasts(p => p.filter(t => t.key !== key)), 3500)
  }, [])

  _show = show
  return { toasts, show }
}

export function showToast(message, type = 'info') {
  if (_show) _show(message, type)
}

export function Toaster({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map(t => (
        <div
          key={t.key}
          className={`animate-slide-up px-4 py-3 rounded-xl text-sm font-semibold shadow-xl border max-w-xs
            ${t.type === 'success' ? 'bg-green-900/90 border-green-700 text-green-100' :
              t.type === 'error'   ? 'bg-red-900/90 border-red-700 text-red-100' :
              'bg-surface border-surface-3 text-zinc-100'}`}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}
