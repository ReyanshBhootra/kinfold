import { useEffect, useMemo, useState } from 'react'
import { Minus, Plus, Maximize2, GitBranch, AlertTriangle, X } from 'lucide-react'
import type { Snapshot } from './types'

export default function Graph({ snapshot: s, selected, onSelect }: {snapshot: Snapshot; selected: string | null; onSelect: (id: string) => void}) {
 const [zoom, setZoom] = useState(1)
 const [focus, setFocus] = useState(false)
 const layout = useMemo(() => {
  const levels = new Map(s.people.map(p => [p.id, 0]))
  const parents = s.relationships.filter(r => /parent|father|mother/i.test(r.type))
  const spouses = s.relationships.filter(r => /spouse|married|sibling/i.test(r.type)) // same generation row
  // Bound iterations so contradictory/cyclic source assertions cannot freeze the graph.
  for (let i = 0; i < Math.min(s.people.length * 2, 12); i++) {
   let changed = false
   for (const r of parents) { const next = Math.min(4, (levels.get(r.source) || 0) + 1); if (next > (levels.get(r.target) || 0)) { levels.set(r.target, next); changed = true } }
   for (const r of spouses) { const level = Math.max(levels.get(r.source) || 0, levels.get(r.target) || 0); for (const id of [r.source, r.target]) { if ((levels.get(id) || 0) < level) { levels.set(id, level); changed = true } } }
   if (!changed) break
  }
  const rows = new Map<number, string[]>()
  for (const p of s.people) { const level = levels.get(p.id) || 0; rows.set(level, [...rows.get(level) || [], p.id]) }
  // Break wide generations into readable rows while retaining source connectors.
  const maxCols = 5; const positions = new Map<string, {x: number; y: number}>(); let row = 0
  const width = Math.max(720, Math.min(maxCols, Math.max(1, ...[...rows.values()].map(r => r.length))) * 152 + 60)
  for (const ids of [...rows.entries()].sort((a,b) => a[0]-b[0]).map(e => e[1])) {
   for (let offset = 0; offset < ids.length; offset += maxCols) {
    const group = ids.slice(offset, offset + maxCols)
    group.forEach((id, i) => positions.set(id, {x: (width - group.length * 152) / 2 + i * 152 + 8, y: 46 + row * 155})); row++
   }
  }
  return {positions, width, height: Math.max(390, row * 155 + 35)}
 }, [s.people, s.relationships])
 // The selected person's branch: every recorded ancestor and descendant, plus direct spouses/siblings.
 const connected = useMemo(() => {
  const out = new Set<string | null>([selected]); if (!selected) return out
  const parentLinks = s.relationships.filter(r => /parent|father|mother/i.test(r.type))
  const walk = (start: string, next: (id: string) => string[]) => { const stack = [start]; while (stack.length) { const id = stack.pop()!; for (const n of next(id)) if (!out.has(n)) { out.add(n); stack.push(n) } } }
  walk(selected, id => parentLinks.filter(r => r.target === id).map(r => r.source)) // ancestors
  walk(selected, id => parentLinks.filter(r => r.source === id).map(r => r.target)) // descendants
  s.relationships.filter(r => !/parent|father|mother/i.test(r.type) && (r.source === selected || r.target === selected)).forEach(r => { out.add(r.source); out.add(r.target) })
  return out
 }, [selected, s.relationships])
 useEffect(() => { if (selected) setFocus(true) }, [selected])
 const sel = selected ? s.people.find(p => p.id === selected) : null
 const selPos = sel ? layout.positions.get(sel.id) : null
 const selLinks = sel ? s.relationships.filter(r => r.source === sel.id || r.target === sel.id) : []
 const nameOf = (id: string) => s.people.find(p => p.id === id)?.name ?? id
 const relText = (r: typeof selLinks[number]) => { const other = nameOf(r.source === sel!.id ? r.target : r.source); if (/parent/i.test(r.type)) return r.source === sel!.id ? `Parent of ${other}` : `Child of ${other}`; return `${r.type.charAt(0).toUpperCase() + r.type.slice(1)} of ${other}` }
 return <section className="graph-section">
  <div className="section-heading"><div><h2>Family tree<span className="count">{s.people.length}</span></h2></div><button className={`quiet small ${focus ? 'active' : ''}`} disabled={!selected} onClick={() => setFocus(!focus)}><GitBranch size={14}/>{focus ? 'All people' : 'Focus branch'}</button></div>
  <div className="graph-viewport"><div className="graph-canvas" style={{width: layout.width * zoom, height: layout.height * zoom}}><div className="graph-scale" style={{width: layout.width, height: layout.height, transform: `scale(${zoom})`}}>
   <svg width={layout.width} height={layout.height} className="graph-lines" aria-hidden="true">
    {s.relationships.map(r => { const a = layout.positions.get(r.source), b = layout.positions.get(r.target); if (!a || !b) return null; const inBranch = !!selected && connected.has(r.source) && connected.has(r.target); const dim = focus && selected && !inBranch; const sameRow = a.y === b.y; const x1 = a.x + 68, y1 = a.y + (sameRow ? 48 : 88), x2 = b.x + 68, y2 = b.y + (sameRow ? 48 : 0); return <g key={r.id} opacity={dim ? .12 : 1} className={inBranch && focus ? 'branch' : ''}><path className={r.status === 'conflicting' || r.status === 'disputed' ? 'conflict-line' : /dna|match|spouse|sibling/i.test(r.type) ? 'inferred-line' : ''} d={sameRow ? `M${x1},${y1} Q${(x1+x2)/2},${y1-65} ${x2},${y2}` : `M${x1},${y1} V${(y1+y2)/2} H${x2} V${y2}`}/><title>{r.type} · {r.status}</title></g> })}
   </svg>
   {s.people.map(p => { const pos = layout.positions.get(p.id)!; const candidate = s.candidates.find(c => c.person_id === p.id); const conflicts = s.findings.some(f => f.kind === 'conflict' && f.person_ids.includes(p.id)); return <button key={p.id} className={`person-node ${selected === p.id ? 'selected' : ''} ${candidate?.status === 'excluded' ? 'excluded' : ''} ${candidate && candidate.status !== 'excluded' ? 'open-lead' : ''} ${candidate?.proposed_by_engine ? 'found' : ''} ${focus && selected && !connected.has(p.id) ? 'dimmed' : ''} ${selected && selected !== p.id && connected.has(p.id) ? 'linked' : ''}`} style={{left: pos.x, top: pos.y}} onClick={() => onSelect(p.id)} aria-pressed={selected === p.id}>
    <span className="person-node-top"><span className={`avatar ${p.candidate ? 'candidate-avatar' : ''}`}>{p.name.split(' ').map(n => n[0]).slice(0,2).join('')}</span><span className="node-role">{candidate?.proposed_by_engine ? 'FOUND BY KINFOLD' : p.candidate ? (candidate?.status === 'excluded' ? 'EXCLUDED LEAD' : 'CANDIDATE LEAD') : 'FAMILY RECORD'}{conflicts && <AlertTriangle size={12} aria-label="Conflicting evidence"/>}</span></span>
    <strong>{p.name}</strong><span className="node-dates">{p.birth_year ? `b. ${p.birth_year}` : 'Birth year unknown'}{p.death_year ? ` — ${p.death_year}` : ''}</span>
   </button>})}
   {sel && selPos && <div className="person-pop" role="dialog" aria-label={`${sel.name} details`} style={{ left: selPos.x + 152 + 250 > layout.width ? selPos.x - 262 : selPos.x + 146, top: Math.max(8, selPos.y - 6) }}>
    <div className="person-pop-head"><strong>{sel.name}</strong><button className="icon-button" aria-label="Close details" onClick={() => onSelect('')}><X size={14}/></button></div>
    <p>{sel.birth_year ? `Born ${sel.birth_year}` : 'Birth year unknown'}{sel.death_year ? ` · died ${sel.death_year}` : ''}{sel.locations.length ? ` · ${sel.locations.join(', ')}` : ''}</p>
    {selLinks.length ? <ul>{selLinks.map(r => <li key={r.id}>{relText(r)}<small>{r.citations.length} source{r.citations.length === 1 ? '' : 's'}</small></li>)}</ul> : <p className="muted">No recorded relationships yet.</p>}
    <small className="person-pop-foot">Branch highlighted · {connected.size - 1} related {connected.size - 1 === 1 ? 'person' : 'people'}</small>
   </div>}
  </div></div>{!s.people.length && <div className="empty">People will appear here as evidence is added.</div>}</div>
  <div className="graph-footer"><div className="legend"><span><i/>Source-backed link</span><span><i className="dashed"/>Other relationship</span></div><div className="zoom-controls"><button aria-label="Zoom out" disabled={zoom <= .6} onClick={() => setZoom(z => Math.max(.6, z-.15))}><Minus size={14}/></button><span>{Math.round(zoom*100)}%</span><button aria-label="Zoom in" disabled={zoom >= 1.6} onClick={() => setZoom(z => Math.min(1.6,z+.15))}><Plus size={14}/></button><button aria-label="Reset graph zoom" onClick={() => setZoom(1)}><Maximize2 size={14}/></button></div></div>
 </section>
}

