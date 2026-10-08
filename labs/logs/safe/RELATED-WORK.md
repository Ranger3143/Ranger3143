# LAB-09 related-work check (no experiment)

Date: 2026-10-08. Purpose: the prior work the LAB-09 note should position against, with the one claim we rely on from each, and an honest statement of what the literature does NOT cover. Nothing in this file is an ALICE measurement; every number below is a number published by the cited authors (Rule A/B do not apply, but every quote can be re-checked in `RELATED-WORK-sources/`).

## How this was done (and its limits)

1. Discovery: WebSearch (standard and extended mode) for each topic, 2026-10-08. WebSearch and WebFetch return model-written summaries, so they were used only to find candidates and were never the source of a quote.
2. Verification: every arXiv item was re-fetched with `curl` from `arxiv.org/abs/<id>` and the `citation_*` meta tags (title, authors, dates, abstract, comments) saved verbatim to `RELATED-WORK-sources/arxiv_abstracts.json` (57 records; script `fetch_arxiv_abstracts.py`). Quotes below are copied from that file. Tables and body sentences for AgentDojo, InjecAgent, Wan et al. and Xu et al. come from `pdftotext` of the arXiv PDFs (saved alongside). The two IETF drafts were read as the datatracker `.txt` files (saved alongside). Greshake's venue, pages and DOI were checked against the Crossref API record for DOI 10.1145/3605764.3623985 (title, "Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security", pages 79-90, issued 2023-11-26).
3. Gap search: 13 arXiv-API phrase queries (`arxiv_gap_queries.py`, raw output `arxiv_gap_queries.out.txt`), plus the extended WebSearch queries listed in the gap section. arXiv `all:` queries are literal-phrase and unranked-by-meaning, so zero hits is weak evidence of absence, not proof.
4. Not searched: Semantic Scholar, Google Scholar, ACL Anthology search, IEEE Xplore, ACM DL search, non-English venues, patents (one USPTO hit on "pre-inference execution compliance" appeared in a search and was not read). WebSearch is US-only.
5. Items seen only in search snippets and NOT verified at primary source are listed in "Unverified" at the end. Do not cite those without opening them.

---

## A. Indirect prompt injection through retrieved or tool content

