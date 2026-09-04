**PROJECT PROPOSAL**

**Agentic AI Triage System for Emergency Departments**

_An explainable, HIPAA/PHIPA-aware, RAG-grounded multi-agent workflow built on hospital HL7/FHIR clinical data_

Draft v0.1 — For Discussion

July 2026

**Table of Contents**

[1\. Executive Summary 3](#_Toc234830876)

[2\. Background and Problem Statement 3](#_Toc234830877)

[2.1 How ED data flows today 3](#_Toc234830878)

[2.2 The triage gap 3](#_Toc234830879)

[2.3 Why now 4](#_Toc234830880)

[3\. Objectives and Scope 4](#_Toc234830881)

[3.1 Objectives 4](#_Toc234830882)

[3.2 In scope (Phase 1) 4](#_Toc234830883)

[3.3 Out of scope (Phase 1) 4](#_Toc234830884)

[4\. Proposed System Architecture 4](#_Toc234830885)

[4.1 High-level design 4](#_Toc234830886)

[4.2 Agent workflow 5](#_Toc234830887)

[4.3 Explainability by construction 5](#_Toc234830888)

[5\. Model Strategy: Frontier LLM vs. Domain-Specific Model 6](#_Toc234830889)

[6\. Privacy, Security, and Compliance 6](#_Toc234830890)

[7\. Evaluation Plan 7](#_Toc234830891)

[7.1 Retrospective (before any live use) 7](#_Toc234830892)

[7.2 Shadow mode 7](#_Toc234830893)

[7.3 Assisted pilot 7](#_Toc234830894)

[8\. Phased Roadmap 7](#_Toc234830895)

[9\. Risks and Mitigations 8](#_Toc234830896)

[10\. Open Questions and Next Steps 8](#_Toc234830897)

# 1\. Executive Summary

Emergency department (ED) triage is a high-stakes, time-pressured decision made with incomplete information. Nurses assign a triage acuity level (e.g., ESI in the US, CTAS in Canada) within minutes of arrival, often before lab results, prior encounters, or medication history are reviewed. Under-triage delays care for deteriorating patients; over-triage consumes scarce resuscitation and monitoring capacity.

This proposal describes an agentic AI triage-support system that combines (a) the hospital's private clinical data streams — HL7 v2 ADT, ORM, and ORU messages and FHIR resources — indexed in a secure retrieval layer (RAG), with (b) a large language model orchestrated as a set of cooperating agents. The system recommends a triage acuity level together with a structured, evidence-linked explanation, so clinicians can inspect the reasoning before acting. The clinician always remains the decision-maker; the system is decision support, not autonomous triage.

Expected outcomes: more consistent acuity assignment, reduced under-triage of high-risk patients with complex histories, shorter door-to-decision times, and a full audit trail suitable for HIPAA (US) and PHIPA/provincial privacy regimes (Canada).

This is a hypothetical/exploratory proposal intended to frame a discussion with hospital clinical-integration stakeholders. It builds on prior hands-on experience integrating HL7 and FHIR messaging systems in Canadian hospitals.

# 2\. Background and Problem Statement

## 2.1 How ED data flows today

When a patient presents to the ED, registration generates HL7 ADT (Admit/Discharge/Transfer) messages; physician orders generate ORM messages; and results — labs, imaging reports, vitals from interfaced devices — flow back as ORU messages. Modern EHRs additionally expose this data as FHIR resources (Patient, Encounter, Observation, Condition, MedicationRequest, DiagnosticReport). All of this is private to the hospital network and governed by health-privacy law.

## 2.2 The triage gap

- Triage decisions are made in 2–5 minutes, largely from the chief complaint, vitals, and a brief interview.
- Relevant history — prior ED visits, chronic conditions, anticoagulant use, recent abnormal labs — often exists in the EHR but is not surfaced at the moment of triage.
- Acuity assignment varies between nurses and across shifts; inter-rater reliability for mid-acuity levels (ESI 2–4 / CTAS II–IV) is a known weak point.
- Under-triage of subtle high-risk presentations (e.g., elderly patients on beta-blockers whose vitals mask shock) is a documented patient-safety issue.

## 2.3 Why now

General-purpose LLMs (Anthropic Claude, OpenAI GPT, Google Gemini) now demonstrate strong performance on medical question-answering and clinical-note reasoning, and — critically — support tool calling and structured outputs, which makes safe, auditable agent architectures practical. Retrieval-augmented generation lets us ground the model in the hospital's own real-time data rather than the model's parametric memory, addressing both accuracy and privacy.

# 3\. Objectives and Scope

## 3.1 Objectives

- Recommend a triage acuity level (CTAS/ESI) for each ED arrival using the chief complaint, vitals, and retrieved patient history.
- Produce a human-readable, evidence-linked rationale for every recommendation (which observations, which historical facts, which guideline criteria).
- Reduce door-to-triage-decision time and triage variability without increasing under-triage risk.
- Maintain full auditability and traceability of every model input, retrieval, and output, aligned with HIPAA/PHIPA expectations.

## 3.2 In scope (Phase 1)

- Adult ED triage decision support at a single pilot site, shadow mode first.
- Ingestion of HL7 v2 ADT/ORM/ORU feeds and/or FHIR APIs into a secure retrieval index.
- Retrospective evaluation against historical triage data and outcomes.

## 3.3 Out of scope (Phase 1)

- Autonomous triage (no human in the loop) — explicitly excluded.
- Pediatric triage, prehospital/EMS triage, and diagnosis or treatment recommendations.
- Model fine-tuning on patient data (deferred to Phase 3, subject to REB/IRB approval).

# 4\. Proposed System Architecture

## 4.1 High-level design

The system is organized as four layers: a data-integration layer, a private retrieval (RAG) layer, an agent-orchestration layer, and a clinician-facing presentation layer. All PHI stays inside the hospital's trust boundary (on-prem or hospital-controlled VPC); the LLM is accessed either through a zero-retention enterprise API with a BAA, or via a self-hosted open-weight model, depending on the site's policy.

| **Layer**                | **Responsibility**                                                                                                                                                                                                                                                     |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1\. Data integration     | HL7 v2 listener (MLLP) for ADT/ORM/ORU; FHIR subscriptions/REST pulls; normalization into a canonical patient-event model; de-duplication and terminology mapping (LOINC, SNOMED CT, RxNorm).                                                                          |
| 2\. Retrieval (RAG)      | Two stores: (a) a structured patient-context store (recent vitals, labs, meds, problem list, prior visits) queried deterministically by patient ID, and (b) a vector/hybrid index over clinical guidelines, triage criteria (CTAS/ESI handbooks), and local protocols. |
| 3\. Agent orchestration  | A supervisor agent decomposes the triage task and calls specialist agents/tools; every step is logged with inputs, retrieved evidence, and outputs.                                                                                                                    |
| 4\. Presentation & audit | Triage dashboard card in the ED tracking board or EHR sidebar (SMART on FHIR app); recommendation + rationale + evidence links; one-click accept/override with reason capture; immutable audit log.                                                                    |

## 4.2 Agent workflow

Rather than a single monolithic prompt, the triage task is decomposed into narrow, verifiable agents:

- **Intake Agent —** Ingest & normalize incoming HL7/FHIR events for the arriving patient; assemble the demographic and presenting-complaint snapshot.
- **History & Retrieval Agent —** Deterministically fetch the patient's structured history (problem list, meds, allergies, last N encounters, recent abnormal results) and retrieve relevant guideline passages from the vector index. Retrieval is filtered by patient ID and role-based access rules — no cross-patient leakage.
- **Risk-Rules Agent —** Compute rule-based red flags first (e.g., vital-sign thresholds, sepsis screens, anticoagulant + head injury). These are deterministic guardrails that the LLM cannot override downward.
- **Triage Reasoning Agent (LLM) —** Reason over the assembled context and propose a CTAS/ESI level with a structured rationale: contributing findings, relevant history, matched guideline criteria, and confidence.
- **Critic / Verification Agent —** Independently verify the recommendation: checks that every cited fact exists in the retrieved evidence (hallucination check), that the level is not below any rule-based floor, and that the output schema is valid.
- **Presentation & Audit Agent —** Format the recommendation for the clinician, capture accept/override + reason, and write the complete decision trace to the audit store.

## 4.3 Explainability by construction

Every recommendation is emitted as a structured object: proposed level, ranked contributing factors each linked to a source (a specific ORU result, a prior encounter, a guideline clause), rule-based floors that applied, and an uncertainty statement. Because citations must resolve to retrieved evidence, the clinician can audit the logic in seconds — and the verification agent rejects any output whose citations do not resolve.

# 5\. Model Strategy: Frontier LLM vs. Domain-Specific Model

A key open question from our brainstorming: are general-purpose frontier models good enough, or is a healthcare-only small model needed? Our recommendation is a staged answer:

| **Option**                                                                 | **Strengths**                                                                                                                                                | **Considerations**                                                                                                      |
| -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Frontier API model (Claude, GPT, Gemini) with RAG                          | Best general clinical reasoning today; tool calling and structured output; fastest path to a working pilot; zero-retention enterprise terms + BAA available. | PHI leaves the hospital network (even if not retained) — requires legal sign-off; per-token cost; internet dependency.  |
| Self-hosted open-weight model (e.g., Llama, Qwen, DeepSeek class) with RAG | PHI never leaves the trust boundary; predictable cost at volume; can be quantized and served on hospital GPUs (vLLM).                                        | Somewhat weaker reasoning than frontier models; ops burden (serving, upgrades, evals).                                  |
| Small fine-tuned healthcare model                                          | Potentially high accuracy on the narrow triage task; cheap inference.                                                                                        | Needs curated labeled data and REB/IRB approval; brittle outside its distribution; months of work — not a Phase 1 item. |

Recommended path: start Phase 1 with a frontier model under a BAA/zero-retention agreement (or a strong open-weight model self-hosted if policy demands), and let RAG carry the domain grounding. The evidence from medical-QA benchmarks suggests grounded frontier models already answer standard health questions well; the differentiator is retrieval quality and guardrails, not model pre-training. Revisit fine-tuning/distillation in Phase 3 once we have accumulated a labeled, consented dataset of triage decisions and outcomes — at which point a distilled domain model could cut cost and latency.

# 6\. Privacy, Security, and Compliance

- **Data residency —** All PHI processing occurs within the hospital trust boundary; the retrieval index and audit store are encrypted at rest (AES-256) and in transit (TLS 1.2+).
- **Access control —** Retrieval is scoped to the current patient and the requesting clinician's role; the vector index over guidelines contains no PHI at all.
- **Vendor terms —** If a frontier API is used: enterprise agreement with zero data retention and a signed BAA (US) / equivalent PHIPA data-processing terms (Ontario) before any PHI is transmitted.
- **Auditability —** Every recommendation stores the full prompt, retrieved evidence identifiers, model version, output, verification result, and clinician action — immutable and queryable for audit or incident review.
- **Minimization —** PHI is minimized in prompts (only fields needed for the task); free-text fields are scrubbed of identifiers not needed for reasoning where feasible.
- **Regulatory posture —** Decision-support framing, human-in-the-loop, and shadow-mode validation are designed to align with FDA CDS guidance / Health Canada SaMD expectations; formal regulatory assessment is a Phase 2 activity with the hospital's compliance office.

# 7\. Evaluation Plan

## 7.1 Retrospective (before any live use)

- Replay 12–24 months of historical ED visits; compare system recommendations against (a) nurse-assigned levels and (b) outcome-derived 'ground truth' (admission, ICU transfer, 72-hour return, mortality).
- Key metrics: under-triage rate on high-risk outcomes (primary safety metric), over-triage rate, agreement (weighted kappa) with nurses, citation-faithfulness rate of explanations.

## 7.2 Shadow mode

- Run live alongside nurses without displaying output; measure prospective accuracy, latency (target: recommendation ready < 60 s from registration), and system reliability.

## 7.3 Assisted pilot

- Display recommendations to triage nurses at one site; measure override rates and reasons, time-to-decision, nurse trust/usability (SUS), and safety events via the hospital's incident process.

# 8\. Phased Roadmap

| **Phase**          | **Deliverables**                                                               | **Key activities**                                                                          | **Duration** |
| ------------------ | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- | ------------ |
| 0\. Discovery      | Data-flow map, privacy assessment, pilot-site agreement                        | Stakeholder interviews; HL7/FHIR feed inventory; legal review                               | 4–6 wks      |
| 1\. Foundation     | Ingestion pipeline, patient-context store, guideline RAG index, agent skeleton | MLLP/FHIR integration; terminology mapping; prompt + schema design                          | 8–10 wks     |
| 2\. Validation     | Retrospective study report; shadow-mode dashboard                              | Historical replay; metric review with clinical champions; regulatory assessment             | 8–12 wks     |
| 3\. Pilot & extend | Assisted pilot at one ED; fine-tuning/distillation feasibility study           | Live pilot with override capture; dataset curation under REB/IRB; cost/latency optimization | 12+ wks      |

Beyond triage, the same data-integration + RAG + agent substrate extends naturally to adjacent use cases already in our portfolio thinking: clinical assistants for documentation, care-pathway optimization, and revenue-cycle (RCM) automation — making the Phase 1 investment reusable.

# 9\. Risks and Mitigations

| **Risk**                               | **Impact**                                        | **Mitigation**                                                                                                         |
| -------------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| LLM hallucination / unsupported claims | Clinician misled by plausible but false rationale | Citation-resolving verification agent; structured outputs; rule-based floors the model cannot lower                    |
| Under-triage by the system             | Patient safety                                    | Deterministic red-flag rules as hard floors; shadow-mode validation gated on under-triage metric; human always decides |
| PHI exposure                           | Legal/regulatory breach                           | Trust-boundary architecture; BAA/zero-retention terms; PHI minimization; encrypted stores; access logging              |
| Automation bias (nurses over-trusting) | Erosion of clinical judgment                      | Rationale-first UI; confidence display; override friction kept low; ongoing override-rate monitoring                   |
| HL7 feed variability across vendors    | Integration delays                                | Canonical event model; interface-engine experience (prior HL7/FHIR hospital work); per-site mapping layer              |
| Regulatory classification as a device  | Deployment delay                                  | Decision-support, human-in-loop framing; early engagement with compliance; Phase 2 formal assessment                   |

# 10\. Open Questions and Next Steps

- Pilot site: which hospital partner, and what is their EHR (Epic/Cerner/Meditech) and interface-engine landscape?
- Deployment stance: frontier API under BAA vs. self-hosted open-weight — driven by the site's privacy office.
- Triage scale: CTAS (Canada) vs. ESI (US) — determines guideline corpus and evaluation labels.
- Access to historical data for the retrospective study (de-identified extract vs. in-situ analysis).
- Clinical champion: identify an ED physician/nurse lead to co-design the rationale UI and override workflow.

Proposed immediate next step: a working session with a hospital clinical-integration team to validate the data-flow assumptions in Section 4 and scope Phase 0.