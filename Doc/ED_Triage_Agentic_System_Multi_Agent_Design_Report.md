# Multi-Agent System Design Report

**Project:** Agentic AI Triage System for Emergency Departments (Proposal Draft v0.1, July 2026)
**Scope of this report:** agent architecture, harness design, and multi-model selection for FinOps
**Date:** September 17, 2026

---

## 1. Summary of findings

The proposal's core safety ideas are sound: deterministic rule floors the LLM cannot lower, citations that must resolve to retrieved evidence, a clinician who always decides, and shadow mode before any live use. This report keeps all of them and tightens the design around three positions.

**1. Build a workflow with two or three LLM nodes, not six agents under an LLM supervisor.** The triage task decomposes the same way for every patient, so there is nothing for a supervisor LLM to plan. Of the six agents in Section 4.2, only the Triage Reasoning Agent and part of the Critic need a language model. Intake, structured history fetch, risk rules, and audit writing are deterministic code. Implementing them as LLM agents adds latency, cost, non-determinism, and PHI exposure while making the audit trail harder to defend. Keep the "agent" vocabulary for stakeholders if it helps, but implement a coded state machine with bounded LLM calls.

**2. The harness is the product; the model is a replaceable part.** Models will be deprecated and replaced several times over the life of this system. What persists is the context assembly, tool contracts, evidence registry, guardrails, audit trace, and evaluation replay. Most of the engineering effort and most of the clinical-safety argument live there.

**3. Live inference is cheap; evaluation and self-hosting are where the money goes.** At a 60,000-visit ED, running every LLM step on a top-tier model costs roughly $7,600 a year. A tiered design costs roughly $2,600. Neither number matters next to one nursing FTE. The costs that do matter are repeated retrospective replays (a single 24-month replay on a top-tier model is about $15,000, and you will run dozens), clinician time for review, and GPU capacity if the site requires self-hosting. Model tiering is justified mainly by latency, replay cost, and multi-site scale, not by single-site inference savings.

---

## 2. Multi-agent architecture

### 2.1 Orchestration pattern

Replace "a supervisor agent decomposes the triage task" with an event-driven, deterministic orchestrator. An ADT registration event (A04/A01) opens a case. The orchestrator runs a fixed graph, fans out the independent steps in parallel, and enforces timeouts, budgets, and fallbacks. New ORU results can reopen a case through a gate (Section 4.5).

```
HL7 ADT / FHIR event
        |
        v
+-----------------------------------------------------------------+
|  ORCHESTRATOR (deterministic state machine, no LLM)             |
|                                                                 |
|   [1] Intake & normalize (code)                                 |
|         |                                                       |
|         +--> [2a] Complaint normalizer (small LLM)              |
|         +--> [2b] Structured history fetch (code, by patient ID)|
|         +--> [2c] Risk rules & floors (code)  ---> provisional  |
|         |                                          card < 2 s   |
|         v                                                       |
|   [3] History condenser (small LLM) + guideline retrieval       |
|         |                                                       |
|         v                                                       |
|   [4] Triage reasoner (mid LLM) ----+                           |
|         |                           |  escalation router (code) |
|         |                           +--> [4b] top-tier re-read  |
|         v                                                       |
|   [5] Verifier: schema -> citations -> floor (code)             |
|                 -> entailment check (small/mid LLM)             |
|         |                                                       |
|         v                                                       |
|   [6] Present & audit (code) --> nurse accept / override        |
+-----------------------------------------------------------------+
        |                                   |
   Evidence registry                 Immutable audit store
```

Why not a dynamic supervisor: a fixed graph gives predictable latency, makes every run comparable in replay, produces an audit trace with the same shape every time, and removes an entire class of failures (supervisor skips the rules step, loops, or calls tools in the wrong order). Dynamic tool use is worth allowing in exactly one place: the reasoner may request one additional, harness-scoped retrieval ("prior encounters mentioning syncope") when the default context is insufficient, capped at one or two calls.

