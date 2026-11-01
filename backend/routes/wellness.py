"""Journal, analysis, mapper, recommendations, and settings endpoints."""
import base64
import hashlib
import importlib.util
import json
import re
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.auth.security import user_key
from backend.database import get_db
from backend.models import EchoPreference, EchoThemeFeedback, Journal, ManualPattern, ProfileSetting, Recommendation, Relation
from backend.schemas import MAX_AUDIO_BYTES, ConsentInput, EchoPreferenceInput, EchoThemeFeedbackInput, FeedbackInput, JournalInput, MapperPatternInput, RelationInput
from backend.services.analysis import SITUATIONS, Groq, analyze, encode, llm_reflection, matches, prior_related, reported_activities
from backend.services.echo import build_echo
from backend.services.personalized import build_recommendations, mapper_patterns


router = APIRouter()
ALLOWED_AUDIO_TYPES = {"audio/webm", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-wav", "audio/mpeg", "audio/aac", "audio/flac"}


def _audio_type_is_allowed(value: str | None) -> bool:
    if not value or len(value) > 100 or any(char in value for char in "\r\n<>"):
        return False
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type in ALLOWED_AUDIO_TYPES and bool(re.fullmatch(r"audio/[a-z0-9.+-]+", media_type))


def _audio_signature_is_valid(content: bytes, media_type: str) -> bool:
    signatures = {
        "audio/webm": lambda data: data.startswith(b"\x1a\x45\xdf\xa3"),
        "audio/mp4": lambda data: len(data) >= 8 and data[4:8] == b"ftyp",
        "audio/ogg": lambda data: data.startswith(b"OggS"),
        "audio/wav": lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE",
        "audio/x-wav": lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE",
        "audio/mpeg": lambda data: data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0),
        "audio/aac": lambda data: len(data) >= 2 and data[0] == 0xFF and data[1] & 0xF6 == 0xF0,
        "audio/flac": lambda data: data.startswith(b"fLaC"),
    }
    return len(content) >= 4 and signatures[media_type](content)


@router.get("/health")
def health():
    similarity = os.getenv("SENTENCE_TRANSFORMER_MODEL") or ("TF-IDF cosine similarity" if importlib.util.find_spec("sklearn") else "topic overlap fallback")
    return {
        "status": "online",
        "whisper": bool(os.getenv("GROQ_API_KEY")),
        "llm_reflections": bool(os.getenv("GROQ_API_KEY")),
        "emotion_model": os.getenv("SENTINEL_EMOTION_MODEL") or "transparent lexicon baseline",
        "semantic_similarity": similarity,
    }


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), user: str = Depends(user_key)):
    if not _audio_type_is_allowed(audio.content_type):
        raise HTTPException(415, "Upload an audio recording.")
    content = await audio.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Recording must be smaller than 20 MB.")
    if not _audio_signature_is_valid(content, audio.content_type.split(";", 1)[0].strip().lower()):
        raise HTTPException(415, "The uploaded file does not match its audio format.")
    if not os.getenv("GROQ_API_KEY") or not Groq:
        raise HTTPException(503, "Whisper transcription is not configured. Add GROQ_API_KEY or edit the browser transcript.")
    try:
        result = Groq(api_key=os.getenv("GROQ_API_KEY"), timeout=30).audio.transcriptions.create(
            file=(audio.filename or "journal.webm", content),
            model=os.getenv("GROQ_WHISPER_MODEL", "whisper-large-v3"),
            response_format="json",
        )
        return {"transcript": result.text}
    except Exception as exc:
        raise HTTPException(502, "Transcription could not be completed. You can still save a written reflection.") from exc


