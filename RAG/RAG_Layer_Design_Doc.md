# Design Doc: Retrieval (RAG) Layer — Agentic AI Triage System for Emergency Departments

**Component:** Layer 2 of 4 (Data Integration → **Retrieval** → Agent Orchestration → Presentation & Audit)<br>
**Parent document:** *Agentic AI Triage System for Emergency Departments — Project Proposal, Draft v0.1* <br>
**Status:** Draft v0.1 — For Discussion <br>
**Date:** September 2026 <br>

---

## 1. Purpose and Scope

The retrieval layer is what grounds the Triage Reasoning Agent in the hospital's own data instead of the model's parametric memory. It has two jobs that are deliberately kept separate:

1. **Patient-context retrieval** — deterministically assemble *this patient's* relevant history from normalized HL7/FHIR data.
2. **Knowledge retrieval** — find the triage criteria, guideline passages, and local protocols that apply to *this presentation*.

Everything the LLM cites must resolve to an object returned by this layer. That property is what makes the Critic/Verification Agent's hallucination check possible, so the retrieval layer is designed around **citability** as a first-class requirement, not just recall.

### 1.1 In scope

- Design of the two retrieval stores (structured patient-context store; guideline vector/hybrid index).
- Ingestion from the canonical patient-event model produced by the data-integration layer.
- Query interfaces exposed to the History & Retrieval Agent and Risk-Rules Agent.
- Context assembly and citation schema handed to the Triage Reasoning Agent.
- Access control, PHI scoping, and retrieval logging.
- Retrieval-specific evaluation.

### 1.2 Out of scope

- HL7 v2 / FHIR parsing and terminology mapping (data-integration layer).
- Prompt design for the reasoning agent beyond the context contract defined here.
- Model selection (see proposal §5); this layer is model-agnostic.
- Fine-tuning or embedding-model training on PHI (Phase 3, REB/IRB-gated).

---

## 2. Design Principles

| Principle | What it means in practice |
|---|---|
| **Deterministic where possible** | Patient history is fetched by patient ID and typed queries, never by semantic search. Vector search is used only over the guideline corpus, which contains no PHI. |
| **PHI never enters the vector index** | Embeddings are computed only for guideline/protocol text. No patient free-text is embedded in Phase 1. |
| **Every retrieved object is citable** | Each item carries a stable `evidence_id` that the audit log and verification agent can resolve back to a source record. |
| **Scoped by construction** | A retrieval request is bound to one `encounter_id` and one clinician role; the store cannot return another patient's data even if asked. |
| **Small, ranked, bounded context** | The reasoning agent receives a fixed-size, prioritized context pack, not a data dump. Token budget is a design parameter. |
| **Freshness matters** | Vitals or labs arriving after registration must be visible to the next retrieval within seconds. |

---

## 3. Data Sources

Inputs arrive from the data-integration layer as canonical events, already normalized and terminology-mapped.

| Source | HL7 v2 / FHIR origin | Used for |
|---|---|---|
| Demographics, arrival, chief complaint | ADT A04/A08; FHIR `Patient`, `Encounter` | Snapshot, age/sex-specific rules |
| Vitals | ORU R01 (device interfaces); FHIR `Observation` (vital-signs category) | Red-flag rules, trend context |
| Lab results | ORU R01; FHIR `Observation` (laboratory), `DiagnosticReport` | Recent abnormal results |
| Imaging reports | ORU R01 (TXT/FT); FHIR `DiagnosticReport` | Recent significant findings (impression only) |
| Active orders | ORM O01; FHIR `ServiceRequest` | Context on in-progress workups |
| Problem list / conditions | FHIR `Condition` (SNOMED CT) | Chronic-disease risk modifiers |
| Medications | FHIR `MedicationRequest`, `MedicationStatement` (RxNorm) | Anticoagulants, beta-blockers, immunosuppressants, etc. |
| Allergies | FHIR `AllergyIntolerance` | Safety context |
| Prior encounters | ADT history; FHIR `Encounter` | Return-visit and frequency signals |
| Triage guidelines | CTAS or ESI handbooks (licensed text), local ED protocols, sepsis/stroke/STEMI pathways | Knowledge index |

Non-PHI knowledge documents are versioned and owned by the ED clinical champion; changes go through the same review as any protocol update.

---

## 4. Architecture

