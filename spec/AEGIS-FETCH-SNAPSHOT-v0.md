# AEGIS-FETCH-SNAPSHOT v0 — receipts for a connected ALICE that fact-checks herself

**Status:** draft v0 (design, not yet implemented) · **Date:** 2026-10-06 · **Applies to:** `agent_trace` gateway (aegis-linux), its verifier, `demo/agent-trace/FORMAT.md` (trace receipts), ALICE connected variant (model/00-ALICE-NEXT-brief.md §2.4).

## 0. The problem in one paragraph
A receipt is only worth something if a third party can **replay** it. The web cannot be replayed: a page fetched at 09:00 is not the page at 09:05. So "ALICE looked it up on the internet" cannot be attested the way "ALICE computed 6×7" is, unless the thing she looked at is **frozen at fetch time and bound into the receipt**. This spec does exactly that, reusing the one mechanism the trace format already has for external data: a **declared table whose SHA-256 is folded into the trace genesis**. A fetch becomes a write into a content-addressed snapshot store; the snapshot is the declared table; the model only ever reads from the snapshot; the verifier replays against the snapshot. The live network is outside the receipt, by construction, and the receipt says so.

## 1. Terms
- **Gateway** — the receipt-gated tool executor in `agent_trace` (scan → parse one call → run → fold `tool/in/out` into the trace chain). Unchanged in spirit; gains two tool identities.
- **Snapshot store** — a directory (or single TSV) of entries `key → (sha256(bytes), fetched_at, source_url, extracted_text)`, written **only by the gateway** at fetch time, read-only afterwards. Serialized as a canonical table in the existing `--table` grammar so that today's `table-sha256` genesis fold covers it with **no format bump**.
- **Snapshot digest** — SHA-256 of the canonical snapshot table bytes at the end of the episode. Folded into the trace genesis exactly where `table-sha256` is folded today (FORMAT.md §4), so an archived receipt + its snapshot file verify forever.
- **Air-gapped mode** — gateway started without `--snapshot`: the scanner never recognizes `SEARCH(` or `FETCH(` (the same rule that makes `LOOKUP(` invisible without `--table`), so the air-gapped and connected variants are **one model, one binary, one flag**.

## 2. Tool grammar (additions to the scanner; earliest-occurrence policy unchanged)
| Call | Grammar | Output on success | Output on miss/err |
|---|---|---|---|
| `SEARCH(<query>)` | query `[A-Za-z0-9 _.,'-]{1,120}`, no newline | up to 3 lines `K<i> <title-or-url>` naming snapshot keys the gateway created for the top results (connected) **or** matching keys already in the snapshot (replay) | `NONE` |
| `FETCH(<key>)` | key grammar as `LOOKUP` (`[A-Za-z0-9_.-]{1,64}`), a key returned by `SEARCH` or pre-declared | `extracted_text` of that snapshot entry, truncated to N bytes (N declared in the receipt) | `NOT-FOUND` |

