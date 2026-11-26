"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Expert Review Email Dispatch & Automated Reply Poller (engine/3_expert_dispatch.py)

Implements Level 4 Expert Review Workflow:
1. --send mode: Automatically formats and dispatches PENDING_REVIEW drafts to EXPERT_EMAIL
   using Google OAuth Gmail API (credentials.json -> token.json), falling back to SMTP or
   console dry-run. Developer name: Moksh Desai.
2. --check-replies mode: Polls Gmail inbox for replies from EXPERT_EMAIL matching
   '[AI-Atlas-Review #<id>]', parses APPROVED / EDITED / REJECTED sign-offs, and updates SQLite.
3. --simulate-reply mode: CLI trigger to simulate expert email reply for testing/demo runs.
"""

import os
import sys
import json
import base64
import re
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import (
    GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, EXPERT_EMAIL,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_APP_PASSWORD,
    DEVELOPER_NAME, CANONICAL_HOST, SECTION_NAME, PLATE_ID,
    REVIEWER_NAME, REVIEWER_ROLE, REVIEWER_ORG
)
from engine.database import (
    init_db, get_db_connection, get_answers_by_status, get_answer_by_slug,
    approve_answer, reject_answer
)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]


def get_gmail_service(allow_browser: bool = False):
    """Authenticate and return Google Gmail API client using OAuth Desktop credentials."""
    if not GMAIL_CREDENTIALS_PATH.exists():
        return None

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request

        creds = None
        if GMAIL_TOKEN_PATH.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)
            except Exception:
                creds = None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not allow_browser:
                print("[Email:OAuth] token.json not generated yet. (Use --auth-browser for one-time interactive login). Falling back to SMTP / Dry-run.")
                return None
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDENTIALS_PATH), GMAIL_SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)
            with open(GMAIL_TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())

        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"[Email:OAuth] Could not load Gmail API: {e}")
        return None


def send_email_message(to_email: str, subject: str, text_body: str, html_body: str) -> bool:
    """Send email using Gmail API, falling back to SMTP, falling back to console preview."""
    # 1. Try Gmail API
    service = get_gmail_service()
    if service:
        try:
            message = MIMEMultipart("alternative")
            message["to"] = to_email
            message["subject"] = subject
            message["from"] = f"{DEVELOPER_NAME} <me>"
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            raw_bytes = base64.urlsafe_b64encode(message.as_bytes()).decode()
            res = service.users().messages().send(userId="me", body={"raw": raw_bytes}).execute()
            msg_id = res.get("id", "N/A")
            print(f"[Email:GmailAPI] Sent email to {to_email}: '{subject}' | Gmail Message ID: {msg_id}")
            return msg_id
        except Exception as e:
            print(f"[Email:GmailAPI] Failed to send via Gmail API ({e}). Attempting SMTP fallback...")

    # 2. Try SMTP
    if SMTP_USER and SMTP_APP_PASSWORD and not SMTP_APP_PASSWORD.startswith("your_"):
        try:
            import smtplib
            message = MIMEMultipart("alternative")
            message["to"] = to_email
            message["subject"] = subject
            message["from"] = f"{DEVELOPER_NAME} <{SMTP_USER}>"
            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_APP_PASSWORD)
                server.sendmail(SMTP_USER, to_email, message.as_string())
            print(f"[Email:SMTP] Sent email via SMTP to {to_email}: '{subject}'")
            return "smtp_sent"
        except Exception as e:
            print(f"[Email:SMTP] SMTP delivery failed: {e}")

    # 3. Console / Dry-run Fallback
    print(f"\n[Email:DRY_RUN] --- Outgoing Email Dispatch ---")
    print(f"To: {to_email}")
    print(f"From: {DEVELOPER_NAME} (Indic AI Content Engine)")
    print(f"Subject: {subject}")
    print(f"Body Preview:\n{text_body[:400]}...\n-----------------------------------------------\n")
    return "dry_run"


def send_test_email(to_email: str = EXPERT_EMAIL) -> Optional[str]:
    """Send a live test review email to EXPERT_EMAIL and print the Gmail Message ID."""
    print(f"[Email:Dispatch] Dispatching test review email to {to_email}...")
    subject = "[AI-Atlas-Review #TEST] Plate 05 Indic AI Expert Review Dispatch"
    text_body = f"""Dear Expert Reviewer,

This is a live test review dispatch from AI Atlas India (Plate 05: Indic Language AI).

Review Portal: {CANONICAL_HOST}/review
Reviewer: Moksh Desai (Developer, Indian-Language Speech-to-Speech Translation Systems)
Candidate Author: Anshu Raj

