import { Check } from 'lucide-react'
import type { Snapshot } from './types'

type Go = 'workspace' | 'candidates' | 'integrity' | 'upload'
type Step = { title: string; detail: string; done: boolean; go: Go; next: string }

/** The case as a storyline. Every step's state is read from the real snapshot, never assumed. */
export function storySteps(s: Snapshot): Step[] {
 const investigated = s.metrics.documents_processed > 0
 const dnaExcluded = s.candidates.filter(c => c.dna_checks?.some(d => d.status === 'inconsistent')).length
 const aiRead = s.findings.some(f => f.kind === 'ai_extraction')
 const found = s.candidates.find(c => c.proposed_by_engine && c.status !== 'excluded')
 const foundName = found && s.people.find(p => p.id === found.person_id)?.name
 const anchored = (s.anchors || []).some(a => a.matches_current)
 return [
  { title: 'The question', detail: '220 cM shared with Ruth Mercer', done: true, go: 'workspace', next: '' },
  { title: 'DNA tests the story', detail: investigated ? `${dnaExcluded} recorded lead${dnaExcluded === 1 ? '' : 's'} ruled out` : 'Run the investigation', done: investigated && dnaExcluded > 0, go: 'candidates', next: 'Run the investigation' },
  { title: 'AI reads new records', detail: aiRead ? 'Every claim checked against its quote' : 'Add the two Hale records', done: aiRead, go: 'workspace', next: 'Add the Hale obituary and birth announcement, then investigate' },
  { title: 'A new lead appears', detail: foundName ? `${foundName}: found by Kinfold` : 'Waiting for evidence', done: !!found, go: 'candidates', next: 'Investigate after the new records' },
  { title: 'Agent checks the lead', detail: s.agent_run ? `${s.agent_run.steps.length} tool steps, cited` : 'Optional', done: !!s.agent_run, go: 'candidates', next: 'Investigate the lead with the agent' },
  { title: 'Anchored on-chain', detail: anchored ? 'This exact state is on Solana devnet' : 'Not anchored', done: anchored, go: 'integrity', next: 'Anchor this state in Evidence integrity' },
 ]
}

export default function CaseStory({ s, onGo }: { s: Snapshot; onGo: (go: Go) => void }) {
 const steps = storySteps(s)
 const current = steps.findIndex(st => !st.done)
 return <nav className="case-story" aria-label="Case storyline">
  <ol>{steps.map((st, i) => <li key={st.title} className={st.done ? 'done' : i === current ? 'current' : ''}>
   <button onClick={() => onGo(st.go)} aria-current={i === current ? 'step' : undefined}>
    <span className="story-dot">{st.done ? <Check size={13}/> : i + 1}</span>
    <span className="story-text"><strong>{st.title}</strong><small>{st.detail}</small></span>
   </button>
  </li>)}</ol>
  {current >= 0 && <p className="story-next"><span>Next</span>{steps[current].next}</p>}
 </nav>
}