**A1. Greshake, Abdelnabi, Mishra, Endres, Holz, Fritz (2023). "Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection." Proceedings of the 16th ACM Workshop on Artificial Intelligence and Security (AISec '23), pp. 79-90; arXiv:2302.12173 (v1 2023-02-23, v2 2023-05-05).**
URL: https://arxiv.org/abs/2302.12173 (DOI 10.1145/3605764.3623985).
Claim we rely on: the threat model itself, that data pulled in by the application can carry instructions. Quote: "We argue that LLM-Integrated Applications blur the line between data and instructions." and "We show how processing retrieved prompts can act as arbitrary code execution, manipulate the application's functionality, and control how and if other APIs are called." Qualitative demonstrations (Bing Chat, GPT-4 apps); no attack-success rate is reported in the abstract.

**A2. Zhan, Liang, Ying, Kang (2024). "InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents." Findings of ACL 2024; arXiv:2403.02691 (v3 2024-08-04).**
URL: https://arxiv.org/abs/2403.02691
Claim: tool results are an attack channel for deployed agents and the rates are large. Quote: "InjecAgent comprises 1,054 test cases covering 17 different user tools and 62 attacker tools." and "ReAct-prompted GPT-4 vulnerable to attacks 24% of the time". Our reading of Table 3 (ASR-valid, base setting, "Total" column, the 18 prompted agents it lists; the abstract says 30 agents were evaluated): prompted agents range from 3.4% (OpenOrca-Mistral) to 86.9% (Llama2-70B); prompted GPT-4 is 23.6% base and 47.0% with the "hacking prompt" (text: "24% in the base setting and a higher ASR of 47% in the enhanced setting"); fine-tuned GPT-4 is 6.6% base and 7.1% enhanced. Metric: the agent's next action runs the attacker's tool (a different metric from echoing an embedded call, see section G).

**A3. Debenedetti, Zhang, Balunovic, Beurer-Kellner, Fischer, Tramer (2024). "AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents." NeurIPS 2024 Datasets and Benchmarks Track; arXiv:2406.13352 (v3 2024-11-24).**
URL: https://arxiv.org/abs/2406.13352
Claim: 97 tasks and 629 security test cases; "AI agents are vulnerable to prompt injection attacks where data returned by external tools hijacks the agent to execute malicious tasks." Numbers from v3 Table 3 (targeted ASR, all models): 0.95% (Command-R+) to 47.69% (GPT-4o); Claude 3.5 Sonnet 33.86%; Llama 3 70b 20.03%; GPT-3.5 Turbo 8.43%. v3 Table 5 (GPT-4o): no defense 57.69%, PI detector 7.95%, tool filter 6.84%.
Flag: the v3 introduction says "our attacks succeed against the best performing agents in less than 25% of cases", which does not match v3 Table 3, where the highest-utility model (Claude 3.5 Sonnet, 78.22% benign utility) has 33.86% targeted ASR. Quote the table, not the sentence, or cite both and say they differ.

**A4. Zhang, Huang, Mei, Yao, Wang, Zhan, Wang, Zhang (2025). "Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents." ICLR 2025; arXiv:2410.02644 (v4 2025-05-30).**
URL: https://arxiv.org/abs/2410.02644
Claim: across 13 LLM backbones, "with the highest average attack success rate of 84.30%, but limited effectiveness shown in current defenses".

**A5. Zou, Lin, Jones, Nowak, Dziemian, Winter, Grattan, Nathanael, Croft, Davies, Patel, Kirk, Burnikell, Gal, Hendrycks, Kolter, Fredrikson (2025). "Security Challenges in AI Agent Deployment: Insights from a Large Scale Public Competition." arXiv:2507.20526 (2025-07-28; no venue listed).**
URL: https://arxiv.org/abs/2507.20526
Claim: "Participants submitted 1.8 million prompt-injection attacks, with over 60,000 successfully eliciting policy violations" against 22 frontier agents; "Nearly all agents exhibit policy violations for most behaviors within 10-100 queries, with high attack transferability across models and tasks"; "limited correlation between agent robustness and model size, capability, or inference-time compute".

**A6. Nasr, Carlini, Sitawarin, Schulhoff, Hayes, Ilie, Pluto, Song, Chaudhari, Shumailov, Thakurta, Xiao, Terzis, Tramer (2025/2026). "The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaks and Prompt Injections." arXiv:2510.09023 (2025-10-10); USENIX Security '26, pp. 1467-1486.**
URL: https://arxiv.org/abs/2510.09023 ; venue page https://www.usenix.org/conference/usenixsecurity26/presentation/nasr
Claim: static or non-adaptive evaluations overstate robustness. Quote: "we bypass 12 recent defenses (based on a diverse set of techniques) with attack success rate above 90% for most; importantly, the majority of defenses originally reported near-zero attack success rates."

**A7. Gateway- and policy-level defenses (design precedent for our "by construction" H4).**
- Debenedetti et al. (2025), "Defeating Prompt Injections by Design" (CaMeL), arXiv:2503.18813: "CaMeL explicitly extracts the control and data flows from the (trusted) query; therefore, the untrusted data retrieved by the LLM can never impact the program flow." Result: "solving 77% of tasks with provable security (compared to 84% with an undefended system) in AgentDojo." https://arxiv.org/abs/2503.18813
- Ma, Xiao, Yeoh, Zhang, Vorobeychik (2026), "ROPE", arXiv:2608.27496: "ROPE holds attack success rate to 1.6--2.6% while retaining 82--100% of undefended clean utility". https://arxiv.org/abs/2608.27496
- Shayoni, Shoaib, Hossain, Mridha (2026), "NetInjectBench", arXiv:2607.10490: "naive execution reached an 82.50% unsafe tool-action rate" (Qwen2.5-7B, Llama3.1-8B, Mistral-7B) and "the metadata-aware policy gate produced 0/240 unsafe attack actions, with a 95% Wilson upper bound of 1.58%". https://arxiv.org/abs/2607.10490
- Shah (2026), "LogJack", arXiv:2604.15368: "verbatim command execution rates range from 0% (Claude Sonnet 4.6) to 86.2% (Llama 3.3 70B)"; cloud guardrails "largely fail to detect log-embedded injections". https://arxiv.org/abs/2604.15368
- Bhagwatkar et al. (2025/2026), arXiv:2510.05244: a tool-interface firewall "achieves perfect security with high utility across all four public benchmarks" while the authors also report "flawed success metrics, implementation bugs, and most importantly, weak attacks" in those benchmarks. https://arxiv.org/abs/2510.05244
Use: a deterministic gateway makes H4 (the gateway never executes text that came from the table) true by construction; what the literature leaves open, and SAFE-02 measures, is what a small model does on its own when it sees an instruction inside a tool result.

## B. Poisoning of instruction-tuning and agent data with triggers

**B1. Wan, Wallace, Shen, Klein (2023). "Poisoning Language Models During Instruction Tuning." ICML 2023 (PMLR 202:35413-35425); arXiv:2305.00944.**
URL: https://arxiv.org/abs/2305.00944
Claim: a trigger phrase can be implanted with very few examples and no visible accuracy loss. Quote: "By using as few as 100 poison examples, we can cause arbitrary phrases to have consistent negative polarity or induce degenerate outputs across hundreds of held-out tasks." Body text: "poisoning does not affect accuracy on regular inputs and it is often more successful on larger LMs". Clean-label variant (label-correct poison): at 100 samples "clean-label poisoning can reach 55.6% misclassification rate" versus 92.8% dirty-label. Models: Tk-Instruct 770M to 11B. Defences: "data filtering or reducing model capacity provide only moderate protections while reducing test accuracy"; flagging high-loss samples removed 50% of poison at a cost of 6.3% of the training set.

**B2. Xu, Ma, Wang, Xiao, Chen (2024). "Instructions as Backdoors: Backdoor Vulnerabilities of Instruction Tuning for Large Language Models." NAACL 2024; arXiv:2305.14710 (v2 2024-04-03).**
URL: https://arxiv.org/abs/2305.14710
Claim (poison rates near 1%): "an attacker can inject backdoors by issuing very few malicious instructions (~1000 tokens)"; "over 90% attack success rate across four commonly used NLP datasets"; body: "The poison ratio can be as low as 1% in our work." (Table 6: 1% is 69 SST-2, 77 HateSpeech, 32 Tweet Emotion, 49 TREC instances.) Mitigation: "RLHF and clean demonstrations might mitigate such backdoors to some degree."

**B3. Souly, Rando, Chapman, Davies, Hasircioglu, Shereen, Mougan, Mavroudis, Jones, Hicks, Carlini, Gal, Kirk (2025). "Poisoning Attacks on LLMs Require a Near-constant Number of Poison Samples." arXiv:2510.07192 (2025-10-08; no peer-reviewed venue listed).**
URL: https://arxiv.org/abs/2510.07192
Claim (the right unit is an absolute count, not a percentage): "250 poisoned documents similarly compromise models across all model and dataset sizes, despite the largest models training on more than 20 times more clean data" (600M to 13B parameters, 6B to 260B tokens), and "Finally, we demonstrate the same dynamics for poisoning during fine-tuning."

**B4. Agent and tool-call poisoning (the closest relatives of SAFE-04).**
- Wang, Xue, Zhang, Qian (2024), "BadAgent", ACL 2024, arXiv:2406.03007: backdoor via fine-tuning data, trigger "in the agent input or environment"; "our proposed attack methods are extremely robust even after fine-tuning on trustworthy data." https://arxiv.org/abs/2406.03007
- Yang, Bi, Lin, Chen, Zhou, Sun (2024), "Watch Out for Your Agents!", NeurIPS 2024, arXiv:2402.11208: agent backdoors where "the backdoor trigger can either be hidden in the user query or appear in an intermediate observation returned by the external environment", on web shopping and tool utilization; "cannot be easily mitigated by current textual backdoor defense algorithms". https://arxiv.org/abs/2402.11208
- Boisvert et al. (2025/2026), "Malice in Agentland", arXiv:2510.05159: "poisoning only a small number of demonstrations is sufficient to embed a backdoor that causes an agent to leak confidential user information with over 80% success." https://arxiv.org/abs/2510.05159
- Pallakonda, Hindsbo, Ehsani, Mishra (2026), "SilentCall", arXiv:2609.32021: on tool-calling agents, "Under the trigger, it fires on at least 99.6% of requests"; a per-call runtime monitor "catches every instance of the payload we tested at a 1.73% false-positive rate"; "Alignment benchmarks, by contrast, do not separate poisoned from benign models." https://arxiv.org/abs/2609.32021
- Guo et al. (2026), "Backdoors in RLVR", ACL 2026, arXiv:2604.09748: "This attack can implant a backdoor without modifying the reward verifier by injecting a small amount of poisoning data into the training set", "less than 2% poisoned data". Nearest published case of a verifier that does not see the attack, but the payload is jailbreak compliance, not a value-consistent tool call. https://arxiv.org/abs/2604.09748
- Lu et al. (2026), "Firefly", arXiv:2605.17558: verified tool-call data from real MCP servers, "guaranteeing label correctness by construction"; no poisoning analysis in the abstract. This is the data-factory pattern our oracle belongs to. https://arxiv.org/abs/2605.17558

## C. Persistence of backdoors

**C1. Hubinger, Denison, Mu, Lambert, Tong, MacDiarmid, Lanham, Ziegler, Maxwell, Cheng, et al. (39 authors, 2024). "Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training." arXiv:2401.05566 (v3 2024-01-17); no venue listed on arXiv.**
URL: https://arxiv.org/abs/2401.05566
Claim: "such backdoor behavior can be made persistent, so that it is not removed by standard safety training techniques, including supervised fine-tuning, reinforcement learning, and adversarial training"; and "adversarial training can teach models to better recognize their backdoor triggers, effectively hiding the unsafe behavior." Relevance: SAFE-05 trains on injected-instruction episodes; this is the reason to hold out injection styles when scoring the defended model (section G).

## D. Attested or verifiable inference and receipt-style audit logs

**D1. Tsyrulnikov, B. (Cyntrisec). "Attested Inference Receipt (AIR): A COSE/CWT Profile for Confidential AI Inference." IETF Internet-Draft draft-tsyrulnikov-rats-attested-inference-receipt-02, 5 July 2026, individual submission, Informational, expires 6 January 2027 (not endorsed by the IETF).**
URL: https://datatracker.ietf.org/doc/draft-tsyrulnikov-rats-attested-inference-receipt/ (text saved in sources). We read "IETF AIR draft" as this document; a datatracker API name search for "attested-inference" returns only this draft (rev 02, 2026-07-05).
Claim: "An AIR receipt is Attester-signed Evidence, not an appraisal verdict: a RATS Verifier must appraise the referenced platform attestation before the receipt establishes TEE provenance." Scope: "AIR v1 targets single-inference receipts emitted by workloads running inside hardware-isolated Trusted Execution Environments (TEEs)"; AWS Nitro Enclaves and Intel TDX only; "Pipeline chaining, multi-inference receipts, composite attesters ... are out of scope." Section 10.2 mentions "a tool-call / tool-result log" only as a possible future profile. The text contains no discussion of prompt injection or poisoning (grep of the saved text: no "injection" or "poison").

**D2. Chueayen, A. (Aqta Technologies). "Enforcement Attestation Receipts for AI Inference Decisions." draft-chueayen-attestation-receipts-03, 20 September 2026, individual, Informational.**
URL: https://datatracker.ietf.org/doc/draft-chueayen-attestation-receipts/
Claim: "A receipt binds an outcome to a request hash under a published Ed25519 public key, so a party that does not trust the issuer's infrastructure can still verify offline what the issuer's signing key attested was decided." It is a format and verification algorithm; the text names a separate ACTION-v1 record for tool actions and defines no injection or poisoning evaluation.

**D3. Receipt, transcript and gateway-evidence work (2025-2026), none evaluated against injection or poisoning in its abstract:**
- Guan (2026), "AEX", arXiv:2603.14283: "adds a signed top-level attestation object that binds a client-visible request projection to either a complete response object or a committed streaming output"; "preserves request, response, tool-calling, streaming, and error semantics". https://arxiv.org/abs/2603.14283
- Basu (2026), "Tool Receipts, Not Zero-Knowledge Proofs" (NabaOS), arXiv:2603.10060: "HMAC-signed tool execution receipts that the LLM cannot forge"; "NabaOS detects 94.2% of fabricated tool references" on its own benchmark of injected hallucinations (synthetic fabrications, not prompt injection). https://arxiv.org/abs/2603.10060
- Figuera (2026), "Notarized Agents" (Sello), arXiv:2606.04193: "the service that receives an agent's call signs a receipt of what it observed using its own key ... and publishes it to a public transparency log". https://arxiv.org/abs/2606.04193
- Wang and Tian (2026), "Evidence-Bound Gateway-Path Provenance for Third-Party LLM Inference", arXiv:2606.22560: attested gateway runtime with "fail-closed detection of policy, routing, endpoint, and stream-evidence tampering outside the attested runtime" (a tamper-evidence claim in the sense of SAFE-01, not an injection claim). https://arxiv.org/abs/2606.22560
- Jin et al. (2026), "Proof-of-Guardrail in AI Agents and What (Not) to Trust from It", AI4GOOD Workshop at ICML'26, arXiv:2603.05786: "cryptographic proof that a response is generated after a specific open-source guardrail" via a TEE-signed attestation; it evaluates latency and cost and flags that a malicious developer could jailbreak the guardrail. https://arxiv.org/abs/2603.05786
- Liu and Yu (2026), arXiv:2608.30387: a signed output hash "records released bytes but does not prevent prompt injection." The clearest statement in the literature that a receipt is evidence, not containment. https://arxiv.org/abs/2608.30387
- Wang, Lou, Li, Yu, Hu (2026), "zkAgent", IACR ePrint 2026/199: a SNARK system that "further binds each tool observation to an authenticated execution via zkTLS or zkVM subproofs, yielding a single end-to-end proof"; proves a complete GPT-2 inference pipeline. https://eprint.iacr.org/2026/199

**D4. TPM/TEE-attested and verifiable LLM inference.**
- Sokolov (2026), "Hardware-rooted attestation for AI-agent evidence: composing IETF RATS with action evidence packages", arXiv:2608.00801 (technical note, 9 pages). The closest published relative of LAB-04: "on a software Trusted Platform Module (TPM; the swtpm emulator), an output-binding protocol folds the hash of an AEP outcome and a fresh appraiser nonce into an attestation-key-signed quote, with a model-artefact measurement carried in a platform register", resolving Attested / Contested (model measurement swapped) / Expired (stale quote); "The result is a feasibility demonstration on emulated hardware, not a hardware-rooted guarantee." Differences to LAB-04: that note quotes an agent-evidence package, not a bit-exact replayable logit-level inference receipt, and does not run the inference inside a measured no-OS image. https://arxiv.org/abs/2608.00801
- Chantasantitam, Caulfield, Duddu, Gunn, Asokan (2026), "PAL*M: Property Attestation for Large Generative Models", arXiv:2601.16199: confidential VMs with security-aware GPUs, "implement PAL*M on Intel TDX+NVIDIA H100", Tamarin model of the protocol. https://arxiv.org/abs/2601.16199
- Schnabl, Hugenroth, Marino, Beresford (2025), "Attestable Audits: Verifiable AI Safety Benchmarks Using Trusted Execution Environments", arXiv:2506.23706 (arXiv comment: "ICML 2024 Workshop TAIG"; arXiv date 2025-06-30, the year is inconsistent across sources, cite the arXiv id): TEEs "enable users to verify interaction with a compliant AI model". https://arxiv.org/abs/2506.23706
- Ong et al. (2025), "TOPLOC: A Locality Sensitive Hashing Scheme for Trustless Verifiable Inference", ICML 2025 (PMLR v267; venue taken from a search result, not opened), arXiv:2501.16007: "detect unauthorized modifications to models, prompts, or precision with 100% accuracy, achieving no false positives or negatives in our empirical evaluations". https://arxiv.org/abs/2501.16007
- Lim and Yong (2026), "Seal, Then Sample", arXiv:2609.27367: sampled layerwise proofs for verifiable inference; the authors state limits "guarantees cover proven chunks only". https://arxiv.org/abs/2609.27367
- Anthropic (2025-06-18), "Confidential Inference via Trusted Virtual Machines": a loader that "only accepts programs that have been signed by our secure continuous integration server", keys released only to a recipient that "has proven itself secure". No receipts, tool calls or injection tests. https://www.anthropic.com/research/confidential-inference-trusted-vms

## E. Honesty, abstention and calibration under pressure

**E1. Sharma, Tong, Korbak, Duvenaud, Askell, Bowman, Cheng, Durmus, Hatfield-Dodds, Johnston, Kravec, Maxwell, McCandlish, Ndousse, Rausch, Schiefer, Yan, Zhang, Perez (2024). "Towards Understanding Sycophancy in Language Models." ICLR 2024 (proceedings.iclr.cc paper page, seen in search results); arXiv:2310.13548 (v4 2025-05-10).**
URL: https://arxiv.org/abs/2310.13548
Claim: "five state-of-the-art AI assistants consistently exhibit sycophancy across four varied free-form text-generation tasks" and "when a response matches a user's views, it is more likely to be preferred." The source of sycophancy it identifies is preference data, which our 17M model has not been through (relevant to why H7 might hold).

**E2. Ren, Agarwal, Mazeika, Menghini, Vacareanu, Kenstler, Yang, Barrass, Gatti, Yin, Trevino, Geralnik, Khoja, Lee, Yue, Hendrycks (2025). "The MASK Benchmark: Disentangling Honesty From Accuracy in AI Systems." arXiv:2503.03750 (v3 2026-01-05; no peer-reviewed venue listed).**
URL: https://arxiv.org/abs/2503.03750
Claim: "while larger models obtain higher accuracy on our benchmark, they do not become more honest" and "most frontier LLMs obtain high scores on truthfulness benchmarks yet exhibit a substantial propensity to lie under pressure". Caveat: MASK's pressure is a system prompt that pushes the model to state something contrary to its belief; our SAFE-03 pressure is user-turn framing on questions with no knowable answer, so the construct differs.

**E3. Kalai, Nachum, Vempala, Zhang (2025). "Why Language Models Hallucinate." arXiv:2509.04664 (2025-09-04; no venue listed).** https://arxiv.org/abs/2509.04664
Claim: "language models hallucinate because the training and evaluation procedures reward guessing over acknowledging uncertainty". Predicts that a model trained on abstention episodes (ours, LAB-08) can abstain where web-trained models guess.

**E4. Kirichenko, Ibrahim, Chaudhuri, Bell (2025). "AbstentionBench: Reasoning LLMs Fail on Unanswerable Questions." arXiv:2506.09038 (2025-06-10).** https://arxiv.org/abs/2506.09038
Claim: "abstention is an unsolved problem, and one where scaling models is of little use"; "reasoning fine-tuning degrades abstention (by 24% on average)"; "a carefully crafted system prompt can boost abstention in practice". Survey: Wen et al., "Know Your Limits: A Survey of Abstention in Large Language Models", TACL 2024, arXiv:2407.18418, https://arxiv.org/abs/2407.18418.

**E5. 2026 pressure work (direction and shape of the effect).**
- Tang, Wei, Jiang, Huang (2026), "Measuring LLM Sycophancy under Sustained Multi-Turn Pressure" (SPINE), arXiv:2609.09090: "collapse rates increase with conversation length for every model"; "the correct position often remains represented in a reasoning trace when the response concedes". SAFE-03 is single-turn, so it will not see this effect. https://arxiv.org/abs/2609.09090
- Jiang et al. (2026), Ghost-100, arXiv:2604.18803 (vision-language models, nine open-weight): "several models exhibit non-monotonic sensitivity peaking at intermediate tone levels". Closest published test of whether fabrication rises with graded pressure; the answer is not uniformly yes, which matters for H8 (direction only). https://arxiv.org/abs/2604.18803

---

## F. Does anything test injection through a receipt-gated tool gateway, or poisoning of oracle-verified tool-call data?

Short answer: not as a combination, and not at our scale, but several papers are close enough that a "first" claim must be worded narrowly.

### F1. Injection through a receipt-gated gateway: nothing found that measures it
What we mean: a gateway that executes only what the model's own decoded text asks for, under a fixed grammar, with each decode bound to a replayable witness receipt, and a count of how many injected runs still verify.

How searched: arXiv API queries Q01-Q04, Q08, Q13 (`arxiv_gap_queries.out.txt`): `"prompt injection" AND receipt` gave 2 hits, `"prompt injection" AND (signed receipt OR tool receipt ...)` gave 0, `"prompt injection" AND gateway AND "tool call"` gave 3, `attested AND inference AND receipt` gave 1 (AEX, section D3), `"prompt injection" AND attestation AND tool` gave 10; I fetched and read the abstract of every hit returned by Q01, Q02, Q03 and Q08 (16 papers; all in `arxiv_abstracts.json`). For Q05 (4 hits) and Q10 (1 hit) relevance was judged from titles only. Extended WebSearch: "prompt injection evaluation attested tool gateway signed tool-call receipts agent LLM verifiable execution log injected tool result".

Nearest, with why each is not it:
- Errico (2026), "AARM", arXiv:2602.09433: a specification of a runtime that "intercepts actions before execution ... enforces authorization decisions, and records tamper-evident receipts", with a threat model that names prompt injection, and a "protocol gateway" architecture. The abstract reports no measurements. https://arxiv.org/abs/2602.09433
- Sambrook and Sovio (2026), "Hardware Keystores for AI Agent Signing Workflows", arXiv:2608.06130 (v2): TPM-held keys behind a five-layer enforcement stack; "Prompt injection in content the agent reads (AgentDojo, three injection-following models, n=144) falls from an 18.1% baseline attack success rate to 0% under the full stack." This is the closest measured combination of a TPM and injection, but the TPM protects a signing key and the model is a hosted-class chat LLM; it is not per-decode witness receipts. https://arxiv.org/abs/2608.06130
- Liu and Yu (2026), arXiv:2608.30387: states the limit outright (signature "does not prevent prompt injection") and evaluates attestation verification, not injection rates. https://arxiv.org/abs/2608.30387
- Kravchenko et al. (2026), APPA, arXiv:2607.24625: reference monitor "at tool dispatch and protocol gateways (e.g., Model Context Protocol)", "zero observed attacks across 1,320 guarded episodes", and an "attest-schema" channel; the attestation there is a schema-bounded exit channel, not a signed inference receipt. https://arxiv.org/abs/2607.24625
- Iyer and Babu (2026), "ContractGuard", arXiv:2606.18550: "signed provenance, typed contract attestation, and runtime effect verification" for tool contracts, injection success restored to zero on a controlled benchmark with six hosted models. https://arxiv.org/abs/2606.18550
- Pandey et al. (2026), arXiv:2609.34245: certified multi-source integrity of structured actions under injection; "naive attestation counting overstates" corroboration. https://arxiv.org/abs/2609.34245
- Maloyan and Namiot (2026), "Breaking the Protocol", arXiv:2601.17549: MCPSec, "a backward-compatible protocol extension adding capability attestation and message authentication, reducing attack success rates from 52.8% to 12.4%" over 847 attack scenarios. The nearest measured case of an attested tool protocol under injection; the attestation is of server capabilities and messages, the models are hosted-class, and there is no per-decode inference receipt. The same author's thesis (arXiv:2610.02432, 2026-10-01) reports "AttestMCP, which attests tool calls with HMAC-protected packets" and a drop in average ASR "from 53.7% to 12.4%" on the same 847 scenarios (note 52.8% vs 53.7%). https://arxiv.org/abs/2601.17549 , https://arxiv.org/abs/2610.02432
- Bicakci (2026), arXiv:2604.25200: TEE-attested evaluation bundle for LLM grant evaluation that "also considers a scenario-specific prompt injection risk" and adds a sanitization layer; the abstract states a design, not an injection rate. https://arxiv.org/abs/2604.25200
- Hou and Hou (2026), SAVOR, arXiv:2608.08795: an injection attack paper whose OpenClaw-IPI benchmark "verifies attacks through tool interactions and execution receipts"; the receipts there are scoring ground truth for the attack, not signed evidence about the model. https://arxiv.org/abs/2608.08795
- Survey, "When Agents Handle Secrets: A Survey of Confidential Computing for Agentic AI", arXiv:2605.03213 (2026): lists "compound attestation for multi-hop" agents among open challenges, i.e. the combination is acknowledged as open. https://arxiv.org/abs/2605.03213
- Gateway checks with no receipts: Device Context Protocol (arXiv:2605.26159, HMAC frames plus a host-side Bridge that "rejects 100% of capability-escalation attempts and 78% of prompt-injection attempts" on 675 tool calls from five hosted LLMs); SafeClawArena (arXiv:2606.30755, 406 tasks, highest attack success rate 70%).
- Wang et al. (2026), ActGuard, arXiv:2609.14987, and Lin et al. (2026), VIGIL, arXiv:2601.05755 (959-case SIREN benchmark): pre-execution action auditing, no receipts.
- Wang and Tian (2026), arXiv:2606.22560 (section D3): attested gateway, but the evidence is about routing and stream integrity.
- Louck, Dvir, Stulman (2026), "Signing the Transaction but Not the Decision", arXiv:2609.11757: shows a valid signature on a purchase says nothing about whether product text steered the decision: "the three attacks succeeded at rates of 90%, 56%, and 73.3%" on Gemini Flash-Lite agents with cryptographically valid carts. https://arxiv.org/abs/2609.11757 It is the strongest published argument that a signature or receipt is not containment, which is the point SAFE-02 tests from the other side (the receipt makes the miss legible; the gateway makes it harmless).

Not found anywhere in what was searched: (i) injection rates for sub-100M or ternary models, (ii) injection scored on a gateway whose executed calls are re-derived from a replayable receipt, (iii) any count of "receipts verified" on injected runs. LogJack, NetInjectBench, InjecAgent, MCPSec and DCP all use 7B-or-larger instruction-tuned or hosted models.

### F2. Poisoning of oracle-verified tool-call data: nothing found that measures it
What we mean: poison episodes whose tool value is computed correctly (so a value oracle in the data factory passes them) but whose call does not match the question, plus a question-consistency checker that does.

How searched: arXiv API Q05 (`poisoning AND "tool call" AND (oracle OR verifier OR "execution-verified")`: 4 hits, none relevant judging by title: pipeline poisoning, RAG salience, MCP workbench, a sandbox benchmark), Q06 (`backdoor AND "tool-call" AND synthetic AND verified`: 0), Q07 (`poisoning AND synthetic AND "consistency check" AND tool`: 0); extended WebSearch "backdoor poisoning function-calling tool-use fine-tuning data verified by execution oracle synthetic tool-call dataset poisoned trigger" and "poisoning verifiable synthetic training data passes verifier unit tests execution-verified backdoor rejection sampling RLVR data poisoning".

Nearest: the RLVR backdoor (B4) where the verifier is untouched but blind to the payload; Malice in Agentland and BadAgent (B4) where a small number of poisoned demonstrations implants trigger-conditioned tool misuse; SilentCall (B4), where the detector that works is a per-call runtime monitor, i.e. a consistency check at the call, not a value check. Firefly (B4) is the verified-tool-data pipeline whose guarantee is label correctness, with no discussion of an attacker. None of these poisons episodes that satisfy a value oracle and then compares a value oracle with a question-consistency checker, so H10 is untested in the literature as far as this search reaches, but note that it is close to a restatement of "execution verification is a quality gate, not a security check", which none of the sources states as such (that sentence is our inference).

### F3. Wording we can defend
Do not write "first to study injection with receipts" or "first to study poisoning of verified tool data". Defensible: "to our knowledge, no prior work reports injection or trigger-poisoning rates for a sub-100M ternary tool-calling model through a gateway whose every decode has a replay-verifiable receipt" (searches dated 2026-10-08, arXiv phrase queries plus web search, limits above).

---

## G. What this changes for the pre-registration (positioning notes; our reading, not claims from the sources)

None of these edit the binding LAB-09 hypotheses or metrics. They are cautions on how to describe and score results.

1. SAFE-02 / H5: the 10% red-flag line sits inside the published range for prompted agents (InjecAgent Table 3: 3.4% to 86.9% base; GPT-4 24%/47%; fine-tuned GPT-4 6.6%/7.1%). Our metric (a call echoed from the table and executed in step 1) is not InjecAgent's (next action is the attacker's tool), so do not set the two side by side as like for like. H4 is the design property CaMeL, ROPE and the NetInjectBench gate already have; report it as a check of that property, not as a finding.
2. SAFE-02 / adaptivity: A6 shows adaptive attackers bypass defenses that looked near-zero against fixed strings, and A5 shows repeated attempts succeed against nearly all agents; fixed injection strings understate the attack. Six fixed styles measure non-adaptive compliance only; say so next to every rate.
3. SAFE-04 / H9: report the absolute number of poisoned episodes at p = 1% and 5% next to the percentages (Wan: 100 examples; Xu: 32-77 instances at 1%; Souly: 250 documents regardless of size). Wan reports that poisoning leaves clean accuracy unchanged and that label-correct (clean-label) poison is weaker (55.6% vs 92.8% at 100 samples); our poison is label-correct by construction at the value level, so a lower attack success rate than a dirty-label attack would be unsurprising.
4. SAFE-05 / H11: Hubinger et al. report adversarial training can teach a model to recognise its trigger instead of dropping the behaviour. Score the defended model on injection styles held out from its training mix, otherwise "falls by half" may mean "learned the six strings". Xu et al. report clean demonstrations only mitigate "to some degree".
5. SAFE-03 / H7-H8: MASK pressure is system-prompt pressure toward lying and SPINE pressure is multi-turn; ours is single-turn user framing, so cite them as motivation, not as predictions. Ghost-100's non-monotonic result is a reason to treat H8 (the 2B invents more under pressure and permission framings than plain) as a direction to test per framing rather than as a trend. Kalai et al. and AbstentionBench support the expectation that a model trained with abstention episodes (op12k) abstains where web-trained models guess, which is a hypothesis about training data, not about size.
6. SAFE-01: AIR (D1) and Sokolov (D4) are the two documents to compare against for the ATTEST.TXT/quote checks. Both are single-inference or emulated-TPM scope; LAB-04's differences are a bit-exact replayable receipt and a measured no-OS image.

## Unverified (seen only in search snippets; do not cite without opening)

- Silent Sabotage (ServiceNow/Mila; ICML 2025 Workshop on Computer Use Agents): the "5% of collected traces" figure came from a search summary of an OpenReview PDF; Malice in Agentland (B4, verified) is the arXiv paper with overlapping authors and was used instead.
- IETF draft-xkumakichi-xaip-receipts-03 (signed receipts for agent tool calls): seen as a search result only.
- Pipelock (open-source agent firewall with signed action receipts): a GitHub project; repository metadata could not be fetched.
- The USPTO publication "Pre-inference execution compliance for artificial intelligence systems" and the vendor/blog items on confidential inference: not read.
- Venue details taken from search results and not from the paper page: Xu et al. NAACL pages 3111-3126, Wan et al. PMLR page range, TOPLOC at ICML 2025 (PMLR v267), Sharma et al. at ICLR 2024 (the arXiv page itself lists no venue).
