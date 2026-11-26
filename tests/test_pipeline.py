"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Comprehensive Test Suite (tests/test_pipeline.py)

Covers all levels and disqualification guardrails:
1. Environment & Config Resilience (safe defaults, MAX_PUBLISHED_ANSWERS = 20, GA4)
2. Discovery Filtering & Deduplication (Regex question filter, exact SHA256 hash, 0.85 cosine deduplication)
3. Disqualification Guardrail: Candidate Anshu Raj Author vs Independent Expert Moksh Desai (No Self-Review)
4. Exact Vyohm Footer Ownership Line on every single HTML file
5. Hard 20-Answer Cap enforcement in exporter
6. Level 4 Automated Email Dispatch by Developer Moksh Desai & Review Tokens
7. Level 5 Scheduled Bluesky Posting, Human-Approved Reply Queue & Commenter Privacy Purge
8. Level 6 AI Crawler / Referral Tracking & Next-Topic Recommender
9. Level 7 Presentation A/B Test Honest Reporting ("Not enough data to call it")
10. Vercel Configuration & Clean Deployment files
"""

import sys
import os
import json
import sqlite3
import pytest
import importlib
import uuid
import glob
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import (
    BASE_DIR, FRONTEND_DIR, GA_MEASUREMENT_ID, SUBDOMAIN,
    CANONICAL_HOST, BLUESKY_DRY_RUN, PLATE_ID,
    MAX_PUBLISHED_ANSWERS, EXACT_FOOTER_OWNERSHIP_LINE,
    CANDIDATE_NAME, CANDIDATE_BRANCH, CANDIDATE_COLLEGE,
    DEVELOPER_NAME, REVIEWER_NAME
)
from engine.database import (
    init_db, get_db_connection, insert_question, get_all_questions,
    insert_answer, approve_answer, reject_answer, get_answer_by_slug,
    get_answer_by_token, record_social_post, is_url_posted,
    purge_all_commenters
)
from engine.exporter import run_export

# Dynamic imports for modules with numeric filenames
discover_mod = importlib.import_module("engine.1_discover")
normalize_text = discover_mod.normalize_text
calculate_hash = discover_mod.calculate_hash
cosine_similarity = discover_mod.cosine_similarity
is_genuine_question = discover_mod.is_genuine_question

draft_mod = importlib.import_module("engine.2_draft")
dispatch_mod = importlib.import_module("engine.3_expert_dispatch")
social_mod = importlib.import_module("engine.5_social")
measure_mod = importlib.import_module("engine.6_measure")


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database is initialized before every test."""
    init_db()


# ==============================================================================
# TEST 1: CONFIG & ENVIRONMENT RESILIENCE
# ==============================================================================
def test_config_and_identities():
    assert PLATE_ID == "05"
    assert "indic" in SUBDOMAIN
    assert GA_MEASUREMENT_ID == "G-WK0D46CCQZ"
    assert MAX_PUBLISHED_ANSWERS == 20
    assert CANDIDATE_NAME == "Anshu Raj"
    assert DEVELOPER_NAME == "Anshu Raj"
    assert REVIEWER_NAME == "Moksh Desai"
    assert "Vyohm AI Private Limited" in EXACT_FOOTER_OWNERSHIP_LINE
    assert isinstance(BLUESKY_DRY_RUN, bool)


# ==============================================================================
# TEST 2: DISCOVERY FILTERING & DEDUPLICATION LOGIC
# ==============================================================================
def test_discovery_filtering():
    # Genuine developer questions
    is_q1, _ = is_genuine_question("What is the cost per minute of Sarvam AI speech to text API in INR?")
    assert is_q1 is True

    is_q2, _ = is_genuine_question("How does Bhashini compare with Sarvam AI for Tamil speech recognition accuracy?")
    assert is_q2 is True

    # Generic comments and spam
    is_spam, reason_spam = is_genuine_question("nice video bro")
    assert is_spam is False
    assert reason_spam == "generic_comment_or_spam"

    is_short, reason_short = is_genuine_question("hello world")
    assert is_short is False
    assert reason_short == "too_short_<15_chars"


def test_cosine_similarity_deduplication():
    # Similar variations should be >= 0.85
    text_a = "What is the per minute price of Sarvam speech to text API in INR?"
    text_b = "What is the per minute pricing of Sarvam AI speech to text API in INR?"
    sim = cosine_similarity(text_a, text_b)
    assert sim >= 0.85, f"Expected cosine similarity >= 0.85, got {sim}"

    # Different queries should be < 0.40
    text_c = "Can I deploy AI4Bharat IndicTrans2 on an on-premise local GPU server?"
    sim_diff = cosine_similarity(text_a, text_c)
    assert sim_diff < 0.40, f"Expected low similarity, got {sim_diff}"


