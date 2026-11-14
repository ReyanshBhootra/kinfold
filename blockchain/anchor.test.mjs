import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { canonical, validateManifest, checkTransaction, buildMemoTransaction, MEMO_PROGRAM } from './anchor.mjs';
import { Keypair, Transaction } from '@solana/web3.js';
const manifest = {version:1,documents:[{id:'d1',text:'Synthetic résumé\nEvidence'}],claims:[]};
const envelope = {algorithm:'sha256',manifest,digest:createHash('sha256').update(canonical(manifest)).digest('hex')};
test('portable canonicalization orders keys and preserves array order and Unicode',()=>{
 assert.equal(canonical({z:2,a:{b:'é',a:1}}),' {"a":{"a":1,"b":"é"},"z":2}'.trim());
 assert.notEqual(canonical([1,2]),canonical([2,1]));
 assert.throws(()=>canonical({score:.5}),/safe integers/);
});
test('anchor payload contains only a namespaced digest; changed content is rejected',()=>{
 const memo=validateManifest(envelope);assert.match(memo,/^kinfold:v1:sha256:[a-f0-9]{64}$/);assert.equal(memo.includes('Synthetic'),false);
 assert.throws(()=>validateManifest({...envelope,manifest:{...manifest,version:2}}),/mismatch/);
 assert.throws(()=>validateManifest({...envelope,algorithm:'md5'}),/SHA-256/);
});
test('verification requires success, exact Memo program payload and signer',()=>{
 const memo=validateManifest(envelope); const tx={meta:{err:null},transaction:{message:{instructions:[{programId:MEMO_PROGRAM,parsed:memo}],accountKeys:[{pubkey:'dev-signer',signer:true}]}},slot:1};
 assert.equal(checkTransaction(tx,memo,'dev-signer'),true);
 assert.throws(()=>checkTransaction(null,memo),/missing/);
 assert.throws(()=>checkTransaction({...tx,meta:{err:{failed:true}}},memo),/failed/);
 assert.throws(()=>checkTransaction(tx,'different'),/expected Kinfold digest/);
 assert.throws(()=>checkTransaction(tx,memo,'wrong-signer'),/signer/);
 const fake={...tx,transaction:{message:{...tx.transaction.message,instructions:[{programId:'another-program',parsed:memo}]}}};
 assert.throws(()=>checkTransaction(fake,memo),/Memo program/);
});
test('real SDK serializes a signed Memo-only transaction without a transfer instruction',async()=>{
 const signer=await Keypair.generate(); // Ephemeral offline test key; never funded or saved.
 const memo=validateManifest(envelope);
 const tx=buildMemoTransaction(memo,signer,{blockhash:'11111111111111111111111111111111',lastValidBlockHeight:100});
 await tx.sign(signer);assert.equal(await tx.verifySignatures(),true);
 const decoded=Transaction.from(await tx.serialize());
 assert.equal(decoded.instructions.length,1);assert.equal(decoded.instructions[0].programId.toBase58(),MEMO_PROGRAM);assert.equal(Buffer.from(decoded.instructions[0].data).toString('utf8'),memo);
 assert.throws(()=>buildMemoTransaction('publish a person name',signer,{}),/Only a namespaced/);
});