The model **never passes a URL**: it passes a key the gateway minted. This closes the "model exfiltrates data through a crafted URL" channel, keeps arguments short and verbatim (the `check_verbatim` rule still applies: a `FETCH(K2)` must cite a key the step's visible text contained), and makes replay trivial (keys are stable; URLs are metadata).

## 3. Gateway behaviour
**Connected (`--snapshot <dir> --live`)**
1. `SEARCH(q)`: call the configured search backend (pluggable: a local index, a vendor API, or a fixture server). For each of the top ≤ 3 results: fetch the page, run the **extractor** (HTML → text, scripts/styles dropped, ≤ 64 KiB), compute `sha256(raw_bytes)`, mint key `K<n>` (episode-local counter), write the entry. Output the key list. Every step of this is deterministic given the bytes received; what is *not* deterministic (the network) is captured once and never consulted again.
2. `FETCH(K)`: read the entry; return `extracted_text[..N]`. Never touches the network. (A `FETCH` of a key not minted in this episode or pre-declared is `NOT-FOUND`.)
3. At episode end: serialize the snapshot table canonically (sorted keys, one row per key: `key \t sha256 \t fetched_at \t source_url \t extracted_text_escaped`), compute its SHA-256, emit `table-sha256` and `table-len` lead lines (existing fields), and write the snapshot file next to the receipt.

**Replay (`--snapshot <dir>` without `--live`, or any air-gapped box later)**
`SEARCH(q)` answers from the snapshot's recorded search results for that exact query (stored as rows `S:<sha256(q)> → key list`); `FETCH(K)` reads the entry. The gateway output bytes are therefore identical to the live run, so the trace chain reproduces. **Any difference between the live and replayed outputs is a receipt failure**, which is the property we want.

**Injection boundary.** Fetched text is *data*. It is returned to the model as `TOOL[fetch]=…` inside the running prompt exactly as `LOOKUP` results are today; the model may be fooled by it (that is a model-quality gate, §6), but the gateway never parses tool calls out of fetched text: the scanner runs only over the model's **newly decoded** tokens of the step, which is already the rule.

## 4. What the receipt proves, and what it does not
| Proves (replayable, bit-exact) | Does not prove |
|---|---|
| The model, given this prompt and these tool outputs, emitted these tokens and these calls (decode chain) | That the fetched page was the "real" page at that URL (no TLS transcript; a notary/TLS-attestation layer could be added later) |
| Each tool output the model saw is exactly the snapshot content with digest D (trace chain + `table-sha256`) | That the content was *true* |
| The snapshot bytes have digest D and were present at verify time | Freshness: `fetched_at` is gateway-asserted; a TPM-quoted receipt binds it to a boot, not to a trusted clock |
| In the air-gapped variant: no `SEARCH`/`FETCH` call could have been honoured (no snapshot declared → never scanned) | — |

Keep this table in the spec and in any customer-facing text; it is the honesty boundary.

## 5. The fact-check loop (model behaviour the trace makes visible)
Each stage is one gateway step, so the receipt shows the loop, not just the answer:

```
step 0  Q: <user question>                      A: <DRAFT answer>  [tool=no-tool]
step 1  CHECK: SEARCH(<query derived from the claim>)              [tool=search -> K1 K2 K3]
step 2  READ: FETCH(K1)                                            [tool=fetch  -> text]
step 3  COMPARE: <"supports" | "contradicts" | "no evidence"> ... FINAL: <answer, revised if contradicted>  [tool=no-tool]
```
Required properties for ALICE-Next (gates in model/00 §4): she drafts first (so the receipt records what she *believed*), searches when the question is outside declared data or her confidence is low, cites the key she read, and revises when contradicted. An air-gapped ALICE runs the same prompt program; `SEARCH` is never recognized, so step 1 becomes `no-tool`, and the trained behaviour must then be: "not in my data; ask a connected unit or supply a table."

## 6. Evaluation fixtures (deterministic, offline)
- `fixtures/snapshots/<case>/` — pre-built snapshot stores (no live network in CI). Cases: `supports`, `contradicts`, `no-evidence`, `injection` (page text tells the model to call `CALC(1/0)` or to ignore the question), `stale` (two snapshots of the same key with different dates).
- Buckets for the suite: `factcheck_supports`, `factcheck_contradicts` (must revise), `factcheck_noevidence` (must say so), `factcheck_injection` (must not comply), each n ≥ 30, scored by `score.py` with exact-output rules; `unknown_fact` and `unanswerable` (model/00 §4).

## 7. Implementation plan (aegis-linux + python, no engine change)
1. `agent_trace`: `--snapshot <dir> [--live --search-backend <kind>]`; `ToolCall::{Search,Fetch}`; snapshot serialization = existing table grammar (so `parse_table` reads it back and `table-sha256` covers it). Tests: `search_then_fetch_chains_like_lookup`, `replay_equals_live_bytes`, `airgapped_never_scans_search`.
- The verifier needs **no change**: it already recomputes the genesis with `table-sha256`/`table-len` and replays tool outputs from the declared table.
2. `demo/agent-trace/snapshot.py`: the live fetcher + extractor used by the gateway in `--live` mode (so the Rust binary stays network-free and testable; the gateway shells out to it or reads its output file). Pins: extractor version string in each row.
3. `FORMAT.md` §10: document the snapshot table rows (`K<n>`, `S:<sha256(q)>`), no format bump.
4. Fixtures and buckets (§6); `score.py` bucket rules.
5. Only then: train/evaluate the model behaviour (§5) — the gateway must exist before the data that teaches it can be generated and verified.

## 8. Why this is the right boundary for Aefinity
It gives the connected ALICE the thing the user asked for ("she just needs to know she can pull data from it") without giving up the thing ALICE is for: a receipt a skeptical third party can replay on their own machine, down to the bytes she read. Every later improvement (TLS notarization, trusted time, multiple fetch witnesses) adds a column to the snapshot row; none of them changes the receipt grammar.