### 2.2 Shared state: the case object and evidence registry

All components read and write a typed, versioned `TriageCase` object rather than passing free text to each other. The most important part is the **evidence registry**: every fact that enters an LLM context gets an ID (`E-014`) and a pointer to its source, such as the HL7 message control ID and segment, the FHIR resource ID and version, or the guideline document and clause.

The reasoner is only allowed to cite evidence IDs. It never writes a lab value or a guideline quote from memory into the citation field. That makes "citations must resolve" a property of the schema rather than something the critic has to discover, and it lets the UI link each factor straight to the source result.

### 2.3 Component roster

| # | Component | Implementation | Input | Output | Failure fallback |
|---|---|---|---|---|---|
| 1 | Intake & normalization | Code (interface engine, terminology mapping) | HL7 v2 / FHIR events | Canonical patient-event, vitals, raw complaint | Queue and retry; case stays open |
| 2a | Complaint normalizer | Small LLM, constrained to the complaint code list (CEDIS for CTAS sites) | Free-text chief complaint | Coded complaint + extracted modifiers (onset, severity, mechanism) | Pass raw text through; flag "uncoded" |
| 2b | Structured history fetch | Code, deterministic queries by patient ID | Patient ID (supplied by harness) | Problem list, meds, allergies, last N encounters, recent abnormal results | Proceed with "history unavailable" banner |
| 2c | Risk rules & floors | Code, versioned rule set owned by clinical leads | Vitals, coded complaint, meds, age | Red flags, acuity floor, rule IDs fired | None needed; this is the fallback for everything else |
| 3 | History condenser | Small LLM | Structured history + complaint | Relevance-ranked history items, each an evidence ID | Send top-N most recent items unranked |
| 3b | Guideline retrieval | Hybrid search + reranker (no generative LLM) | Coded complaint, modifiers, flags | Guideline clauses as evidence IDs | Static per-complaint clause bundle |
| 4 | Triage reasoner | Mid-tier LLM, structured output | Complaint, vitals, flags, floor, evidence | Level, ranked factors with evidence IDs, matched criteria, uncertainty | Rules-only card |
| 4b | Escalated re-read | Top-tier LLM, triggered by router | Same context + reasoner output hidden or shown by policy | Second opinion | Skip; flag for nurse attention |
| 5 | Verifier | Code checks first, then small/mid LLM entailment | Reasoner output + evidence registry | Pass / revise / reject with reasons | Reject leads to rules-only card |
| 6 | Presentation & audit | Code, templates | Verified recommendation | Dashboard card, audit record, override capture | N/A |

### 2.4 Decision policy and asymmetric safety

The cost of under-triage is far higher than the cost of over-triage, so every tie-break should resolve toward higher acuity.

- The final level is the more acute of the rule floor and the verified LLM level. The LLM can raise acuity above the floor freely and can never go below it.
- When the reasoner and the escalated re-read disagree, present the more acute level and show the disagreement to the nurse.
- The verifier gets at most one "revise" cycle. A second failure produces the rules-only card. Unbounded reasoner-critic loops are a latency and cost hazard.

### 2.5 Escalation router

Do not route on the model's self-reported confidence; LLM confidence statements are poorly calibrated. Use observable signals instead:

- Proposed level sits on the CTAS II/III or ESI 2/3 boundary, where the clinical consequences of a miss are largest.
- High-risk cohort flags: age 65 or over, anticoagulants, beta-blockers with borderline vitals, immunosuppression, pregnancy, recent discharge or 72-hour return.
- Verifier raised an entailment concern that one revision did not clear.
- Proposed level equals the floor only because of the floor (the LLM wanted lower).
- Optional: disagreement across two or three low-cost samples of the reasoner in the mid-acuity band.

Expect 10 to 20 percent of cases to escalate. Track the rate; if it climbs, the router thresholds or the reasoner prompt have drifted.

