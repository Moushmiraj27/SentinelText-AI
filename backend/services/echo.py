"""Account-scoped, local-first Emotional Echo analysis."""
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from backend.models import EchoPreference, EchoThemeFeedback, Journal


def _utc_now() -> datetime:
    # Existing journal timestamps are naive UTC; normalize new clock reads to match.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clean_terms(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z'-]{2,}", text.casefold())


def _make_groups(rows: list[Journal]) -> list[list[Journal]]:
    """Group entries by cosine similarity, with a topic-overlap fallback."""
    size = len(rows)
    if not size:
        return []
    if size == 1:
        return [[rows[0]]]
    scores: dict[tuple[int, int], float] = {}
    try:
        model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "").strip()
        if model_name:
            from sklearn.neighbors import NearestNeighbors
            from sentence_transformers import SentenceTransformer
            from backend.services.analysis import _sentence_model

            embeddings = _sentence_model(model_name, SentenceTransformer).encode([row.transcript for row in rows], normalize_embeddings=True)
            neighbors = NearestNeighbors(n_neighbors=min(12, size), metric="cosine").fit(embeddings)
            distances, indices = neighbors.kneighbors(embeddings)
            for left, (row_distances, row_indices) in enumerate(zip(distances, indices)):
                for distance, right in zip(row_distances, row_indices):
                    if left < int(right):
                        scores[left, int(right)] = 1.0 - float(distance)
            similarity_threshold = 0.55
        else:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.neighbors import NearestNeighbors

            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000).fit_transform([row.transcript for row in rows])
            distances, indices = NearestNeighbors(n_neighbors=min(12, size), metric="cosine").fit(matrix).kneighbors(matrix)
            for left, (row_distances, row_indices) in enumerate(zip(distances, indices)):
                for distance, right in zip(row_distances, row_indices):
                    if left < int(right):
                        scores[left, int(right)] = 1.0 - float(distance)
            similarity_threshold = 0.16
    except Exception:
        # The optional local sentence model may be missing or unavailable; use local TF-IDF.
        similarity_threshold = 0.16
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.neighbors import NearestNeighbors

            matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000).fit_transform([row.transcript for row in rows])
            distances, indices = NearestNeighbors(n_neighbors=min(12, size), metric="cosine").fit(matrix).kneighbors(matrix)
            for left, (row_distances, row_indices) in enumerate(zip(distances, indices)):
                for distance, right in zip(row_distances, row_indices):
                    if left < int(right):
                        scores[left, int(right)] = 1.0 - float(distance)
        except (ImportError, ValueError):
            pass

    parent = list(range(size))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    row_topics = [set(json.loads(row.topics or "[]")) for row in rows]
    for (left, right), similarity in scores.items():
        if similarity >= similarity_threshold or (row_topics[left] & row_topics[right] and similarity >= 0.04):
            a, b = find(left), find(right)
            if a != b:
                parent[b] = a
    groups: dict[int, list[Journal]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[find(index)].append(row)
    return list(groups.values())


def _theme_identity(group: list[Journal]) -> tuple[str, str, str]:
    texts = [row.transcript for row in group]
    terms: Counter[str] = Counter()
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=1500)
        matrix = vectorizer.fit_transform(texts)
        totals = matrix.sum(axis=0).A1
        terms.update({word: float(score) for word, score in zip(vectorizer.get_feature_names_out(), totals)})
    except (ImportError, ValueError):
        for text in texts:
            terms.update(term for term in _clean_terms(text) if term not in {"today", "really", "thing", "things", "feel", "felt"})
    keywords = [word for word, _ in terms.most_common(3)]
    if not keywords:
        keywords = sorted({topic for row in group for topic in json.loads(row.topics or "[]")})[:3]
    title = " & ".join(word.title() for word in keywords[:2]) or "Shared wording"
    # Anchor the feedback key to the oldest source journal so adding new entries
    # does not silently reset a user's decision about an otherwise stable theme.
    key_material = f"journal:{min(row.id for row in group)}"
    key = hashlib.sha256(key_material.casefold().encode()).hexdigest()
    explanation = f"These entries use related words around {', '.join(keywords)}." if keywords else "These entries share similar wording in your journal."
    return key, title, explanation


def _entry(row: Journal) -> dict:
    text = row.transcript.strip()
    return {
        "id": row.id,
        "date": row.created_at.isoformat() + "Z",
        "emotion": row.emotion,
        "excerpt": text[:240] + ("…" if len(text) > 240 else ""),
        "transcript": text,
    }


def local_reflections(themes: list[dict], emotion_counts: Counter, rows: list[Journal]) -> list[dict]:
    reflections = []
    for theme in themes[:2]:
        reflections.append({
            "text": f"The words “{theme['topic']}” appear across {theme['count']} of your entries in this period. You might notice what feels similar or different between those moments.",
            "source_entry_ids": [entry["id"] for entry in theme["entries"][:3]],
            "kind": "pattern_summary",
        })
    if rows and emotion_counts:
        emotion, count = emotion_counts.most_common(1)[0]
        reflections.append({
            "text": f"You recorded “{emotion}” language in {count} of {len(rows)} entries in this period. This is a count of your saved labels, not a measure of how you feel overall.",
            "source_entry_ids": [row.id for row in rows if row.emotion == emotion][:3],
            "kind": "recorded_summary",
        })
    return reflections


