import { useEffect, useRef, useState } from 'react'
import { Check, Clock, Users } from 'lucide-react'
import { RESEARCHER_KEY, researcherName } from './api'
import type { Snapshot } from './types'

export const initials = (name: string) => name.split(/\s+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
export const contributors = (s: Snapshot) => [...new Set(s.audit.map(a => a.actor).filter((a): a is string => !!a))]
const ago = (iso: string) => { const m = Math.round((Date.now() - new Date(iso).getTime()) / 60000); return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : new Date(iso).toLocaleDateString() }

/** Case header line: identifier, status, who has worked on it, last activity. */
export function CaseMeta({ s }: { s: Snapshot }) {
 const people = contributors(s), last = s.audit[s.audit.length - 1]
 return <div className="case-meta">
  <span className={`status-pill st-${s.case.status}`}>{s.case.status.replaceAll('_', ' ')}</span>
  <span className="case-meta-item"><Users size={13}/>{people.length ? <span className="avatar-stack">{people.slice(0, 4).map(p => <span key={p} className="mini-avatar" title={p}>{initials(p)}</span>)}</span> : null}{people.length ? `${people.length} ${people.length === 1 ? 'researcher' : 'researchers'}` : 'No named researchers yet'}</span>
  {last && <span className="case-meta-item"><Clock size={13}/>Updated {ago(last.timestamp)}</span>}
 </div>
}

/** Top-bar badge: set the name your actions are logged under. A display name, not a sign-in. */
export function ResearcherBadge() {
 const [name, setName] = useState(researcherName()), [open, setOpen] = useState(false), [draft, setDraft] = useState(name), ref = useRef<HTMLDivElement>(null)
 useEffect(() => { if (!open) return; const away = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }; document.addEventListener('mousedown', away); return () => document.removeEventListener('mousedown', away) }, [open])
 function save() { const n = draft.trim().slice(0, 60); try { n ? localStorage.setItem(RESEARCHER_KEY, n) : localStorage.removeItem(RESEARCHER_KEY) } catch { /* private mode */ } setName(n); setOpen(false) }
 return <div className="researcher" ref={ref}>
  <button className={`researcher-avatar ${name ? 'named' : ''}`} aria-haspopup="dialog" aria-expanded={open} title={name ? `Working as ${name}` : 'Set your name for the case activity log'} onClick={() => { setDraft(name); setOpen(o => !o) }}>{name ? initials(name) : '?'}</button>
  {open && <form className="researcher-pop" onSubmit={e => { e.preventDefault(); save() }}>
   <label htmlFor="researcher-name"><strong>Your name</strong><small>Every step you take is logged under this name, so the next person knows who did what. It's a display name, not a sign-in.</small></label>
   <input id="researcher-name" autoFocus maxLength={60} placeholder="e.g. Det. Shippy" value={draft} onChange={e => setDraft(e.target.value)}/>
   <button type="submit" className="primary small"><Check size={14}/>Save</button>
  </form>}
 </div>
}
