"""Transparent text analysis and optional AI/similarity services."""
import base64
import json
import os
import re
from functools import lru_cache
from typing import Any

from backend.models import Journal

try:
    from groq import Groq
except ImportError:
    Groq = None


EMOTIONS = {
    "stress": ["overwhelmed", "pressure", "stressed", "deadline", "workload", "falling behind", "too much"],
    "anxiety": ["worried", "worry", "nervous", "uncertain", "afraid", "anxious", "can't stop thinking"],
    "sadness": ["sad", "lonely", "empty", "miss", "down", "hopeless", "crying"],
    "frustration": ["frustrated", "angry", "annoyed", "argument", "irritated", "upset"],
    "happiness": ["happy", "excited", "joy", "grateful", "proud", "good day", "looking forward"],
    "calm": ["calm", "peaceful", "relaxed", "rested", "okay", "content", "at ease"],
}
TOPICS = {
    "academics": ["exam", "assignment", "study", "class", "college", "school", "grade", "deadline"],
    "work": ["work", "office", "project", "manager", "job", "career", "meeting"],
    "relationships": ["friend", "partner", "relationship", "argument", "conversation", "roommate"],
    "family": ["family", "parent", "mother", "father", "sister", "brother", "home"],
    "personal": ["myself", "future", "sleep", "health", "routine", "confidence"],
}
COPING = {
    "walking": ["walk", "walking", "went outside", "fresh air"],
    "talking with someone": ["talked to", "talking to", "called my friend", "shared with"],
    "breathing": ["breathing", "breath exercise", "slow breaths"],
    "mindfulness": ["meditat", "mindful", "grounding"],
    "taking a break": ["break", "rested", "stepped away"],
    "journaling": ["wrote", "journal", "writing it down"],
    "listening to music": ["music", "song", "playlist", "listened to"],
    "screen break": ["screen break", "put my phone away", "stepped away from my screen"],
    "relaxing activity": ["hobby", "painted", "gardening", "read a book"],
}
SITUATIONS = {
    "examinations and deadlines": ["exam", "assignment", "deadline", "workload"],
    "relationship conversations": ["argument", "partner", "friend", "relationship"],
    "work demands": ["work", "office", "manager", "meeting"],
    "family moments": ["family", "parent", "mother", "father"],
}
EXPLICIT_EMOTION_STATES = {
    "stress": ["stressed", "overwhelmed", "under pressure"],
    "anxiety": ["anxious", "worried", "nervous", "afraid", "uncertain"],
    "sadness": ["sad", "lonely", "empty", "down", "hopeless"],
    "frustration": ["frustrated", "angry", "annoyed", "irritated", "upset"],
    "happiness": ["happy", "excited", "joyful", "grateful", "proud"],
    "calm": ["calm", "peaceful", "relaxed", "rested", "content", "at ease"],
}


def matches(text: str, mapping: dict[str, list[str]]) -> list[str]:
    low = text.lower()
    return [label for label, terms in mapping.items() if any(term in low for term in terms)]


def reported_emotions(text: str) -> list[str]:
    """Find emotion labels stated with a first-person feeling cue."""
    cue = r"(?:i\s+(?:feel|felt|am|was|have been|became|got)|i['’]m|feeling)\s+(?:(?:very|really|so|quite|a little|a bit)\s+)?"
    low = text.casefold()
    return [label for label, states in EXPLICIT_EMOTION_STATES.items() if any(re.search(r"\b" + cue + re.escape(state) + r"\b", low) for state in states)]


def reported_activities(text: str) -> list[str]:
    low = text.lower()
    helpful_cues = ("helped", "helps", "help me", "feel better", "felt better", "feel calmer", "felt calmer", "relieved", "relaxing", "works for me", "enjoy", "grateful for")
    if not any(cue in low for cue in helpful_cues):
        return []
    return matches(text, COPING)


@lru_cache(maxsize=2)
def _emotion_classifier(model_name: str, pipeline_factory: Any) -> Any:
    return pipeline_factory("text-classification", model=model_name, top_k=1)


