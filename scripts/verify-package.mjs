import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { parseArgs } from 'node:util';
import { pathToFileURL } from 'node:url';
import { canonical, validateManifest } from '../blockchain/anchor.mjs';

export function verifyPackage(bundle, expectedDigest) {
 if(bundle.export_schema_version!==1 || bundle.package_type!=='kinfold_research_package' || !bundle.snapshot) throw new Error('Expected a Kinfold research package v1.');
 validateManifest(bundle.manifest);
 const s=bundle.snapshot;
 const byId=(a,b)=>a.id<b.id?-1:a.id>b.id?1:0;
 const content={schema_version:1,case:s.case,people:[...s.people].sort(byId),documents:[...s.documents].sort(byId),relationships:[...s.relationships].sort(byId),findings:[...s.findings].sort(byId),candidates:[...s.candidates].sort((a,b)=>a.person_id<b.person_id?-1:a.person_id>b.person_id?1:0)};
 // Canonical object keys are sorted; array ordering follows ASCII IDs from the API.
 if(canonical(content)!==canonical(bundle.manifest.manifest)) throw new Error('Snapshot does not match the bundled evidence manifest.');
 if(expectedDigest && expectedDigest.toLowerCase()!==bundle.manifest.digest) throw new Error('Package differs from the supplied comparison digest.');
 let fingerprints=0, missing=0;
 for(const d of s.documents){const actual=createHash('sha256').update(d.text,'utf8').digest('hex');const captured=d.provenance?.text_sha256;if(!captured){missing++;continue}if(captured!==actual)throw new Error(`Source fingerprint mismatch: ${d.id}`);fingerprints++;}
 const docs=new Map(s.documents.map(d=>[d.id,d]));let citations=0;
 for(const item of [...s.relationships,...s.findings,...s.candidates])for(const c of item.citations){const d=docs.get(c.document_id);if(!d||c.start_line<1||c.end_line<c.start_line||c.end_line>d.text.split('\n').length||!d.text.split('\n').slice(c.start_line-1,c.end_line).join('\n').includes(c.quote))throw new Error(`Invalid citation: ${c.document_id}`);citations++;}
 return {status:'local_package_consistent',digest:bundle.manifest.digest,comparison_digest_supplied:!!expectedDigest,source_fingerprints_verified:fingerprints,sources_without_captured_fingerprint:missing,citations_checked:citations,notice:'Local consistency only. An independently saved digest is needed to detect a wholly rewritten package. This does not establish evidence truth, authorship, identity or an on-chain anchor.'};
}
async function run(){const{values}=parseArgs({options:{file:{type:'string'},digest:{type:'string'},help:{type:'boolean'}}});if(values.help||!values.file){console.log('npm run verify:package -- --file exported-research-package.json [--digest previous-sha256]');return}console.log(JSON.stringify(verifyPackage(JSON.parse(await readFile(values.file,'utf8')),values.digest),null,2));}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)run().catch(e=>{console.error(e.message);process.exitCode=1});