# ==============================================================================
# TEST 3: DATABASE OPERATIONS & SELECTION REASON
# ==============================================================================
def test_database_question_dedup_and_selection_reason():
    test_q = f"unique developer question {uuid.uuid4().hex}"
    q_hash = calculate_hash(test_q)
    sel_reason = "High search demand for Indic speech latency."

    qid1 = insert_question(
        source="test", source_id="t1", raw_text=test_q,
        clean_question=test_q, query_keyword="test",
        hash_key=q_hash, status="DISCOVERED",
        selection_reason=sel_reason
    )
    assert qid1 is not None

    # Duplicate must return None
    qid2 = insert_question(
        source="test", source_id="t2", raw_text=test_q,
        clean_question=test_q, query_keyword="test",
        hash_key=q_hash, status="DISCOVERED"
    )
    assert qid2 is None


# ==============================================================================
# TEST 4: DISQUALIFICATION GUARDRAIL: NO SELF-REVIEW BY ANSHU RAJ
# ==============================================================================
def test_disqualification_guardrail_no_self_review():
    from fastapi.testclient import TestClient
    from engine.main import app

    client = TestClient(app)

    # Attempting to approve an answer with reviewer_name == "Anshu Raj" must fail
    res = client.post("/api/answers/sarvam-vs-bhashini-speech-to-text-cost-accuracy/approve", json={
        "reviewer_name": "Anshu Raj",
        "reviewer_role": "Section Author",
        "reviewer_org": "HIT",
        "reviewed_at": "23 November 2026",
        "reviewer_declaration": "Self review",
        "expert_final_json": {
            "question": "Sarvam vs Bhashini",
            "summary": "Summary",
            "comparison_table": [],
            "runnable_python_code": "print('ok')",
            "technical_breakdown": [],
            "sources": ["https://docs.sarvam.ai/"]
        }
    })
    assert res.status_code == 400
    assert "cannot review their own section" in res.text

    # Approving with independent domain expert Moksh Desai must succeed
    res_ok = client.post("/api/answers/sarvam-vs-bhashini-speech-to-text-cost-accuracy/approve", json={
        "reviewer_name": "Moksh Desai",
        "reviewer_role": "Developer, Indian-Language Speech-to-Speech Translation Systems",
        "reviewer_org": "Independent Indic AI Systems",
        "reviewed_at": "23 November 2026",
        "reviewer_declaration": "Declared independent of covered commercial providers",
        "expert_final_json": {
            "question": "Sarvam vs Bhashini Speech-to-Text Comparison",
            "summary": "Verified benchmark comparison.",
            "comparison_table": [{"provider": "Sarvam AI", "price_inr": "₹0.45/min"}],
            "runnable_python_code": "import requests\nprint('verified')",
            "technical_breakdown": ["Sarvam Saaras ASR excels on 8kHz audio."],
            "sources": ["https://docs.sarvam.ai/"]
        }
    })
    assert res_ok.status_code == 200
    assert res_ok.json()["status"] == "APPROVED"


# ==============================================================================
# TEST 5: EXACT FOOTER OWNERSHIP LINE & ABOUT PAGE
# ==============================================================================
def test_exact_footer_ownership_line_and_about_page():
    # Ensure at least one answer is approved by Moksh Desai (Strict Human Gate)
    approve_answer(
        slug="sarvam-vs-bhashini-speech-to-text-cost-accuracy",
        expert_final_json={
            "question": "Sarvam AI vs Bhashini: Speech-to-Text Pricing, Latency & Accuracy Compared",
            "summary": "Verified benchmark comparison.",
            "comparison_table": [{"provider": "Sarvam AI", "price_inr": "₹0.40/min"}],
            "runnable_python_code": "import requests\nprint('verified')",
            "technical_breakdown": ["Sarvam Saaras ASR excels on 8kHz audio."],
            "sources": ["https://docs.sarvam.ai/"]
        },
        reviewer_name="Moksh Desai",
        reviewer_role="Developer, Indian-Language Speech-to-Speech Translation Systems",
        reviewer_org="Independent Indic AI Systems",
        reviewed_at="23 November 2026",
        reviewer_declaration="Confirmed independent expert review by Moksh Desai."
    )

    # Run export
    stats = run_export()
    assert stats["answers_exported"] >= 1
    assert stats["about_path"] is not None

    # Check about.html
    about_path = FRONTEND_DIR / "about.html"
    assert about_path.exists()
    with open(about_path, "r", encoding="utf-8") as f:
        about_text = f.read()

    assert "Built by Anshu Raj" in about_text
    assert "Moksh Desai" in about_text
    assert EXACT_FOOTER_OWNERSHIP_LINE in about_text

    # Check all HTML files in frontend/
    html_files = glob.glob(str(FRONTEND_DIR / "**/*.html"), recursive=True) + glob.glob(str(FRONTEND_DIR / "*.html"))
    html_files = [f for f in set(html_files) if not f.endswith("header.html")]

    for hf in html_files:
        with open(hf, "r", encoding="utf-8") as fp:
            content = fp.read()
        assert EXACT_FOOTER_OWNERSHIP_LINE in content, f"Missing footer in {hf}"