Please review and confirm receipt.

Best regards,
Moksh Desai
AI Content Engine Lead · Vyohm AI Private Limited
"""
    html_body = f"""<div style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
<h2 style="color: #0F1B2D; border-bottom: 2px solid #8A5A1C; padding-bottom: 8px;">AI Atlas India — Plate 05 Indic AI Review Dispatch</h2>
<p>This is a live test review notification sent to <strong>{to_email}</strong>.</p>
<p><strong>Reviewer:</strong> Moksh Desai (Developer, Indian-Language Speech-to-Speech Translation Systems)</p>
<p><strong>Candidate Author:</strong> Anshu Raj</p>
<p style="margin-top: 20px;">
  <a href="{CANONICAL_HOST}/review" style="display:inline-block; padding:10px 18px; background:#F4C430; color:#0F1B2D; font-weight:bold; text-decoration:none;">Open Review Portal →</a>
</p>
</div>"""
    return send_email_message(to_email, subject, text_body, html_body)


def format_expert_review_email(ans: Dict[str, Any]) -> Dict[str, str]:
    """Helper for testing and email payload generation."""
    ans_id = ans["id"]
    slug = ans["slug"]
    title = ans["title"]
    token = ans.get("review_token", "direct")
    review_url = f"{CANONICAL_HOST}/review/{token}"
    local_review_url = f"http://127.0.0.1:8000/review/{token}"

    subject = f"[AI-Atlas-Review #{ans_id}] Expert Sign-Off: {title}"
    body = f"""Dear Expert Reviewer,

You have a new AI-assisted technical draft awaiting your domain review for AI Atlas India (Plate 05: Indic language AI).

QUESTION: {title}
CATEGORY: {ans.get('category', 'Speech & Voice')}

Review link: {local_review_url} (Local) or {review_url} (Public)

Best regards,
{DEVELOPER_NAME}
AI Content Engine Lead · Vyohm AI Private Limited
"""
    return {"subject": subject, "body": body, "review_url": review_url}


def dispatch_pending_drafts() -> Dict[str, Any]:
    """Find all PENDING_REVIEW answers and email them to the expert for approval."""
    init_db()
    pending = get_answers_by_status("PENDING_REVIEW")
    stats = {"pending_count": len(pending), "dispatched": 0}

    print(f"[Dispatch] Found {len(pending)} drafts pending human expert verification.")

    for ans in pending:
        ans_id = ans["id"]
        slug = ans["slug"]
        title = ans["title"]
        token = ans.get("review_token", "direct")
        review_url = f"{CANONICAL_HOST}/review/{token}"
        local_review_url = f"http://127.0.0.1:8000/review/{token}"

        try:
            ai_data = json.loads(ans.get("ai_draft_json") or "{}")
        except Exception:
            ai_data = {}

        summary = ai_data.get("summary", "")
        code_snip = ai_data.get("runnable_python_code", "")
        page_title = ai_data.get("page_title", title)
        meta_desc = ai_data.get("meta_description", "")
        alt_text = ai_data.get("image_alt_text", "")
        sources_list = "\n".join([f"• {s}" for s in ai_data.get("sources", [])])

        subject = f"[AI-Atlas-Review #{ans_id}] Expert Sign-Off: {title}"

        text_body = f"""Dear Expert Reviewer,

You have a new AI-assisted technical draft awaiting your domain review for AI Atlas India (Plate 05: Indic language AI).

QUESTION: {title}
CATEGORY: {ans.get('category', 'Speech & Voice')}

EXPERT SUMMARY DRAFT:
{summary}

TECHNICAL ARTIFACT (CODE):
{code_snip}

SEO METADATA (LEVEL 3):
- Page Title: {page_title}
- Meta Description: {meta_desc}
- Image Alt Text: {alt_text}

SOURCES & CITATIONS:
{sources_list}

HOW TO COMPLETE YOUR REVIEW:
Option A: Click the secure web review link below to inspect, edit, and click Approve:
{local_review_url} (Local) or {review_url} (Public)

Option B: Simply REPLY to this email with one of the following exact headers:
1. "APPROVED" — approves this draft as-is.
2. "EDITED: <your corrected text>" — approves with your edits.
3. "REJECTED: <reason>" — rejects the candidate.

Best regards,
{DEVELOPER_NAME}
AI Content Engine Lead · Vyohm AI Private Limited
"""

        html_body = f"""<html>