def analyze(text: str) -> dict:
    scores = {name: sum(text.lower().count(term) for term in terms) for name, terms in EMOTIONS.items()}
    emotion, hits = max(scores.items(), key=lambda item: item[1])
    confidence = round(min(0.9, 0.5 + hits * 0.1), 2) if hits else 0.0
    if not hits:
        emotion = "mixed / unclear"

    model_name = os.getenv("SENTINEL_EMOTION_MODEL", "").strip()
    if model_name:
        try:
            from transformers import pipeline

            predictions = _emotion_classifier(model_name, pipeline)(text[:4000], truncation=True)
            if predictions and isinstance(predictions[0], list):
                predictions = predictions[0]
            result = predictions[0]
            label = str(result["label"]).lower()
            label_map = {"anger": "frustration", "disgust": "frustration", "fear": "anxiety", "sadness": "sadness", "joy": "happiness", "surprise": "mixed / unclear", "neutral": "mixed / unclear"}
            emotion = label_map.get(label, label)
            confidence = round(float(result["score"]), 2)
        except Exception:
            # Optional model failure intentionally falls back to the local baseline.
            pass

    positive = scores["happiness"] + scores["calm"]
    negative = sum(scores[name] for name in ("stress", "anxiety", "sadness", "frustration"))
    sentiment = "positive language" if positive > negative else "difficult language" if negative > positive else "mixed / unclear"
    phrases = [part[:180] for part in re.split(r"(?<=[.!?])\s+|\n", text.strip()) if any(term in part.lower() for terms in EMOTIONS.values() for term in terms)][:4]
    return {"emotion": emotion, "confidence": confidence, "sentiment": sentiment, "topics": matches(text, TOPICS), "phrases": phrases}


def encode(journal: Journal, include_audio: bool = False) -> dict:
    data = {
        "id": journal.id,
        "transcript": journal.transcript,
        "emotion": journal.emotion,
        "confidence": journal.confidence,
        "sentiment": journal.sentiment,
        "topics": json.loads(journal.topics or "[]"),
        "phrases": json.loads(journal.phrases or "[]"),
        "reflection": journal.reflection,
        "created_at": journal.created_at.isoformat() + "Z",
        "has_audio": bool(journal.audio),
    }
    if include_audio and journal.audio:
        data["audio_data"] = "data:" + (journal.audio_type or "audio/webm") + ";base64," + base64.b64encode(journal.audio).decode()
    return data


def llm_reflection(text: str, analysis: dict, related: tuple | list = ()) -> str | None:
    key = os.getenv("GROQ_API_KEY")
    if not key or not Groq:
        return None
    try:
        context = "; ".join(f"{item['emotion']} on {item['date']}: {item['topic']}" for item in related)
        result = Groq(api_key=key, timeout=8).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0.3,
            max_tokens=120,
            messages=[
                {"role": "system", "content": "Offer a brief, gentle, non-diagnostic reflection grounded only in the journal text and supplied prior themes. Ask one open question. Do not claim certainty or prescribe treatment."},
                {"role": "user", "content": json.dumps({"journal": text[:3000], "analysis": analysis, "previous_sessions": context})},
            ],
        )
        return result.choices[0].message.content
    except Exception:
        return None


@lru_cache(maxsize=2)
def _sentence_model(model_name: str, model_factory: Any) -> Any:
    return model_factory(model_name)


def prior_related(db, user_id: str, current: Journal) -> list[dict]:
    previous = db.query(Journal).filter(Journal.user_id == user_id, Journal.id != current.id).order_by(Journal.created_at.desc()).limit(30).all()
    topics = json.loads(current.topics or "[]")
    ranked = []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        texts = [current.transcript] + [journal.transcript for journal in previous]
        model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "").strip()
        if model_name:
            try:
                from sentence_transformers import SentenceTransformer

                matrix = _sentence_model(model_name, SentenceTransformer).encode(texts, normalize_embeddings=True)
                scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
            except Exception:
                model_name = ""
        if not model_name:
            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000).fit_transform(texts)
            scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
        ranked = sorted(zip(previous, scores), key=lambda pair: pair[1], reverse=True)
    except (ImportError, ValueError):
        ranked = [(journal, 1.0 if set(topics) & set(json.loads(journal.topics or "[]")) else 0.0) for journal in previous]
        ranked.sort(key=lambda pair: pair[1], reverse=True)

    related = []
    for journal, score in ranked:
        shared = set(topics) & set(json.loads(journal.topics or "[]"))
        if score >= 0.08 or shared:
            related.append({"date": journal.created_at.strftime("%b %d"), "emotion": journal.emotion, "topic": sorted(shared)[0] if shared else "similar wording", "similarity": round(float(score), 2)})
        if len(related) == 4:
            break
    return related
