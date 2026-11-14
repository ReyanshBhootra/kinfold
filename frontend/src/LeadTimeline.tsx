import { useState } from 'react'
import { Anchor, ArrowUpRight, CheckCircle2, LoaderCircle, AlertTriangle } from 'lucide-react'
import { api } from './api'
import type { AnchorRecord, Snapshot } from './types'

type Check = { verified_on_chain: boolean; current_matches_anchor: boolean; detail: string }
export const ANCHOR_LIMITS = 'Proves this exact state existed by this time, unchanged; it does not prove the records are true.'

const time = (iso: string) => new Date(iso).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })

/** Lead timeline: each research state anchored on Solana devnet, with what changed and an on-chain re-check. */
export default function LeadTimeline({ s, busy, onSnapshot, onError }: { s: Snapshot; busy: boolean; onSnapshot: (s: Snapshot) => void; onError: (m: string) => void }) {
 const [working, setWorking] = useState<string>(''), [checks, setChecks] = useState<Record<number, Check>>({})
 const anchors: AnchorRecord[] = s.anchors || []
 const base = `/api/cases/${encodeURIComponent(s.case.id)}`
 const latest = anchors[anchors.length - 1]
 async function anchorNow() {
  setWorking('anchor'); onError('')
  try { onSnapshot(await api<Snapshot>(`${base}/anchor`, {})) } catch (e) { onError((e as Error).message) } finally { setWorking('') }
 }
 async function check(n: number) {
  setWorking(`verify-${n}`); onError('')
  try { const r = await api<Check>(`${base}/anchors/${n}/verify`, {}); setChecks(c => ({ ...c, [n]: r })) } catch (e) { onError((e as Error).message) } finally { setWorking('') }
 }
 return <section className="lead-timeline" aria-labelledby="lead-timeline-title">
  <div className="timeline-head"><div><h3 id="lead-timeline-title">Lead timeline</h3><p>Anchor a hash of this research state on Solana devnet: the cited records, the AI's raw outputs and the lead decisions. Only the hash goes on-chain.</p></div>
   <button className="secondary small" disabled={busy || !!working || (latest?.matches_current ?? false)} onClick={() => void anchorNow()} title={latest?.matches_current ? 'This exact state is already anchored' : undefined}>{working === 'anchor' ? <LoaderCircle className="spin" size={15}/> : <Anchor size={15}/>}{working === 'anchor' ? 'Anchoring on devnet…' : latest?.matches_current ? 'State already anchored' : 'Anchor this state'}</button></div>
  <p className="timeline-limits">{ANCHOR_LIMITS}</p>
  {latest && !latest.matches_current && <div className="verification changed" role="status"><AlertTriangle size={14}/> Current evidence differs from anchor #{latest.number}.</div>}
  {anchors.length === 0 ? <p className="small-muted">No anchors yet. Until a real devnet transaction is confirmed, this case is not anchored.</p> :
   <ol className="timeline-list">{[...anchors].reverse().map(a => { const c = checks[a.number]; return <li key={a.number} className={a.matches_current ? 'current' : ''}>
    <div className="timeline-row"><strong>#{a.number} · {time(a.anchored_at)}</strong><span className="tag">v{a.version}</span>{a.matches_current && <span className="tag">matches current</span>}</div>
    <code className="digest" title={a.digest}>{a.digest.slice(0, 16)}…</code>
    <ul className="timeline-changes">{a.changes.map(ch => <li key={ch}>{ch}</li>)}</ul>
    <div className="timeline-leads">{Object.entries(a.leads).map(([pid, status]) => <span key={pid} className={`tag ${status === 'excluded' ? 'red' : ''}`}>{a.lead_names?.[pid] || pid}: {status}</span>)}</div>
    <div className="timeline-actions"><a className="text-button" href={a.explorer} target="_blank" rel="noreferrer">Solana Explorer<ArrowUpRight size={12}/></a>
     <button className="quiet small" disabled={busy || !!working} onClick={() => void check(a.number)}>{working === `verify-${a.number}` ? <LoaderCircle className="spin" size={14}/> : <CheckCircle2 size={14}/>}Verify</button></div>
    {c && <div className={`verification ${c.verified_on_chain && c.current_matches_anchor ? '' : 'changed'}`} role="status">
     {c.verified_on_chain ? 'On-chain: transaction found on devnet with this digest.' : `On-chain check failed: ${c.detail}`} {c.current_matches_anchor ? 'Current evidence matches this anchor.' : `Current evidence differs from anchor #${a.number}.`}</div>}
   </li> })}</ol>}
 </section>
}
