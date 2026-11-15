import { ArrowRight, Bot, Check, ChevronDown, Dot, Sparkles, X } from 'lucide-react'
import DnaBar from './DnaBar'
import type { Candidate, Citation, EvidenceDocument, Person } from './types'

type Props = { c: Candidate; person?: Person; nameOf: (id?: string) => string | undefined; docs: EvidenceDocument[]; busy: string; onAgent: () => void; onGraph: () => void; onCite: (c: Citation) => void }

/** What a reason is, read from the engine's own wording (+n points, an exclusion, or a note). */
const kindOf = (r: string): 'ok' | 'x' | 'note' => /^Excluded|falls? outside|postdates/i.test(r) ? 'x' : /\(\+\d+\)/.test(r) ? 'ok' : 'note'
const MARK = { ok: Check, x: X, note: Dot }

/** Sources grouped by record: "Clara Mercer · birth register — L2, L3", each line a link to the cited span. */
function Sources({ items, docs, onCite }: { items: Citation[]; docs: EvidenceDocument[]; onCite: (c: Citation) => void }) {
 const groups = new Map<string, Citation[]>()
 items.forEach(c => groups.set(c.document_id, [...(groups.get(c.document_id) || []), c]))
 return <details className="lead-sources"><summary><ChevronDown size={15}/>Sources <span>{groups.size} record{groups.size === 1 ? '' : 's'} · {items.length} cited line{items.length === 1 ? '' : 's'}</span></summary>
  <ul>{[...groups.entries()].map(([id, cs]) => <li key={id}><strong>{docs.find(d => d.id === id)?.name || id}</strong>{cs.map((c, i) => <button key={i} className="line-link" onClick={() => onCite(c)} title={c.quote}>L{c.start_line}{c.end_line !== c.start_line ? `–${c.end_line}` : ''}</button>)}</li>)}</ul>
 </details>
}

export default function LeadCard({ c, person, nameOf, docs, busy, onAgent, onGraph, onCite }: Props) {
 const excluded = c.status === 'excluded'
 const dna = c.dna_checks?.find(d => d.status !== 'unchecked')
 // The DNA bar already states the DNA result, so its sentence isn't repeated in the list.
 const reasons = c.reasons.filter(r => !(dna && /^(Excluded by DNA|DNA fits)/.test(r)))
 const blocking = reasons.filter(r => kindOf(r) === 'x')
 const name = person?.name || c.person_id
 const facts = `${person?.birth_year ? `Born ${person.birth_year}` : 'Birth year unknown'} · ${person?.locations.join(', ') || 'Location unknown'}`
 const body = <>
  {c.dna_checks?.map((d, i) => <DnaBar key={i} check={d} person={name} match={nameOf(d.match_person_id)}/>)}
  {reasons.length > 0 && <ul className="reason-list marked">{reasons.map((r, i) => { const k = kindOf(r); const M = MARK[k]; return <li key={i} className={`r-${k}`}><M size={15} aria-label={k === 'ok' ? 'supports' : k === 'x' ? 'excludes' : 'note'}/><span>{r}</span></li> })}</ul>}
  <Sources items={c.citations} docs={docs} onCite={onCite}/>
 </>
 const head = <div className="lead-head">
  <span className="candidate-rank">{String(c.rank).padStart(2, '0')}</span>
  <div className="lead-id"><div className="candidate-title"><h2>{name}</h2><span className={`tag ${excluded ? 'red' : 'green'}`}>{c.status}</span>{c.proposed_by_engine && <span className="tag found-tag" title="Kinfold proposed this lead from the record graph; nobody named them as a candidate."><Sparkles size={12}/>Found by Kinfold</span>}</div>
   <p className="small-muted">{facts}</p></div>
  <div className="score" title="Heuristic evidence score, not a probability"><strong>{c.score}</strong><span>evidence<br/>score</span></div>
 </div>
 if (excluded) return <details className="candidate-card excluded lead-fold">
  <summary>{head}<p className="why-excluded"><X size={15}/><span><b>Why excluded:</b> {dna?.status === 'inconsistent' ? `DNA doesn't fit (as ${(dna.relationship_label ?? 'recorded relative').replace(' / ', ' and ')} they'd share ${dna.expected_low_cm?.toLocaleString()}–${dna.expected_high_cm?.toLocaleString()} cM; they share ${dna.observed_cm} cM)` : blocking[0] ?? 'see details'}{blocking.length > (dna?.status === 'inconsistent' ? 0 : 1) ? ` · ${blocking.length - (dna?.status === 'inconsistent' ? 0 : 1)} more record-based reason${blocking.length - (dna?.status === 'inconsistent' ? 0 : 1) === 1 ? '' : 's'}` : ''}</span><em className="fold-hint">Details<ChevronDown size={14}/></em></p></summary>
  <div className="lead-body">{body}<div className="candidate-actions"><button className="text-button" onClick={onGraph}>View in family tree<ArrowRight size={14}/></button></div></div>
 </details>
 return <article className="candidate-card open-lead-card">
  {head}
  <div className="lead-body">{body}
   <div className="candidate-actions"><button className="primary small agent-button" disabled={!!busy} onClick={onAgent}><Bot size={14}/>{busy === 'Agent investigating lead' ? 'Agent investigating…' : 'Investigate with the agent'}</button><button className="text-button" onClick={onGraph}>View in family tree<ArrowRight size={14}/></button></div>
  </div>
 </article>
}
