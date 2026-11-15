import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ComponentType } from 'react'
import { ArrowLeft, ArrowUpRight, Briefcase, Calendar, Dna, FileText, Folder, FolderPlus, Landmark, ListChecks, MapPin, Newspaper, ScrollText, Search, Trash2, Upload, UserRound, X } from 'lucide-react'
import type { EvidenceDocument, Snapshot } from './types'

type GroupBy = 'type' | 'year' | 'place' | 'progress' | 'mine'
type Tone = 'rec' | 'dna' | 'ai' | 'chain' | 'warn' | 'teal' | 'sand' | 'slate'
type FolderView = { key: string; name: string; tone: Tone; icon: ComponentType<{ size?: number }>; docs: EvidenceDocument[]; note?: string; personal?: boolean }
type Personal = { id: string; name: string; docIds: string[] }

// Record kinds grouped into families a researcher recognises. Colour follows the app-wide meaning.
const FAMILIES: Record<string, { name: string; tone: Tone; icon: ComponentType<{ size?: number }> }> = {
 simulated_dna: { name: 'DNA evidence', tone: 'dna', icon: Dna },
 birth_register: { name: 'Vital records', tone: 'rec', icon: ScrollText }, marriage: { name: 'Vital records', tone: 'rec', icon: ScrollText }, family_register: { name: 'Vital records', tone: 'rec', icon: ScrollText },
 obituary: { name: 'Obituaries & news', tone: 'sand', icon: Newspaper },
 census: { name: 'Census & directories', tone: 'teal', icon: Landmark }, directory: { name: 'Census & directories', tone: 'teal', icon: Landmark }, address_index: { name: 'Census & directories', tone: 'teal', icon: Landmark },
 case_intake: { name: 'Case file', tone: 'slate', icon: Briefcase },
 uploaded_text: { name: 'Uploaded records', tone: 'ai', icon: Upload },
}
const STATES = ['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming']
const ABBR: Record<string, string> = { 'N.J.': 'New Jersey', 'N.Y.': 'New York', 'Pa.': 'Pennsylvania' }

const familyOf = (d: EvidenceDocument) => FAMILIES[d.kind] ?? { name: 'Other records', tone: 'slate' as Tone, icon: FileText }
/** The year a record is about: from its title, else its first lines. Undated if none is stated. */
export function recordYear(d: EvidenceDocument): number | null {
 const m = `${d.name}\n${d.text.split('\n').slice(0, 3).join(' ')}`.match(/\b(18[5-9]\d|19\d\d|20[0-2]\d)\b/)
 return m ? Number(m[1]) : null
}
/** The first U.S. state a record names, if any. */
export function recordPlace(d: EvidenceDocument): string | null {
 let best: { at: number; name: string } | null = null
 for (const st of STATES) { const at = d.text.indexOf(st); if (at >= 0 && (!best || at < best.at)) best = { at, name: st } }
 for (const [ab, st] of Object.entries(ABBR)) { const at = d.text.indexOf(ab); if (at >= 0 && (!best || at < best.at)) best = { at, name: st } }
 return best?.name ?? null
}

const storeKey = (caseId: string) => `kinfold-folders-${caseId}`
function loadPersonal(caseId: string): Personal[] { try { return JSON.parse(localStorage.getItem(storeKey(caseId)) || '[]') } catch { return [] } }
function savePersonal(caseId: string, folders: Personal[]) { try { localStorage.setItem(storeKey(caseId), JSON.stringify(folders)) } catch { /* private mode: folders last for this visit */ } }

const GROUPS: { id: GroupBy; label: string; icon: ComponentType<{ size?: number }> }[] = [
 { id: 'type', label: 'Type', icon: FileText }, { id: 'year', label: 'Year', icon: Calendar }, { id: 'place', label: 'Place', icon: MapPin },
 { id: 'progress', label: 'Progress', icon: ListChecks }, { id: 'mine', label: 'My folders', icon: UserRound },
]

