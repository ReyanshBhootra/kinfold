# Digest anchoring on Solana devnet

Kinfold's local SHA-256 manifest works without a wallet. Optional anchoring puts only `kinfold:v1:sha256:<digest>` into a real Solana Memo transaction. It does not publish evidence, DNA summaries, candidate names, or case IDs. An anchor establishes that a digest was recorded; it cannot establish the truth of the records.

## Prepare and preview

Export the manifest from **Evidence integrity** in the app. Keep the exported JSON local.

```powershell
npm run anchor -- --manifest C:/path/to/kinfold-manifest-v1.json
```

Preview recomputes the SHA-256 digest over recursively sorted-key compact UTF-8 JSON. It refuses altered exports. It does not read keys or call RPC. Arrays retain their exported order; numbers must be safe integers.

## Send explicitly

Install the Solana CLI separately if you need to create a wallet. Use a dedicated **devnet-only** keypair, outside the repository, with faucet devnet SOL. Never reuse a wallet holding real funds. No wallet creation, funding, airdrop, signing, or broadcast is automatic.

```powershell
solana-keygen new --outfile C:/path/outside/repository/kinfold-dev.keypair.json
solana airdrop 1 --url devnet --keypair C:/path/outside/repository/kinfold-dev.keypair.json
npm run anchor -- --manifest C:/path/to/kinfold-manifest-v1.json --send --keypair C:/path/outside/repository/kinfold-dev.keypair.json --out C:/path/to/kinfold-anchor-receipt.json
```

The script checks the RPC genesis hash matches devnet, signs a Memo-only transaction, reserves a new receipt file, broadcasts with preflight, records the returned signature, waits for confirmation, and checks the confirmed instruction and signer before marking the receipt `confirmed`. It refuses to overwrite an existing output receipt. `SOLANA_DEVNET_RPC` optionally selects a different devnet RPC provider; other networks fail the genesis check.

If confirmation times out, `submitted` is the honest status. Preserve the receipt and verify later rather than blindly resending. A `prepared` receipt alone means a broadcast was not confirmed by the script; inspect the command error and wallet history before retrying. Public RPC/faucets may rate-limit requests.

## Verify from the chain

```powershell
npm run anchor -- --manifest C:/path/to/kinfold-manifest-v1.json --verify C:/path/to/kinfold-anchor-receipt.json
```

Verification recomputes the local digest, checks the devnet network, retrieves the actual transaction, requires successful execution, and matches the exact Memo program payload and receipt signer. A receipt file by itself is never proof. A changed manifest cannot verify against an earlier receipt. Devnet history may be reset or pruned.

CLI receipt files are never imported or trusted by the UI. The app's own **Anchor this state** button (Evidence integrity) runs this same script via `POST /api/cases/{id}/anchor` with `KINFOLD_SOLANA_KEYPAIR`. It records an anchor only when the script returns a confirmed, on-chain-checked receipt. Otherwise the UI stays `not_anchored`.

```powershell
npm run test:anchor
```

Offline tests cover canonicalization, Unicode, tampering, digest-only payloads, failed/missing transactions, spoofed memo programs and signer mismatches. They do not substitute for a real devnet transaction.

References: [Solana Memo cookbook](https://solana.com/developers/cookbook/transactions/add-memo), [getTransaction RPC](https://solana.com/docs/rpc/http/gettransaction), [genesis hash RPC](https://solana.com/docs/rpc/http/getgenesishash). SDK is pinned to the installed `@solana/web3.js` v3 compatibility API; no smart contract deployment is needed.
