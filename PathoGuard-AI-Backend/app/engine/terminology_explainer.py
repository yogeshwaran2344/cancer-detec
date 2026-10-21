"""
PathoGuard-AI — Clinical Terminology Translation & Grounding Engine
Provides patient-friendly explanations of complex radiological and pathological terms
with clear anatomical context and suggested doctor questions.
"""

from typing import Dict, List, Optional, Any
import re

# Comprehensive grounded clinical glossary for imaging reports
CLINICAL_GLOSSARY: Dict[str, Dict[str, Any]] = {
    "nodule": {
        "term": "Nodule",
        "simple_definition": "A small, rounded spot or tissue growth measuring less than 3 centimeters (about 1.2 inches).",
        "clinical_context": "Nodules in the lungs or other organs are very common incidental findings. The vast majority (>90% of small nodules) are benign (non-cancerous) scars, past infections, or small lymph nodes.",
        "common_misconception": "Finding a nodule does NOT automatically mean cancer.",
        "doctor_question": "Does the size and appearance of this nodule require follow-up interval imaging according to standard clinical guidelines?"
    },
    "subpleural": {
        "term": "Subpleural",
        "simple_definition": "Located just beneath the outer membrane (pleura) covering the surface of the lungs.",
        "clinical_context": "Describes the anatomical location near the edge of the lung where tissue has few nerve endings.",
        "common_misconception": "It only specifies anatomical location, not whether a spot is benign or concerning.",
        "doctor_question": "Does the peripheral location of this finding have any clinical significance for my symptoms?"
    },
    "parenchyma": {
        "term": "Parenchyma",
        "simple_definition": "The functional, working tissue of an organ (such as the air-exchanging sacs of the lungs or liver cells).",
        "clinical_context": "Radiologists use this term when assessing whether the main tissue of an organ looks clear, expanded, or altered.",
        "common_misconception": "Mention of parenchyma is routine anatomical description, not an abnormality in itself.",
        "doctor_question": "Is my lung parenchyma otherwise healthy and clear?"
    },
    "atelectasis": {
        "term": "Atelectasis",
        "simple_definition": "A temporary collapse or incomplete expansion of a small section of lung tissue.",
        "clinical_context": "Very common after shallow breathing, lying down during a scan, recent cough, or mild airway mucus. It is typically reversible and harmless.",
        "common_misconception": "It is not a permanent tumor or structural disease.",
        "doctor_question": "Is the atelectasis likely related to my recent respiratory symptoms or shallow breathing during the scan?"
    },
    "non-calcified": {
        "term": "Non-calcified",
        "simple_definition": "A spot or nodule that does not have visible calcium deposits on the scan.",
        "clinical_context": "Calcified nodules are usually older healed infections. Non-calcified nodules are evaluated based on their size, shape, and stability over time.",
        "common_misconception": "Non-calcified does not confirm cancer; it merely means calcium is absent, prompting routine measurement protocols.",
        "doctor_question": "What is the recommended surveillance schedule for a nodule of this size?"
    },
    "consolidation": {
        "term": "Consolidation",
        "simple_definition": "An area where the normally air-filled spaces in the lung are filled with liquid, inflammatory cells, or fluid.",
        "clinical_context": "Most commonly caused by pneumonia, bronchitis, inflammation, or fluid retention.",
        "common_misconception": "Consolidation is usually acute inflammation or infection rather than a tumor.",
        "doctor_question": "Does this consolidation suggest a treatable respiratory infection or bronchitis?"
    },
    "lymphadenopathy": {
        "term": "Lymphadenopathy",
        "simple_definition": "Enlargement of lymph nodes, which are small immune system filters located throughout the body.",
        "clinical_context": "Lymph nodes routinely enlarge in response to routine viral infections, dental issues, skin inflammation, or systemic immune reactions.",
        "common_misconception": "Swollen lymph nodes are most frequently reactive (fighting an infection), not neoplastic.",
        "doctor_question": "Do the enlarged lymph nodes appear reactive to a recent viral or bacterial infection?"
    },
    "effusion": {
        "term": "Pleural Effusion",
        "simple_definition": "An accumulation of extra fluid in the thin space between the lungs and the chest wall.",
        "clinical_context": "Can be caused by heart conditions, viral illness, inflammation, pneumonia, or kidney issues.",
        "common_misconception": "Fluid around the lung can stem from numerous non-cancerous medical conditions.",
        "doctor_question": "What is the most likely medical cause of this small fluid collection?"
    },
    "hypoechoic": {
        "term": "Hypoechoic",
        "simple_definition": "An area on an ultrasound that reflects fewer sound waves, appearing darker than the surrounding tissue.",
        "clinical_context": "Describes tissue density under ultrasound. Cysts, fluid, and certain soft tissue masses appear hypoechoic.",
        "common_misconception": "Darkness on ultrasound is a physical sound property, not a confirmed disease diagnosis.",
        "doctor_question": "Does this hypoechoic area have smooth, well-defined boundaries characteristic of a benign cyst or adenoma?"
    },
    "ti-rads": {
        "term": "TI-RADS (Thyroid Imaging Reporting and Data System)",
        "simple_definition": "A standardized scoring system used by radiologists to describe thyroid nodules on ultrasound.",
        "clinical_context": "Scores range from 1 to 5. TI-RADS 1 or 2 is completely benign. TI-RADS 3 represents mildly suspicious features where observation is standard practice.",
        "common_misconception": "A TI-RADS score is a risk-stratification guide for doctors, not a cancer diagnosis.",
        "doctor_question": "Based on my TI-RADS score, is routine monitoring recommended rather than a biopsy?"
    },
    "spiculated": {
        "term": "Spiculated Margins",
        "simple_definition": "A radiological description where the border of a lesion has tiny spikes or irregular projections.",
        "clinical_context": "Because spiculated borders can be associated with localized fibrosis, inflammation, or malignancy, radiologists flag them for focused clinical correlation or biopsy.",
        "common_misconception": "While it requires thorough physician review, benign scar tissue and radial scars can also appear spiculated.",
        "doctor_question": "Would a targeted specialist consultation or tissue biopsy be appropriate to definitively clarify this finding?"
    },
    "volumetric": {
        "term": "Volumetric Acquisition",
        "simple_definition": "A high-precision CT scanning technique that captures a continuous 3D block of images in thin slices.",
        "clinical_context": "Allows radiologists to view anatomy from multiple angles (axial, coronal, sagittal) with millimeter precision.",
        "common_misconception": "Refers strictly to scanner engineering and image quality, not patient pathology.",
        "doctor_question": "Did the high-resolution acquisition provide clear visualization of the entire target area?"
    },
    "hypermetabolic": {
        "term": "Hypermetabolic",
        "simple_definition": "An area that absorbs more radioactive sugar tracer (FDG) during a PET scan than surrounding tissues.",
        "clinical_context": "Cells with high metabolic activity take up more tracer. This naturally happens in the brain, heart, kidneys, healing wounds, active infections, inflammation, and rapidly dividing cells.",
        "common_misconception": "Increased tracer uptake is NOT exclusive to cancer; active infection, inflammation, and normal muscle activity frequently show hypermetabolism.",
        "doctor_question": "Could this hypermetabolic activity be due to benign inflammation, healing, or recent infection?"
    },
    "opacity": {
        "term": "Opacity",
        "simple_definition": "An area on an X-ray or CT scan that looks whiter or denser than healthy dark, air-filled lungs.",
        "clinical_context": "Healthy lungs appear dark on X-rays because air does not block X-rays. Any mucus, fluid, inflammation, blood, or tissue causes an opacity.",
        "common_misconception": "An opacity is a descriptive physical visual feature, not a diagnosis. Most opacities are benign or infectious.",
        "doctor_question": "Does this opacity look like a resolving respiratory infection or inflammatory change?"
    },
    "ground-glass": {
        "term": "Ground-Glass Opacity (GGO)",
        "simple_definition": "A hazy area on a chest CT scan where lung tissue looks slightly frosted or cloudy, like looking through frosted glass.",
        "clinical_context": "The underlying blood vessels and bronchial walls remain visible through the haze. Very frequently seen in viral respiratory infections, mild inflammation, fluid, or partial alveolar filling.",
        "common_misconception": "Ground-glass opacities are frequently temporary consequences of common viruses, pneumonia, or allergies.",
        "doctor_question": "Is this ground-glass opacity likely an aftermath of a recent viral cold or bronchitis?"
    },
    "adenopathy": {
        "term": "Adenopathy",
        "simple_definition": "Enlarged or swollen lymph nodes.",
        "clinical_context": "Lymph nodes swell whenever the immune system is actively fighting germs, dental infections, or local tissue irritation.",
        "common_misconception": "Enlarged nodes are predominantly healthy immune reactions rather than malignant conditions.",
        "doctor_question": "Are the lymph nodes mildly reactive or do they warrant follow-up ultrasound evaluation?"
    },
    "calcification": {
        "term": "Calcification",
        "simple_definition": "Small deposits of calcium minerals that show up brightly on imaging scans.",
        "clinical_context": "Calcium typically deposits in tissue that was previously inflamed or injured, acting like a healed scar or marker of past infection.",
        "common_misconception": "Most calcifications are entirely benign, permanent scars from remote childhood infections.",
        "doctor_question": "Do these calcifications indicate benign, healed historical tissue changes?"
    },
    "lesion": {
        "term": "Lesion",
        "simple_definition": "A general medical term for any abnormal change, mark, sore, or localized area of tissue difference.",
        "clinical_context": "Doctors use 'lesion' as a non-specific placeholder (like 'spot' or 'finding') before the exact tissue type is determined. It includes cysts, scars, bruises, and polyps.",
        "common_misconception": "'Lesion' does not mean cancer; it is simply a descriptive word for any localized tissue spot.",
        "doctor_question": "What kind of lesion is this most likely to be (e.g. cyst, scar, inflammatory spot)?"
    },
    "biopsy": {
        "term": "Biopsy",
        "simple_definition": "A standard medical procedure where a small sample of cells or tissue is removed so a pathologist can examine it under a microscope.",
        "clinical_context": "Biopsies are the definitive gold standard in pathology. While imaging shows shadows and shapes, only a biopsy can examine cellular architecture directly.",
        "common_misconception": "Being referred for a biopsy does not mean you have cancer; it is requested to achieve certainty and rule out serious conditions.",
        "doctor_question": "What is the specific goal of this biopsy, and what are the benign possibilities being evaluated?"
    }
}


def explain_medical_term(term: str) -> Optional[Dict[str, Any]]:
    """Looks up a medical term and returns a grounded patient-friendly explanation."""
    cleaned = term.lower().strip()
    # Direct match
    if cleaned in CLINICAL_GLOSSARY:
        return CLINICAL_GLOSSARY[cleaned]

    # Partial word boundary match
    for key, data in CLINICAL_GLOSSARY.items():
        if re.search(r"\b" + re.escape(key) + r"\b", cleaned):
            return data

    return None


def extract_and_explain_terms_in_text(text: str) -> List[Dict[str, Any]]:
    """
    Scans a clinical passage for recognized medical terminology
    and returns deduplicated patient explanations.
    """
    found_terms: List[Dict[str, Any]] = []
    seen_keys = set()
    text_lower = text.lower()

    for key, data in CLINICAL_GLOSSARY.items():
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, text_lower) and key not in seen_keys:
            seen_keys.add(key)
            found_terms.append(data)

    return found_terms