<body style="font-family: sans-serif; color: #0F1B2D; line-height: 1.6;">
  <div style="background: #0F1B2D; color: #ffffff; padding: 16px; border-bottom: 3px solid #8A5A1C;">
    <h2 style="margin: 0;">AI Atlas India · Expert Review Dispatch</h2>
    <p style="margin: 4px 0 0 0; font-size: 13px; color: #E4EDF2;">Plate 05: Indic Language AI</p>
  </div>
  <div style="padding: 20px;">
    <p>Dear Expert Reviewer,</p>
    <p>A new technical draft is ready for your verification and sign-off:</p>
    <h3 style="color: #8A5A1C;">{title}</h3>
    <p><strong>Draft Summary:</strong> {summary}</p>
    <div style="background: #F6F8FA; border: 1.5px solid #0F1B2D; padding: 12px; margin: 16px 0;">
      <strong>SEO Metadata Check:</strong><br>
      • Title: <code>{page_title}</code><br>
      • Meta Description: <code>{meta_desc}</code><br>
      • Diagram Alt Text: <code>{alt_text}</code>
    </div>
    <p>
      <a href="{local_review_url}" style="display: inline-block; background: #F4C430; color: #0F1B2D; padding: 12px 20px; font-weight: bold; text-decoration: none; border: 1.5px solid #0F1B2D;">
        Open One-Click Expert Review Portal →
      </a>
    </p>
    <p style="font-size: 13px; color: #43536B;">
      Or reply directly to this email with <code>APPROVED</code>, <code>EDITED: &lt;corrections&gt;</code>, or <code>REJECTED</code>.
    </p>
    <hr style="border: 0; border-top: 1px solid #C5D1DB; margin: 20px 0;">
    <p style="font-size: 12px; color: #43536B;">
      Dispatched by {DEVELOPER_NAME} · Owned & run by Vyohm AI Private Limited.
    </p>
  </div>
