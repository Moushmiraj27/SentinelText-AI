"""SentinelText API application."""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.routes import router

init_db()

app = FastAPI(title="SentinelText — Voice Journal & Wellness Reflection API", version="1.0.0")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
if "*" in cors_origins:
    raise RuntimeError("CORS_ORIGINS must list explicit origins when credentialed cookies are enabled.")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Content-Type"])
app.include_router(router, prefix="/api")

@app.get("/")
@app.get("/api")
def health():
    return {"status": "online", "service": "SentinelText", "docs": "/docs"}
