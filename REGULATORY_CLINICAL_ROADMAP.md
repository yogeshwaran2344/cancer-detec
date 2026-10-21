# PathoGuard-AI — Regulatory Classification & Supervised Clinical Pilot Roadmap

---

## 1. Regulatory Classification Analysis

### A. India: Central Drugs Standard Control Organisation (CDSCO)
- **Framework:** Medical Device Rules, 2017 & Digital Health Guidelines.
- **Classification Status:**
  - Tools intended solely for patient education, visit preparation, and organizing verified diagnostic data without autonomous diagnostic or therapeutic intervention generally fall under **Class A (Low Risk) or Non-Regulated Health IT Software**.
  - To maintain this classification:
    1. The software must NOT render autonomous clinical decisions.
    2. All outputs must clearly cite their origin in verified reports.
    3. The physician must remain the sole diagnostic decision-maker.

### B. United States: FDA Non-Device Clinical Decision Support (CDS) Analysis
- **Framework:** 21 U.S.C. § 360j(o)(1)(E) & FDA Final Guidance on Clinical Decision Support Software (Sept 2022).
- **The 4-Part CDS Exclusion Test:**
  1. *Not intended to acquire, process, or analyze medical images directly?* **YES.** Operates on textual report transcripts, not raw DICOM pixel signals.
  2. *Intended for displaying, analyzing, or printing medical information?* **YES.** Displays and organizes verified medical report findings and symptoms.
  3. *Intended to support or provide recommendations to healthcare professionals?* **YES.** Provides structured visit preparation for clinical review.
  4. *Enables the health care professional to independently review the basis for the recommendations?* **YES.** Every single recommendation and explanation explicitly displays the verbatim source report passage, section, and page number so the clinician can independently review the underlying basis.

---

## 2. Supervised Clinical Pilot Protocol

### Objective
To evaluate patient comprehension, physician communication efficiency, and evidence traceability of PathoGuard-AI summaries in an outpatient oncology/pulmonology clinic under licensed physician supervision.

### Inclusion Criteria
- Adult patients (aged 18 to 75 years) presenting for outpatient evaluation with a completed, verified diagnostic scan report (CT, MRI, or Ultrasound).
- Ability to provide written informed consent.
- Access to a smartphone or computer with web browsing capabilities.

### Exclusion Criteria
- Patients presenting with acute medical emergencies (severe acute dyspnea, hemodynamic instability, active massive hemoptysis).
- Inability to provide informed consent or cognitive impairment.
- Absence of a verified diagnostic scan report.

### Stopping Conditions (Adverse Incident Triggers)
The pilot protocol mandates immediate cessation and investigation if:
1. **False Reassurance Incident:** The system fails to abstain or provide appropriate warnings on alarming symptoms accompanied by clear imaging.
2. **Unsupported Diagnostic Pronouncement:** Any instance of the software generating an autonomous cancer diagnosis or cancer percentage risk score.
3. **Data Security Breach:** Any unauthorized access or leakage of patient session data outside the sandbox environment.

---

## 3. Pre-Pilot Institutional Review Board (IRB) Checklist

- [ ] Ethics Committee / IRB Protocol Submission & Approval
- [ ] Patient Informed Consent Form (ICF) detailing educational CDS scope
- [ ] Principal Investigator (PI) Oversight Agreement (Licensed Oncologist/Radiologist)
- [ ] Data Protection Compliance Audit under India's Digital Personal Data Protection (DPDP) Act, 2023
- [ ] Adverse Event & Clinical Feedback Logging Mechanism
- [ ] Secure Sandbox Data Erasure Protocol post-consultation