# ==============================================================================
# TEST 6: HARD CAP OF 20 ANSWERS
# ==============================================================================
def test_hard_cap_20_answers():
    conn = get_db_connection()
    # Check that exporter never publishes more than MAX_PUBLISHED_ANSWERS
    stats = run_export()
    assert stats["answers_exported"] <= MAX_PUBLISHED_ANSWERS


# ==============================================================================
# TEST 7: LEVEL 4 EMAIL DISPATCH & REVIEW TOKEN
# ==============================================================================
def test_level_4_email_dispatch_and_token():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM answers WHERE review_token IS NOT NULL LIMIT 1")
    row = cur.fetchone()
    conn.close()

    assert row is not None
    token = row["review_token"]
    assert len(token) >= 16

    ans_by_tok = get_answer_by_token(token)
    assert ans_by_tok is not None
    assert ans_by_tok["id"] == row["id"]

    # Verify email formatting
    email_data = dispatch_mod.format_expert_review_email(ans_by_tok)
    assert DEVELOPER_NAME in email_data["body"]
    assert f"/review/{token}" in email_data["body"]
    assert f"[AI-Atlas-Review #{ans_by_tok['id']}]" in email_data["subject"]


# ==============================================================================
# TEST 8: LEVEL 5 SOCIAL AUTOMATION & COMMENTER PRIVACY PURGE
# ==============================================================================
def test_level_5_social_scheduled_and_purge():
    # Schedule posts
    sched_count = social_mod.schedule_approved_answers()
    assert isinstance(sched_count, int)

    # Run scheduled
    stats = social_mod.run_scheduled_posts()
    assert "due_count" in stats
    assert "posted" in stats

    # Queue a mention suggestion
    notif_uri = f"at://did:plc:test_{uuid.uuid4().hex[:6]}/app.bsky.feed.post/1"
    author_did = "did:plc:dev_indic_test"
    post_text = "What is the token cost of Krutrim Cloud?"
    ai_reply = "Krutrim Cloud offers Indic LLM inference at competitive INR rates."

    q_ok = social_mod.queue_reply_suggestion(notif_uri, author_did, post_text, ai_reply)
    assert q_ok is True

    # Purge commenters (Disqualification Guardrail: look after people's data)
    purged = purge_all_commenters()
    assert purged >= 1

    # Verify replies table is empty
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM social_replies")
    assert cur.fetchone()["cnt"] == 0
    conn.close()


# ==============================================================================
# TEST 9: LEVEL 6 ANALYTICS & LEVEL 7 A/B HONEST REPORTING
# ==============================================================================
def test_level_6_analytics_and_ab_reporting():
    summary = measure_mod.get_analytics_summary()
    assert "total_requests" in summary
    assert "ai_crawler_hits" in summary
    assert "ab_experiment" in summary

    # Level 7 Honest Reporting check: when sessions < 100, must report "Not enough data to call it"
    ab = summary["ab_experiment"]
    if ab.get("total_sessions", 0) < 100:
        assert ab.get("verdict") == "Not enough data to call it"
        assert ab.get("honest_reporting") is True

    # Next topic recommendation check
    recs = measure_mod.recommend_next_topics()
    assert len(recs) == 3
    assert "suggested_title" in recs[0]
    assert "rationale" in recs[0]