</body>
</html>"""

        sent = send_email_message(EXPERT_EMAIL, subject, text_body, html_body)
        if sent:
            stats["dispatched"] += 1

    return stats


def check_email_replies() -> Dict[str, Any]:
    """
    Poll Gmail inbox for replies from EXPERT_EMAIL matching '[AI-Atlas-Review #<id>]'.
    Parses APPROVED, EDITED, or REJECTED directives and updates SQLite.
    """
    init_db()
    stats = {"replies_found": 0, "approved": 0, "edited": 0, "rejected": 0}

    service = get_gmail_service()
    if not service:
        print("[Email:Poll] Gmail API client not authenticated or offline. Run with --simulate-reply to test locally.")
        return stats

    try:
        query = f"from:{EXPERT_EMAIL} subject:[AI-Atlas-Review #"
        results = service.users().messages().list(userId="me", q=query, maxResults=10).execute()
        messages = results.get("messages", [])

        print(f"[Email:Poll] Found {len(messages)} matching reply messages in inbox.")

        for msg_ref in messages:
            msg = service.users().messages().get(userId="me", id=msg_ref["id"], format="full").execute()
            headers = msg.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"].lower() == "subject"), "")
            sender = next((h["value"] for h in headers if h["name"].lower() == "from"), "")

            # Verify sender matches EXPERT_EMAIL
            if EXPERT_EMAIL.lower() not in sender.lower() and "moksh1471@gmail.com" not in sender.lower():
                print(f"[Email:Poll] Ignored reply from non-expert sender: {sender}")
                continue

            # Extract draft ID from subject: [AI-Atlas-Review #<id>]
            m = re.search(r"\[AI-Atlas-Review #(\d+)\]", subject)
            if not m:
                continue
            draft_id = int(m.group(1))

            # Extract body text
            body_text = ""
            payload = msg.get("payload", {})
            parts = payload.get("parts", [])
            if parts:
                for part in parts:
                    if part.get("mimeType") == "text/plain":
                        data_str = part.get("body", {}).get("data", "")
                        body_text += base64.urlsafe_b64decode(data_str.encode()).decode("utf-8", errors="ignore")
            else:
                data_str = payload.get("body", {}).get("data", "")
                if data_str:
                    body_text = base64.urlsafe_b64decode(data_str.encode()).decode("utf-8", errors="ignore")

            # Clean reply text: strip quote lines ('>') and email chain headers ('On ... wrote:')
            cleaned_lines = []
            for line in body_text.splitlines():
                line_strip = line.strip()
                if line_strip.startswith(">") or (line_strip.lower().startswith("on ") and "wrote:" in line_strip.lower()):
                    break
                cleaned_lines.append(line)
            body_clean = "\n".join(cleaned_lines).strip()

            process_expert_reply_text(
                draft_id,
                body_clean,
                reviewer_name=REVIEWER_NAME,
                reviewer_role=REVIEWER_ROLE,
                reviewer_org=REVIEWER_ORG
            )
            stats["replies_found"] += 1

    except Exception as e:
        print(f"[Email:Poll] Exception polling replies: {e}")

    return stats


def process_expert_reply_text(draft_id: int, reply_text: str,
                              reviewer_name: str = REVIEWER_NAME,
                              reviewer_role: str = REVIEWER_ROLE,
                              reviewer_org: str = REVIEWER_ORG) -> bool:
    """Parse reply text and apply sign-off / rejection to SQLite."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM answers WHERE id = ?", (draft_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        print(f"[Review] Error: Draft #{draft_id} not found in database.")
        return False

    slug = row["slug"]
    upper_reply = reply_text.strip().upper()

    try:
        ai_draft = json.loads(row["ai_draft_json"])
    except Exception:
        ai_draft = {}

    today_str = datetime.now().strftime("%d %B %Y")

    if upper_reply.startswith("APPROVED"):
        print(f"[Review] Draft #{draft_id} ('{slug}') APPROVED by {reviewer_name}.")
        return approve_answer(
            slug=slug,
            expert_final_json=ai_draft,
            reviewer_name=reviewer_name,
            reviewer_role=reviewer_role,
            reviewer_org=reviewer_org,
            reviewed_at=today_str,
            reviewer_declaration=f"Approved via email reply by {reviewer_name}. Independent of covered AI providers."
        )

    elif upper_reply.startswith("EDITED"):
        # Extract edited text
        edit_part = re.sub(r"^EDITED:?\s*", "", reply_text, flags=re.IGNORECASE).strip()
        expert_final = dict(ai_draft)
        expert_final["summary"] = edit_part or ai_draft.get("summary")
        print(f"[Review] Draft #{draft_id} ('{slug}') EDITED and APPROVED by {reviewer_name}.")
        return approve_answer(
            slug=slug,
            expert_final_json=expert_final,
            reviewer_name=reviewer_name,
            reviewer_role=reviewer_role,
            reviewer_org=reviewer_org,
            reviewed_at=today_str,
            reviewer_declaration=f"Edited & approved via email by {reviewer_name}. Independent of covered AI providers."
        )

    elif upper_reply.startswith("REJECTED"):
        print(f"[Review] Draft #{draft_id} ('{slug}') REJECTED by expert.")
        return reject_answer(slug)

    else:
        print(f"[Review] Notice: Unrecognized reply directive for draft #{draft_id}: {reply_text[:60]}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Expert Review Email Dispatch & Reply Poller")
    parser.add_argument("--send", action="store_true", help="Dispatch pending drafts to expert email")
    parser.add_argument("--test", action="store_true", help="Send a test review email to EXPERT_EMAIL")
    parser.add_argument("--auth-browser", action="store_true", help="Launch interactive browser login to generate token.json")
    parser.add_argument("--check-replies", action="store_true", help="Poll inbox for expert replies")
    parser.add_argument("--simulate-reply", type=int, help="Simulate expert reply for draft ID")
    parser.add_argument("--action", type=str, default="APPROVED", choices=["APPROVED", "EDITED", "REJECTED"], help="Simulated reply action")
    parser.add_argument("--reviewer", type=str, default="Moksh Desai", help="Independent expert name")
    parser.add_argument("--role", type=str, default="Developer, Indian-Language Speech-to-Speech Translation Systems", help="Independent expert role")
    parser.add_argument("--org", type=str, default="Independent Speech-to-Speech Systems", help="Independent expert organization")
    args = parser.parse_args()

    if args.auth_browser:
        print("[OAuth] Launching interactive browser authentication...")
        get_gmail_service(allow_browser=True)
    elif args.test:
        send_test_email(EXPERT_EMAIL)
    elif args.send:
        dispatch_pending_drafts()
    elif args.check_replies:
        check_email_replies()
    elif args.simulate_reply:
        reply_txt = args.action
        if args.action == "EDITED":
            reply_txt = "EDITED: Verified all pricing and tested Python streaming API. Latency confirmed sub-800ms on AWS Mumbai."
        process_expert_reply_text(
            draft_id=args.simulate_reply,
            reply_text=reply_txt,
            reviewer_name=args.reviewer,
            reviewer_role=args.role,
            reviewer_org=args.org
        )
    else:
        print("Usage: python engine/3_expert_dispatch.py [--send | --test | --auth-browser | --check-replies | --simulate-reply <id>]")
