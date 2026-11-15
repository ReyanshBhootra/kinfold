import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Anchor, Bot, FileText, Layers3 } from 'lucide-react'
import type { Snapshot } from './types'

type Cat = 'all' | 'ai' | 'records' | 'chain'
const CAT_OF: Record<string, Exclude<Cat, 'all'>> = {
 ai_extraction: 'ai', ai_extraction_failed: 'ai', provider_success: 'ai', provider_unavailable: 'ai', agent_run: 'ai',
 anchored: 'chain', anchor_verified: 'chain', anchor_verify_failed: 'chain',
}
const catOf = (action: string) => CAT_OF[action] ?? 'records'
const CATS: { id: Cat; label: string; icon: typeof FileText }[] = [
 { id: 'all', label: 'Everything', icon: Layers3 }, { id: 'records', label: 'Records & review', icon: FileText },
 { id: 'ai', label: 'AI & agent', icon: Bot }, { id: 'chain', label: 'On-chain', icon: Anchor },
]
const label = (a: string) => { const t = a.replaceAll('_', ' ').replace(/\bai\b/g, 'AI'); return t.charAt(0).toUpperCase() + t.slice(1) }
const day = (iso: string) => new Date(iso).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })

/** The audit trail, newest first, colour-coded by what kind of step it was. */
export default function ResearchLog({ s, actions }: { s: Snapshot; actions: ReactNode }) {
 const [cat, setCat] = useState<Cat>('all')
 const entries = [...s.audit].reverse()
 const counts = Object.fromEntries(CATS.map(c => [c.id, c.id === 'all' ? entries.length : entries.filter(e => catOf(e.action) === c.id).length]))
 const shown = entries.filter(e => cat === 'all' || catOf(e.action) === cat)
 let lastDay = ''
 return <section className="activity-list">
  <div className="section-heading"><h2>The research trail</h2>{actions}</div>
  <div className="log-filters" role="tablist" aria-label="Filter the research trail">{CATS.map(c => <button key={c.id} role="tab" aria-selected={cat === c.id} className={`log-filter lc-${c.id} ${cat === c.id ? 'on' : ''}`} onClick={() => setCat(c.id)}><c.icon size={14}/>{c.label}<span>{counts[c.id]}</span></button>)}</div>
  <ol className="log-timeline">{shown.map((a, i) => { const d = day(a.timestamp); const head = d !== lastDay; lastDay = d; const c = catOf(a.action)
   return <li key={a.id} className={`log-entry lc-${c}`} style={{ '--i': Math.min(i, 12) } as CSSProperties}>
    {head && <div className="log-day">{d}</div>}
    <div className="log-body"><span className="log-dot" aria-hidden="true"/><div><h3><span className={`kind-chip kind-${a.action}`}>{label(a.action)}</span>{a.description}</h3><time dateTime={a.timestamp}>{new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></div></div>
   </li> })}</ol>
  {!shown.length && <div className="empty">Nothing in this category yet.</div>}
 </section>
}
