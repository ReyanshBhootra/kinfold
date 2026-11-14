export interface Citation { document_id: string; quote: string; start_line: number; end_line: number }
export interface Person { id: string; name: string; birth_year: number | null; death_year: number | null; locations: string[]; candidate: boolean }
export interface Relationship { id: string; source: string; target: string; type: string; status: string; citations: Citation[] }
export interface EvidenceDocument { id: string; name: string; text: string; kind: string; synthetic: boolean; processed: boolean; provenance?: {origin:string; original_name:string; received_at:string|null; text_sha256:string; authenticity:string} }
export interface Finding { id: string; kind: string; title: string; description: string; severity: string; person_ids: string[]; citations: Citation[] }
export interface DnaCheck { status: 'consistent' | 'inconsistent' | 'unchecked'; observed_cm: number; match_person_id?: string; relationship_label?: string; expected_low_cm?: number; expected_high_cm?: number; reference_source?: string }
export interface Candidate { person_id: string; rank: number; status: string; score: number; reasons: string[]; citations: Citation[]; dna_checks?: DnaCheck[]; proposed_by_engine?: boolean }
export interface Snapshot {
 case: { id: string; title: string; summary: string; status: string; synthetic: boolean; mode: string; version: number };
 people: Person[]; relationships: Relationship[]; documents: EvidenceDocument[]; findings: Finding[]; candidates: Candidate[];
 next_actions: {id: string; title: string; reason: string; person_ids: string[]; document_ids: string[]}[];
 audit: {id: string; timestamp: string; action: string; description: string}[];
 metrics: {documents_processed: number; supported_relationships: number; conflicts: number; remaining_candidates: number};
 anchors?: AnchorRecord[]; ai_recordings?: {document_id: string; model: string; recorded_at: string; raw_sha256: string}[];
}
export interface AnchorRecord { number: number; digest: string; version: number; network: string; transaction: string; explorer: string; anchored_at: string; leads: Record<string,string>; lead_names?: Record<string,string>; documents: number; changes: string[]; matches_current: boolean; limits: string }
export interface Manifest { case_id: string; version: number; algorithm: string; digest: string; manifest: unknown; anchor: { status: string; network: string; transaction: string | null; explorer?: string; anchored_at?: string; number?: number } }
export interface Health {status: string; mode: string; providers: Record<string, boolean>}
