import { useMemo, useState } from 'react'
import { Minus, Plus, Maximize2, GitBranch, AlertTriangle } from 'lucide-react'
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
 const connected = new Set([selected, ...s.relationships.filter(r => r.source === selected || r.target === selected).flatMap(r => [r.source, r.target])])
 return <section className="graph-section">
  <div className="section-heading"><div><h2>Follow the family thread<span className="count">{s.people.length}</span></h2></div><button className={`quiet small ${focus ? 'active' : ''}`} disabled={!selected} onClick={() => setFocus(!focus)}><GitBranch size={14}/>{focus ? 'All people' : 'Focus branch'}</button></div>
  <div className="graph-viewport"><div className="graph-canvas" style={{width: layout.width * zoom, height: layout.height * zoom}}><div className="graph-scale" style={{width: layout.width, height: layout.height, transform: `scale(${zoom})`}}>
   <svg width={layout.width} height={layout.height} className="graph-lines" aria-hidden="true">
    {s.relationships.map(r => { const a = layout.positions.get(r.source), b = layout.positions.get(r.target); if (!a || !b) return null; const dim = focus && selected && ![r.source, r.target].includes(selected); const sameRow = a.y === b.y; const x1 = a.x + 68, y1 = a.y + (sameRow ? 48 : 88), x2 = b.x + 68, y2 = b.y + (sameRow ? 48 : 0); return <g key={r.id} opacity={dim ? .12 : 1}><path className={r.status === 'conflicting' || r.status === 'disputed' ? 'conflict-line' : /dna|match|spouse|sibling/i.test(r.type) ? 'inferred-line' : ''} d={sameRow ? `M${x1},${y1} Q${(x1+x2)/2},${y1-65} ${x2},${y2}` : `M${x1},${y1} V${(y1+y2)/2} H${x2} V${y2}`}/><title>{r.type} · {r.status}</title></g> })}
   </svg>
   {s.people.map(p => { const pos = layout.positions.get(p.id)!; const candidate = s.candidates.find(c => c.person_id === p.id); const conflicts = s.findings.some(f => f.kind === 'conflict' && f.person_ids.includes(p.id)); return <button key={p.id} className={`person-node ${selected === p.id ? 'selected' : ''} ${candidate?.status === 'excluded' ? 'excluded' : ''} ${focus && selected && !connected.has(p.id) ? 'dimmed' : ''}`} style={{left: pos.x, top: pos.y}} onClick={() => onSelect(p.id)} aria-pressed={selected === p.id}>
    <span className="person-node-top"><span className={`avatar ${p.candidate ? 'candidate-avatar' : ''}`}>{p.name.split(' ').map(n => n[0]).slice(0,2).join('')}</span><span className="node-role">{p.candidate ? 'CANDIDATE LEAD' : 'FAMILY RECORD'}{conflicts && <AlertTriangle size={12} aria-label="Conflicting evidence"/>}</span></span>
    <strong>{p.name}</strong><span className="node-dates">{p.birth_year ? `b. ${p.birth_year}` : 'Birth year unknown'}{p.death_year ? ` — ${p.death_year}` : ''}</span>
   </button>})}
  </div></div>{!s.people.length && <div className="empty">People will appear here as evidence is added.</div>}</div>
  <div className="graph-footer"><div className="legend"><span><i/>Source-backed link</span><span><i className="dashed"/>Other relationship</span></div><div className="zoom-controls"><button aria-label="Zoom out" disabled={zoom <= .6} onClick={() => setZoom(z => Math.max(.6, z-.15))}><Minus size={14}/></button><span>{Math.round(zoom*100)}%</span><button aria-label="Zoom in" disabled={zoom >= 1.6} onClick={() => setZoom(z => Math.min(1.6,z+.15))}><Plus size={14}/></button><button aria-label="Reset graph zoom" onClick={() => setZoom(1)}><Maximize2 size={14}/></button></div></div>
 </section>
}