### 2.6 Verifier independence

The proposal says the critic verifies "independently." Make that concrete, because a critic that shares the reasoner's blind spots gives false assurance.

- Run the deterministic checks first: schema validity, every evidence ID exists in the registry, level is at or above the floor, every matched guideline criterion maps to a retrieved clause. These catch most faults for free.
- The LLM entailment step sees only claim-evidence pairs ("does E-014 support the statement 'INR supratherapeutic'?"), never the reasoner's chain of thought. Small, atomic judgments are where smaller models are reliable.
- Decide deliberately whether the verifier uses a different model family. It reduces correlated error but adds a second vendor agreement and BAA. A same-vendor, different-tier verifier with a narrow task is a reasonable Phase 1 compromise.
- Measure the verifier with fault injection (Section 3.8). An unmeasured critic is a risk-register entry, not a mitigation.

### 2.7 Progressive results and degraded modes

The rules engine finishes in well under two seconds. Show its output immediately as a provisional card ("Floor: CTAS II, anticoagulant + head injury") and upgrade the card when the LLM path completes. The nurse is never waiting on a model, and if the LLM endpoint is slow or down, the system degrades to a clearly labelled rules-only mode instead of failing. Proposed latency budget against the 60-second target: intake and parallel fetch 3 s, condenser and retrieval 5 s, reasoner 15 s, verifier 5 s, escalation (when triggered) 20 s.

### 2.8 Automation bias

The proposal lists rationale-first UI and override monitoring. Consider one more option for the assisted pilot: the nurse records an initial impression before the recommendation is revealed, at least for a sampled subset. This gives a clean measure of how often the system changes decisions and in which direction, which both the safety case and the regulatory assessment will want.

---

## 3. Harness design

"Harness" here means everything that surrounds the model calls: control flow, context assembly, tool contracts, output constraints, guardrails, budgets, observability, and evaluation.

### 3.1 Control flow

Model the case as an explicit state machine: `RECEIVED → CONTEXT_READY → FLOORED → REASONED → VERIFIED → PRESENTED → RESOLVED`, with side states `DEGRADED` and `REOPENED`. Persist every transition. Any durable workflow engine or a graph framework works; the requirement is that transitions, retries, and timeouts are defined in code and logged, not decided by a model.

### 3.2 Context engineering

- **Per-node allow-lists.** PHI minimization (proposal Section 6) is enforced by the harness, not by prompt instructions. Each LLM node has a declared list of fields it may receive. The complaint normalizer sees the complaint text and age band, not the name, MRN, or history.
- **Prompt layout for caching.** Order every prompt from most static to most dynamic: system instructions, triage scale criteria, output schema, and worked examples first; site protocols next; patient context last. This maximises the cacheable prefix.
- **Untrusted text.** Referral letters, prior notes, and HL7 NTE free text are data, not instructions. Delimit them clearly, tell the model they may contain irrelevant or instruction-like content, and give LLM nodes no write-capable tools so that an injected instruction has nothing to act on.
- **Context budgets.** Cap history items and guideline clauses per case. A patient with 200 prior encounters should not produce a 60,000-token prompt; the condenser exists to prevent that.

### 3.3 Tool contracts

All tools exposed to LLM nodes are read-only and typed. The patient ID and the clinician's role scope are injected by the harness from the case object and are never parameters the model can set. This is what actually guarantees "no cross-patient leakage"; a filter the model is asked to respect does not.

### 3.4 Structured output

Use schema-constrained output for every LLM node: enumerated acuity level, array of factors each with evidence IDs, matched criterion IDs, and a free-text uncertainty statement. Allow one automatic repair attempt on schema failure, then fall back. Keep the nurse-facing prose generated from the structured object by template where possible, so the text cannot diverge from the verified structure.

### 3.5 Guardrail layers

