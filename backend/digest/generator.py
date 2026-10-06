"""Catch-Me-Up digest generation with Groq model routing and local fallback."""

from __future__ import annotations

import re
import json
import logging
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)
SUMMARY_PROMPT_VERSION = "speaker-voice-v3"


URGENT_PATTERN = re.compile(r"\b(urgent|asap|bloqu(?:é|e)|prod|incident)\b", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@([\w.-]+)")

LANGUAGE_LABELS = {
    "french": "français",
    "english": "anglais",
    "fusha": "arabe standard",
    "darija_arabic": "darija en arabe",
    "darija_latin": "darija en alphabet latin",
}

MODEL_FALLBACKS = {
    "arabic": [
        "allam-2-7b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
    ],
    "general": [
        "openai/gpt-oss-120b",
        "allam-2-7b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
    ],
}


def _detect_language(messages: list[dict[str, Any]]) -> str:
    """Return a practical default language for the conversation."""
    text = " ".join(str(message.get("content", "")) for message in messages)
    if re.search(r"[\u0600-\u06ff]", text):
        darija_words = re.findall(r"\b(شنو|واش|بزاف|كاين|علاش|بغيت|دابا|غادي)\b", text, re.IGNORECASE)
        return "darija_arabic" if darija_words else "fusha"
    french_words = len(re.findall(r"\b(le|la|les|des|une|avec|pour|dans|est|pas|bonjour|merci)\b", text, re.IGNORECASE))
    english_words = len(re.findall(r"\b(the|and|with|for|this|that|is|are|please|thanks)\b", text, re.IGNORECASE))
    return "french" if french_words >= english_words else "english"


def _language_name(language: str) -> str:
    return LANGUAGE_LABELS.get(language, language or "la langue détectée")


def _language_instruction(language: str) -> tuple[str, str]:
    if language == "fusha":
        return (
            "اكتب الملخص والنقاط المهمة باللغة العربية الفصحى فقط. لا تستخدم الفرنسية أو الإنجليزية.",
            "أنت مساعد ذكي يلخص محادثات العمل بدقة وبشكل شامل.",
        )
    if language == "darija_arabic":
        return (
            "كتب الملخص والنقاط المهمة بالدارجة المغربية بالحروف العربية فقط. ما تستعملش الفرنسية أو الإنجليزية.",
            "أنت مساعد ذكي كيلخص محادثات العمل بدقة وبشكل شامل.",
        )
    if language == "darija_latin":
        return (
            "Ktəb l-molakhas w nqat l-mohimma b-darija l-maghribiya b-l7orof latin. Ma تستعملch français wla anglais.",
            "Nta assistant ذكي kaylakhkhes l-mohadatat b-d9a w b-chkl شامل.",
        )
    if language == "english":
        return (
            "Write the summary and key points in English only. Do not use French or Arabic.",
            "You are an assistant that produces accurate, global chat summaries.",
        )
    return (
        "Écris le résumé et les points importants uniquement en français. N'utilise pas l'anglais ni l'arabe.",
        "Tu es un assistant qui produit des résumés globaux et fiables de conversations.",
    )


def _voice_instruction(language: str, chat_type: str) -> str:
    if chat_type == "group":
        if language == "fusha":
            return "هذه محادثة جماعية. ابدأ كل سطر باسم المتحدث متبوعاً بـ :، وحافظ على صيغة المتكلم والمخاطب. لا تقل قال أو ذكرت أو أوضح."
        if language == "darija_arabic":
            return "هادي محادثة جماعية. بدا كل سطر بسميّة المتكلم ومن بعدها :، وحافظ على أنا ونتا/نتي وحنا. ما تستعملش قال أو ذكرت أو شرح."
        if language == "darija_latin":
            return "Hadi mohadatha jama3iya. Bda kol star b smiyet li tkalem w mn ba3d :; khalli ana, nta/nti w 7na. Ma tgolch قال ولا ذكرت ولا شرح."
        if language == "english":
            return "This is a group chat. Start every line with the speaker name followed by ':'. Keep first-person and direct-address wording. Never write 'said that', 'explained that', or 'announced that'."
        return "C'est un groupe. Commence chaque ligne par le nom de la personne suivi de « : ». Garde Je, Tu et Nous ainsi que les tâches adressées directement. N'écris jamais « a dit que », « a expliqué que » ou « a annoncé que »."
    if language == "fusha":
        return "هذه محادثة خاصة. لا تضع أي اسم في بداية الملخص. اكتب كأن المتحدث الأصلي يتكلم مباشرة بصيغة أنا، مع الحفاظ على أنت ونحن. لا تستخدم صيغة الغائب أو قال أو ذكرت."
    if language == "darija_arabic":
        return "هادي محادثة خاصة. ما تحط حتى سميّة فبداية الملخص. كتب بحال المتكلم الأصلي كيهضر مباشرة بصيغة أنا، وخلي نتا/نتي وحنا. ما تستعملش صيغة الغائب أو قال أو ذكرت."
    if language == "darija_latin":
        return "Hadi mohadatha khassa. Ma t7et 7ta smiya f l-bidaya. Kteb b7al li tkalem kayhder مباشرة b ana, w khalli nta/nti w 7na. Ma tsta3melch صيغة الغائب."
    if language == "english":
        return "This is a private chat. Do not put any name at the beginning. Write as a condensed direct quote from the original speaker using 'I', 'you', and 'we'. Never narrate in the third person."
    return "C'est une conversation privée. N'ajoute aucun nom au début. Écris comme une citation directe condensée de l'expéditeur avec Je, Tu et Nous. Ne raconte jamais la situation à la troisième personne."


def _model_candidates(language: str) -> list[str]:
    family = "arabic" if language in {"fusha", "darija_arabic", "darija_latin"} else "general"
    if family == "arabic":
        configured = [
            os.environ.get("GROQ_MODEL_ARABIC", "allam-2-7b").strip(),
            os.environ.get("GROQ_MODEL_ARABIC_FALLBACK", "qwen/qwen3.8-27b").strip(),
            os.environ.get("GROQ_MODEL_GENERAL", "openai/gpt-oss-120b").strip(),
        ]
        max_models = 3
    else:
        configured = [
            os.environ.get("GROQ_MODEL_GENERAL", "openai/gpt-oss-120b").strip(),
            os.environ.get("GROQ_MODEL_GENERAL_FALLBACK", "allam-2-7b").strip(),
            os.environ.get("GROQ_MODEL_FALLBACK", "openai/gpt-oss-20b").strip(),
            os.environ.get("GROQ_MODEL_GENERAL_LAST_FALLBACK", "qwen/qwen3.8-27b").strip(),
        ]
        max_models = 4
    configured.extend(MODEL_FALLBACKS[family])
    return list(dict.fromkeys(model for model in configured if model))[:max_models]


def _ai_digest(messages: list[dict[str, Any]], language: str, username: str, chat_type: str) -> dict[str, Any] | None:
    """Ask Groq for a concise summary, returning None when it is unavailable."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key or not messages:
        return None

    transcript = "\n".join(
        f"[{message.get('id')}] {message.get('sender_username', 'Utilisateur')}: {message.get('content', '')}"
        for message in messages[-120:]
    )
    language_instruction, system_instruction = _language_instruction(language)
    voice_instruction = _voice_instruction(language, chat_type)
    prompt = f"""Tu es l'assistant Catch-Me-Up d'une application de chat.
Résume uniquement les messages non lus fournis ci-dessous.
{language_instruction}
Type de conversation : {"groupe" if chat_type == "group" else "privée"}.
L'utilisateur connecté est « {username or 'utilisateur'} », mais tu dois respecter le point de vue des expéditeurs et non raconter la situation de l'extérieur.
{voice_instruction}
Retourne uniquement un JSON valide avec cette forme :
{{"summary":"résumé de 2 à 4 phrases", "key_points":[{{"message_id":"id", "text":"point important"}}]}}
Règles :
- Fais une synthèse globale par sujets : ne fais jamais un résumé séparé pour chaque message.
- Regroupe les informations qui parlent du même sujet en une seule phrase fluide.
- Pour un groupe, produis 2 à 4 lignes regroupées par personne ou par sujet, chaque ligne commençant par « Nom : ».
- Pour un privé, produis un seul texte continu sans nom et à la première personne de l'expéditeur.
- Identifie les décisions, demandes, urgences, blocages et prochaines étapes.
- Ne fabrique aucune information.
- Ne propose pas de conseils ni d'aide en dehors des faits de la conversation.
- Utilise au maximum 6 points clés.
- Chaque message_id doit exister dans le transcript.

Messages non lus :
{transcript}"""
    for model in _model_candidates(language):
        payload_data = {
            "model": model,
            "temperature": 0.2,
            "max_tokens": 2400 if model.startswith("openai/") else 1200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
        }
        if model.startswith("openai/gpt-oss"):
            payload_data["reasoning_effort"] = "low"
        payload = json.dumps(payload_data).encode("utf-8")
        request = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "FlowDesk/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            result = json.loads(content)
            if not isinstance(result, dict) or not isinstance(result.get("summary"), str):
                continue
            source_messages = {_message_id(message): message for message in messages}
            points = []
            raw_points = result.get("key_points", [])
            for point in raw_points if isinstance(raw_points, list) else []:
                if not isinstance(point, dict) or not isinstance(point.get("text"), str):
                    continue
                source = source_messages.get(str(point.get("message_id")))
                if source and point["text"].strip():
                    points.append({**_key_point(source), "text": point["text"].strip()[:280]})
            points = points[:6]
            summary = result["summary"].strip()[:1200]
            if summary and _valid_voice_summary(summary, messages, chat_type, language):
                return {"summary": summary, "key_points": points, "language": language, "model": model}
        except urllib.error.HTTPError as error:
            logger.warning("Groq digest model %s returned HTTP %s", model, error.code)
        except (urllib.error.URLError, TimeoutError, KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
            logger.warning("Groq digest model %s failed (%s)", model, type(error).__name__)
            continue
    return None


def _message_id(message: dict[str, Any]) -> str:
    return str(message.get("id", ""))


def _valid_voice_summary(summary: str, messages: list[dict[str, Any]], chat_type: str, language: str) -> bool:
    """Reject narrator-style output before it reaches the user."""
    forbidden = re.compile(
        r"\b(a dit que|a expliqué que|a annoncé que|said that|explained that|announced that)\b|"
        r"\b(il|elle|ils|elles)\s+(a dit|a expliqué|a annoncé)\b|"
        r"\b(قال|ذكرت|ذكر|أوضح|أوضحت)\b",
        re.IGNORECASE,
    )
    if forbidden.search(summary):
        return False
    if chat_type != "group":
        if any(summary.lower().startswith(f"{str(message.get('sender_username', '')).lower()} :") for message in messages):
            return False
        first_person_patterns = {
            "french": r"\b(je|j'|nous|mon|ma|mes|moi|tu|ton|ta)\b",
            "english": r"\b(i|we|my|me|you|your)\b",
            "fusha": r"(أنا|نحن|أريد|أحتاج|يجب|لي|لدي)",
            "darija_arabic": r"(أنا|حنا|بغيت|خاصني|عندي|نتا|نتي)",
            "darija_latin": r"\b(ana|7na|bghit|khasni|3ndi|nta|nti)\b",
        }
        return bool(re.search(first_person_patterns.get(language, first_person_patterns["french"]), summary, re.IGNORECASE))
    names = {str(message.get("sender_username", "")).strip() for message in messages if message.get("sender_username")}
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    return bool(lines) and all(any(line.lower().startswith(f"{name.lower()} :") for name in names) for line in lines)


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _timestamp_sort_key(message: dict[str, Any]) -> float:
    timestamp = _parse_timestamp(message.get("created_at"))
    if timestamp is None:
        return float("-inf")
    return timestamp.timestamp()


def _rule_reply_count(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return messages that have replies, ordered by reply count descending."""
    reply_counts = Counter(
        str(message.get("reply_to_id"))
        for message in messages
        if message.get("reply_to_id") is not None
    )
    positions = {_message_id(message): index for index, message in enumerate(messages)}
    candidates = [message for message in messages if _message_id(message) in reply_counts]
    return sorted(
        candidates,
        key=lambda message: (-reply_counts[_message_id(message)], positions[_message_id(message)]),
    )


def _rule_urgent(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return explicitly urgent messages and messages containing urgent keywords."""
    return [
        message
        for message in messages
        if bool(message.get("is_urgent"))
        or bool(URGENT_PATTERN.search(str(message.get("content", ""))))
    ]


def _rule_time_gaps(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the first message and the first message after every two-hour gap."""
    if not messages:
        return []

    ordered = sorted(
        enumerate(messages),
        key=lambda pair: (_timestamp_sort_key(pair[1]), pair[0]),
    )
    selected = [ordered[0][1]]
    previous_timestamp = _parse_timestamp(ordered[0][1].get("created_at"))

    for _, message in ordered[1:]:
        timestamp = _parse_timestamp(message.get("created_at"))
        if timestamp and previous_timestamp and (timestamp - previous_timestamp).total_seconds() > 2 * 60 * 60:
            selected.append(message)
        if timestamp:
            previous_timestamp = timestamp

    return selected


def _rule_mentions(messages: list[dict[str, Any]], username: str) -> list[dict[str, Any]]:
    """Return the four most recent messages mentioning the current user."""
    if not username:
        return []

    mention_pattern = re.compile(rf"@{re.escape(username)}\b", re.IGNORECASE)
    matching = [
        message
        for message in messages
        if mention_pattern.search(str(message.get("content", "")))
    ]

    return [
        {
            "message_id": _message_id(message),
            "preview": str(message.get("content", ""))[:160],
            "username": str(message.get("sender_username", "")),
            "ts": str(message.get("created_at", "")),
        }
        for message in reversed(matching[-4:])
    ]


def _key_point(message: dict[str, Any], chat_type: str = "direct") -> dict[str, str]:
    text = str(message.get("content", ""))[:280]
    if chat_type == "group" and message.get("sender_username"):
        text = f"{message['sender_username']} : {text}"
    return {
        "text": text,
        "message_id": _message_id(message),
        "ts": str(message.get("created_at", "")),
        "username": str(message.get("sender_username", "")),
    }


def _local_voice_summary(messages: list[dict[str, Any]], chat_type: str) -> str:
    """Keep the fallback in the same speaker voice as the AI contract."""
    if not messages:
        return "Aucun nouveau message dans cette période."
    if chat_type != "group":
        return " ".join(
            str(message.get("content", "")).strip()
            for message in messages
            if str(message.get("content", "")).strip()
        )[:1200]

    by_sender: dict[str, list[str]] = {}
    for message in messages:
        sender = str(message.get("sender_username", "Utilisateur"))
        content = str(message.get("content", "")).strip()
        if content:
            by_sender.setdefault(sender, []).append(content)
    return "\n".join(
        f"{sender} : {' '.join(contents)}"
        for sender, contents in by_sender.items()
    )[:1200]


def build_digest(
    messages: list[dict[str, Any]],
    me: dict[str, Any],
    since: Any,
    until: Any,
    lang_pref: str | None = None,
    use_ai: bool = False,
    chat_type: str = "direct",
) -> dict[str, Any]:
    """Build an AI digest with a deterministic local fallback."""

    supported_languages = set(LANGUAGE_LABELS)
    language = lang_pref if lang_pref in supported_languages else _detect_language(messages)

    username = str(me.get("username", ""))
    unique_participants = {
        str(message.get("sender_username"))
        for message in messages
        if message.get("sender_username")
    }

    decision_count = sum(
        1
        for message in messages
        if message.get("is_decision") is True
        or message.get("message_type") == "decision"
    )

    reply_points = _rule_reply_count(messages)
    urgent_points = _rule_urgent(messages)
    gap_points = _rule_time_gaps(messages)

    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for message in [*urgent_points, *reply_points, *gap_points]:
        message_id = _message_id(message)
        if message_id in seen_ids:
            continue
        seen_ids.add(message_id)
        candidates.append(message)

    candidates.sort(
        key=_timestamp_sort_key,
    )
    key_points = [_key_point(message, chat_type) for message in candidates[:6]]

    summary = _local_voice_summary(messages, chat_type)

    ai_result = _ai_digest(messages, language, username, chat_type) if use_ai else None
    if ai_result:
        summary = ai_result["summary"]
        key_points = ai_result["key_points"] or key_points

    return {
        "since": str(since),
        "until": str(until),
        "summary": summary,
        "key_points": key_points,
        "mentions": _rule_mentions(messages, username),
        "summary_language": ai_result["language"] if ai_result else language,
        "stats": {
            "message_count": len(messages),
            "participants": len(unique_participants),
            "decisions_count": decision_count,
            # The API enriches this field with the room's current open actions.
            "open_items": 0,
            "summary_language": ai_result["language"] if ai_result else language,
            "summary_model": ai_result.get("model") if ai_result else "local-heuristic",
            "summary_prompt_version": SUMMARY_PROMPT_VERSION,
        },
    }
