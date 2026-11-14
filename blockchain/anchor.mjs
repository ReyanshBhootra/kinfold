import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { parseArgs } from 'node:util';
import { pathToFileURL } from 'node:url';
import { Connection, Keypair, PublicKey, Transaction, TransactionInstruction } from '@solana/web3.js';

export const MEMO_PROGRAM = 'MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr';
export const DEVNET_GENESIS = 'EtWTRABZaYq6iMfeYKouRu166VU2xqa1wcaWoxPkrZBG';
export function canonical(value) {
 if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
 if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(',')}}`;
 if (typeof value === 'number' && !Number.isSafeInteger(value)) throw new Error('Manifest numbers must be safe integers for portable canonicalization.');
 return JSON.stringify(value);
}
export function validateManifest(envelope) {
 if (envelope.algorithm !== 'sha256' || !/^[a-f0-9]{64}$/.test(envelope.digest || '') || !envelope.manifest || typeof envelope.manifest !== 'object') throw new Error('Expected an exported Kinfold SHA-256 manifest envelope.');
 const actual = createHash('sha256').update(canonical(envelope.manifest), 'utf8').digest('hex');
 if (actual !== envelope.digest) throw new Error('Manifest digest mismatch. Export an intact manifest before anchoring.');
 return `kinfold:v1:sha256:${actual}`;
}
export function checkTransaction(tx, expectedMemo, expectedSigner) {
 if (!tx || !tx.meta || tx.meta.err !== null) throw new Error('Transaction is missing, unconfirmed, or failed. No verified anchor.');
 const instructions = tx.transaction.message.instructions;
 const found = instructions.some(i => i.programId?.toString() === MEMO_PROGRAM && i.parsed === expectedMemo);
 if (!found) throw new Error('Confirmed transaction does not contain the expected Kinfold digest in the Memo program.');
 if (expectedSigner && !tx.transaction.message.accountKeys.some(k => k.signer && k.pubkey.toString() === expectedSigner)) throw new Error('Receipt signer does not match the transaction.');
 return true;
}
export function buildMemoTransaction(memo, signer, latest) {
 if (!/^kinfold:v1:sha256:[a-f0-9]{64}$/.test(memo)) throw new Error('Only a namespaced SHA-256 digest may be anchored.');
 return new Transaction({feePayer:signer.publicKey,blockhash:latest.blockhash,lastValidBlockHeight:latest.lastValidBlockHeight}).add(new TransactionInstruction({programId:new PublicKey(MEMO_PROGRAM),keys:[{pubkey:signer.publicKey,isSigner:true,isWritable:false}],data:Buffer.from(memo,'utf8')}));
}
export async function run(args = process.argv.slice(2)) {
 const {values} = parseArgs({args,options:{manifest:{type:'string'},send:{type:'boolean',default:false},keypair:{type:'string'},out:{type:'string'},verify:{type:'string'},help:{type:'boolean',default:false}},strict:true});
 if (values.help || !values.manifest) { console.log('Preview: npm run anchor -- --manifest exported-manifest.json\nSend: npm run anchor -- --manifest exported-manifest.json --send --keypair path/to/dev-only.keypair.json --out receipt.json\nVerify: npm run anchor -- --manifest exported-manifest.json --verify receipt.json\nDevnet only. Preview does not load keys or contact the network.');return; }
 if (values.send && values.verify) throw new Error('Choose either --send or --verify.');
 const envelope = JSON.parse(await readFile(values.manifest,'utf8'));
 const memo = validateManifest(envelope);
 if (!values.send && !values.verify) { console.log(JSON.stringify({status:'not_anchored',network:'solana-devnet',memo,private_data_on_chain:false},null,2));return; }
 const connection = new Connection(process.env.SOLANA_DEVNET_RPC || 'https://api.devnet.solana.com','confirmed');
 if (await connection.getGenesisHash() !== DEVNET_GENESIS) throw new Error('RPC genesis hash is not Solana devnet. Refusing this network.');
 if (values.verify) {
  const receipt = JSON.parse(await readFile(values.verify,'utf8'));
  if (receipt.digest !== envelope.digest || receipt.memo !== memo || receipt.network !== 'solana-devnet') throw new Error('Receipt is for a different manifest or network.');
  const tx = await connection.getParsedTransaction(receipt.transaction,{commitment:'confirmed',maxSupportedTransactionVersion:0});
  checkTransaction(tx,memo,receipt.signer);
  console.log(JSON.stringify({status:'verified_on_chain',digest:envelope.digest,transaction:receipt.transaction,slot:String(tx.slot),network:'solana-devnet'},null,2));return;
 }
 if (!values.keypair || !values.out) throw new Error('--send requires an explicit development --keypair and --out receipt path.');
 const bytes = JSON.parse(await readFile(values.keypair,'utf8'));
 if (!Array.isArray(bytes) || bytes.length!==64 || bytes.some(x=>!Number.isInteger(x)||x<0||x>255)) throw new Error('Expected a 64-byte Solana CLI development keypair file.');
 const signer = await Keypair.fromSecretKey(Uint8Array.from(bytes));
 const latest = await connection.getLatestBlockhash('confirmed');
 const tx = buildMemoTransaction(memo,signer,latest);
 await tx.sign(signer);
 // Persist the known signature immediately after submission, before waiting for confirmation.
 // Reserve the receipt before broadcasting, so an existing file cannot cause a post-send failure.
 await writeFile(values.out,JSON.stringify({network:'solana-devnet',status:'prepared',digest:envelope.digest,memo},null,2),{flag:'wx'});
 const signature = await connection.sendRawTransaction(await tx.serialize(),{skipPreflight:false,maxRetries:3});
 const receipt = {network:'solana-devnet',status:'submitted',digest:envelope.digest,memo,transaction:signature,signer:signer.publicKey.toBase58(),explorer:`https://explorer.solana.com/tx/${signature}?cluster=devnet`};
 await writeFile(values.out,JSON.stringify(receipt,null,2));
 console.log(`Submitted ${signature}. Receipt saved. Awaiting confirmation; submission alone is not an anchor.`);
 const result = await connection.confirmTransaction({signature,...latest},'confirmed');
 if (result.value.err) throw new Error(`Transaction failed. Receipt remains submitted; inspect ${signature}.`);
 const confirmed = await connection.getParsedTransaction(signature,{commitment:'confirmed',maxSupportedTransactionVersion:0});
 checkTransaction(confirmed,memo,receipt.signer);
 receipt.status = 'confirmed'; receipt.slot = String(confirmed.slot);
 await writeFile(values.out,JSON.stringify(receipt,null,2));
 console.log(JSON.stringify(receipt,null,2));
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) run().catch(error => {console.error(error.message);process.exitCode=1});
