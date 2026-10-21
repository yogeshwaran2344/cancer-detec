# PathoGuard-AI — Intended Use Statement & Clinical Limitations

---

## 1. Official Intended Use Statement

> **PathoGuard-AI** is a clinical decision-support (CDS) and health literacy platform intended for educational evidence synthesis and clinical visit preparation. It organizes patient-reported physical symptoms and verified diagnostic imaging text into structured, evidence-grounded summaries to facilitate informed communication between patients and qualified licensed healthcare professionals.

---

## 2. What PathoGuard-AI Is NOT (Explicit Non-Indications)

- **NOT an Autonomous Diagnostic Device:** PathoGuard-AI does not diagnose, treat, cure, or stage cancer or any other medical condition.
- **NOT an Autonomous Cancer Rule-Out Tool:** A normal imaging report cannot independently rule out mucosal, hematological, or microscopic disease. The platform strictly abstains from providing definitive reassurance.
- **NO Mathematical Cancer Risk Probability Meters:** PathoGuard-AI strictly prohibits the generation of arbitrary, unvalidated statistical cancer probability percentages (e.g. "82% chance of cancer").
- **NOT a Replacement for Medical Advice:** All syntheses, glossaries, and suggested doctor questions are strictly educational and must be reviewed alongside a licensed physician.
- **NOT for Emergency Medical Care:** Patients experiencing acute chest pain, severe dyspnea, profuse bleeding, or acute neurological deficits must seek emergency medical services immediately.

---

## 3. Target User Population & Operating Environment

### Target Users
1. **Adult Patients (Ages 18+)**: Individuals reviewing their diagnostic imaging summaries or preparing structured symptoms for an upcoming clinical consultation.
2. **Attending Clinicians & Specialists**: Healthcare providers seeking a structured, passage-grounded patient intake summary reconciling physical symptoms with radiologist findings.

### Operating Environment
- Modern desktop or mobile web browsers supporting TLS 1.3 and HTML5.
- Private local sandbox or protected cloud environment adhering to healthcare data protection standards.

---

## 4. Clinical Evidence Principles & Safeguards

1. **Passage-Level Grounding:** Every anatomical explanation is linked to an exact verbatim passage and page anchor from the source report.
2. **Clear Source Distinction:** Original medical report text is distinguished visually and structurally (`VERBATIM_REPORT`) from plain-language educational explanations (`AI_PATIENT_EXPLANATION`).
3. **Mandatory Clinical Abstention:** When queries demand autonomous cancer diagnoses or progression certainty, the engine withholds conclusions and provides clinical safety guidance.
4. **Longitudinal Caution:** Differences in phrasing between separate radiologists or institutions are not interpreted as confirmed disease progression without direct radiologist review of original DICOM imaging slices.
