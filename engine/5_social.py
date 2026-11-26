"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Social Automation & Bluesky Publisher (engine/5_social.py)

Implements Level 5 Social Automation:
1. Scheduled Auto-Posting: Posts newly published canonical URLs to Bluesky (@vyohm-bot.bsky.social).
   - Enforces idempotency via SQLite (unique URL constraint): NO URL is ever posted twice.
   - Posts can be scheduled with an ISO timestamp (scheduled_at) and sent via '--run-scheduled'.
2. Human-in-the-Loop Reply Drafting:
   - Fetches ONLY direct replies and mentions to our account.
   - Drafts contextual AI reply suggestions.
   - Queues suggestions for manual human approval (status='PENDING_APPROVAL').
   - NEVER sends automated replies without explicit human confirmation.
   - Never implements automated follows, likes, reposts, or DMs.
3. Disqualification Guardrail (Look after people's data):
   - Stores only minimal identifiers (notification_uri, author_did, post_text). Never stores usernames.
   - CLI command '--purge-commenters' permanently wipes all commenter records at assignment end.
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import (
    BLUESKY_HANDLE, BLUESKY_APP_PASSWORD, BLUESKY_DRY_RUN,
    CANONICAL_HOST, SECTION_NAME, PLATE_ID
)
from engine.database import (
    init_db, get_db_connection, is_url_posted, record_social_post,
    get_answers_by_status, purge_all_commenters
)

# Optional ATProto client initialization
atp_client = None
if not BLUESKY_DRY_RUN:
    try:
        from atproto import Client
        atp_client = Client()
        atp_client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
        print(f"[Social] Logged in to ATProto Bluesky as @{BLUESKY_HANDLE}")
    except Exception as e:
        print(f"[Social] Notice: ATProto login failed ({e}). Defaulting to DRY_RUN=True.")
        BLUESKY_DRY_RUN = True


def craft_social_post(title: str, url: str, category: str) -> str:
    """Format an informative, compliant Bluesky post with tags and canonical URL."""
    return f"""AI Atlas India — Plate 05: Indic language AI

New verified technical guide:
"{title}"

• Grounded pricing in INR + 18% GST
• Working Python code implementation
• Supported Indian language matrix

Read the full expert-reviewed answer:
{url}

#AIAtlasIndia #IndicAI #SarvamAI #Bhashini #Krutrim #OpenSourceAI"""


MAX_BLUESKY_POSTS_PER_DAY = 3


def schedule_approved_answers() -> int:
    """Queue newly approved answers into social_posts with scheduled timestamps (rate-limited to 3/day)."""
    init_db()
    approved_answers = get_answers_by_status("APPROVED")
    scheduled_count = 0

    # Rate limiting: maximum 3 posts per 24 hours
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as cnt FROM social_posts
        WHERE created_at >= datetime('now', '-1 day')
    """)
    recent_cnt = cur.fetchone()["cnt"]
    conn.close()

    if recent_cnt >= MAX_BLUESKY_POSTS_PER_DAY:
        print(f"[Social] Daily rate limit reached: {recent_cnt} posts recorded in past 24h (cap: {MAX_BLUESKY_POSTS_PER_DAY}).")
        return 0

    slots_available = MAX_BLUESKY_POSTS_PER_DAY - recent_cnt

    for idx, ans in enumerate(approved_answers):
        if scheduled_count >= slots_available:
            break
        slug = ans["slug"]
        url = f"{CANONICAL_HOST}/answers/{slug}.html"
        title = ans["title"]
        category = ans.get("category", "Speech & Voice")

        if is_url_posted(url):
            continue

        # Check if already queued
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM social_posts WHERE url = ?", (url,))
        exists = cur.fetchone() is not None
        conn.close()

        if exists:
            continue

        post_text = craft_social_post(title, url, category)
        # Schedule post (e.g., immediate or staged by 30 mins)
        sched_time = (datetime.now(timezone.utc) + timedelta(minutes=idx * 30)).isoformat()
        record_social_post(url=url, content=post_text, status="SCHEDULED", scheduled_at=sched_time)
        scheduled_count += 1
        print(f"[Social] Scheduled post for '{slug}' at {sched_time}")

    return scheduled_count


def run_scheduled_posts() -> Dict[str, Any]:
    """Publish posts whose scheduled_at timestamp has arrived."""
    init_db()
    conn = get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute("""
        SELECT * FROM social_posts
        WHERE status IN ('SCHEDULED', 'QUEUED')
          AND (scheduled_at IS NULL OR scheduled_at <= ?)
        ORDER BY id ASC
    """, (now_iso,))
    due_posts = [dict(r) for r in cur.fetchall()]
    conn.close()

    stats = {
        "due_count": len(due_posts),
        "posted": 0,
        "failed": 0,
        "dry_run": BLUESKY_DRY_RUN
    }

    print(f"[Social] Processing {len(due_posts)} scheduled posts (DRY_RUN={BLUESKY_DRY_RUN})...")

    for p in due_posts:
        p_id = p["id"]
        url = p["url"]
        post_text = p["content"]

        if is_url_posted(url):
            continue

        if BLUESKY_DRY_RUN:
            print(f"\n[Social:DRY_RUN] Publishing scheduled post #{p_id} to @{BLUESKY_HANDLE}:\n---\n{post_text}\n---")
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE social_posts
                SET status = 'DRY_RUN', post_rkey = 'dry_run_simulated', posted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (p_id,))
            conn.commit()
            conn.close()
            stats["posted"] += 1
        else:
            try:
                response = atp_client.send_post(text=post_text)
                post_rkey = getattr(response, "uri", "posted_atproto")
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE social_posts
                    SET status = 'POSTED', post_rkey = ?, posted_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (post_rkey, p_id))
                conn.commit()
                conn.close()
                print(f"[Social:LIVE] Successfully posted #{p_id} to Bluesky: {url}")
                stats["posted"] += 1
            except Exception as e:
                err_msg = str(e)
                print(f"[Social:ERROR] Failed to post #{p_id}: {err_msg}")
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE social_posts SET status = 'FAILED', error_message = ? WHERE id = ?", (err_msg, p_id))
                conn.commit()
                conn.close()
                stats["failed"] += 1

    return stats


def queue_reply_suggestion(notification_uri: str, author_did: str,
                           post_text: str, ai_draft_reply: str) -> bool:
    """
    Queue an AI-drafted reply suggestion in SQLite for human review.
    Enforces status='PENDING_APPROVAL'. Never auto-sends without human approval.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO social_replies (notification_uri, author_did, post_text, ai_draft_reply, status)
            VALUES (?, ?, ?, ?, 'PENDING_APPROVAL')
        """, (notification_uri, author_did, post_text, ai_draft_reply))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def fetch_and_queue_mentions() -> Dict[str, Any]:
    """
    Fetch notifications/mentions and queue AI reply drafts.
    In DRY_RUN mode, populates realistic community inquiries.
    """
    init_db()
    stats = {"fetched": 0, "queued": 0}

    if BLUESKY_DRY_RUN:
        print("[Social] Simulating incoming Bluesky mentions in DRY_RUN mode...")
        samples = [
            {
                "notification_uri": "at://did:plc:sample01/app.bsky.feed.post/3k1",
                "author_did": "did:plc:dev_indic_9918",
                "text": "Does Sarvam's Saaras ASR handle Bengali audio well compared to Bhashini?",
                "ai_reply": "Yes! Saaras supports Bengali with competitive WER on conversational speech. For public/free research, Bhashini also covers Bengali via ULCA: https://indic.aiatlasindia.com/answers/sarvam-vs-bhashini-speech-to-text-cost-accuracy.html"
            },
            {
                "notification_uri": "at://did:plc:sample02/app.bsky.feed.post/3k2",
                "author_did": "did:plc:dev_indic_7712",
                "text": "Is IndicTrans2 free for commercial use in an Indian SaaS company?",
                "ai_reply": "IndicTrans2 is released under MIT / CC-BY 4.0 licenses by AI4Bharat, permitting commercial self-hosting without software royalties: https://indic.aiatlasindia.com/answers/how-to-self-host-ai4bharat-indictrans2-on-premise.html"
            }
        ]
        for s in samples:
            if queue_reply_suggestion(s["notification_uri"], s["author_did"], s["text"], s["ai_reply"]):
                stats["queued"] += 1
            stats["fetched"] += 1
        return stats

    # Live ATProto Notifications
    try:
        notifications = atp_client.app.bsky.notification.list_notifications()
        for notif in getattr(notifications, "notifications", []):
            if notif.reason in ("mention", "reply"):
                n_uri = str(notif.uri)
                author_did = str(notif.author.did)
                text = getattr(notif.record, "text", "")
                ai_reply = f"Thank you for your question. Our independent technical breakdown is documented with verified sources at {CANONICAL_HOST}"
                if queue_reply_suggestion(n_uri, author_did, text, ai_reply):
                    stats["queued"] += 1
                stats["fetched"] += 1
    except Exception as e:
        print(f"[Social] Error fetching mentions: {e}")

    return stats


def approve_and_send_reply(reply_id: int, reviewer_name: str, edited_text: Optional[str] = None) -> bool:
    """
    Human sign-off gate: only sends a reply after human reviewer explicitly approves.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM social_replies WHERE id = ?", (reply_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    final_text = edited_text if edited_text else row["ai_draft_reply"]

    if BLUESKY_DRY_RUN:
        print(f"[Social:DRY_RUN] Human approved reply #{reply_id} by {reviewer_name}:\n'{final_text}'")
        cur.execute("""
            UPDATE social_replies
            SET expert_approved_reply = ?,
                reviewer_name = ?,
                status = 'SENT',
                sent_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (final_text, reviewer_name, reply_id))
        conn.commit()
        conn.close()
        return True
    else:
        try:
            atp_client.send_post(text=final_text)
            cur.execute("""
                UPDATE social_replies
                SET expert_approved_reply = ?,
                    reviewer_name = ?,
                    status = 'SENT',
                    sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (final_text, reviewer_name, reply_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[Social] Live reply failed: {e}")
            conn.close()
            return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Atlas India Social Automation (Plate 05)")
    parser.add_argument("--schedule", action="store_true", help="Queue newly approved answers for scheduled posting")
    parser.add_argument("--run-scheduled", action="store_true", help="Publish due scheduled posts to Bluesky")
    parser.add_argument("--fetch-mentions", action="store_true", help="Fetch mentions and draft reply suggestions")
    parser.add_argument("--purge-commenters", action="store_true", help="DISQUALIFICATION GUARDRAIL: Wipe all commenter records at assignment end")
    args = parser.parse_args()

    if args.purge_commenters:
        count = purge_all_commenters()
        print(f"[Privacy] Successfully purged {count} commenter records from database. Privacy preserved.")
    elif args.schedule:
        count = schedule_approved_answers()
        print(f"[Social] Successfully scheduled {count} new posts.")
    elif args.run_scheduled:
        run_scheduled_posts()
    elif args.fetch_mentions:
        fetch_and_queue_mentions()
    else:
        # Default workflow
        schedule_approved_answers()
        run_scheduled_posts()
        fetch_and_queue_mentions()
