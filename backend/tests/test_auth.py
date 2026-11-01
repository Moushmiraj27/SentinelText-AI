"""End-to-end auth tests against an isolated temporary SQLite database."""
import os
import json
import hashlib
import tempfile
import unittest
from unittest.mock import patch
from fastapi import Response

TEST_DB = os.path.join(tempfile.gettempdir(), f"sentinel-auth-tests-{os.getpid()}.db")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("VERCEL", None)
os.environ.pop("AWS_LAMBDA_FUNCTION_NAME", None)
os.environ["SENTINEL_DB_PATH"] = TEST_DB
os.environ["JWT_SECRET_KEY"] = "test-only-secret-that-is-long-enough-for-jwt-validation-0001"
os.environ["COOKIE_SECURE"] = "false"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from fastapi.testclient import TestClient
from jose import jwt
from api.index import app as vercel_app
from backend.main import app
from backend.auth.security import set_session_cookie
from backend.wellness import COOKIE_NAME, Base, EchoPreference, EchoThemeFeedback, PasswordReset, Recommendation, Relation, Journal, User, ProfileSetting, engine, SessionLocal


class AuthFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        engine.dispose()
        try:
            os.remove(TEST_DB)
        except FileNotFoundError:
            pass

    def setUp(self):
        self.client.cookies.clear()
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_FROM", None)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            db.add(Journal(user_id="legacy-browser-profile", transcript="An older private journal entry", emotion="calm", confidence=0.0, sentiment="mixed / unclear", topics="[]", phrases="[]"))
            db.commit()

    def signup(self, name, email, password="StrongPassword123"):
        return self.client.post("/api/auth/register", json={"name": name, "email": email, "password": password, "terms_accepted": True})

    def test_auth_sessions_password_reset_and_user_isolation(self):
        self.assertIs(vercel_app, app)
        self.assertEqual(self.client.get("/").json()["service"], "SentinelText")
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200, health.text)
        self.assertIn("semantic_similarity", health.json())
        cors = self.client.options("/api/auth/me", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
        self.assertEqual(cors.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(cors.headers.get("access-control-allow-credentials"), "true")
        # Protected API rejects anonymous callers.
        self.assertEqual(self.client.get("/api/journals").status_code, 401)
        self.assertEqual(self.signup("New User", "terms@example.com", "StrongPassword123").status_code, 201)
        for period in ("week", "month", "quarter"):
            self.assertEqual(self.client.get(f"/api/dashboard?period={period}").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard?period=year").status_code, 422)
        empty_dashboard = self.client.get("/api/dashboard?period=month").json()
        self.assertEqual(empty_dashboard["entry_count"], 0)
        self.assertEqual(empty_dashboard["total_entry_count"], 0)
        self.assertEqual(empty_dashboard["recent"], [])
        self.assertEqual(len(empty_dashboard["trend"]), 30)
        self.client.post("/api/auth/logout")
        missing_terms = self.client.post("/api/auth/register", json={"name":"No Terms", "email":"terms2@example.com", "password":"StrongPassword123", "terms_accepted":False})
        weak_password = self.client.post("/api/auth/register", json={"name":"Weak Pass", "email":"weak@example.com", "password":"short", "terms_accepted":True})
        self.assertEqual(missing_terms.status_code, 422)
        self.assertEqual(weak_password.status_code, 422)
        self.assertEqual(self.client.post("/api/auth/forgot-password", json={"email":"alex@example.com"}).status_code, 503)

        created = self.signup("Alex Example", "alex@example.com")
        self.assertEqual(created.status_code, 201, created.text)
        self.assertTrue(created.cookies.get(COOKIE_NAME))
        self.assertIn("httponly", created.headers.get("set-cookie", "").lower())
        alex_id = created.json()["user"]["id"]
        self.assertEqual(self.client.get("/api/auth/me").json()["user"]["id"], alex_id)

        duplicate = self.signup("Alex Again", "ALEX@example.com")
        self.assertEqual(duplicate.status_code, 409)
        bad_login = self.client.post("/api/auth/login", json={"email": "alex@example.com", "password": "WrongPassword123"})
        self.assertEqual(bad_login.status_code, 401)

        saved = self.client.post("/api/journals", json={"transcript": "I feel worried about my upcoming exam."})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(len(self.client.get("/api/journals").json()), 1)
        alex_dashboard = self.client.get("/api/dashboard?period=month").json()
        self.assertEqual(alex_dashboard["entry_count"], 1)
        self.assertEqual(sum(alex_dashboard["emotion_counts"].values()), 1)
        self.assertEqual(alex_dashboard["recent"][0]["transcript"], "I feel worried about my upcoming exam.")
        self.assertEqual(len(alex_dashboard["trend"]), 30)

        # Logout revokes this session server-side, not just in the browser.
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/journals").status_code, 401)

        created_b = self.signup("Blair Example", "blair@example.com")
        self.assertEqual(created_b.status_code, 201, created_b.text)
        blair_id = created_b.json()["user"]["id"]
        self.assertNotEqual(alex_id, blair_id)
        self.assertEqual(self.client.get("/api/journals").json(), [])
        self.client.post("/api/journals", json={"transcript": "A calm walk outside helped me feel better."})
        blair_dashboard = self.client.get("/api/dashboard?period=week").json()
        self.assertEqual(blair_dashboard["entry_count"], 1)
        self.assertEqual(sum(blair_dashboard["emotion_counts"].values()), 1)
        self.assertIn("calm walk", blair_dashboard["recent"][0]["transcript"])
        # A forged legacy identity header is ignored; account ownership comes from the cookie.
        only_blair = self.client.get("/api/journals", headers={"X-User-Id": alex_id}).json()
        self.assertEqual(len(only_blair), 1)
        self.assertIn("calm walk", only_blair[0]["transcript"])
        self.client.post("/api/auth/logout")

        # A tampered/expired JWT cannot access protected endpoints.
        expired = jwt.encode({"sub": alex_id, "sv": 1, "exp": 1}, os.environ["JWT_SECRET_KEY"], algorithm="HS256")
        self.client.cookies.set(COOKIE_NAME, expired, path="/api")
        self.assertEqual(self.client.get("/api/journals").status_code, 401)
        self.client.cookies.clear()

        # Reset email contains a random, single-use token; only a hash is persisted.
        captured = {}
        os.environ["SMTP_HOST"] = "smtp.example.test"
        os.environ["SMTP_FROM"] = "no-reply@example.test"
        with patch("backend.routes.auth.send_reset_email", side_effect=lambda email, token: captured.update(email=email, token=token)):
            requested = self.client.post("/api/auth/forgot-password", json={"email": "blair@example.com"})
        self.assertEqual(requested.status_code, 202)
        self.assertEqual(captured["email"], "blair@example.com")
        reset = self.client.post("/api/auth/reset-password", json={"token": captured["token"], "password": "NewSecurePassword456"})
        self.assertEqual(reset.status_code, 200, reset.text)
        self.assertEqual(self.client.post("/api/auth/reset-password", json={"token": captured["token"], "password": "AnotherPassword789"}).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "blair@example.com", "password": "StrongPassword123"}).status_code, 401)
        self.assertEqual(self.client.post("/api/auth/login", json={"email": "blair@example.com", "password": "NewSecurePassword456"}).status_code, 200)

        with SessionLocal() as db:
            stored = db.query(User).filter_by(email="alex@example.com").one()
            self.assertNotEqual(stored.password_hash, "StrongPassword123")
            self.assertTrue(stored.password_hash.startswith("$argon2"))
            self.assertEqual(db.query(Journal).count(), 3)
            self.assertIsNotNone(db.query(Journal).filter_by(user_id="legacy-browser-profile").first())
            self.assertEqual(db.query(Relation).count(), 2)

    def test_audio_validation_and_all_journal_data_cleanup(self):
        self.assertEqual(self.signup("Audio User", "audio@example.com").status_code, 201)
        invalid_type = self.client.post("/api/journals", json={"transcript": "A journal with a bad audio type", "audio_type": "text/html", "audio_data": "data:text/html;base64,SGVsbG8="})
        self.assertEqual(invalid_type.status_code, 422)
        invalid_signature = self.client.post("/api/journals", json={"transcript": "A journal with an invalid audio file", "audio_type": "audio/webm", "audio_data": "data:audio/webm;base64,SGVsbG8="})
        self.assertEqual(invalid_signature.status_code, 422)
        saved = self.client.post("/api/journals", json={"transcript": "A journal with webm audio", "audio_type": "audio/webm;codecs=opus", "audio_data": "data:audio/webm;base64,GkXfow=="})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertTrue(saved.json()["journal"]["has_audio"])
        audio_entry = self.client.get("/api/journals").json()[0]
        self.assertTrue(audio_entry["audio_data"].startswith("data:audio/webm;codecs=opus;base64,"))
        rejected_upload = self.client.post("/api/transcribe", files={"audio": ("clip.html", b"<html>", "text/html")})
        self.assertEqual(rejected_upload.status_code, 415)
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            unavailable = self.client.post("/api/transcribe", files={"audio": ("clip.webm", bytes.fromhex("1a45dfa3"), "audio/webm")})
        self.assertEqual(unavailable.status_code, 503)
        user_id = self.client.get("/api/auth/me").json()["user"]["id"]
        self.client.put("/api/echo/preferences", json={"external_ai_consent": True})
        self.client.post("/api/settings", json={"recording_consent": True})
        with SessionLocal() as db:
            db.add(EchoThemeFeedback(user_id=user_id, theme_key="a" * 64, title="Work", status="confirmed"))
            db.commit()
        self.client.delete("/api/journals")
        with SessionLocal() as db:
            self.assertEqual(db.query(Journal).filter_by(user_id=user_id).count(), 0)
            self.assertEqual(db.query(EchoPreference).count(), 0)
            self.assertEqual(db.query(EchoThemeFeedback).count(), 0)
            self.assertEqual(db.query(ProfileSetting).count(), 0)

    def test_serverless_session_cookie_defaults_to_secure(self):
        user = User(id="secure-cookie-test", session_version=0)
        with patch.dict(os.environ, {"VERCEL": "1"}):
            os.environ.pop("COOKIE_SECURE", None)
            response = Response()
            set_session_cookie(response, user)
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertIn("samesite=lax", cookie)

    def test_emotional_echo_themes_feedback_deletion_and_filters(self):
        created = self.signup("Echo User", "echo@example.com")
        self.assertEqual(created.status_code, 201)
        user_id = created.json()["user"]["id"]
        empty_response = self.client.get("/api/echo?days=7")
        self.assertEqual(empty_response.status_code, 200, empty_response.text)
        empty = empty_response.json()
        self.assertEqual(empty["total_entries"], 0)
        self.assertEqual(empty["trend"], [])
        self.assertEqual(len(empty["daily_trend"]), 7)
        self.assertEqual(empty["themes"], [])

        first = self.client.post("/api/journals", json={"transcript": "At work my project deadline feels overwhelming. I feel stressed and worried about falling behind."}).json()["journal"]
        single = self.client.get("/api/echo?days=30").json()
        self.assertEqual(single["total_entries"], 1)
        self.assertEqual(single["themes"], [])
        self.assertTrue(single["reflections"])
        second = self.client.post("/api/journals", json={"transcript": "Work has been busy with a project deadline. I feel stressed and worried about falling behind at the office."}).json()["journal"]
        echo = self.client.get("/api/echo?days=30").json()
        self.assertEqual(echo["total_entries"], 2)
        self.assertTrue(echo["themes"], "related work/deadline entries should form a theme")
        theme = echo["themes"][0]
        self.assertEqual(theme["count"], 2)
        self.assertEqual({item["id"] for item in theme["entries"]}, {first["id"], second["id"]})

        feedback = self.client.put(f"/api/echo/themes/{theme['key']}", json={"title": "Project pressures", "status": "confirmed"})
        self.assertEqual(feedback.status_code, 200, feedback.text)
        updated = self.client.get("/api/echo?days=30").json()["themes"][0]
        self.assertEqual(updated["title"], "Project pressures")
        self.assertEqual(updated["status"], "confirmed")
        self.assertEqual(self.client.put(f"/api/echo/themes/{theme['key']}", json={"title": "Project pressures", "status": "dismissed"}).status_code, 200)
        dismissed = self.client.get("/api/echo?days=30").json()
        self.assertEqual(dismissed["themes"][0]["status"], "dismissed")
        self.assertEqual(self.client.delete(f"/api/journals/{first['id']}").status_code, 200)
        with SessionLocal() as db:
            deleted_theme_key = hashlib.sha256(f"journal:{first['id']}".casefold().encode()).hexdigest()
            self.assertIsNone(db.query(EchoThemeFeedback).filter_by(user_id=user_id, theme_key=deleted_theme_key).first())
        after_delete = self.client.get("/api/echo?days=30").json()
        self.assertEqual(after_delete["themes"], [])
        self.assertEqual(after_delete["feedback_history"], [])
        self.assertEqual(after_delete["total_entries"], 1)

    def test_emotional_echo_many_entries_date_ranges_and_account_isolation(self):
        created = self.signup("Echo Many", "echo-many@example.com")
        user_id = created.json()["user"]["id"]
        from datetime import datetime, timedelta, timezone
        from backend.services.analysis import analyze
        with SessionLocal() as db:
            for index in range(36):
                text = f"Work project deadline {index} feels busy and stressful. I worry about finishing the project at work."
                result = analyze(text)
                db.add(Journal(user_id=user_id, transcript=text, emotion=result["emotion"], confidence=result["confidence"], sentiment=result["sentiment"], topics=json.dumps(result["topics"]), phrases=json.dumps(result["phrases"])))
            text = "An old reflection about a project deadline at work from last season."
            result = analyze(text)
            db.add(Journal(user_id=user_id, transcript=text, emotion=result["emotion"], confidence=result["confidence"], sentiment=result["sentiment"], topics=json.dumps(result["topics"]), phrases=json.dumps(result["phrases"]), created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=120)))
            db.commit()
        short = self.client.get("/api/echo?days=7").json()
        month = self.client.get("/api/echo?days=30").json()
        quarter = self.client.get("/api/echo?days=90").json()
        self.assertEqual((short["total_entries"], month["total_entries"], quarter["total_entries"]), (36, 36, 36))
        self.assertEqual(quarter["all_time_entries"], 37)
        self.assertEqual(len(quarter["themes"][0]["entries"]), 36)
        default_echo = self.client.get("/api/echo").json()
        self.assertEqual(default_echo["total_entries"], 37)
        self.assertIn("confidence", default_echo["trend"][0])
        theme_key = quarter["themes"][0]["key"]
        self.client.post("/api/auth/logout")
        self.assertEqual(self.signup("Other Echo", "other-echo@example.com").status_code, 201)
        other = self.client.get("/api/echo?days=90").json()
        self.assertEqual(other["total_entries"], 0)
        self.assertEqual(other["themes"], [])
        self.assertEqual(self.client.put(f"/api/echo/themes/{theme_key}", json={"title": "Other user", "status": "confirmed"}).status_code, 404)

    def test_emotional_echo_optional_provider_failure_uses_local_grounded_summary(self):
        self.assertEqual(self.signup("Echo AI", "echo-ai@example.com").status_code, 201)
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch("backend.routes.wellness.llm_reflection") as journal_provider:
            self.client.post("/api/journals", json={"transcript": "I feel anxious about my exam and worried about the assignment."})
            journal_provider.assert_not_called()
        self.assertEqual(self.client.put("/api/echo/preferences", json={"external_ai_consent": True}).status_code, 200)
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}), patch("backend.services.echo._optional_ai_reflections", return_value=None) as provider:
            result = self.client.get("/api/echo?days=30").json()
        provider.assert_called_once()
        self.assertTrue(result["ai_fallback"])
        self.assertTrue(result["reflection_configured"])
        self.assertFalse(result["reflection_generated"])
        self.assertTrue(result["reflections"])
        self.assertTrue(all(item["kind"] != "ai_interpretation" for item in result["reflections"]))
        self.assertIn("anxiety", " ".join(item["text"] for item in result["reflections"]).lower())

    def test_mapper_aggregates_patterns_manual_feedback_sources_and_isolation(self):
        self.assertEqual(self.signup("Mapper Owner", "mapper@example.com").status_code, 201)
        first = self.client.post("/api/journals", json={"transcript": "At work I felt stressed about a project deadline. Taking a walk helped me feel calmer."}).json()["journal"]
        second = self.client.post("/api/journals", json={"transcript": "At work I felt stressed about a project deadline again. Taking a walk helped me feel calmer."}).json()["journal"]
        patterns_response = self.client.get("/api/mapper/patterns")
        self.assertEqual(patterns_response.status_code, 200, patterns_response.text)
        patterns = patterns_response.json()
        work = next(item for item in patterns if item["situation"] == "work demands" and item["emotion"] == "stress")
        self.assertEqual(work["frequency"], 2)
        self.assertEqual(len(work["entries"]), 2)
        self.assertTrue(all(entry["emotion_explicitly_reported"] for entry in work["entries"]))
        self.assertTrue(any(item["activity"] == "walking" for item in patterns))

        added = self.client.post("/api/mapper/patterns", json={"journal_id": first["id"], "situation": "After a long shift", "emotion": "tired", "activity": "listening to music"})
        self.assertEqual(added.status_code, 201, added.text)
        manual_id = added.json()["id"]
        self.assertEqual(self.client.put(f"/api/mapper/patterns/{manual_id}", json={"status": "confirmed", "situation": "After a long shift", "emotion": "tired", "activity": "listening to music"}).status_code, 200)
        self.assertEqual(self.client.put(f"/api/mapper/patterns/{work['id']}", json={"status": "rejected", "situation": "At work", "emotion": "stress", "activity": None}).status_code, 200)
        changed = self.client.get("/api/mapper/patterns").json()
        self.assertTrue(any(item["situation"] == "At work" and item["status"] == "rejected" for item in changed))

        self.client.post("/api/auth/logout")
        self.assertEqual(self.signup("Mapper Other", "mapper-other@example.com").status_code, 201)
        self.assertEqual(self.client.get("/api/mapper/patterns").json(), [])
        self.assertEqual(self.client.put(f"/api/mapper/patterns/{manual_id}", json={"status": "confirmed"}).status_code, 404)
        foreign = self.client.post("/api/mapper/patterns", json={"journal_id": first["id"], "situation": "Private", "emotion": "sad", "activity": "journaling"})
        self.assertEqual(foreign.status_code, 404)

    def test_coping_recommendations_are_grounded_learn_feedback_and_suppress_crisis(self):
        self.assertEqual(self.signup("Coping User", "coping@example.com").status_code, 201)
        empty = self.client.get("/api/recommendations").json()
        self.assertFalse(empty["has_journals"])
        self.assertEqual(empty["items"], [])

        self.client.post("/api/journals", json={"transcript": "At work I felt stressed by the project deadline. Taking a walk helped me feel calmer."})
        self.client.post("/api/journals", json={"transcript": "Another busy work deadline. A walk outside helped me feel better."})
        recommendations = self.client.get("/api/recommendations").json()
        self.assertTrue(recommendations["items"])
        walking = next(item for item in recommendations["items"] if item["activity"] == "walking")
        self.assertIn("wrote that walking helped", walking["explanation"])
        self.assertTrue(walking["source_entry_ids"])
        self.assertEqual(self.client.post(f"/api/recommendations/{walking['id']}/feedback", json={"feedback": "not_helpful"}).status_code, 200)
        next_items = self.client.get("/api/recommendations").json()
        self.assertNotIn("walking", [item["activity"] for item in next_items["items"]])

        for item, value in zip(next_items["items"][:2], ("helpful", "somewhat_helpful")):
            self.assertEqual(self.client.post(f"/api/recommendations/{item['id']}/feedback", json={"feedback": value}).status_code, 200)
        history = self.client.get("/api/recommendations").json()["history"]
        self.assertIn("helpful", [item["feedback"] for item in history])
        self.assertIn("somewhat_helpful", [item["feedback"] for item in history])
        self.assertIn("not_helpful", [item["feedback"] for item in history])

        self.client.post("/api/journals", json={"transcript": "I may hurt myself and I cannot keep myself safe."})
        safety = self.client.get("/api/recommendations").json()
        self.assertTrue(safety["safety_alert"])
        self.assertEqual(safety["items"], [])
        self.assertIn("local emergency number", safety["safety_message"])

    def test_manual_mapper_pattern_can_personalize_without_a_journal(self):
        self.assertEqual(self.signup("Pattern User", "pattern-only@example.com").status_code, 201)
        created = self.client.post("/api/mapper/patterns", json={"situation": "Before presentations", "emotion": "nervous", "activity": "breathing"})
        self.assertEqual(created.status_code, 201, created.text)
        data = self.client.get("/api/recommendations").json()
        self.assertFalse(data["has_journals"])
        breathing = next(item for item in data["items"] if item["activity"] == "breathing")
        self.assertIn("You confirmed a pattern", breathing["explanation"])

if __name__ == "__main__":
    unittest.main()