```
            Data-integration layer (canonical events)
                            │
          ┌─────────────────┴──────────────────┐
          ▼                                    ▼
  ┌──────────────────┐               ┌──────────────────────┐
  │ Patient-Context  │               │ Knowledge Index      │
  │ Store (PCS)      │               │ (guidelines, no PHI) │
  │ • relational +   │               │ • chunk store        │
  │   time-series    │               │ • dense vectors      │
  │ • keyed by       │               │ • BM25 / keyword     │
  │   patient_id     │               │ • metadata filters   │
  └────────┬─────────┘               └──────────┬───────────┘
           │                                    │
           └──────────────┬─────────────────────┘
                          ▼
              ┌───────────────────────┐
              │ Retrieval Service     │
              │ • scoped query API    │
              │ • ranking & budgeting │
              │ • context assembly    │
              │ • evidence registry   │
              └───────────┬───────────┘
                          ▼
     History & Retrieval Agent  /  Risk-Rules Agent  /  Critic Agent
```

### 4.1 Patient-Context Store (PCS)

**Role:** the single source of truth for "what do we know about this patient right now."

- **Storage:** relational database (PostgreSQL or equivalent) for demographics, conditions, meds, allergies, encounters; a time-series table (or TimescaleDB extension) for vitals and labs.
- **Keying:** `patient_id` (hospital MRN, mapped to an internal surrogate key) and `encounter_id`.
- **Write path:** the integration layer upserts events in near real time (target: < 5 s from HL7 receipt to queryable). Idempotency on HL7 message control ID / FHIR resource version.
- **Read path:** typed, parameterized queries only. No free-text or semantic query on PCS in Phase 1.
- **Retention:** rolling window configurable per site (default: 24 months of encounters; full problem list and meds). Older data remains in the EHR and is not replicated.
- **Encryption:** AES-256 at rest, TLS 1.2+ in transit, inside the hospital trust boundary.

**Canonical views exposed to agents** (each returns a list of evidence-tagged records):

| View | Contents | Default window |
|---|---|---|
| `current_snapshot` | Demographics, arrival time, mode of arrival, chief complaint (coded + free text), first vitals set | This encounter |
| `vitals_trend` | All vitals for the encounter, ordered; flags for values crossing thresholds | This encounter |
| `recent_abnormal_labs` | Lab results flagged abnormal/critical (from OBX abnormal flags) | 72 h, then last 12 months |
| `active_meds` | Active medication list, with high-risk class tags (anticoagulant, beta-blocker, opioid, immunosuppressant, insulin) | Current |
| `problem_list` | Active conditions, with chronic-risk tags (CHF, COPD, CKD, diabetes, cancer, pregnancy) | Current |
| `allergies` | Active allergies | Current |
| `prior_ed_visits` | Last N encounters: date, chief complaint, triage level, disposition | 12 months, N ≤ 5 |
| `recent_reports` | Imaging/diagnostic report impressions | 30 days |

The **high-risk class tags** and **chronic-risk tags** are computed at ingest from RxNorm / SNOMED CT value sets, so the Risk-Rules Agent can evaluate red flags without parsing free text.

### 4.2 Knowledge Index

**Role:** retrieve the guideline and protocol passages relevant to the current presentation.

- **Corpus:** CTAS or ESI handbook (site-dependent), CTAS/ESI modifier tables, local ED protocols (sepsis screen, stroke, STEMI, trauma activation), institutional triage policy. Strictly no PHI.
- **Chunking:** structure-aware. Handbook criteria are chunked at the level of a single criterion or modifier row (typically 50–200 tokens) so a citation points to one rule, not a page. Narrative protocol text is chunked at paragraph/section level (≤ 400 tokens) with heading breadcrumbs prepended.
- **Metadata per chunk:** `doc_id`, `doc_version`, `section_path`, `triage_scale` (CTAS/ESI), `acuity_levels_referenced`, `presentation_category` (e.g., cardiovascular, neurological, respiratory), `age_group` (adult only in Phase 1), `effective_date`.
- **Indexing:** hybrid — dense embeddings plus BM25/keyword — with reciprocal-rank fusion. Keyword search matters here because clinical criteria use precise terms and thresholds ("SBP < 90", "GCS ≤ 13") that dense retrieval handles poorly.
- **Embedding model:** a general-purpose or biomedical text-embedding model, self-hosted inside the trust boundary. Because the corpus contains no PHI, an external embedding API is also acceptable if the site permits; the choice does not affect privacy posture.
- **Re-indexing:** triggered on any corpus document update; old versions kept read-only so historical audit records remain resolvable.

### 4.3 Retrieval Service

A single internal service that the agents call. It enforces scoping, builds queries, fuses and ranks results, applies the token budget, and registers evidence.

**API surface (illustrative):**

```
GET  /context/{encounter_id}/snapshot
GET  /context/{encounter_id}/history?views=vitals_trend,recent_abnormal_labs,active_meds,...
POST /knowledge/search         { query, filters, top_k }
POST /context/{encounter_id}/assemble   { presentation_summary, red_flags, budget_tokens }
GET  /evidence/{evidence_id}   → source record (used by Critic Agent and audit)
```

