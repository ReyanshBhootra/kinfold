import type { DnaCheck } from './types'

// Log-scale shared-cM axis: 10 cM … 4,000 cM covers distant cousins up to parent/child.
const MIN = 10, MAX = 4000
const pos = (cm: number) => `${Math.min(100, Math.max(0, (Math.log(Math.max(cm, MIN)) - Math.log(MIN)) / (Math.log(MAX) - Math.log(MIN)) * 100))}%`
const TICKS = [10, 50, 200, 1000, 4000]

/** The DNA range check, drawn: the expected range for the recorded relationship vs the observed shared cM.
 *  Purely a picture of backend data (dna_checks); it computes nothing itself. */
export default function DnaBar({ check, person, match }: { check: DnaCheck; person?: string; match?: string }) {
 if (check.status === 'unchecked' || check.expected_low_cm == null || check.expected_high_cm == null) return null
 const fits = check.status === 'consistent'
 const low = check.expected_low_cm, high = check.expected_high_cm
 return <figure className={`dna-bar ${fits ? 'fits' : 'misses'}`} aria-label={`Expected ${low} to ${high} centimorgans for ${check.relationship_label}; observed ${check.observed_cm}. ${fits ? 'Inside the range.' : 'Outside the range.'}`}>
  <figcaption>
   <span className="dna-title">DNA check: <span className="dna-verdict">{fits ? 'consistent' : 'inconsistent'}</span></span>
   <span className="dna-sentence">On the recorded family tree, {person || 'this lead'} and {match || 'the DNA match'} would be <strong>{(check.relationship_label ?? 'related').replace(' / ', ' and ')}</strong>. Relatives like that usually share <strong>{low.toLocaleString()}–{high.toLocaleString()} cM</strong> of DNA. They share <strong>{check.observed_cm.toLocaleString()} cM</strong>{fits ? ', inside that range.' : check.observed_cm < low ? ', well below that range, so the recorded tree doesn\'t fit the DNA.' : ', above that range, so the recorded tree doesn\'t fit the DNA.'}</span>
  </figcaption>
  <div className="dna-track" aria-hidden="true">
   <div className="dna-range" style={{ left: pos(low), width: `calc(${pos(high)} - ${pos(low)})` }}/>
   <div className="dna-marker" style={{ left: pos(check.observed_cm) }}><span>{check.observed_cm}</span></div>
  </div>
  <div className="dna-ticks" aria-hidden="true">{TICKS.map(t => <span key={t} style={{ left: pos(t) }}>{t >= 1000 ? `${t / 1000}k` : t}</span>)}</div>
  <div className="dna-legend" aria-hidden="true"><span><i className="sw-range"/>Usual range for that relationship</span><span><i className="sw-mark"/>DNA they actually share</span><span className="dna-units">cM = centimorgans, a measure of shared DNA</span></div>
 </figure>
}

type Hypothesis = { relationship: string; relationship_label: string; expected_low_cm: number; expected_high_cm: number; observed_cm: number; status: string }

/** Several relationship hypotheses on one shared axis, with a single line at the observed cM.
 *  Purely a picture of the agent's recorded test results; it computes nothing itself. */
export function DnaHypotheses({ tests, observed }: { tests: Hypothesis[]; observed: number }) {
 return <figure className="dna-hyp" aria-label={`Observed ${observed} centimorgans against ${tests.length} relationship hypotheses`}>
  <div className="dna-hyp-plot">
   <div className="dna-hyp-overlay" aria-hidden="true"><div className="dna-hyp-line" style={{ left: pos(observed) }}><span>{observed} cM observed</span></div></div>
   {tests.map(t => <div className={`dna-hyp-row ${t.status === 'consistent' ? 'fits' : 'misses'}`} key={t.relationship}>
    <span className="dna-hyp-label">{t.relationship_label}<small>{t.expected_low_cm.toLocaleString()}–{t.expected_high_cm.toLocaleString()} cM · {t.status === 'consistent' ? 'fits' : 'does not fit'}</small></span>
    <span className="dna-hyp-track"><span className="dna-range" style={{ left: pos(t.expected_low_cm), width: `calc(${pos(t.expected_high_cm)} - ${pos(t.expected_low_cm)})` }}/></span>
   </div>)}
   <div className="dna-hyp-axis" aria-hidden="true"><span/><span className="dna-ticks">{TICKS.map(t => <span key={t} style={{ left: pos(t) }}>{t >= 1000 ? `${t / 1000}k` : t}</span>)}</span></div>
  </div>
 </figure>
}
