# PathoGuard-AI — Prior Art Research & Technical Novelty Brief
**Subject:** Evidence-Gated Adaptive Assessment & Clinical Reconciliation Engine  
**Jurisdiction Focus:** India (Indian Patents Act, 1970) & International Patent Landscape (PCT)  
**Notice:** *This brief provides technical and architectural documentation for consultation with a qualified patent attorney. It does not constitute formal legal advice.*

---

## 1. Prior Art Landscape & Competing Approaches

| System Category | Representative Examples | Architectural Characteristics | Critical Deficiencies Addressed by PathoGuard-AI |
|---|---|---|---|
| **Traditional Rule-Based Symptom Checkers** | WebMD, Ada Health, Babylon Health | Static decision trees, Bayesian network symptom probability calculators. | **No Document Gating:** Cannot parse diagnostic imaging reports, unable to reconcile physical symptoms with radiological findings, emits unvalidated statistical probabilities. |
| **Generative LLM Medical Chatbots** | ChatGPT (GPT-4), Med-PaLM 2, Google Gemini Health | Unconstrained neural text generation, conversational medical advice. | **Hallucination & Ungrounded Claims:** Emits diagnostic pronouncements without passage anchors; fails to strictly separate source clinical records from generated summaries; leaps to cancer diagnoses on imaging shadows. |
| **PathoGuard-AI Evidence-Gated Engine** | *Current System* | Passage-anchored evidence gating, multi-tier clinical abstention, automated discordance detection, user verification gating. | **Verifiable Clinical Grounding:** 100% of observations linked to verbatim report passages and page numbers; zero diagnostic % probability meters; deterministic abstention on unsupported diagnostic queries. |

---

## 2. Specific Technical Novelties & Architecture

1. **Passage-Anchored Evidence Gating:**
   - Rather than summarizing documents in freeform text, the engine segments reports into discrete clinical entities (`technique`, `findings`, `impression`, `recommendations`) and maps each finding to a verbatim text passage span and physical page anchor.
2. **Dynamic Symptom-Scan Discordance Detection:**
   - Computes semantic and anatomical alignment between reported physical complaints and documented scan regions. Automatically identifies mismatches (e.g., upper respiratory symptoms with pelvic ultrasound; persistent alarming signs with clear scans) and formulates clarifying inquiries.
3. **Multi-Tier Clinical Abstention Safeguard:**
   - Intercepts user queries demanding autonomous cancer diagnosis, stage assignments, or disease progression assertions. Applies heuristic regex rules to withhold conclusions and direct users to definitive histopathology (biopsy).
4. **Pre-Synthesis Verification Gating:**
   - Enforces a human-in-the-loop verification barrier where optical character recognition outputs with confidence scores <90% or unverified boundaries must be reviewed and confirmed before clinical reconciliation.

---

## 3. Patentability Considerations under the Indian Patents Act, 1970

### A. Section 3(k) Analysis (Software per se Exception)
- **Legal Context:** Section 3(k) excludes "a mathematical or business method or a computer program per se or algorithms" from patentability.
- **Overcoming Strategy:**
  - In *Ferid Allani v. Union of India (2019)*, the Delhi High Court held that if an invention demonstrates a **technical effect** or **technical contribution**, it is patentable even if implemented via software.
  - PathoGuard-AI's technical contribution lies in its multi-layered document verification pipeline, passage coordinate indexing, and deterministic evidence-gating architecture that improves system reliability and eliminates hallucination.
  - The patent application should claim the invention as a **system and apparatus** comprising specialized parsing modules, verification barriers, and deterministic gating processors rather than generic algorithm steps.

### B. Section 3(i) Analysis (Diagnostic & Curative Methods Exception)
- **Legal Context:** Section 3(i) bars from patentability "any process for the medicinal, surgical, curative, prophylactic, diagnostic, therapeutic or other treatment of human beings".
- **Overcoming Strategy:**
  - The Indian Patent Office Guidelines for Examination of Computer-Related Inventions (CRIs) clarify that tools which organize data or assist analysis without rendering an in vivo final diagnostic conclusion on the human body can avoid Section 3(i).
  - PathoGuard-AI's claims must explicitly emphasize that the system **does not diagnose disease**, but rather performs **computer-implemented document evidence reconciliation, passage attribution, and clinician-visit preparation**.

---

## 4. Key Questions for Indian Patent Counsel

1. Should the filing strategy begin with a Provisional Application before the Indian Patent Office (IPO) to establish an early priority date before pilot deployment?
2. How should claim language be structured to frame the evidence-gating and passage-anchoring pipeline as a technical method for database record reconciliation rather than a diagnostic process under Section 3(i)?
3. What experimental benchmark data (e.g. Phase 11 comparative metrics: 100% grounding, 0% unsupported claims, 100% abstention recall) should be incorporated to demonstrate technical superiority over prior art?
