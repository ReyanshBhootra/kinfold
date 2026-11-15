import { useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Anchor, ArrowRight, Bot, FileText, Layers3, Users } from 'lucide-react'
import { initials } from './CaseMeta'
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
 // Handoff: who did what, from the audit trail itself.
 const WHAT: Record<string, string> = { document_added: 'records added', investigation_demo: 'investigations run', ai_extraction: 'AI reads', agent_run: 'agent runs', anchored: 'anchors', anchor_verified: 'anchor checks', case_loaded: 'case resets' }
 const people = new Map<string, Map<string, number>>()
 for (const e of s.audit) { const who = e.actor || 'Unattributed'; const what = WHAT[e.action]; if (!what) continue; const m = people.get(who) ?? new Map(); m.set(what, (m.get(what) || 0) + 1); people.set(who, m) }
 const named = [...people.keys()].filter(p => p !== 'Unattributed')
 const nameOf = (id: string) => s.people.find(p => p.id === id)?.name ?? id
 const anchors = s.anchors || [], lastAnchor = anchors[anchors.length - 1]
 let lastDay = ''
 return <section className="activity-list">
  <div className="handoff">
   <section className="handoff-card"><h3><Users size={16}/>Who worked on this case</h3>
    {people.size ? <ul className="handoff-people">{[...people.entries()].sort((a, b) => (a[0] === 'Unattributed' ? 1 : 0) - (b[0] === 'Unattributed' ? 1 : 0)).map(([who, m]) => <li key={who} className={who === 'Unattributed' ? 'anon' : ''}><span className="mini-avatar big">{who === 'Unattributed' ? '?' : initials(who)}</span><div><strong>{who === 'Unattributed' ? 'Unattributed' : who}</strong><small>{[...m.entries()].map(([w, n]) => `${n} ${w}`).join(' · ')}</small></div></li>)}</ul> : <p className="muted">No activity yet.</p>}
    {!named.length && <p className="handoff-hint">Set your name with the badge in the top-right corner, and your next steps are logged under it.</p>}
   </section>
   <section className="handoff-card"><h3><Layers3 size={16}/>Where the case stands</h3>
    <ul className="handoff-state">
     <li><span>Records</span><strong>{s.metrics.documents_processed} of {s.documents.length} reviewed</strong></li>
     {s.candidates.map(c => <li key={c.person_id}><span>{nameOf(c.person_id)}</span><strong className={c.status === 'excluded' ? 'warn' : 'ok'}>{c.status}</strong></li>)}
     <li><span>Open contradictions</span><strong className={s.metrics.conflicts ? 'warn' : ''}>{s.metrics.conflicts}</strong></li>
     <li><span>On-chain</span><strong className={lastAnchor?.matches_current ? 'chain' : ''}>{lastAnchor ? (lastAnchor.matches_current ? `Anchored (#${lastAnchor.number})` : `Changed since anchor #${lastAnchor.number}`) : 'Not anchored'}</strong></li>
    </ul>
   </section>
   <section className="handoff-card"><h3><ArrowRight size={16}/>Next steps for whoever picks it up</h3>
    {s.next_actions.length ? <ol className="handoff-next">{s.next_actions.slice(0, 3).map(a => <li key={a.id}><strong>{a.title}</strong><small>{a.reason}</small></li>)}</ol> : <p className="muted">Run the investigation to generate next steps.</p>}
   </section>
  </div>
  <div className="section-heading"><h2>Full activity trail</h2>{actions}</div>
  <div className="log-filters" role="tablist" aria-label="Filter the research trail">{CATS.map(c => <button key={c.id} role="tab" aria-selected={cat === c.id} className={`log-filter lc-${c.id} ${cat === c.id ? 'on' : ''}`} onClick={() => setCat(c.id)}><c.icon size={14}/>{c.label}<span>{counts[c.id]}</span></button>)}</div>
  <ol className="log-timeline">{shown.map((a, i) => { const d = day(a.timestamp); const head = d !== lastDay; lastDay = d; const c = catOf(a.action)
   return <li key={a.id} className={`log-entry lc-${c}`} style={{ '--i': Math.min(i, 12) } as CSSProperties}>
    {head && <div className="log-day">{d}</div>}
    <div className="log-body"><span className="log-dot" aria-hidden="true"/><div><h3><span className={`kind-chip kind-${a.action}`}>{label(a.action)}</span>{a.description}</h3><time dateTime={a.timestamp}>{new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · {a.actor ? <span className="by">by {a.actor}</span> : <span className="by anon">unattributed</span>}</time></div></div>
   </li> })}</ol>
  {!shown.length && <div className="empty">Nothing in this category yet.</div>}
 </section>
}
