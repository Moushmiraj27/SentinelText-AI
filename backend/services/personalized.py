"""Account-scoped mapper and deterministic coping recommendation logic."""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from backend.models import Journal, ManualPattern, Recommendation, Relation
from backend.services.analysis import reported_activities, reported_emotions


SUGGESTIONS = {
    "walking": "If it suits you, consider a short walk or stepping outside for fresh air.",
    "talking with someone": "You could consider sharing one thing on your mind with someone you trust.",
    "breathing": "Try a comfortable, unhurried breathing pause for a minute or two; stop if it feels uncomfortable.",
    "mindfulness": "Pause to notice a few things around you, without needing to change how you feel.",
    "taking a break": "Consider stepping away from one task briefly and returning when you are ready.",
    "journaling": "Write a few lines about what feels present, without needing to solve it now.",
    "listening to music": "You could listen to a song or playlist you choose and notice how the pause feels.",
    "screen break": "Consider putting a screen aside briefly and doing something restful instead.",
    "relaxing activity": "Spend a few minutes with a low-pressure activity you enjoy, if one comes to mind.",
}
TOPIC_OPTIONS = {
    "academics": ("taking a break", "journaling"),
    "work": ("taking a break", "walking", "journaling"),
    "relationships": ("talking with someone", "journaling"),
    "family": ("talking with someone", "journaling"),
    "personal": ("walking", "mindfulness", "journaling"),
}
EMOTION_OPTIONS = {
    "stress": ("breathing", "taking a break"),
    "anxiety": ("breathing", "mindfulness"),
    "sadness": ("talking with someone", "walking"),
    "frustration": ("taking a break", "walking"),
}
CRISIS_RE = re.compile(r"\b(?:suicid(?:e|al|ality)|kill myself|end my life|hurt myself|self[- ]harm|don't want to live|do not want to live|can't keep myself safe|cannot keep myself safe)\b", re.I)


def mapper_patterns(db, user_id: str) -> list[dict]:
    """Aggregate repeated per-entry relations, joining only the owner's journals."""
    rows = (
        db.query(Relation)
        .join(Journal, Journal.id == Relation.journal_id)
        .filter(Relation.user_id == user_id, Journal.user_id == user_id)
        .order_by(Journal.created_at.desc(), Relation.id.desc())
        .all()
    )
    groups: dict[tuple[str, str, str], list[Relation]] = defaultdict(list)
    for row in rows:
        key = (row.situation.casefold().strip(), row.emotion.casefold().strip(), (row.activity or "").casefold().strip())
        groups[key].append(row)

    output = []
    for items in groups.values():
        items.sort(key=lambda item: item.journal.created_at, reverse=True)
        first = items[0]
        sources = {}
        for item in items:
            journal = item.journal
            sources[journal.id] = {
                "id": journal.id,
                "date": journal.created_at.isoformat() + "Z",
                "transcript": journal.transcript,
                "emotion_explicitly_reported": item.emotion in reported_emotions(journal.transcript),
            }
        states = {item.status for item in items}
        status = "confirmed" if "confirmed" in states else "rejected" if states == {"rejected"} else "suggested"
        output.append({
            "id": min(item.id for item in items),
            "relation_ids": [item.id for item in items],
            "situation": first.situation,
            "emotion": first.emotion,
            "emotion_label": "Explicitly reported" if all(source["emotion_explicitly_reported"] for source in sources.values()) else "Language label; not explicitly stated in every entry",
            "activity": first.activity,
            "status": status,
            "frequency": len(sources),
            "entries": list(sources.values()),
            "date": first.journal.created_at.isoformat() + "Z",
            "manual": False,
        })
    for item in db.query(ManualPattern).filter_by(user_id=user_id).order_by(ManualPattern.created_at.desc()).all():
        sources = []
        if item.journal and item.journal.user_id == user_id:
            sources.append({
                "id": item.journal.id,
                "date": item.journal.created_at.isoformat() + "Z",
                "transcript": item.journal.transcript,
                "emotion_explicitly_reported": item.emotion in reported_emotions(item.journal.transcript),
            })
        output.append({
            "id": f"manual-{item.id}",
            "relation_ids": [],
            "situation": item.situation,
            "emotion": item.emotion,
            "emotion_label": "User-entered pattern",
            "activity": item.activity,
            "status": item.status,
            "frequency": 1,
            "entries": sources,
            "date": (item.created_at.isoformat() + "Z"),
            "manual": True,
        })
    return sorted(output, key=lambda pattern: (-pattern["frequency"], pattern["situation"].casefold(), pattern["emotion"].casefold()))


