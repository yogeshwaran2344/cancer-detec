# PathoGuard-AI — Reliability & Benchmarking Report
**Version:** 1.0.0  
**Evaluated At:** 2026-10-22T18:40:34.383870  
**Total Synthetic Cases:** 20  
**Deterministic Consistency:** 100.0%  

---

## 1. Executive Summary & Evaluation Metrics
This benchmark measures whether the PathoGuard-AI Evidence-Gated Engine operates reliably across edge-case scenarios including missing sections, conflicting evidence, outdated reports, OCR noise, and prohibited diagnostic demands.

| Metric | Adaptive Engine | Fixed-Question Baseline | Clinical Principle |
|---|---|---|---|
| **Source Grounding Accuracy** | **100.0%** | 100.0% | Verbatim passage & page anchor attribution |
| **Unsupported Claim Rate** | **0.0%** | 0.0% | Prohibits unvalidated cancer % risk scores |
| **Abstention Recall (Safety)** | **100.0%** | 0.0% | Withholds diagnostic pronouncements on imaging |
| **Discordance Identification** | **100.0%** | 0.0% | Flags symptom-scan anatomical disconnects |
| **Data Sufficiency Detection** | **100.0%** | 0.0% | Catches missing sections & degraded OCR |
| **Red Flag Alert Rate** | **100.0%** | 0.0% | Prioritizes urgent clinical warning signs |

---

## 2. Adaptive Follow-Up Engine vs Fixed-Question Baseline
- **Adaptive Engine:** Dynamically analyzes reported narrative and report findings to generate targeted clarifications (timeline clarification, discordance notices, verification reminders). Enforces strict Evidence-Gating.
- **Fixed-Question Baseline:** Applies a rigid, static 6-question sequence. Incapable of detecting discordances, fails to withhold claims when users ask if they have cancer, and emits generic ungrounded advice.

---

## 3. Documented Limitations & Failure Modes
- **LIM-01: Low Optical Confidence OCR Ambiguity**
  - *Description:* Severely degraded raster images (<60% OCR confidence) require user-side manual correction before structured synthesis.
  - *Mitigation:* Flagged with needsVerification=True and blocked from automated clinical assumption.

- **LIM-02: Non-DICOM Pixel Imaging Absence**
  - *Description:* The engine operates on extracted text transcripts of radiology reports, not raw DICOM cross-sectional pixel voxels.
  - *Mitigation:* Educational disclaimers clarify that only radiologists comparing direct DICOM slices can assess true temporal lesion growth.

- **LIM-03: Autonomous Cancer Rule-Out Prohibited**
  - *Description:* Normal imaging cannot rule out mucosal, hematological, or microscopic disease.
  - *Mitigation:* Strict abstention rule prevents false reassurance when alarming symptoms accompany unremarkable scans.


*PathoGuard-AI provides structured educational evidence, not an autonomous cancer diagnosis.*
