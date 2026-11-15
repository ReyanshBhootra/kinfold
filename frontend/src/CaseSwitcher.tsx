import { useEffect, useRef, useState } from 'react'
import { Briefcase, Check, ChevronDown, RotateCcw } from 'lucide-react'

export type CaseSummary = { id: string; title: string; status: string; synthetic: boolean }

/** One obvious control for "which case am I working on?" — lists every case the backend has. */
export default function CaseSwitcher({ cases, currentId, onSwitch, onFresh, compact = false }: { cases: CaseSummary[]; currentId?: string; onSwitch: (id: string) => void; onFresh: () => void; compact?: boolean }) {
 const [open, setOpen] = useState(false), ref = useRef<HTMLDivElement>(null)
 const current = cases.find(c => c.id === currentId)
 useEffect(() => {
  if (!open) return
  const away = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
  const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
  document.addEventListener('mousedown', away); document.addEventListener('keydown', esc)
  return () => { document.removeEventListener('mousedown', away); document.removeEventListener('keydown', esc) }
 }, [open])
 return <div className={`case-switcher ${compact ? 'compact' : ''}`} ref={ref}>
  <button className="case-switch-button" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(o => !o)}>
   <span className="case-switch-icon"><Briefcase size={16}/></span>
   <span className="case-switch-text"><small>Case</small><strong>{current?.title || 'Choose a case'}</strong></span>
   <ChevronDown size={16} className="case-switch-chev"/>
  </button>
  {open && <div className="case-menu" role="menu">
   <p className="case-menu-label">Your cases</p>
   {cases.map(c => <button key={c.id} role="menuitemradio" aria-checked={c.id === currentId} className={c.id === currentId ? 'on' : ''} onClick={() => { setOpen(false); if (c.id !== currentId) onSwitch(c.id) }}>
    <span className="case-menu-check">{c.id === currentId && <Check size={14}/>}</span>
    <span><strong>{c.title}</strong><small>{c.synthetic ? 'Synthetic demo' : 'Case'} · {c.status.replaceAll('_', ' ')}</small></span>
   </button>)}
   <hr/>
   <button role="menuitem" className="case-menu-fresh" onClick={() => { setOpen(false); onFresh() }}><RotateCcw size={14}/><span><strong>Start a fresh copy</strong><small>Resets the synthetic demo case and its uploads</small></span></button>
  </div>}
 </div>
}