# ==============================================================================
# TEST 10: VERCEL DEPLOYMENT CONFIGURATION
# ==============================================================================
def test_vercel_configuration():
    vercel_json_path = BASE_DIR / "vercel.json"
    vercel_ignore_path = BASE_DIR / ".vercelignore"

    assert vercel_json_path.exists()
    assert vercel_ignore_path.exists()

    with open(vercel_json_path, "r", encoding="utf-8") as f:
        v_data = json.load(f)
        assert v_data.get("outputDirectory") == "frontend"
        assert v_data.get("cleanUrls") is True

    with open(vercel_ignore_path, "r", encoding="utf-8") as f:
        v_ignore = f.read()
        assert "engine/" in v_ignore
        assert "references/" in v_ignore
        assert "rules/" in v_ignore
        assert "*.db" in v_ignore
        assert "credentials.json" in v_ignore
        assert "token.json" in v_ignore


# ==============================================================================
# TEST 11: UNIFIED PIPELINE ORCHESTRATOR
# ==============================================================================
def test_unified_pipeline_orchestrator():
    orchestrator_path = BASE_DIR / "engine" / "run_pipeline.py"
    assert orchestrator_path.exists()

    orchestrator_mod = importlib.import_module("engine.run_pipeline")
    assert hasattr(orchestrator_mod, "run_stage_1")
    assert hasattr(orchestrator_mod, "run_stage_2")
    assert hasattr(orchestrator_mod, "run_stage_3")
    assert hasattr(orchestrator_mod, "run_stage_4")
    assert hasattr(orchestrator_mod, "run_stage_5")
    assert hasattr(orchestrator_mod, "run_stage_6")


# ==============================================================================
# TEST 12: PURGE OLD & STALE REVIEWS (/api/reviews/clear-old)
# ==============================================================================
def test_clear_old_reviews_endpoint():
    from fastapi.testclient import TestClient
    from engine.main import app

    client = TestClient(app)

    # Insert a temporary unapproved answer record
    test_slug = f"test-stale-draft-{uuid.uuid4().hex[:6]}"
    qid = insert_question(
        source="test",
        source_id=f"test_{uuid.uuid4().hex[:6]}",
        raw_text="How to test clear old reviews?",
        clean_question="How to test clear old reviews?",
        query_keyword="test",
        hash_key=f"hash_{uuid.uuid4().hex[:8]}"
    )
    aid = insert_answer(
        slug=test_slug,
        title="Test Stale Draft Title",
        meta_description="Test meta description for stale draft",
        category="Speech & Voice",
        ai_draft_json={"question": "How to test clear old reviews?", "summary": "Stale summary"},
        question_id=qid,
        status="PENDING_REVIEW"
    )

    # Verify it exists in DB
    ans = get_answer_by_slug(test_slug)
    assert ans is not None
    assert ans["status"] == "PENDING_REVIEW"

    # Call /api/reviews/clear-old
    res = client.post("/api/reviews/clear-old")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["deleted_count"] >= 1

    # Verify stale draft is permanently purged
    ans_after = get_answer_by_slug(test_slug)
    assert ans_after is None

    # Verify orphaned html file does not exist in frontend/answers/
    orphan_file = FRONTEND_DIR / "answers" / f"{test_slug}.html"
    assert not orphan_file.exists()


# ==============================================================================
# TEST 13: LOCAL-ONLY APPROVAL GATE & GITHUB/VERCEL PUBLISH ENDPOINT
# ==============================================================================
def test_local_only_approval_and_publish_endpoint():
    from fastapi.testclient import TestClient
    from engine.main import app

    client = TestClient(app)

    # Verify frontend/vercel.json configuration
    frontend_vercel_json = FRONTEND_DIR / "vercel.json"
    assert frontend_vercel_json.exists()
    with open(frontend_vercel_json, "r", encoding="utf-8") as f:
        v_data = json.load(f)
        assert v_data.get("cleanUrls") is True
        assert v_data.get("trailingSlash") is False

    # Verify publish endpoint returns valid response without crashing
    res = client.post("/api/publish")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("published", "no_changes")
    assert "approved_count" in data


# ==============================================================================
# TEST 14: CLOUDFLARE QUICK TUNNEL HELPER
# ==============================================================================
def test_cloudflare_tunnel_helper():
    tunnel_path = BASE_DIR / "engine" / "tunnel.py"
    assert tunnel_path.exists()

    tunnel_mod = importlib.import_module("engine.tunnel")
    assert hasattr(tunnel_mod, "run_tunnel")
    assert hasattr(tunnel_mod, "start_tunnel_background")
    assert hasattr(tunnel_mod, "find_or_download_cloudflared")