def _optional_ai_reflections(rows: list[Journal], themes: list[dict]) -> list[dict] | None:
    """Use Groq only after a separate, persisted opt-in; failures use local copy."""
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    try:
        from groq import Groq

        evidence = [{"id": row.id, "text": row.transcript[:1000], "recorded_emotion": row.emotion} for row in rows[:30]]
        result = Groq(api_key=key, timeout=10).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0.1,
            max_tokens=260,
            messages=[
                {"role": "system", "content": "Write at most two short, gentle, non-diagnostic reflections based only on the supplied journal excerpts. Do not infer causes, events, diagnoses, or facts not stated. Treat recorded emotion labels as user-reported labels, not measurements. Cite supporting entry ids as source_entry_ids. Return JSON array with objects text and source_entry_ids. If evidence is insufficient, return []."},
                {"role": "user", "content": json.dumps({"themes": [{"title": t["title"], "count": t["count"]} for t in themes[:6]], "entries": evidence})},
            ],
            response_format={"type": "json_object"},
        )
        payload = json.loads(result.choices[0].message.content or "{}")
        values = payload.get("reflections", []) if isinstance(payload, dict) else payload
        allowed_ids = {row.id for row in rows[:30]}
        output = []
        for item in values[:2]:
            text = str(item.get("text", "")).strip()[:500]
            refs = [int(value) for value in item.get("source_entry_ids", []) if str(value).isdigit() and int(value) in allowed_ids]
            if text and refs:
                output.append({"text": text, "source_entry_ids": refs, "kind": "ai_interpretation"})
        return output or None
    except Exception:
        return None


def build_echo(db, user_id: str, days: int | None = 90) -> dict:
    all_rows = db.query(Journal).filter_by(user_id=user_id).order_by(Journal.created_at.desc()).all()
    groups = _make_groups(all_rows)
    active_keys = set()
    all_themes = []
    for group in groups:
        if len(group) < 2:
            continue
        key, title, explanation = _theme_identity(group)
        active_keys.add(key)
        all_themes.append((key, title, explanation, group))

    # Feedback tied to themes with no remaining source entries is removed after journal deletion.
    feedback_rows = db.query(EchoThemeFeedback).filter_by(user_id=user_id).all()
    stale = [item for item in feedback_rows if item.theme_key not in active_keys]
    for item in stale:
        db.delete(item)
    if stale:
        db.flush()
    feedback = {item.theme_key: item for item in feedback_rows if item.theme_key in active_keys}

    if days is None:
        rows = all_rows
        oldest_day = min((row.created_at.date() for row in rows), default=_utc_now().date())
        trend_days = min(90, max(7, (_utc_now().date() - oldest_day).days + 1))
    else:
        cutoff = _utc_now() - timedelta(days=days)
        rows = [row for row in all_rows if row.created_at >= cutoff]
        trend_days = days
    emotion_counts = Counter(row.emotion for row in rows)
    themes = []
    for key, title, explanation, group in all_themes:
        matched = group if days is None else [row for row in group if row.created_at >= cutoff]
        if len(matched) < 2:
            continue
        saved = feedback.get(key)
        chosen_title = saved.title if saved else title
        themes.append({
            "key": key,
            "topic": title,
            "title": chosen_title,
            "count": len(matched),
            "explanation": explanation,
            "status": saved.status if saved else "suggested",
            "entries": [_entry(row) for row in matched],
        })
    themes.sort(key=lambda item: (-item["count"], item["title"].casefold()))

    daily: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        daily[row.created_at.date().isoformat()][row.emotion] += 1
    today = _utc_now().date()
    daily_trend = []
    for offset in range(trend_days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        daily_trend.append({"date": day, "emotions": dict(daily.get(day, {})), "count": sum(daily.get(day, {}).values())})
    trend = [{"date": row.created_at.isoformat() + "Z", "emotion": row.emotion, "confidence": row.confidence} for row in reversed(rows)]

    preference = db.query(EchoPreference).filter_by(user_id=user_id).first()
    has_consent = bool(preference and preference.external_ai_consent)
    reflections = local_reflections(themes, emotion_counts, rows)
    ai_available = bool(os.getenv("GROQ_API_KEY"))
    ai_reflections = _optional_ai_reflections(rows, themes) if has_consent and ai_available else None
    if ai_reflections:
        reflections = ai_reflections
    db.flush()
    return {
        "total_entries": len(rows),
        "all_time_entries": len(all_rows),
        "days": days,
        "themes": themes,
        "emotion_counts": dict(emotion_counts),
        "trend": trend,
        "daily_trend": daily_trend,
        "reflections": reflections,
        "reflection_configured": ai_available,
        "reflection_generated": bool(ai_reflections),
        "ai_fallback": bool(has_consent and ai_available and not ai_reflections),
        "ai_provider_available": ai_available,
        "ai_consent": has_consent,
        "feedback_history": [
            {"key": key, "title": item.title, "status": item.status, "updated_at": item.updated_at.isoformat() + "Z"}
            for key, item in feedback.items()
        ],
    }