export default function EvidenceLibrary({ s, openSource }: { s: Snapshot; openSource: (id: string) => void }) {
 const [groupBy, setGroupBy] = useState<GroupBy>('type'), [open, setOpen] = useState<string | null>(null), [query, setQuery] = useState('')
 const [personal, setPersonal] = useState<Personal[]>(() => loadPersonal(s.case.id)), [naming, setNaming] = useState(''), [creating, setCreating] = useState(false)
 useEffect(() => { savePersonal(s.case.id, personal) }, [personal, s.case.id])
 useEffect(() => { setOpen(null) }, [groupBy])

 // Which records the current analysis actually cites, so "progress" reflects real use, not a label.
 const cited = useMemo(() => new Set([...s.relationships.flatMap(r => r.citations), ...s.findings.flatMap(f => f.citations), ...s.candidates.flatMap(c => c.citations)].map(c => c.document_id)), [s])
 const progressOf = (d: EvidenceDocument) => !d.processed ? 'Awaiting review' : cited.has(d.id) ? 'Cited in the analysis' : 'Reviewed, nothing cited'

 const folders: FolderView[] = useMemo(() => {
  const bucket = (keyOf: (d: EvidenceDocument) => string, meta: (k: string) => Omit<FolderView, 'key' | 'docs'>, order?: (a: string, b: string) => number) => {
   const map = new Map<string, EvidenceDocument[]>()
   s.documents.forEach(d => { const k = keyOf(d); map.set(k, [...(map.get(k) || []), d]) })
   return [...map.entries()].sort(([a], [b]) => order ? order(a, b) : a.localeCompare(b)).map(([key, docs]) => ({ key, docs, ...meta(key) }))
  }
  if (groupBy === 'type') return bucket(d => familyOf(d).name, k => { const f = Object.values(FAMILIES).find(f => f.name === k) ?? { name: k, tone: 'slate' as Tone, icon: FileText }; return { name: f.name, tone: f.tone, icon: f.icon } })
  if (groupBy === 'year') return bucket(d => { const y = recordYear(d); return y ? `${Math.floor(y / 10) * 10}s` : 'Undated' }, k => ({ name: k, tone: k === 'Undated' ? 'slate' : 'dna', icon: Calendar }), (a, b) => a === 'Undated' ? 1 : b === 'Undated' ? -1 : a.localeCompare(b))
  if (groupBy === 'place') return bucket(d => recordPlace(d) ?? 'No place stated', k => ({ name: k, tone: k === 'No place stated' ? 'slate' : 'teal', icon: MapPin }), (a, b) => a.startsWith('No place') ? 1 : b.startsWith('No place') ? -1 : a.localeCompare(b))
  if (groupBy === 'progress') { const order = ['Awaiting review', 'Cited in the analysis', 'Reviewed, nothing cited']; return bucket(progressOf, k => ({ name: k, tone: k === 'Awaiting review' ? 'warn' : k.startsWith('Cited') ? 'rec' : 'slate', icon: ListChecks, note: k === 'Awaiting review' ? 'Run the investigation to review these' : undefined }), (a, b) => order.indexOf(a) - order.indexOf(b)) }
  return personal.map(p => ({ key: p.id, name: p.name, tone: 'chain', icon: Folder, docs: s.documents.filter(d => p.docIds.includes(d.id)), personal: true }))
 }, [groupBy, s.documents, personal, cited])

 const current = folders.find(f => f.key === open) ?? null
 const results = query.trim() ? s.documents.filter(d => `${d.name} ${d.text}`.toLowerCase().includes(query.trim().toLowerCase())) : null

 function createFolder() { const name = naming.trim(); if (!name) return; setPersonal(p => [...p, { id: `f-${Date.now().toString(36)}`, name: name.slice(0, 40), docIds: [] }]); setNaming(''); setCreating(false) }
 const toggleIn = (folderId: string, docId: string) => setPersonal(p => p.map(f => f.id !== folderId ? f : { ...f, docIds: f.docIds.includes(docId) ? f.docIds.filter(i => i !== docId) : [...f.docIds, docId] }))

 const fileRow = (d: EvidenceDocument, i: number, inFolder?: FolderView) => { const fam = familyOf(d); const y = recordYear(d), pl = recordPlace(d), prog = progressOf(d)
  return <li key={d.id} className={`file-row tone-${fam.tone}`} style={{ '--i': i } as CSSProperties}>
   <button className="file-open" onClick={() => openSource(d.id)}>
    <span className="file-icon"><fam.icon size={18}/></span>
    <span className="file-main"><strong>{d.name}</strong><small>{fam.name}{y ? ` · ${y}` : ''}{pl ? ` · ${pl}` : ''} · {d.synthetic ? 'Synthetic' : 'User supplied'}</small></span>
    <span className={`prog prog-${prog === 'Awaiting review' ? 'pending' : prog.startsWith('Cited') ? 'cited' : 'quiet'}`}>{prog}</span>
    <ArrowUpRight size={15} className="file-go"/>
   </button>
   {inFolder?.personal ? <button className="icon-button file-remove" aria-label={`Remove ${d.name} from ${inFolder.name}`} onClick={() => toggleIn(inFolder.key, d.id)}><X size={14}/></button>
    : personal.length > 0 && <select className="file-add" aria-label={`Add ${d.name} to a folder`} value="" onChange={e => { if (e.target.value) toggleIn(e.target.value, d.id) }}><option value="">Add to folder…</option>{personal.map(p => <option key={p.id} value={p.id}>{p.docIds.includes(d.id) ? '✓ ' : ''}{p.name}</option>)}</select>}
  </li> }

 return <section className="library">
  <div className="library-bar">
   <label className="search-box"><Search size={17}/><input aria-label="Search evidence" placeholder="Search every record…" value={query} onChange={e => setQuery(e.target.value)}/></label>
   <div className="group-switch" role="tablist" aria-label="Organise folders by">{GROUPS.map(g => <button key={g.id} role="tab" aria-selected={groupBy === g.id} className={groupBy === g.id ? 'on' : ''} onClick={() => { setGroupBy(g.id); setQuery('') }}><g.icon size={14}/>{g.label}</button>)}</div>
  </div>

  {results ? <div className="folder-open-view"><div className="folder-head"><h2>{results.length} record{results.length === 1 ? '' : 's'} match “{query.trim()}”</h2><button className="text-button" onClick={() => setQuery('')}>Clear search</button></div>
   {results.length ? <ul className="file-list">{results.map((d, i) => fileRow(d, i))}</ul> : <div className="empty">No records match this search.</div>}</div>

  : current ? <div className={`folder-open-view tone-${current.tone}`}>
   <div className="folder-head"><button className="back-button" onClick={() => setOpen(null)}><ArrowLeft size={15}/>All folders</button>
    <h2><span className="folder-dot"><current.icon size={16}/></span>{current.name}<span className="count">{current.docs.length}</span></h2>
    {current.personal && <button className="text-button danger" onClick={() => { setPersonal(p => p.filter(f => f.id !== current.key)); setOpen(null) }}><Trash2 size={14}/>Delete folder</button>}</div>
   {current.docs.length ? <ul className="file-list">{current.docs.map((d, i) => fileRow(d, i, current))}</ul>
    : <div className="empty">{current.personal ? 'This folder is empty. Open another folder and use “Add to folder…” on any record.' : 'No records here.'}</div>}
  </div>

  : <div className="folder-grid">
   {folders.map((f, i) => <button key={f.key} className={`folder-card tone-${f.tone}`} style={{ '--i': i } as CSSProperties} onClick={() => setOpen(f.key)}>
    <span className="folder-tab" aria-hidden="true"/>
    <span className="folder-top"><span className="folder-dot"><f.icon size={18}/></span><span className="folder-count">{f.docs.length}</span></span>
    <strong>{f.name}</strong>
    <small>{f.note ?? ((f.docs.slice(0, 2).map(d => d.name).join(' · ') + (f.docs.length > 2 ? ` · +${f.docs.length - 2} more` : '')) || 'Empty folder')}</small>
   </button>)}
   {groupBy === 'mine' && (creating
    ? <form className="folder-card folder-new editing" onSubmit={e => { e.preventDefault(); createFolder() }}><FolderPlus size={20}/><input autoFocus aria-label="Folder name" placeholder="e.g. Shippy's review" value={naming} maxLength={40} onChange={e => setNaming(e.target.value)} onKeyDown={e => { if (e.key === 'Escape') { setCreating(false); setNaming('') } }}/><span className="folder-new-actions"><button type="submit" className="primary small" disabled={!naming.trim()}>Create</button><button type="button" className="text-button" onClick={() => { setCreating(false); setNaming('') }}>Cancel</button></span></form>
    : <button className="folder-card folder-new" onClick={() => setCreating(true)}><FolderPlus size={22}/><strong>New folder</strong><small>Collect the records you're reviewing. Saved in this browser.</small></button>)}
  </div>}
 </section>
}
