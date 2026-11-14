import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {canonical} from '../blockchain/anchor.mjs';
import {verifyPackage} from './verify-package.mjs';
const text='SYNTHETIC RECORD\nA located source excerpt.';
const snapshot={case:{id:'case',version:1},people:[],documents:[{id:'d',text,provenance:{text_sha256:createHash('sha256').update(text).digest('hex')}}],relationships:[],findings:[{id:'f',citations:[{document_id:'d',quote:'A located source excerpt.',start_line:2,end_line:2}]}],candidates:[]};
function bundle(s=structuredClone(snapshot)){const manifest=structuredClone({schema_version:1,case:s.case,people:s.people,documents:s.documents,relationships:s.relationships,findings:s.findings,candidates:s.candidates});return{export_schema_version:1,package_type:'kinfold_research_package',snapshot:s,manifest:{algorithm:'sha256',manifest,digest:createHash('sha256').update(canonical(manifest)).digest('hex')}}}
test('research package verifies source fingerprints, citation spans and optional baseline',()=>{const b=bundle();const r=verifyPackage(b,b.manifest.digest);assert.equal(r.source_fingerprints_verified,1);assert.equal(r.citations_checked,1);assert.equal(r.comparison_digest_supplied,true);assert.throws(()=>verifyPackage(b,'0'.repeat(64)),/comparison digest/)});
test('source tampering is detected even if the bundled manifest was recomputed',()=>{const s=structuredClone(snapshot);s.documents[0].text+='\nEdited';assert.throws(()=>verifyPackage(bundle(s)),/fingerprint mismatch/)});
test('snapshot divergence and forged citations are rejected',()=>{const b=bundle();b.snapshot.documents[0].text='tampered';assert.throws(()=>verifyPackage(b),/Snapshot does not match/);const s=structuredClone(snapshot);s.findings[0].citations[0].start_line=1;s.findings[0].citations[0].end_line=1;assert.throws(()=>verifyPackage(bundle(s)),/Invalid citation/)});
