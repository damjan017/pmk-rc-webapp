export default function RennStatus({ status, size = 'sm' }) {
  const cfg = {
    offen:         { label: 'Anmeldung offen', cls: 'badge-green', dot: 'bg-green-400' },
    laufend:       { label: 'Renndurchführung', cls: 'badge-gold', dot: 'bg-gold animate-pulse' },
    abgeschlossen: { label: 'Abgeschlossen', cls: 'badge-gray', dot: 'bg-zinc-500' },
  }[status] || { label: status, cls: 'badge-gray', dot: 'bg-zinc-500' }

  return (
    <span className={cfg.cls}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  )
}