Every call carries the caller's identity (agent name), the clinician's role from the session, and the `encounter_id`; the service rejects any query that references a different patient.

---

## 5. Retrieval Flow per Triage Request

```
1. Intake Agent
   → snapshot = PCS.current_snapshot(encounter_id)

2. History & Retrieval Agent
   → history  = PCS.history(encounter_id, all views)
   → red_flag_inputs = derived tags (anticoagulant, beta-blocker, chronic risks) + vitals

3. Risk-Rules Agent
   → floors = deterministic rules over (snapshot, history)
   → e.g., anticoagulant + head-injury complaint ⇒ floor CTAS II / ESI 2

4. History & Retrieval Agent (knowledge step)
   → queries built from: chief complaint (coded + text), abnormal vitals,
     red-flag outputs, top chronic conditions
   → knowledge_hits = KnowledgeIndex.hybrid_search(queries, filters, top_k=8–12)

5. Retrieval Service
   → context_pack = assemble(snapshot, history, knowledge_hits, floors, budget)
   → each item registered with evidence_id and written to the retrieval log

6. Triage Reasoning Agent (LLM)
   → consumes context_pack; may cite only evidence_ids present in it

7. Critic / Verification Agent
   → resolves every cited evidence_id via /evidence; rejects if unresolved
   → checks proposed level ≥ every floor
```

### 5.1 Query construction for the knowledge index

Queries are generated by templates, not by the LLM, so that retrieval is reproducible from the log:

- **Complaint query:** chief complaint text + mapped SNOMED CT concept + synonyms from a small local synonym table.
- **Vitals query:** one query per threshold-crossing vital, phrased in guideline vocabulary ("hypotension adult", "tachycardia HR > 120").
- **Modifier queries:** one per high-risk tag present (e.g., "anticoagulant head injury", "immunocompromised fever").
- **Filters:** `triage_scale` = site's scale; `age_group` = adult.

Results from all queries are fused, deduplicated by `chunk_id`, and re-ranked with a lightweight cross-encoder when latency allows (see §8). Top-k after fusion is capped at 12 chunks in Phase 1.

### 5.2 Context assembly and token budget

The context pack is a JSON object with a fixed section order and a hard token budget (default 6,000 tokens for the patient section, 3,000 for the knowledge section). Within each section, items are ranked and truncated by priority:

1. Current snapshot and latest vitals (always included).
2. Rule-based red flags and floors (always included).
3. High-risk medications and chronic-risk conditions.
4. Critical/abnormal labs (most recent first).
5. Prior ED visits.
6. Recent report impressions.
7. Guideline chunks (fused rank order).

Free-text fields (chief complaint, report impressions) pass through a **PHI-minimization scrubber** that removes names, MRNs, phone numbers, and addresses that the integration layer has not already stripped. Clinical content is left intact.

### 5.3 Evidence schema

Every item in the context pack carries:

```json
{
  "evidence_id": "ev_01J8...",
  "type": "observation | condition | medication | encounter | report | guideline_chunk",
  "source": {
    "system": "fhir | hl7v2 | knowledge_index",
    "resource_ref": "Observation/abc123",
    "message_control_id": "MSG00042",
    "doc_id": "ctas_2016_v2", "chunk_id": "ctas_2016_v2#s4.3.2", "doc_version": "2.1"
  },
  "timestamp": "2026-09-03T14:02:11Z",
  "content": { "...typed payload or chunk text..." },
  "rank_reason": "abnormal_flag=H | red_flag=anticoag_head_injury | fused_rank=3"
}
```

`evidence_id` is the only handle the reasoning agent is allowed to cite. It is opaque, per-request, and resolvable for the life of the audit record.

---

## 6. Access Control, Privacy, and Logging

- **Scope binding.** A retrieval session is created per `encounter_id` by the orchestration layer and passed to every agent. The service refuses cross-encounter reads, and the PCS query layer enforces `patient_id` as a mandatory predicate — there is no "search all patients" endpoint.
- **Role-based views.** Which PCS views a role can see is a config table (e.g., triage nurse: all Phase 1 views; registration clerk: none). Roles come from the SMART on FHIR launch context.
- **No PHI in embeddings.** Verified by a CI check that the knowledge-index ingestion path only accepts documents from the approved corpus repository.
- **Minimization.** Views return only the fields listed in §4.1; the scrubber handles residual identifiers in free text.
- **Retrieval log.** For each request: session ID, agent, views queried, knowledge queries issued, all `evidence_id`s returned (with rank), token budget applied, and latency per step. Stored alongside the decision trace in the immutable audit store, so an audit can reconstruct exactly what the model saw.
- **Encryption and residency.** Same posture as the proposal §6: all stores inside the hospital trust boundary; AES-256 at rest; TLS 1.2+ in transit.