@router.post("/journals")
def create_journal(payload: JournalInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    text = payload.transcript.strip()
    if len(text) < 2:
        raise HTTPException(422, "Write or transcribe a little more before saving.")
    analysis = analyze(text)
    journal = Journal(
        user_id=user,
        transcript=text,
        emotion=analysis["emotion"],
        confidence=analysis["confidence"],
        sentiment=analysis["sentiment"],
        topics=json.dumps(analysis["topics"]),
        phrases=json.dumps(analysis["phrases"]),
    )
    if payload.audio_data:
        encoded_audio = payload.audio_data.split(",", 1)[-1]
        if len(encoded_audio) > ((MAX_AUDIO_BYTES + 2) // 3) * 4:
            raise HTTPException(413, "Recording must be smaller than 20 MB.")
        audio_type = payload.audio_type or "audio/webm"
        if not _audio_type_is_allowed(audio_type):
            raise HTTPException(422, "Choose a supported audio recording format.")
        try:
            raw = base64.b64decode(encoded_audio, validate=True)
            if len(raw) > 20 * 1024 * 1024:
                raise ValueError("Audio is too large.")
            if not _audio_signature_is_valid(raw, audio_type.split(";", 1)[0].strip().lower()):
                raise ValueError("Audio format is invalid.")
            journal.audio = raw
            journal.audio_type = audio_type
        except Exception as exc:
            raise HTTPException(422, "Audio attachment could not be read.") from exc

    db.add(journal)
    db.commit()
    db.refresh(journal)
    related = prior_related(db, user, journal)
    for situation in matches(text, SITUATIONS) or analysis["topics"]:
        db.add(Relation(user_id=user, journal_id=journal.id, situation=situation, emotion=analysis["emotion"]))
    for activity in reported_activities(text):
        db.add(Relation(user_id=user, journal_id=journal.id, situation="User-reported helpful activity", emotion="relief reported", activity=activity))
    echo_preference = db.query(EchoPreference).filter_by(user_id=user).first()
    reflection = llm_reflection(text, analysis, related) if echo_preference and echo_preference.external_ai_consent else None
    if reflection:
        journal.reflection = reflection
    db.commit()
    db.refresh(journal)
    return {"journal": encode(journal), "analysis": analysis, "reflection_configured": bool(reflection)}


@router.get("/journals")
def journals(q: Optional[str] = None, user: str = Depends(user_key), db: Session = Depends(get_db)):
    rows = db.query(Journal).filter_by(user_id=user).order_by(Journal.created_at.desc()).limit(150).all()
    if q:
        query = q.casefold()
        rows = [row for row in rows if query in row.transcript.casefold() or query in row.emotion.casefold() or query in (row.topics or "").casefold()]
    return [encode(row, True) for row in rows]


@router.delete("/journals/{journal_id}")
def delete_journal(journal_id: int, user: str = Depends(user_key), db: Session = Depends(get_db)):
    journal = db.query(Journal).filter_by(id=journal_id, user_id=user).first()
    if not journal:
        raise HTTPException(404, "Journal entry not found.")
    theme_key = hashlib.sha256(f"journal:{journal.id}".casefold().encode()).hexdigest()
    db.query(EchoThemeFeedback).filter_by(user_id=user, theme_key=theme_key).delete()
    db.query(Relation).filter_by(user_id=user, journal_id=journal_id).delete()
    db.query(ManualPattern).filter_by(user_id=user, journal_id=journal_id).update({"journal_id": None})
    db.query(Recommendation).filter_by(user_id=user, journal_id=journal_id).update({"journal_id": None})
    db.delete(journal)
    db.commit()
    return {"deleted": True}


@router.delete("/journals")
def delete_all(user: str = Depends(user_key), db: Session = Depends(get_db)):
    db.query(Relation).filter_by(user_id=user).delete()
    db.query(ManualPattern).filter_by(user_id=user).delete()
    db.query(Recommendation).filter_by(user_id=user).delete()
    db.query(EchoThemeFeedback).filter_by(user_id=user).delete()
    db.query(EchoPreference).filter_by(user_id=user).delete()
    db.query(ProfileSetting).filter_by(user_id=user).delete()
    db.query(Journal).filter_by(user_id=user).delete()
    db.commit()
    return {"deleted": True}


@router.get("/echo")
def echo(days: Optional[int] = None, user: str = Depends(user_key), db: Session = Depends(get_db)):
    if days is not None and days not in (7, 30, 90):
        raise HTTPException(422, "Choose a 7, 30, or 90 day range.")
    return build_echo(db, user, days)


@router.put("/echo/themes/{theme_key}")
def update_echo_theme(theme_key: str, payload: EchoThemeFeedbackInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    if len(theme_key) != 64 or any(char not in "0123456789abcdef" for char in theme_key):
        raise HTTPException(404, "Theme not found.")
    if len(payload.title.strip()) < 2:
        raise HTTPException(422, "Enter a theme title with at least two characters.")
    # Only accept a key that can be produced from this user's current journal data.
    current = build_echo(db, user, 90)
    theme = next((item for item in current["themes"] if item["key"] == theme_key), None)
    if not theme:
        raise HTTPException(404, "Theme not found.")
    item = db.query(EchoThemeFeedback).filter_by(user_id=user, theme_key=theme_key).first()
    if not item:
        item = EchoThemeFeedback(user_id=user, theme_key=theme_key, title=payload.title.strip(), status=payload.status)
        db.add(item)
    else:
        item.title = payload.title.strip()
        item.status = payload.status
    db.commit()
    return {"saved": True, "key": theme_key, "title": item.title, "status": item.status}


@router.put("/echo/preferences")
def update_echo_preference(payload: EchoPreferenceInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    preference = db.query(EchoPreference).filter_by(user_id=user).first()
    if not preference:
        preference = EchoPreference(user_id=user, external_ai_consent=int(payload.external_ai_consent))
        db.add(preference)
    else:
        preference.external_ai_consent = int(payload.external_ai_consent)
    db.commit()
    return {"external_ai_consent": bool(preference.external_ai_consent)}


@router.get("/mapper")
def mapper(user: str = Depends(user_key), db: Session = Depends(get_db)):
    rows = db.query(Relation).filter_by(user_id=user).order_by(Relation.id.desc()).all()
    return [{"id": row.id, "journal_id": row.journal_id, "situation": row.situation, "emotion": row.emotion, "activity": row.activity, "status": row.status, "date": row.journal.created_at.isoformat() + "Z"} for row in rows]


@router.get("/mapper/patterns")
def mapper_patterns_endpoint(user: str = Depends(user_key), db: Session = Depends(get_db)):
    return mapper_patterns(db, user)


@router.post("/mapper/patterns", status_code=201)
def add_mapper_pattern(payload: MapperPatternInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    journal = db.query(Journal).filter_by(id=payload.journal_id, user_id=user).first() if payload.journal_id is not None else None
    if payload.journal_id is not None and not journal:
        raise HTTPException(404, "Choose one of your own journal entries as the source for this pattern.")
    situation, emotion, activity = payload.situation.strip(), payload.emotion.strip(), payload.activity.strip()
    if min(len(situation), len(emotion), len(activity)) < 2:
        raise HTTPException(422, "Enter a situation, emotion, and helpful activity.")
    existing = db.query(ManualPattern).filter_by(user_id=user, situation=situation, emotion=emotion, activity=activity).first()
    if existing:
        existing.status = "confirmed"
        if journal:
            existing.journal_id = journal.id
        relation = existing
    else:
        relation = ManualPattern(user_id=user, journal_id=journal.id if journal else None, situation=situation, emotion=emotion, activity=activity, status="confirmed")
        db.add(relation)
    db.commit()
    db.refresh(relation)
    return {"saved": True, "id": f"manual-{relation.id}", "status": relation.status}


@router.put("/mapper/patterns/{pattern_id}")
def update_mapper_pattern(pattern_id: str, payload: RelationInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    if pattern_id.startswith("manual-"):
        try:
            manual_id = int(pattern_id.removeprefix("manual-"))
        except ValueError as exc:
            raise HTTPException(404, "Pattern not found.") from exc
        manual = db.query(ManualPattern).filter_by(id=manual_id, user_id=user).first()
        if not manual:
            raise HTTPException(404, "Pattern not found.")
        manual.situation = payload.situation.strip() if payload.situation is not None else manual.situation
        manual.emotion = payload.emotion.strip() if payload.emotion is not None else manual.emotion
        manual.activity = payload.activity.strip() if payload.activity is not None else manual.activity
        if min(len(manual.situation), len(manual.emotion), len(manual.activity)) < 2:
            raise HTTPException(422, "Pattern fields must contain meaningful text.")
        manual.status = payload.status
        db.commit()
        return {"id": pattern_id, "status": manual.status, "situation": manual.situation, "emotion": manual.emotion, "activity": manual.activity}
    if not pattern_id.isdigit():
        raise HTTPException(404, "Pattern not found.")
    anchor = db.query(Relation).filter_by(id=int(pattern_id), user_id=user).first()
    if not anchor:
        raise HTTPException(404, "Pattern not found.")
    query = db.query(Relation).filter_by(user_id=user, situation=anchor.situation, emotion=anchor.emotion)
    query = query.filter(Relation.activity.is_(None)) if anchor.activity is None else query.filter_by(activity=anchor.activity)
    rows = query.all()
    situation = payload.situation.strip() if payload.situation is not None else anchor.situation
    emotion = payload.emotion.strip() if payload.emotion is not None else anchor.emotion
    activity = payload.activity.strip() if payload.activity is not None else anchor.activity
    if len(situation) < 2 or len(emotion) < 2 or (activity is not None and not activity):
        raise HTTPException(422, "Pattern fields must contain meaningful text.")
    for relation in rows:
        relation.situation, relation.emotion, relation.activity, relation.status = situation, emotion, activity, payload.status
    db.commit()
    return {"id": pattern_id, "status": payload.status, "situation": situation, "emotion": emotion, "activity": activity}


@router.put("/mapper/{item_id}")
def update_mapper(item_id: int, payload: RelationInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    relation = db.query(Relation).filter_by(id=item_id, user_id=user).first()
    if not relation:
        raise HTTPException(404, "Relationship not found.")
    relation.status = payload.status
    if payload.situation is not None:
        relation.situation = payload.situation
    if payload.emotion is not None:
        relation.emotion = payload.emotion
    if payload.activity is not None:
        relation.activity = payload.activity
    db.commit()
    return {"id": relation.id, "status": relation.status, "situation": relation.situation, "activity": relation.activity}


@router.get("/recommendations")
def recommendations(user: str = Depends(user_key), db: Session = Depends(get_db)):
    return build_recommendations(db, user)


@router.post("/recommendations/{item_id}/feedback")
def feedback(item_id: int, payload: FeedbackInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    recommendation = db.query(Recommendation).filter_by(id=item_id, user_id=user).first()
    if not recommendation:
        raise HTTPException(404, "Recommendation not found.")
    recommendation.feedback = payload.feedback
    db.commit()
    return {"saved": True, "feedback": recommendation.feedback}


@router.get("/dashboard")
def dashboard(period: Literal["week", "month", "quarter"] = "month", user: str = Depends(user_key), db: Session = Depends(get_db)):
    # Aggregates are always limited to the authenticated account.
    all_rows = db.query(Journal).filter_by(user_id=user).order_by(Journal.created_at.desc()).all()
    now = datetime.utcnow()
    span = {"week": 7, "month": 30, "quarter": 90}[period]
    cutoff = now - timedelta(days=span - 1)
    rows = [row for row in all_rows if row.created_at >= cutoff]
    days = [(now - timedelta(days=offset)).date() for offset in range(span - 1, -1, -1)]
    daily = {day: {"count": 0, "emotions": Counter()} for day in days}
    for row in rows:
        bucket = daily.get(row.created_at.date())
        if bucket is not None:
            bucket["count"] += 1
            bucket["emotions"][row.emotion] += 1
    trend = [{"date": day.isoformat(), "count": daily[day]["count"], "emotions": dict(daily[day]["emotions"])} for day in days]
    week = [now - timedelta(days=offset) for offset in range(6, -1, -1)]
    weekly = [{"day": day.strftime("%a"), "count": sum(row.created_at.date() == day.date() for row in all_rows)} for day in week]
    return {
        "period": period,
        "entry_count": len(rows),
        "total_entry_count": len(all_rows),
        "this_week": sum(row.created_at >= now - timedelta(days=7) for row in all_rows),
        "emotion_counts": dict(Counter(row.emotion for row in rows)),
        "trend": trend,
        "recent": [encode(row) for row in rows[:3]],
        "latest_emotion": rows[0].emotion if rows else None,
        "weekly": weekly,
    }


@router.get("/settings")
def settings(user: str = Depends(user_key), db: Session = Depends(get_db)):
    setting = db.query(ProfileSetting).filter_by(user_id=user).first()
    return {"recording_consent": bool(setting and setting.recording_consent)}


@router.post("/settings")
def save_settings(payload: ConsentInput, user: str = Depends(user_key), db: Session = Depends(get_db)):
    setting = db.query(ProfileSetting).filter_by(user_id=user).first()
    if not setting:
        setting = ProfileSetting(user_id=user)
        db.add(setting)
    setting.recording_consent = int(payload.recording_consent)
    db.commit()
    return {"recording_consent": payload.recording_consent}
