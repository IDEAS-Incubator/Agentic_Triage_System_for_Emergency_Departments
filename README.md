# Agentic_Triage_System_for_Emergency_Departments
Agentic AI Triage System for Emergency Departments

Executive Summary

Emergency department (ED) triage is a high-stakes, time-pressured decision made with incomplete information. Nurses assign a triage acuity level (e.g., ESI in the US, CTAS in Canada) within minutes of arrival, often before lab results, prior encounters, or medication history are reviewed. Under-triage delays care for deteriorating patients; over-triage consumes scarce resuscitation and monitoring capacity.

This proposal describes an agentic AI triage-support system that combines (a) the hospital's private clinical data streams — HL7 v2 ADT, ORM, and ORU messages and FHIR resources — indexed in a secure retrieval layer (RAG), with (b) a large language model orchestrated as a set of cooperating agents. The system recommends a triage acuity level together with a structured, evidence-linked explanation, so clinicians can inspect the reasoning before acting. The clinician always remains the decision-maker; the system is decision support, not autonomous triage.

Expected outcomes: more consistent acuity assignment, reduced under-triage of high-risk patients with complex histories, shorter door-to-decision times, and a full audit trail suitable for HIPAA (US) and PHIPA/provincial privacy regimes (Canada).
This is a hypothetical/exploratory proposal intended to frame a discussion with hospital clinical-integration stakeholders. It builds on prior hands-on experience integrating HL7 and FHIR messaging systems in Canadian hospitals.