| Layer | Examples |
|---|---|
| Input | Vitals plausibility (HR 700 is a device error), missing-data flags, patient identity match between ADT and FHIR |
| In-flight | Rule floors, high-risk cohort flags, context allow-lists |
| Output | Schema, citation resolution, floor check, entailment check |
| Presentation | Provisional vs. verified labelling, degraded-mode banner, low-friction override with reason capture |

### 3.6 Reproducibility

Pin dated model snapshots, never floating aliases. Version prompts, rule sets, the guideline corpus, and retrieval configuration in source control, and write a single configuration hash into every audit record. Store the assembled inputs so any case can be re-run exactly. For a system subject to incident review, "what did the system see and which version decided" must be answerable years later.

### 3.7 Budgets and observability

Each case has caps on total tokens, LLM calls, wall-clock time, and revision cycles. Emit one trace per case with a span per node, tagged with site, node, model, prompt version, token counts, cache hits, and cost. Traces contain PHI, so the trace store lives inside the trust boundary with the same retention and access rules as the audit store. These tags are also the foundation for cost attribution in Section 4.

### 3.8 Evaluation harness

The proposal's Section 7 defines end-to-end metrics. Add per-node metrics, because an end-to-end number cannot tell you which component regressed.

| Node | Metric |
|---|---|
| Complaint normalizer | Coding accuracy against nurse-selected complaint codes |
| History condenser | Recall of clinician-marked relevant items |
| Guideline retrieval | Recall@k of the applicable clause |
| Reasoner | Under-triage rate on outcome-defined high-risk cases (primary), over-triage rate, weighted kappa |
| Verifier | Catch rate on seeded faults: fabricated evidence IDs, claims that contradict their evidence, levels below floor |
| End to end | Latency percentiles, degraded-mode rate, escalation rate, cost per encounter |

Run the harness at three scales: a small golden set of a few hundred clinician-adjudicated cases on every change; a stratified sample of roughly 5,000 encounters, over-weighted toward high-acuity and high-risk outcomes, for iteration; and the full 12 to 24 month replay only at release gates. A model or prompt change ships only if under-triage is non-inferior on the full replay. Vendor model deprecations will force this process periodically, so budget for it as a recurring cost.

### 3.9 Model gateway

Put a gateway between the orchestrator and all model endpoints. It owns the routing policy (node to model), the allow-list of BAA-covered, zero-retention endpoints, regional pinning (relevant for PHIPA sites), rate limits, fallbacks, and cost metering. With the gateway in place, moving a node from a frontier API to a self-hosted model is a configuration change followed by a replay, not a rewrite. This is what keeps the proposal's Section 5 decision reversible.

---

## 4. Multi-model selection for FinOps

### 4.1 Principles

1. Route by task difficulty and clinical risk. Spend model capability where an error becomes an under-triage.
2. Use no LLM where code suffices. The cheapest and most auditable token is the one never generated.
3. Track unit economics: cost per triaged encounter, and cost per full replay. Keep live and offline budgets separate.
4. Do not trade safety for cents. At single-site volume the absolute savings from a cheaper reasoner are small; take them only if replay shows non-inferiority.

### 4.2 Model tiers and assignment

The tiers are vendor-neutral. Anthropic's current lineup is used as the worked example; the same structure maps to the equivalent small, mid, and flagship models from OpenAI and Google, or to self-hosted open-weight models of roughly 8B, 30 to 70B, and largest-available size.

| Tier | Example (list price per 1M tokens, input / output) | Assigned nodes | Rationale |
|---|---|---|---|
| R: rules | Code, $0 | Intake, history fetch, risk floors, deterministic verification, audit | Deterministic, instantly available, fully auditable |
| S: small | Claude Haiku 4.5 ($1 / $5) | Complaint normalizer, history condenser, entailment checks | Narrow, high-volume, latency-sensitive; easy to evaluate; first candidates for distillation |
| M: mid | Claude Sonnet 5 ($2 / $10, see note) | Triage reasoner (default) | Multi-factor reasoning over guideline modifiers with structured output |
| L: large | Claude Opus 5 ($5 / $25) | Escalated re-read (10 to 20% of cases) | Hardest and highest-consequence cases only |
| Offline top tier | Highest available tier (for Anthropic, $10 / $50) | Adjudicating disagreement sets, drafting labels for distillation, rubric-based rationale grading | Batch-only; never in the live path |

