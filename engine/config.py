"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Configuration Module. Gracefully parses .env with support for active,
commented-out, and default values. Never crashes when optional keys are absent.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
ENGINE_DIR = BASE_DIR / "engine"
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "indic_atlas.db"

# Load standard .env first
load_dotenv(BASE_DIR / ".env")


def _read_env_fallback():
    """
    Parse .env manually to extract keys even if they are commented out
    (e.g., `# YOUTUBE_API_KEY= ...` or `# Gemini APi key = ...`).
    """
    env_file = BASE_DIR / ".env"
    extra = {}
    if not env_file.exists():
        return extra

    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                m = re.match(r"^#*\s*([A-Za-z0-9_]+(?:\s+[A-Za-z0-9_]+)*)\s*[:=]\s*(.+)$", line)
                if m:
                    raw_k, v = m.group(1).strip(), m.group(2).strip()
                    norm_k = raw_k.upper().replace(" ", "_")
                    v = v.strip("\"' \t")
                    if norm_k not in extra and v and not v.startswith("your_"):
                        extra[norm_k] = v
    except Exception:
        pass
    return extra


_FALLBACK_ENV = _read_env_fallback()


def get_env_var(key: str, default: str = "") -> str:
    """Get environment variable with fallback to commented keys or default."""
    val = os.getenv(key)
    if val and not val.startswith("your_"):
        return val.strip("\"' ")

    norm_k = key.upper()
    if norm_k in _FALLBACK_ENV:
        return _FALLBACK_ENV[norm_k]

    # Special aliases
    if norm_k in ("GEMINI_API_KEY", "GEMINI_API", "GEMINI_API_KEY_LLM"):
        for alias in ("GEMINI_API_KEY", "GEMINI_API", "GEMINI_API_KEY_LLM"):
            if alias in _FALLBACK_ENV:
                return _FALLBACK_ENV[alias]
    if norm_k in ("GA_MEASUREMENT_ID", "GA4_MEASUREMENT_ID"):
        for alias in ("GA_MEASUREMENT_ID", "GA4_MEASUREMENT_ID"):
            if alias in _FALLBACK_ENV:
                return _FALLBACK_ENV[alias]
        return "G-WK0D46CCQZ"

    return default


# Sourced Keys
GEMINI_API_KEY = get_env_var("GEMINI_API_KEY")
YOUTUBE_API_KEY = get_env_var("YOUTUBE_API_KEY")
STACKEXCHANGE_API_KEY = get_env_var("STACKEXCHANGE_API_KEY", "")
SARVAM_API_KEY = get_env_var("SARVAM_API_KEY", get_env_var("SARVAM_API", ""))

# Social Keys (Bluesky)
BLUESKY_HANDLE = get_env_var("BLUESKY_HANDLE", "indic-aiatlas.bsky.social")
BLUESKY_APP_PASSWORD = get_env_var("BLUESKY_APP_PASSWORD", "")
BLUESKY_DRY_RUN = (not BLUESKY_APP_PASSWORD) or (BLUESKY_APP_PASSWORD.startswith("your_"))

# Analytics
GA_MEASUREMENT_ID = get_env_var("GA_MEASUREMENT_ID", "G-WK0D46CCQZ")

# Review Admin & Dispatch
ADMIN_SECRET_TOKEN = get_env_var("ADMIN_SECRET_TOKEN", "indic-atlas-expert-review-2026")
EXPERT_EMAIL = get_env_var("EXPERT_EMAIL", "jagatsumi@gmail.com")
REVIEWER_NAME = "Moksh Desai"
REVIEWER_ROLE = "Developer, Indian-Language Speech-to-Speech Translation Systems"
REVIEWER_ORG = "Independent Speech-to-Speech Systems"
DEVELOPER_NAME = "Moksh Desai"  # System Developer / Dispatcher
CANDIDATE_NAME = "Anshu Raj"    # Assigned Section Author (rules.md)
CANDIDATE_COLLEGE = "Heritage Institute of Technology, Kolkata"
CANDIDATE_BRANCH = "B.Tech ECE"

# Gmail API OAuth Paths
GMAIL_CREDENTIALS_PATH = BASE_DIR / "credentials.json"
GMAIL_TOKEN_PATH = BASE_DIR / "token.json"

# SMTP Fallback
SMTP_HOST = get_env_var("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(get_env_var("SMTP_PORT", "587"))
SMTP_USER = get_env_var("SMTP_USER", get_env_var("SMTP_EMAIL", ""))
SMTP_APP_PASSWORD = get_env_var("SMTP_APP_PASSWORD", "")

# Bonus Level 7: PostHog A/B Experiment
POSTHOG_PROJECT_KEY = get_env_var("POSTHOG_PROJECT_KEY", get_env_var("NEXT_PUBLIC_POSTHOG_KEY", ""))
POSTHOG_HOST = get_env_var("POSTHOG_HOST", get_env_var("NEXT_PUBLIC_POSTHOG_HOST", "https://us.i.posthog.com"))

# Compliance Constants
MAX_PUBLISHED_ANSWERS = 20
EXACT_FOOTER_OWNERSHIP_LINE = "AI Atlas India is owned by Vyohm AI Private Limited, which also sells AI products. We cover every provider, Vyohm included, by the same rules."

# Section Identity (Plate 05)
PLATE_ID = "05"
SECTION_NAME = "Indic language AI"
SECTION_KEY = "indic"
SUBDOMAIN = "indic.aiatlasindia.com"
CANONICAL_HOST = f"https://{SUBDOMAIN}"
COLOR_INDIC = "#8A5A1C"
COLOR_INK = "#0F1B2D"
COLOR_PAPER = "#FFFFFF"
COLOR_SEA = "#E4EDF2"
COLOR_GRID = "#D5E1E9"
COLOR_MUTED = "#43536B"
COLOR_RULE = "#C5D1DB"
COLOR_SIGNAL = "#F4C430"
COLOR_ROUTE = "#C9361A"