---

## 7. Freshness and Consistency

- **Event-driven updates.** New ORU/ADT events for an active encounter trigger a PCS upsert and invalidate any cached snapshot for that encounter.
- **Re-retrieval triggers.** The orchestration layer may request a fresh context pack when a critical lab or new vitals set arrives before the nurse has acted; the retrieval log records both packs.
- **Clock discipline.** All timestamps normalized to UTC at ingest; display-layer converts to local time.
- **Consistency guarantee.** Read-your-writes within the PCS; the snapshot returned to the Intake Agent includes every event acknowledged by the integration layer before the request.

---

## 8. Performance Targets (Phase 1)

| Metric | Target |
|---|---|
| HL7 receipt → queryable in PCS | < 5 s (p95) |
| Full patient-context fetch | < 300 ms (p95) |
| Knowledge hybrid search (all queries, fused) | < 500 ms (p95); < 900 ms with cross-encoder re-rank |
| Context assembly + evidence registration | < 200 ms |
| End-to-end retrieval budget within the 60 s recommendation SLA | ≤ 2 s |

If the re-ranker pushes latency over budget, it is disabled per request and the log records `rerank=skipped`.

---

## 9. Evaluation

Retrieval is evaluated independently of the reasoning model so failures can be attributed.

**Knowledge retrieval**
- Build a labeled set of (presentation → relevant guideline chunks) pairs with the clinical champion (target: 200–300 cases spanning CTAS/ESI levels and presentation categories).
- Metrics: recall@k and nDCG@k for k = 5, 10, 12; keyword-vs-dense-vs-hybrid ablation.

**Patient-context retrieval**
- Replay historical encounters; verify that every red flag a rule *should* have fired on had its inputs present in the context pack (input completeness rate, target > 99%).
- Measure truncation frequency: how often the token budget drops an item that a clinician reviewer judged relevant.

**Citation faithfulness (joint with reasoning agent)**
- Fraction of citations in model rationales that resolve to a real `evidence_id` and whose content supports the claim, as judged by a reviewer sample. This is the proposal's "citation-faithfulness rate."

**Privacy checks**
- Automated scans of the knowledge index and embedding store for PHI patterns (MRN formats, names from a synthetic list) on every rebuild.
- Penetration-style tests attempting cross-encounter retrieval through the API.

---

## 10. Risks Specific to the Retrieval Layer

| Risk | Mitigation |
|---|---|
| Guideline chunk retrieved is from an outdated version | Versioned corpus; `effective_date` filter; old versions read-only for audit only |
| Dense search misses threshold-based criteria | Hybrid index with BM25; template queries phrased in guideline vocabulary |
| Relevant history truncated by token budget | Priority ordering (§5.2); truncation logged and measured; budget tunable per site |
| HL7 vendor variation yields missing abnormal flags | Integration layer recomputes flags from reference ranges when OBX-8 is absent; PCS marks `flag_source` |
| PHI leaks into free-text fields sent to the model | Scrubber + minimization; free-text kept to chief complaint and report impressions only |
| Stale snapshot after late-arriving results | Event-driven invalidation and re-retrieval triggers (§7) |
| Embedding model drift on corpus update | Re-index entire corpus on embedding-model change; regression eval before switch |

---

## 11. Open Questions

1. **Triage scale** — CTAS vs. ESI determines the corpus, chunking templates, and labeled eval set. Blocked on pilot-site selection.
2. **Guideline licensing** — Can the CTAS/ESI handbook text be indexed under the site's existing licence, or is a summarized/derived criteria table required?
3. **Embedding model** — Self-hosted general-purpose vs. biomedical model; decide after the recall@k ablation in Phase 1.
4. **Window sizes** — Are 12 months of prior visits and 72 h of labs the right defaults for the pilot ED? Needs clinical-champion input.
5. **Phase 2+** — Should nursing notes or triage free-text from prior visits be added to PCS (would require a PHI-safe semantic search path and REB review)?

---

## 12. Phase 1 Deliverables for This Layer

- PCS schema, ingestion upserts, and the eight canonical views.
- Knowledge corpus repository with versioning and chunking pipeline.
- Hybrid index with fusion and optional re-ranker.
- Retrieval Service with scoped API, context assembly, evidence registry, and retrieval log.
- Retrieval evaluation harness and initial labeled set.
- Privacy CI checks (no-PHI-in-index; cross-encounter access tests).
