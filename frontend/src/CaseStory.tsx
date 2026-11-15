import { Check } from 'lucide-react'
import type { Snapshot } from './types'

type Go = 'workspace' | 'candidates' | 'integrity' | 'upload'
type Domain = 'records' | 'dna' | 'ai' | 'chain'
type Step = { title: string; detail: string; done: boolean; go: Go; next: string; domain: Domain }

/** The case as a storyline. Every step's state is read from the real snapshot, never assumed. */
export function storySteps(s: Snapshot): Step[] {
 const investigated = s.metrics.documents_processed > 0
 const dnaExcluded = s.candidates.filter(c => c.dna_checks?.some(d => d.status === 'inconsistent')).length
 const aiRead = s.findings.some(f => f.kind === 'ai_extraction')
 const found = s.candidates.find(c => c.proposed_by_engine && c.status !== 'excluded')
 const foundName = found && s.people.find(p => p.id === found.person_id)?.name
 const anchored = (s.anchors || []).some(a => a.matches_current)
 // The case question, from the case's own DNA data rather than hard-coded text.
 const dnaCheck = s.candidates.flatMap(c => c.dna_checks || []).find(d => d.observed_cm)
 const matchName = dnaCheck?.match_person_id ? s.people.find(p => p.id === dnaCheck.match_person_id)?.name : undefined
 const question = dnaCheck ? `${dnaCheck.observed_cm} cM shared${matchName ? ` with ${matchName}` : ''}` : 'The unidentified person'
 return [
  { title: 'The question', detail: question, done: true, go: 'workspace', next: '', domain: 'records' },
  { title: 'DNA tests the story', detail: investigated ? `${dnaExcluded} recorded lead${dnaExcluded === 1 ? '' : 's'} ruled out` : 'Run the investigation', done: investigated && dnaExcluded > 0, go: 'candidates', next: 'Run the investigation', domain: 'dna' },
  { title: 'AI reads new records', detail: aiRead ? 'Every claim checked against its quote' : 'Add the two Hale records', done: aiRead, go: 'workspace', next: 'Add the Hale obituary and birth announcement, then investigate', domain: 'ai' },
  { title: 'A new lead appears', detail: foundName ? `${foundName}: found by KinFold` : 'Waiting for evidence', done: !!found, go: 'candidates', next: 'Investigate after the new records', domain: 'records' },
  { title: 'Agent checks the lead', detail: s.agent_run ? `${s.agent_run.steps.length} tool steps, claims cited` : 'Optional', done: !!s.agent_run, go: 'candidates', next: 'Investigate the lead with the agent', domain: 'ai' },
  { title: 'Anchored on-chain', detail: anchored ? 'This exact state is on Solana devnet' : 'Not anchored', done: anchored, go: 'integrity', next: 'Anchor this state in Evidence integrity', domain: 'chain' },
 ]
}

export default function CaseStory({ s, onGo }: { s: Snapshot; onGo: (go: Go) => void }) {
 const steps = storySteps(s)
 const current = steps.findIndex(st => !st.done)
 return <nav className="case-story" aria-label="Case storyline">
  <ol>{steps.map((st, i) => <li key={st.title} className={`d-${st.domain} ${st.done ? 'done' : i === current ? 'current' : ''}`}>
   <button onClick={() => onGo(st.go)} aria-current={i === current ? 'step' : undefined}>
    <span className="story-dot">{st.done ? <Check size={13}/> : i + 1}</span>
    <span className="story-text"><strong>{st.title}</strong><small>{st.detail}</small></span>
   </button>
  </li>)}</ol>
  {current >= 0 && <p className="story-next"><span>Next</span>{steps[current].next}</p>}
 </nav>
}
