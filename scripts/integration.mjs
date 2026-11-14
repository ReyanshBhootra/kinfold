import assert from 'node:assert/strict';
import { validateManifest } from '../blockchain/anchor.mjs';
if (!process.argv.includes('--reset-demo')) throw new Error('This check resets the synthetic case and adds a synthetic test record. Run with --reset-demo on a local development backend.');
const base = process.env.KINFOLD_API || 'http://127.0.0.1:8000';
async function api(path, body) {
 const r=await fetch(`${base}${path}`,{signal:AbortSignal.timeout(120000),...(body!==undefined?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{})});
 const value=await r.json();assert.ok(r.ok,`${path}: ${JSON.stringify(value)}`);return value;
}
function citations(s) {
 const references=[...s.relationships,...s.findings,...s.candidates].flatMap(x=>x.citations);
 assert.ok(references.length>0,'Investigation must produce real citations.');
 for(const c of references){const d=s.documents.find(d=>d.id===c.document_id);assert.ok(d,`Missing source ${c.document_id}`);assert.ok(c.start_line>=1 && c.end_line>=c.start_line,'Valid line range');assert.ok(d.text.split('\n').slice(c.start_line-1,c.end_line).join('\n').includes(c.quote),`Quote not located: ${c.quote}`)}
 return references.length;
}
const health=await api('/health');assert.equal(health.status,'ok');
const before=await api('/api/cases/demo',{});assert.equal(before.case.synthetic,true);
const path=`/api/cases/${encodeURIComponent(before.case.id)}`;
assert.equal((await api('/api/cases')).cases.some(c=>c.id===before.case.id),true);
const initial=await api(`${path}/manifest`), repeat=await api(`${path}/manifest`);
assert.equal(initial.digest,repeat.digest,'Repeated manifest reads must be stable.');validateManifest(initial);
const reviewed=await api(`${path}/investigate`,{question:'Review supported family relationships and preserve contradictory evidence.',max_steps:3});
assert.ok(reviewed.metrics.documents_processed>0,'Records reviewed');assert.ok(reviewed.metrics.supported_relationships>0,'Source-backed connections');assert.ok(reviewed.findings.some(f=>f.kind==='conflict'),'Contradiction remains visible');assert.ok(reviewed.candidates.some(c=>c.status==='excluded' && c.reasons.length>0),'Explainable exclusion');
const count=citations(reviewed);
const manifest=await api(`${path}/manifest`);validateManifest(manifest);
assert.equal((await api(`${path}/verify`,{digest:manifest.digest})).matches,true);
const added=await api(`${path}/documents`,{name:'Synthetic integration note.txt',text:'SYNTHETIC TEST RECORD\nThis is a synthetic source uploaded by the local integration check.\nNo identity claim is asserted.'});
assert.equal(added.documents.length,reviewed.documents.length+1,'Upload persisted');
const updated=await api(`${path}/manifest`);validateManifest(updated);assert.notEqual(updated.digest,manifest.digest,'Upload changes evidence digest');
assert.equal((await api(`${path}/verify`,{digest:manifest.digest})).matches,false,'Old digest detects new record');
const continued=await api(`${path}/investigate`,{question:'Review the newly added source.',max_steps:3});assert.ok(continued.documents.find(d=>d.name==='Synthetic integration note.txt')?.processed,'Investigation continues over upload');citations(continued);
assert.equal(updated.anchor.status,'not_anchored');assert.equal(updated.anchor.transaction,null);
console.log(JSON.stringify({status:'passed',case:reviewed.case.id,citations_checked:count,documents:reviewed.documents.length,candidates:reviewed.candidates.length,checks:['health','case load','investigation','citation spans','contradictions','candidate exclusion','manifest stability','cross-language digest','upload','continued investigation','change detection','honest anchor status']},null,2));