Pricing note: these are rates as publicly reported in September 2026. Reports on Sonnet 5 conflict ($2/$10 in most sources, $3/$15 in at least one), so confirm against the vendor's pricing page and your enterprise agreement before budgeting. Newer tokenizers can also produce noticeably more tokens for the same text, so measure tokens on real prompts rather than estimating from word counts.

### 4.3 Cost model

Planning assumptions: 60,000 ED visits per year (about 165 per day); token counts per node as below; reasoning tokens billed as output; 15% escalation rate; 0.3 LLM re-triage runs per encounter after the debounce gate. Replace these with measured values in Phase 1.

| Node | Model | Fresh input | Cached input | Output | Cost per call |
|---|---|---|---|---|---|
| Complaint normalizer | Haiku 4.5 | 600 | 0 | 150 | $0.0014 |
| History condenser | Haiku 4.5 | 6,000 | 0 | 500 | $0.0085 |
| Retrieval query shaping | Haiku 4.5 | 400 | 0 | 100 | $0.0009 |
| Triage reasoner | Sonnet 5 | 2,500 | 2,500 | 900 | $0.0145 |
| Entailment verifier | Haiku 4.5 | 2,000 | 1,500 | 300 | $0.0037 |
| Escalated re-read | Opus 5 | 3,500 | 2,500 | 1,500 | $0.0563 (x 15% = $0.0084) |

| Scenario | Cost per encounter | Annual, one site |
|---|---|---|
| A. Every LLM step on Opus 5, no caching | $0.126 | about $7,600 |
| B. Tiered, with prompt caching | $0.037 | about $2,200 |
| B plus re-triage runs | $0.043 | about $2,600 |
| B without any cache hits | $0.045 | about $2,700 |

Two observations. First, the entire live LLM bill is a rounding error in an ED budget under either scenario, so the choice of reasoner tier should be made on replay results and latency, not price. Second, caching contributes little at this volume. With one arrival every several minutes, a short cache lifetime will mostly miss; a longer cache lifetime costs more to write. Caching pays off in replay and at multi-site scale, not at a single ED's live traffic. Check the vendor's current cache lifetimes, write surcharges, and minimum cacheable prompt lengths.

### 4.4 Where the money actually goes

**Evaluation replays.** A full 24-month replay is about 120,000 encounters.

| Replay configuration | Cost per full replay | 30 replays during development |
|---|---|---|
| All Opus 5, synchronous | about $15,150 | about $455,000 |
| All Opus 5, batch API (50% off) | about $7,600 | about $227,000 |
| Tiered, batch API | about $2,240 | about $67,000 |
| Tiered, batch, 5,000-case stratified sample | about $95 | about $2,800 |

Controls, in order of impact: iterate on the stratified sample and reserve full replays for release gates; use batch pricing for every offline run; and cache node outputs keyed by input hash, prompt version, and model version, so that changing the reasoner prompt does not re-run the normalizer and condenser across 120,000 cases.

**Clinician review time.** Adjudicating 500 golden-set cases at three minutes each is 25 clinician hours, per reviewer, before any double-review. This will exceed the token bill. Spend it on the disagreement set (system vs. nurse vs. outcome), not on random samples.

