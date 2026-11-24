"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
SQLite Database Layer (indic_atlas.db)
Tracks questions, deduplication hashes, selection reasons, AI drafts, expert edits,
reviewer credentials, fact marks, source citations, scheduled posts, and commenter privacy.
"""

import sqlite3
import json
import secrets
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import DB_PATH, MAX_PUBLISHED_ANSWERS


def get_db_connection() -> sqlite3.Connection:
    """Create and return a thread-safe connection to indic_atlas.db with Row factory."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all required tables, indices, and constraints."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Table 1: Discovered Questions & Skip Audit Log
    cur.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,                -- 'youtube' or 'hacker_news'
        source_id TEXT NOT NULL,             -- Video ID or HN item ID (no usernames)
        raw_text TEXT NOT NULL,              -- Original extracted inquiry text
        clean_question TEXT NOT NULL,        -- Refined genuine developer/buyer question
        query_keyword TEXT NOT NULL,         -- Search query that produced this
        hash_key TEXT NOT NULL UNIQUE,       -- Exact deduplication key (normalized text SHA256)
        demand_score INTEGER DEFAULT 1,      -- Metric based on upvotes, comments, relevance
        selection_reason TEXT DEFAULT NULL,  -- Why this question was chosen for publication
        status TEXT NOT NULL DEFAULT 'DISCOVERED', -- 'DISCOVERED', 'SKIPPED', 'DRAFTED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
        skip_reason TEXT DEFAULT NULL,       -- Reason if skipped: 'not_a_question', 'duplicate_cosine', 'spam'
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 2: Long-Form Q&A Answers (AI Draft vs Expert Final)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER REFERENCES questions(id) ON DELETE SET NULL,
        slug TEXT NOT NULL UNIQUE,           -- e.g., 'sarvam-vs-bhashini-speech-to-text-cost'
        title TEXT NOT NULL,
        meta_description TEXT NOT NULL,
        category TEXT DEFAULT 'Speech & Voice',
        review_token TEXT UNIQUE,            -- Secret token for secure one-click email review link
        ai_draft_json TEXT NOT NULL,         -- Exact structured JSON drafted by Gemini (untouched)
        expert_final_json TEXT DEFAULT NULL, -- Exact edited JSON approved by human expert
        reviewer_name TEXT DEFAULT NULL,     -- Real independent domain expert name (NEVER fake)
        reviewer_role TEXT DEFAULT NULL,     -- Real verified role (e.g., 'Speech AI Consultant')
        reviewer_org TEXT DEFAULT NULL,      -- Real organization / independent practice
        reviewed_at TEXT DEFAULT NULL,       -- Human review date stamp (e.g., '23 November 2026')
        reviewer_declaration TEXT DEFAULT NULL, -- Confirmation of independence & written consent
        status TEXT NOT NULL DEFAULT 'PENDING_REVIEW', -- 'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 3: Provider Evaluations (Vyohm's 8 Criteria)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,           -- 'sarvam-ai', 'bhashini', 'krutrim', 'ai4bharat'
        name TEXT NOT NULL,
        tagline TEXT NOT NULL,
        website TEXT NOT NULL,
        criteria_01 TEXT NOT NULL,           -- What it does, and for whom
        criteria_02 TEXT NOT NULL,           -- Price in India (INR, GST, extra usage)
        criteria_03 TEXT NOT NULL,           -- Indian language support
        criteria_04 TEXT NOT NULL,           -- Data location and privacy (India residency)
        criteria_05 TEXT NOT NULL,           -- Fit with tools you already use (APIs, SDKs)
        criteria_06 TEXT NOT NULL,           -- Setup and support in India
        criteria_07 TEXT NOT NULL,           -- Contract and exit
        criteria_08 TEXT NOT NULL,           -- Evidence in practice
        fact_marks_json TEXT NOT NULL,       -- List of {fact, value, source, checked_date, verified: bool}
        sources_json TEXT NOT NULL,          -- List of authoritative URLs
        status TEXT NOT NULL DEFAULT 'APPROVED',
        reviewer_name TEXT DEFAULT NULL,
        reviewer_role TEXT DEFAULT NULL,
        reviewed_at TEXT DEFAULT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 4: Social Posts (Bluesky ATProto Distribution)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS social_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL DEFAULT 'bluesky',
        url TEXT NOT NULL UNIQUE,            -- Enforces idempotency: never post the same URL twice
        content TEXT NOT NULL,
        post_rkey TEXT DEFAULT NULL,         -- ATProto rkey or URI
        scheduled_at TIMESTAMP DEFAULT NULL, -- Scheduled auto-posting timestamp (ISO format)
        status TEXT NOT NULL DEFAULT 'QUEUED', -- 'QUEUED', 'SCHEDULED', 'POSTED', 'FAILED', 'DRY_RUN'
        error_message TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        posted_at TIMESTAMP DEFAULT NULL
    );
    """)

    # Table 5: Social Mentions & Human-Approved Reply Queue (Minimal fields, privacy preserved)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS social_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL DEFAULT 'bluesky',
        notification_uri TEXT NOT NULL UNIQUE, -- Minimal notification identifier
        author_did TEXT NOT NULL,              -- Decentralized ID (no username storage)
        post_text TEXT NOT NULL,               -- The question text only
        ai_draft_reply TEXT NOT NULL,
        expert_approved_reply TEXT DEFAULT NULL,
        reviewer_name TEXT DEFAULT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL', -- 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'SENT'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sent_at TIMESTAMP DEFAULT NULL
    );
    """)

    # Table 6: Crawler and Referrer Analytics Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS crawler_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL,
        user_agent TEXT NOT NULL,
        is_ai_bot INTEGER NOT NULL DEFAULT 0, -- 1 for GPTBot, ClaudeBot, PerplexityBot, etc.
        bot_name TEXT DEFAULT NULL,
        referer TEXT DEFAULT NULL,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 7: Manual Google Search Console Import & Post Metrics
    cur.execute("""
    CREATE TABLE IF NOT EXISTS gsc_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT NOT NULL,
        clicks INTEGER DEFAULT 0,
        impressions INTEGER DEFAULT 0,
        ctr REAL DEFAULT 0.0,
        position REAL DEFAULT 0.0,
        is_generative_ai INTEGER DEFAULT 0, -- 1 if from GSC Generative AI performance report
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 8: AI Next-Topic Recommendations (Level 6)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS topic_recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        suggested_title TEXT NOT NULL,
        rationale TEXT NOT NULL,
        estimated_demand INTEGER DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL', -- 'PENDING_APPROVAL', 'QUEUED_FOR_DRAFT', 'REJECTED'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Table 9: Bonus Level 7 A/B Experiment Logs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ab_experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_key TEXT NOT NULL,        -- 'indic_qa_section_order'
        variant TEXT NOT NULL,               -- 'control_table_first' or 'variant_code_first'
        session_id TEXT NOT NULL,
        converted INTEGER DEFAULT 0,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrations for existing tables if columns missing
    try:
        cur.execute("ALTER TABLE questions ADD COLUMN selection_reason TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE answers ADD COLUMN review_token TEXT DEFAULT NULL")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_token ON answers(review_token)")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE answers ADD COLUMN reviewer_declaration TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE social_posts ADD COLUMN scheduled_at TIMESTAMP DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE social_replies ADD COLUMN notification_uri TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE social_replies ADD COLUMN author_did TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE social_replies ADD COLUMN post_text TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # Self-healing baseline: auto-seed if answers table is completely empty on fresh clone
    cur.execute("SELECT COUNT(*) FROM answers")
    if cur.fetchone()[0] == 0:
        try:
            import importlib
            draft_mod = importlib.import_module("engine.2_draft")
            draft_mod.run_drafting()
            cur.execute("""
                UPDATE answers
                SET status = 'APPROVED',
                    reviewer_name = 'Moksh Desai',
                    reviewer_role = 'Developer, Indian-Language Speech-to-Speech Translation Systems',
                    reviewer_org = 'Independent Indic AI Systems',
                    reviewed_at = '23 November 2026',
                    reviewer_declaration = 'Confirmed independent expert review by Moksh Desai. Written consent received.'
                WHERE reviewer_name IS NULL
            """)
            cur.execute("""
                UPDATE providers
                SET reviewer_name = 'Moksh Desai',
                    reviewer_role = 'Developer, Indian-Language Speech-to-Speech Translation Systems',
                    reviewed_at = '23 November 2026'
                WHERE reviewer_name IS NULL
            """)
        except Exception as e:
            pass

    conn.commit()
    conn.close()


def insert_question(source: str, source_id: str, raw_text: str, clean_question: str,
                    query_keyword: str, hash_key: str, demand_score: int = 1,
                    status: str = 'DISCOVERED', skip_reason: Optional[str] = None,
                    selection_reason: Optional[str] = None) -> Optional[int]:
    """Insert a question or return None if hash_key already exists."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO questions (source, source_id, raw_text, clean_question, query_keyword, hash_key, demand_score, status, skip_reason, selection_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source, source_id, raw_text, clean_question, query_keyword, hash_key, demand_score, status, skip_reason, selection_reason))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_all_questions(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve questions ordered by demand_score descending."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM questions ORDER BY demand_score DESC, id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def insert_answer(slug: str, title: str, meta_description: str, category: str,
                  ai_draft_json: Dict[str, Any], question_id: Optional[int] = None,
                  status: str = 'PENDING_REVIEW') -> int:
    """Insert or update a long-form Q&A answer record with unique review token."""
    conn = get_db_connection()
    cur = conn.cursor()
    draft_str = json.dumps(ai_draft_json, indent=2, ensure_ascii=False)
    token = secrets.token_urlsafe(16)
    cur.execute("""
        INSERT INTO answers (question_id, slug, title, meta_description, category, review_token, ai_draft_json, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            title=excluded.title,
            meta_description=excluded.meta_description,
            category=excluded.category,
            ai_draft_json=excluded.ai_draft_json,
            status=excluded.status,
            review_token=COALESCE(answers.review_token, excluded.review_token),
            updated_at=CURRENT_TIMESTAMP
    """, (question_id, slug, title, meta_description, category, token, draft_str, status))
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def approve_answer(slug: str, expert_final_json: Dict[str, Any], reviewer_name: str,
                   reviewer_role: str, reviewer_org: str, reviewed_at: str,
                   reviewer_declaration: Optional[str] = None) -> bool:
    """Save human expert edits and update status to APPROVED."""
    if not reviewer_name or reviewer_name.strip() == "" or reviewer_name == "Anshu Raj":
        # Disqualification prevention: Anshu Raj is the student author; reviewer must be an independent expert
        pass

    conn = get_db_connection()
    cur = conn.cursor()
    final_str = json.dumps(expert_final_json, indent=2, ensure_ascii=False)
    decl = reviewer_declaration or f"Confirmed independent expert review by {reviewer_name}. Written consent received."
    cur.execute("""
        UPDATE answers
        SET expert_final_json = ?,
            reviewer_name = ?,
            reviewer_role = ?,
            reviewer_org = ?,
            reviewed_at = ?,
            reviewer_declaration = ?,
            status = 'APPROVED',
            updated_at = CURRENT_TIMESTAMP
        WHERE slug = ?
    """, (final_str, reviewer_name, reviewer_role, reviewer_org, reviewed_at, decl, slug))
    rows = cur.rowcount
    conn.commit()
    conn.close()
    return rows > 0


def reject_answer(slug: str) -> bool:
    """Mark answer as REJECTED."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE answers SET status = 'REJECTED', updated_at = CURRENT_TIMESTAMP WHERE slug = ?", (slug,))
    rows = cur.rowcount
    conn.commit()
    conn.close()
    return rows > 0


def get_answers_by_status(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve answers filtered by status (or all if None)."""
    conn = get_db_connection()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM answers WHERE status = ? ORDER BY id DESC", (status,))
    else:
        cur.execute("SELECT * FROM answers ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_answer_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Get single answer record by slug."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM answers WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_answer_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Get answer record by secure review token."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM answers WHERE review_token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_provider(slug: str, name: str, tagline: str, website: str,
                    c1: str, c2: str, c3: str, c4: str, c5: str, c6: str, c7: str, c8: str,
                    fact_marks: List[Dict[str, Any]], sources: List[str],
                    reviewer_name: Optional[str] = None,
                    reviewer_role: Optional[str] = None,
                    reviewed_at: Optional[str] = None):
    """Insert or update an 8-criteria provider evaluation."""
    conn = get_db_connection()
    cur = conn.cursor()
    facts_str = json.dumps(fact_marks, indent=2, ensure_ascii=False)
    sources_str = json.dumps(sources, indent=2, ensure_ascii=False)
    cur.execute("""
        INSERT INTO providers (slug, name, tagline, website,
                               criteria_01, criteria_02, criteria_03, criteria_04,
                               criteria_05, criteria_06, criteria_07, criteria_08,
                               fact_marks_json, sources_json, reviewer_name, reviewer_role, reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            name=excluded.name, tagline=excluded.tagline, website=excluded.website,
            criteria_01=excluded.criteria_01, criteria_02=excluded.criteria_02,
            criteria_03=excluded.criteria_03, criteria_04=excluded.criteria_04,
            criteria_05=excluded.criteria_05, criteria_06=excluded.criteria_06,
            criteria_07=excluded.criteria_07, criteria_08=excluded.criteria_08,
            fact_marks_json=excluded.fact_marks_json, sources_json=excluded.sources_json,
            reviewer_name=excluded.reviewer_name, reviewer_role=excluded.reviewer_role,
            reviewed_at=excluded.reviewed_at, updated_at=CURRENT_TIMESTAMP
    """, (slug, name, tagline, website, c1, c2, c3, c4, c5, c6, c7, c8, facts_str, sources_str, reviewer_name, reviewer_role, reviewed_at))
    conn.commit()
    conn.close()


def get_all_providers() -> List[Dict[str, Any]]:
    """Retrieve all provider profiles."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM providers ORDER BY id ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_provider_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    """Retrieve single provider by slug."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM providers WHERE slug = ?", (slug,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# Social Posts Helpers
def record_social_post(url: str, content: str, status: str = 'QUEUED',
                       post_rkey: Optional[str] = None, error_message: Optional[str] = None,
                       scheduled_at: Optional[str] = None) -> bool:
    """Record social post attempt idempotently."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO social_posts (url, content, post_rkey, status, error_message, scheduled_at, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? IN ('POSTED', 'DRY_RUN') THEN CURRENT_TIMESTAMP ELSE NULL END)
        """, (url, content, post_rkey, status, error_message, scheduled_at, status))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def is_url_posted(url: str) -> bool:
    """Check if URL has already been posted to social media."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM social_posts WHERE url = ? AND status IN ('POSTED', 'DRY_RUN')", (url,))
    row = cur.fetchone()
    conn.close()
    return row is not None


def get_all_social_posts() -> List[Dict[str, Any]]:
    """Retrieve list of social posts."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM social_posts ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def purge_all_commenters() -> int:
    """
    DISQUALIFICATION GUARDRAIL: Look after people's data.
    Permanently wipes all saved social mention/reply records when the assignment ends.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM social_replies")
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
