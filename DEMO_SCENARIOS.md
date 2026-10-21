# PathoGuard-AI — Synthetic Demonstration Scenarios

This document provides step-by-step scripted demonstration walkthroughs using synthetic, de-identified clinical test cases.

---

## Scenario A: Incidental Solitary Pulmonary Nodule (Standard Fleischner Guidance)

### Patient Profile
- **Age:** 54 years old
- **Reported Symptoms:** Persistent dry cough for 5 weeks following a viral cold, mild exertion shortness of breath, no fever.
- **Uploaded Document:** `Thoracic_CT_Contrast_2026.pdf` (High-resolution CT thorax without IV contrast).

### Demonstration Steps
1. **Report Upload:**
   - Navigate to **Scan Report Analysis** (`#view-reports`).
   - Select the preset *Thoracic CT Scan with Contrast (Pulmonary Nodule)* or upload synthetic PDF.
   - Observe extraction badge: `Digital PDF Parser (pypdf) — Confidence: 99.2%`.
2. **Text & Passage Review:**
   - In the left pane, observe highlighted passage anchors (`#p0` to `#p3`).
   - Click `#p1` (`6.2 mm non-calcified solid subpleural nodule in RLL`) to highlight the corresponding finding card on the right.
3. **Patient Explanations & Terminology:**
   - Toggle to **Patient Explanations & Grounding (AI)** tab.
   - Observe distinct badges: `[ORIGINAL REPORT VERBATIM]` in slate vs `[AI PATIENT EXPLANATION]` in mint.
   - Click the clinical term chip `[Nodule]`.
   - In the modal, review plain definition, clinical context, and common misconception: *"Finding a nodule does NOT automatically mean cancer (>90% of small nodules are benign scars or past infections)."*
4. **Symptom Intake & Evidence Synthesis:**
   - Navigate to **Symptom Assessment** (`#view-symptoms`).
   - Select *Dry Cough*, onset *3-6 weeks*, trajectory *Stable*.
   - Click *Continue to Results*.
   - Review synthesized next steps: *"Schedule an appointment to review these structured findings with your treating physician. Bring a printed copy of your verified imaging report."*

---

## Scenario B: Symptom-Scan Discordance & Red Flag Detection

### Patient Profile
- **Age:** 61 years old
- **Reported Symptoms:** Coughing blood (hemoptysis) for 4 days, mild fatigue.
- **Uploaded Document:** `Thoracic_CT_Clear.pdf` (Normal thoracic CT scan).

### Demonstration Steps
1. **Intake & Red Flag Alarm:**
   - In **Symptom Intake**, enter *Coughing blood* in the primary concerns.
   - Notice immediate red flag alert badge and prioritized clarification.
2. **Discordance Detection:**
   - Associate the unremarkable chest CT report.
   - Complete assessment and view **Assessment Results** (`#view-results`).
   - Review the **Discordance Analysis** card:
     - *"Patient reported hemoptysis, but imaging findings state lungs are completely clear."*
     - Clinical note: *"Normal imaging does not rule out mucosal, endobronchial, or upper airway etiologies. Prompt in-person specialist review required."*
3. **Abstention Safeguard:**
   - Open **Clinical Safeguards Checker** and test: *"Does this clean scan prove I don't have cancer?"*
   - Observe triggered abstention: `AUTONOMOUS_DIAGNOSIS_UNSUPPORTED`.
   - Review safeguard rationale explaining that normal CT imaging cannot autonomously rule out non-radiological or microscopic conditions.

---

## Scenario C: Low Optical Confidence OCR Scan & User Text Correction

### Patient Profile
- **Age:** 48 years old
- **Uploaded Document:** `Scanned_CT_Noisy.png` (Optical scan with 62% optical confidence).

### Demonstration Steps
1. **Low Confidence Flag:**
   - Upload low-quality raster image.
   - Status card shows: `Needs verification (62% confidence)`.
   - Finding is flagged with amber tag: `Needs Verification`.
2. **Text Correction Workflow:**
   - Click the pencil icon (`Correct Finding`).
   - In the modal, replace garbled OCR text (`6.Z rnm n0du1e`) with confirmed source text (`6.2 mm nodule`).
   - Click *Save Correction & Mark Verified*.
   - Notice status changes to green: `Reliably Extracted (Verified by User)`.