def build_recommendations(db, user_id: str) -> dict:
    journals = db.query(Journal).filter_by(user_id=user_id).order_by(Journal.created_at.desc()).limit(150).all()
    history = db.query(Recommendation).filter_by(user_id=user_id).order_by(Recommendation.created_at.desc()).all()
    relations = db.query(Relation).filter_by(user_id=user_id, status="confirmed").order_by(Relation.id.desc()).all()
    manual_patterns = db.query(ManualPattern).filter_by(user_id=user_id, status="confirmed").order_by(ManualPattern.id.desc()).all()
    serialized_history = [
        {"id": row.id, "activity": row.activity, "feedback": row.feedback, "created_at": row.created_at.isoformat() + "Z"}
        for row in history
    ]
    if not journals and not manual_patterns:
        return {"items": [], "history": serialized_history, "has_journals": False, "safety_alert": False, "safety_message": None}

    safety_alert = any(CRISIS_RE.search(row.transcript) for row in journals[:5])
    if safety_alert:
        return {
            "items": [], "history": serialized_history, "has_journals": True, "safety_alert": True,
            "safety_message": "Some words in a recent entry may point to immediate danger. If you may hurt yourself or cannot stay safe, contact your local emergency number or crisis support service now, and reach out to someone you trust. SentinelText is not monitored and cannot provide emergency support.",
        }

    feedback_helpful = Counter(row.activity for row in history if row.feedback == "helpful")
    feedback_somewhat = Counter(row.activity for row in history if row.feedback == "somewhat_helpful")
    avoid = {row.activity for row in history if row.feedback == "not_helpful"}
    recent_cutoff = datetime.utcnow() - timedelta(days=14)
    recent_rows = [row for row in history if row.created_at >= recent_cutoff]
    recent_feedback = {row.activity for row in recent_rows if row.feedback is not None}
    pending = {row.activity: row for row in recent_rows if row.feedback is None and row.activity not in avoid}

    reported_sources: dict[str, Journal] = {}
    topic_sources: dict[str, list[Journal]] = defaultdict(list)
    emotion_sources: dict[str, list[Journal]] = defaultdict(list)
    for journal in journals:
        for activity in reported_activities(journal.transcript):
            reported_sources.setdefault(activity, journal)
        for topic in set(json.loads(journal.topics or "[]")):
            topic_sources[topic].append(journal)
        emotion_sources[journal.emotion].append(journal)

    confirmed_activity: dict[str, tuple[str, int | None]] = {}
    for relation in relations:
        if relation.activity in SUGGESTIONS:
            confirmed_activity.setdefault(relation.activity, (relation.situation, relation.journal_id))
    for pattern in manual_patterns:
        if pattern.activity in SUGGESTIONS:
            confirmed_activity.setdefault(pattern.activity, (pattern.situation, pattern.journal_id))

    evidence: dict[str, dict] = {}
    def offer(activity: str, score: int, explanation: str, source_ids: list[int] | None = None):
        if activity not in SUGGESTIONS:
            return
        current = evidence.get(activity)
        if not current or score > current["score"]:
            evidence[activity] = {"score": score, "explanation": explanation, "source_entry_ids": source_ids or []}

    for activity, journal in reported_sources.items():
        offer(activity, 100, f"You previously wrote that {activity} helped. This suggestion is based on that entry.", [journal.id])
    for activity, (situation, journal_id) in confirmed_activity.items():
        offer(activity, 80, f"You confirmed a pattern mentioning {activity} with {situation}. This is an association you confirmed, not a claim that one caused the other.", [journal_id] if journal_id else [])
    for activity, count in feedback_helpful.items():
        offer(activity, 70 + min(count, 10), "You marked this activity helpful before.")
    for activity, count in feedback_somewhat.items():
        offer(activity, 40 + min(count, 10), "You previously said this activity was somewhat helpful.")

    topic_counts = Counter({topic: len(items) for topic, items in topic_sources.items()})
    for topic, count in topic_counts.items():
        options = TOPIC_OPTIONS.get(topic, ())
        if options:
            ids = [row.id for row in topic_sources[topic][:5]]
            for activity in options:
                offer(activity, 30 + min(count, 10), f"{count} of your saved entries mention {topic}. {activity.title()} is an optional activity to explore; you have not reported it as helpful.", ids)

    emotion_counts = Counter({emotion: len(items) for emotion, items in emotion_sources.items()})
    for emotion, count in emotion_counts.items():
        for activity in EMOTION_OPTIONS.get(emotion, ()):
            ids = [row.id for row in emotion_sources[emotion][:5]]
            offer(activity, 15 + min(count, 10), f"The {emotion} language label appears in {count} of your recent entries. {activity.title()} is a general option to consider, not a claim about what will change how you feel.", ids)

    if not evidence and journals:
        offer("journaling", 1, "You have saved reflections but have not mentioned an activity that helped yet. Journaling is a general option to explore, not a pattern inferred about you.")
        offer("taking a break", 1, "You have saved reflections but have not mentioned an activity that helped yet. A short break is a general option to explore, not a pattern inferred about you.")

    ordered = sorted(evidence.items(), key=lambda item: (item[0] in avoid, item[0] in recent_feedback, -item[1]["score"], item[0]))
    selected: list[tuple[str, Recommendation, dict]] = []
    for activity in pending:
        if activity in evidence:
            selected.append((activity, pending[activity], evidence[activity]))
    used = {activity for activity, _, _ in selected}
    for activity, detail in ordered:
        if activity in used or activity in avoid or activity in recent_feedback:
            continue
        recommendation = Recommendation(user_id=user_id, journal_id=detail["source_entry_ids"][0] if detail["source_entry_ids"] else (journals[0].id if journals else None), activity=activity, description=SUGGESTIONS[activity])
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        selected.append((activity, recommendation, detail))
        used.add(activity)
        if len(selected) == 4:
            break

    items = [{
        "id": recommendation.id,
        "activity": activity,
        "description": SUGGESTIONS[activity],
        "helpful_count": feedback_helpful[activity],
        "explanation": detail["explanation"],
        "source_entry_ids": detail["source_entry_ids"],
        "source_situation": confirmed_activity.get(activity, (None, None))[0] if activity in confirmed_activity else None,
    } for activity, recommendation, detail in selected[:4]]
    return {"items": items, "history": serialized_history, "has_journals": bool(journals), "safety_alert": False, "safety_message": None}