**Self-hosting.** The proposal describes self-hosted open-weight models as "predictable cost at volume." That holds only at volume. Taking $50,000 to $100,000 per year as an illustrative all-in cost for a redundant GPU serving node plus operations (an assumption to be replaced with a real quote), break-even against the tiered API design is on the order of 1.2 to 2.3 million encounters per year, roughly 20 to 40 EDs of this size. At a single site, self-hosting is 20 to 40 times more expensive per encounter. It can still be the right choice when the privacy office requires that PHI never leave the network, or when the same GPUs also serve the documentation and RCM use cases the proposal mentions. It should be presented to stakeholders as a policy-driven cost, not a saving. A hybrid is also worth considering: self-host the small-tier nodes that see the most raw PHI, and send a minimized, structured context to a frontier reasoner under BAA.

**Secondary items.** Embedding and reranking for the guideline index (small, mostly one-off), vector store and trace storage, long-term audit retention of full prompts, and retries. None is large, but all belong in the cost-per-encounter figure.

### 4.5 Runtime cost controls

- **Re-triage debounce.** A patient with a 40-result lab panel must not trigger 40 reasoning runs. New ORU results go to the rules engine first; the LLM path reopens only when a result crosses a significance threshold or changes the floor, with a minimum interval per case.
- **Per-case and per-day budgets** enforced at the gateway, with anomaly alerts on cost per encounter, escalation rate, revision rate, and output tokens per call. A jump in any of these usually signals a prompt or upstream data change before it shows up in clinical metrics.
- **Cost attribution** by site, node, model, and prompt version from the trace tags, reported alongside the clinical metrics.

### 4.6 Phase 3 path: distillation

The audit store accumulates exactly the data needed to reduce cost later: inputs, tiered outputs, top-tier second opinions, nurse overrides with reasons, and outcomes. Subject to REB/IRB approval, distil in order of risk. Start with the complaint normalizer and history condenser, which are narrow and easy to validate, then the entailment verifier. Move the reasoner last, and keep the large-tier escalation path in place as a safety net for the distilled model. Each substitution goes through the same replay gate as any other model change.

---

## 5. Design risks specific to the multi-agent approach

| Risk | Effect | Mitigation |
|---|---|---|
| Error propagation between nodes | A wrong complaint code skews retrieval, reasoning, and verification together | Pass the raw complaint alongside the coded one; per-node metrics; verifier checks the code against the text |
| Correlated reasoner and verifier failure | False assurance from a critic with the same blind spots | Deterministic checks first; atomic entailment judgments; fault-injection testing; consider a second model family |
| Latency creep | Misses the 60-second target as nodes are added | Fixed graph, parallel fan-out, per-node timeouts, provisional rules card |
| Agent sprawl | More LLM nodes, more prompts to maintain, larger PHI surface | A node uses an LLM only if code cannot do the job; each node needs its own metric to exist |
| Silent model drift | Behaviour changes on vendor update | Pinned snapshots, configuration hash in audit record, replay gate before any swap |
| Vendor dependence | Pricing or terms change | Model gateway, vendor-neutral schemas, periodic replay of an alternate model to keep the option warm |

---

## 6. Recommended changes to the proposal

1. Rewrite Section 4.2 so that the orchestrator, intake, structured history fetch, risk rules, and audit steps are described as deterministic services, with LLMs named only where they are used.
2. Add the evidence registry and the "cite by ID only" rule to Section 4.3.
3. Add an escalation router and the asymmetric tie-break policy.
4. Add a harness section covering the state machine, context allow-lists, harness-injected patient scope, budgets, tracing, and the model gateway.
5. Extend Section 7 with per-node metrics, verifier fault injection, the three-scale replay approach, and the non-inferiority release gate.
6. Extend Section 5 with the tier table, a cost-per-encounter model, the replay cost analysis, and an honest self-hosting break-even.
7. Add re-triage debounce to the architecture and the risk table.

## 7. Decisions to take into the first working session

- Deployment stance per node (frontier API, self-hosted, or hybrid), since it sets the cost baseline.
- Whether the verifier uses a second model family.
- Who owns the rule set and its change control.
- Whether the pilot records the nurse's initial impression before reveal.
- Measured token counts and arrival patterns from a sample of real encounters, to replace the planning assumptions in Section 4.3.
