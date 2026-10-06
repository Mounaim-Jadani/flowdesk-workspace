import re

COMMITMENT_PATTERNS = [
    r"\bje m'en occupe\b", r"\bje m'occupe\b", r"\bje vais faire\b", r"\bje vais préparer\b", r"\bje prépare\b", r"\bje prepare\b",
    r"\bj'enverrai\b", r"\bje t'envoie\b", r"I'll send\b", r"I'll take care of\b",
    r"\bon dit quoi pour\b",
]
REQUEST_PATTERNS = [
    r"\bpeux[- ]tu\b", r"\bpourrais[- ]tu\b", r"\bvoudrais[- ]tu\b",
    r"\best-ce que tu peux\b", r"\bmerci de\b", r"\bcan you\b",
    r"\bcould you\b", r"\bplease\b",
]
DEADLINE_PATTERNS = {
    'friday': r"\b(vendredi|ven\.?|friday|fri\.?)\b", 'monday': r"\b(lundi|monday|mon\.?)\b", 'tomorrow': r"\b(demain|tomorrow)\b",
    'tonight': r"\b(ce soir|tonight)\b", 'next_week': r"\b(la semaine prochaine|next week)\b",
    'date': r"\b(\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?)\b", 'delay': r"\bdans (\d+) (heures|jours|h|j)\b|in (\d+) (hours|days|h|d)\b",
}
MENTION = r"@([\w.-]+)"

# Ajoute des patterns d'exclusion pour réduire les faux positifs
EXCLUSION_PATTERNS = [r"\bhier\b", r"\bj'ai fait\b", r"\byesterday\b", r"\bfaudrait\b", r"\bje devrais\b"]

def detect_commitment(text: str) -> dict | None:
    """
    Retourne {'is_commitment': bool, 'deadline_raw': str|None, 'mentioned': list[str], 'confidence': float}
    ou None. confidence = 0.6 si pattern engagement seul, 0.8 si + échéance, 0.9 si + mention.
    """
    text_lower = text.lower()
    
    # 1. Si un pattern d'exclusion (passé/conditionnel) se trouve avant un pattern d'engagement, retourner None.
    for excl in EXCLUSION_PATTERNS:
        excl_match = re.search(excl, text, re.IGNORECASE)
        if excl_match:
            for comm in COMMITMENT_PATTERNS:
                comm_match = re.search(comm, text, re.IGNORECASE)
                if comm_match and excl_match.start() < comm_match.start():
                    return None
            return None

    # 2. Chercher les mentions @bob et les destinataires écrits "Bob, ...".
    mentions = [mention.lower() for mention in re.findall(MENTION, text)]
    leading_name = re.match(r"^\s*([A-ZÀ-ÖØ-Ý][\w.-]{1,30})\s*[,;:]", text)
    if leading_name and leading_name.group(1).lower() not in mentions:
        mentions.insert(0, leading_name.group(1).lower())

    # 3. Chercher si un des COMMITMENT_PATTERNS matche. Si non, retourner None (échéance seule ou mention seule = None).
    is_commitment = False
    for pattern in COMMITMENT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            is_commitment = True
            break
    if not is_commitment:
        is_commitment = any(re.search(pattern, text, re.IGNORECASE) for pattern in REQUEST_PATTERNS)
            
    if not is_commitment:
        return None

    # 4. Chercher les DEADLINE_PATTERNS.
    deadline_raw = None
    for key, pattern in DEADLINE_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            deadline_raw = match.group(0)
            break

    # 5. Calculer le score de confiance selon la règle (0.6, 0.8 ou 0.9).
    confidence = 0.6
    if deadline_raw:
        confidence = 0.8
        if mentions:
            confidence = 0.9
    elif mentions:
        confidence = 0.9

    return {
        'is_commitment': True,
        'deadline_raw': deadline_raw,
        'mentioned': mentions,
        'confidence': confidence
    }
