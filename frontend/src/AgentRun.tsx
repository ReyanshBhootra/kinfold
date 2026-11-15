import type { ReactNode } from 'react'
import { DnaHypotheses } from './DnaBar'
import { AlertTriangle, Bot, Check, X } from 'lucide-react'
import type { AgentRunRecord, Citation } from './types'

const kindText = (c: {kind: string; person: string; other_person: string | null; year: number | null}) =>
 `${c.kind}: ${c.person}${c.other_person ? ` → ${c.other_person}` : ''}${c.year ? ` (${c.year})` : ''}`

/** The latest lead-investigator run. Every result shown here was computed by KinFold's own tools, not written by the model. */
/** The agent writes its report as dashed prose ("Intro. Heading Words: - point - point Next Heading: - point").
 *  Show it as headings and bullets. Text is unchanged apart from dropping internal person ids. */
function formatReport(text: string) {
 const clean = text.replace(/\s*\(person_id:[^)]*\)/g, '')
 const chunks = clean.split(/\s+-\s+/)
 const sections: { head: string | null; items: string[] }[] = [{ head: null, items: [] }]
 const trailing = /((?:[A-Z][A-Za-z]*\s){0,3}[A-Z][A-Za-z]*):\s*$/
 chunks.forEach(chunk => {
  const m = chunk.match(trailing)
  const body = (m ? chunk.slice(0, m.index) : chunk).trim()
  if (body) sections[sections.length - 1].items.push(body)
  if (m) sections.push({ head: m[1], items: [] })
 })
 return sections.filter(sec => sec.head || sec.items.length).map((sec, i) => <div key={i} className="report-part">
  {sec.head && <h4>{sec.head}</h4>}
  {sec.head ? <ul>{sec.items.map((b, j) => <li key={j}>{b}</li>)}</ul> : sec.items.map((b, j) => <p key={j} className="report-intro">{b}</p>)}
 </div>)
}

export default function AgentRun({run, citations, openSource}: {run: AgentRunRecord; citations: (items: Citation[]) => ReactNode; openSource: (id: string) => void}) {
 const when = new Date(run.source === 'live' ? run.ran_at : run.recorded_at).toLocaleString()
 return <section className="agent-run" aria-label="Lead investigator run">
  <div className="agent-run-head">
   <h2>{run.target.name}: what the agent checked</h2>
   <p className="small-muted"><Bot size={13} aria-hidden="true"/> Lead investigator (LangChain deepagents) · {run.source === 'live' ? `Live run · ${run.model} · ${when}` : `Replay of a recorded agent run · ${run.model} · recorded ${when}`} · {run.steps.length} tool calls · lead statuses unchanged</p>
   {run.note && <p className="agent-warning"><AlertTriangle size={14}/>{run.note}</p>}
   {run.stale && <p className="agent-warning"><AlertTriangle size={14}/>New evidence arrived after this run. Run the agent again to check the current records.</p>}
  </div>
  {run.report && <div className="agent-report">{formatReport(run.report.summary)}{run.report.open_questions.length > 0 && <><h4>Open questions</h4><ul>{run.report.open_questions.map((q,i) => <li key={i}>{q}</li>)}</ul></>}</div>}
  {run.dna_tests.length > 0 && <div className="agent-block"><h4>DNA hypotheses tested: {[...new Set(run.dna_tests.map(t => `${t.name} and ${t.match_name}`))].join(', ')}</h4><DnaHypotheses tests={run.dna_tests} observed={run.dna_tests[0].observed_cm}/><small className="small-muted">Reference-range checks, not likelihoods.</small></div>}
  {(run.verified_claims.length > 0 || run.rejected_claims.length > 0) && <div className="agent-block"><h4>Claims the agent proposed</h4>
   {run.verified_claims.map((c,i) => <div className="agent-row" key={`v${i}`}><span className="tag green"><Check size={11}/>verified</span><div><span>{kindText(c)}</span>{citations([c.citation])}</div></div>)}
   {run.rejected_claims.map((c,i) => <div className="agent-row" key={`r${i}`}><span className="tag red"><X size={11}/>rejected</span><div><span>{kindText(c)}: {c.reason}</span> <button className="text-button" onClick={() => openSource(c.document_id)}>Open source (L{c.start_line})</button></div></div>)}
  </div>}
  {run.next_actions.length > 0 && <div className="agent-block"><h4>Proposed next steps</h4><ol>{run.next_actions.map((a,i) => <li key={i}><strong>{a.title}</strong> {a.reason}</li>)}</ol></div>}
  <details className="package-details"><summary>Every tool call ({run.steps.length})</summary><ol className="agent-steps">{run.steps.map(s => <li key={s.n} className={s.ok ? '' : 'refused'}><code>{s.tool}</code> <span className="small-muted">{s.args}</span><br/>{s.result}</li>)}</ol></details>
  <p className="modal-note">{run.limits}</p>
 </section>
}
