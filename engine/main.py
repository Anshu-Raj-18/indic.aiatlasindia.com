"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
FastAPI Main Application & Expert Review Portal (engine/main.py)

Features:
1. /review & /review/{token} — Human Expert Review Portal styled strictly with Section Kit tokens.css:
   - External domain expert inspects the raw AI draft alongside source URLs and fact marks.
   - Editable fields for human review: Title, Summary, Comparison Matrix, Runnable Code, Trade-Offs.
   - Mandatory Reviewer Name, Role, Organization, and Date inputs.
   - Disqualification prevention: Anshu Raj is candidate author; self-review is strictly rejected.
   - Saves expert_final_json alongside ai_draft_json to maintain full before/after audit proof.
   - One-click tokenized review link (/review/{token}) sent via email dispatch.
2. /admin/diffs — Side-by-Side Audit Portal:
   - Compares raw AI draft (Gemini 2.5 Flash) vs Human Expert Final version.
   - Shows reviewer identity, verification date, and exact editorial refinements.
3. /analytics — Level 6 Analytics & Bonus Level 7 A/B Experiment Dashboard:
   - Tracks human visitors, AI referrers (ChatGPT, Perplexity), and AI crawlers (GPTBot, ClaudeBot).
   - Shows Google Search Console queries and impressions.
   - Bonus Level 7 A/B test monitor with honest reporting ("Not enough data to call it" when sessions < 100).
   - AI Next-Topic Recommender with one-click "Approve Topic" button.
4. /admin/social — Level 5 Social Automation Queue:
   - Human approval queue for Bluesky replies (HITL gate — never auto-replies).
   - Shows scheduled posts and privacy-compliant mention logs.
   - One-click commenter data purge button.
5. /export & CLI flag (--export) — Renders static HTML to frontend/.
"""

import sys
import json
import argparse
import html
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.config import (
    FRONTEND_DIR, SECTION_NAME, PLATE_ID, COLOR_INDIC, CANONICAL_HOST,
    CANDIDATE_NAME, CANDIDATE_BRANCH, CANDIDATE_COLLEGE,
    DEVELOPER_NAME, EXACT_FOOTER_OWNERSHIP_LINE, BLUESKY_HANDLE,
    REVIEWER_NAME, REVIEWER_ROLE, REVIEWER_ORG
)
from engine.database import (
    init_db, get_db_connection, get_all_questions, get_answers_by_status,
    get_answer_by_slug, get_answer_by_token, approve_answer, reject_answer,
    get_all_providers, get_all_social_posts, purge_all_commenters
)
from engine.exporter import run_export
import importlib
_measure = importlib.import_module("engine.6_measure")
get_analytics_summary = _measure.get_analytics_summary
recommend_next_topics = _measure.recommend_next_topics
approve_topic_recommendation = _measure.approve_topic_recommendation

_social = importlib.import_module("engine.5_social")
approve_and_send_reply = _social.approve_and_send_reply
run_scheduled_posts = _social.run_scheduled_posts
fetch_and_queue_mentions = _social.fetch_and_queue_mentions

app = FastAPI(
    title="AI Atlas India — Plate 05 Indic Language AI Engine",
    description="Private Automation & Expert Review Portal for indic.aiatlasindia.com",
    version="2.0.0"
)

# Mount frontend directory for static assets (tokens.css, logo.svg, etc.)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def mask_sensitive(text: str) -> str:
    """Mask email addresses or secret keys for UI display privacy."""
    if not text:
        return ""
    if "@" in text:
        parts = text.split("@")
        name = parts[0]
        domain = parts[1]
        masked_name = name[:2] + "••••" if len(name) > 2 else "••"
        return f"{masked_name}@{domain}"
    if len(text) > 8:
        return text[:3] + "••••" + text[-3:]
    return "••••••••"


# Common navigation bar for admin / review pages
def render_admin_nav(active_tab: str = "review") -> str:
    tabs = [
        ("review", "Expert Review Portal", "/review"),
        ("diffs", "Before / After Diffs", "/admin/diffs"),
        ("analytics", "Analytics & A/B Experiments", "/analytics"),
        ("social", "Social & Reply Queue", "/admin/social")
    ]
    tabs_html = ""
    for tab_id, label, url in tabs:
        is_active = (tab_id == active_tab)
        bg = "var(--atlas-indic)" if is_active else "transparent"
        color = "#ffffff" if is_active else "var(--atlas-grid)"
        border = "var(--atlas-indic)" if is_active else "transparent"
        tabs_html += f"""
        <a href="{url}" style="color: {color}; text-decoration: none; padding: 6px 14px; font-family: var(--atlas-font-mono); font-size: 12px; font-weight: 600; text-transform: uppercase; background: {bg}; border: 1px solid {border};">
          {label}
        </a>
"""

    return f"""
    <div style="background: var(--atlas-ink); color: var(--atlas-paper); padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--atlas-indic); flex-wrap: wrap; gap: 12px;">
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-family: var(--atlas-font-mono); font-size: 12px; font-weight: 700; background: var(--atlas-indic); color: #fff; padding: 4px 8px;">
          PLATE 05 · INDIC
        </span>
        <span style="font-family: var(--atlas-font-display); font-size: 18px; font-weight: 700;">
          AI Atlas India Management Engine
        </span>
      </div>
      <div style="display: flex; gap: 8px; align-items: center;">
        {tabs_html}
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <form action="/api/export" method="post" style="margin: 0;">
          <button type="submit" style="background: var(--atlas-signal); color: var(--atlas-ink); border: 1.5px solid var(--atlas-ink); padding: 6px 14px; font-family: var(--atlas-font-mono); font-size: 12px; font-weight: 700; cursor: pointer; text-transform: uppercase;">
            Export Static Site →
          </button>
        </form>
        <a href="/" target="_blank" style="color: var(--atlas-paper); font-size: 13px; text-decoration: underline;">View Live Hub ↗</a>
      </div>
    </div>
"""


# Pydantic model for approval payload
class ApproveRequest(BaseModel):
    reviewer_name: str
    reviewer_role: str
    reviewer_org: str
    reviewed_at: str
    reviewer_declaration: Optional[str] = None
    expert_final_json: Dict[str, Any]


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", response_class=RedirectResponse)
def index():
    return RedirectResponse(url="/review")


# ==============================================================================
# 1. HUMAN EXPERT REVIEW PORTAL (/review & /review/{token})
# ==============================================================================
@app.get("/review", response_class=HTMLResponse)
def review_portal_home(slug: Optional[str] = None):
    return render_review_interface(slug=slug, token=None)


@app.get("/review/{token}", response_class=HTMLResponse)
def review_portal_by_token(token: str):
    """Secure one-click review URL dispatched via email to real independent expert."""
    answer = get_answer_by_token(token)
    if not answer:
        return HTMLResponse(
            content=f"""
            <div style="font-family: monospace; padding: 40px; text-align: center;">
              <h2>Invalid or Expired Review Token</h2>
              <p>The review token <code>{html.escape(token)}</code> was not found in the database.</p>
              <a href="/review">Go to Main Review Portal →</a>
            </div>
            """,
            status_code=404
        )
    return render_review_interface(slug=answer["slug"], token=token)


def _render_readonly_table_html(comp_table: List[Dict[str, Any]]) -> str:
    """Render human-readable HTML table for Raw AI Draft with zero horizontal scroll."""
    if not comp_table or not isinstance(comp_table, list):
        return "<p style='color: var(--atlas-muted); font-size: 13px; font-style: italic; margin: 4px 0;'>No comparison table drafted.</p>"

    known_order = ["provider", "price_inr", "price", "languages", "latency", "data_residency", "onboarding"]
    all_keys = []
    for row in comp_table:
        if isinstance(row, dict):
            for k in row.keys():
                if k not in all_keys:
                    all_keys.append(k)
    ordered_keys = [k for k in known_order if k in all_keys] + [k for k in all_keys if k not in known_order]

    label_map = {
        "provider": "Provider",
        "price_inr": "Price in India (INR)",
        "price": "Price in India (INR)",
        "languages": "Supported Languages",
        "latency": "Observed Latency",
        "data_residency": "Data Residency",
        "onboarding": "Setup & Onboarding"
    }

    th_items = "".join([
        f"<th style='padding: 8px 10px; background: #0F1B2D; color: #FFFFFF; font-family: var(--atlas-font-mono); font-size: 10.5px; text-transform: uppercase; text-align: left; font-weight: 600; letter-spacing: 0.05em;'>{html.escape(label_map.get(k, k.replace('_', ' ').title()))}</th>"
        for k in ordered_keys
    ])

    tr_items = ""
    for r in comp_table:
        if not isinstance(r, dict):
            continue
        tds = ""
        for k in ordered_keys:
            raw_v = str(r.get(k, "") or "")
            v_escaped = html.escape(raw_v)
            if "●" in v_escaped:
                v_escaped = v_escaped.replace("●", "<span style='color: #0F1B2D; font-weight: 700;'>●</span>")
            if "◌" in v_escaped:
                v_escaped = v_escaped.replace("◌", "<span style='color: #64748B; font-weight: 700;'>◌</span>")
            tds += f"<td style='padding: 8px 10px; border-bottom: 1px solid #E2E8F0; font-size: 11.5px; line-height: 1.45; word-break: break-word; vertical-align: top;'>{v_escaped}</td>"
        tr_items += f"<tr style='background: #FFFFFF;'>{tds}</tr>"

    return f"""
    <div style="border: 1px solid #CBD5E1; border-radius: 6px; overflow: hidden; background: #FFFFFF; margin-top: 6px;">
      <table style="width: 100%; border-collapse: collapse; table-layout: auto;">
        <thead><tr>{th_items}</tr></thead>
        <tbody>{tr_items}</tbody>
      </table>
    </div>
    """


def render_review_interface(slug: Optional[str] = None, token: Optional[str] = None) -> HTMLResponse:
    """Core review portal rendering logic with spacious 2-pane workspace, collapsible queue, and structured table editor."""
    answers = get_answers_by_status()
    questions = get_all_questions(limit=50)

    selected_answer = None
    if token:
        selected_answer = get_answer_by_token(token)
    elif slug:
        selected_answer = get_answer_by_slug(slug)

    if not selected_answer and answers:
        pending = [a for a in answers if a["status"] == "PENDING_REVIEW"]
        selected_answer = pending[0] if pending else answers[0]

    raw_ai_draft = {}
    expert_final = {}
    if selected_answer:
        try:
            raw_ai_draft = json.loads(selected_answer.get("ai_draft_json") or "{}")
        except Exception:
            pass
        try:
            expert_final = json.loads(selected_answer.get("expert_final_json") or "{}")
        except Exception:
            pass

    display_data = expert_final if expert_final else raw_ai_draft

    answers_nav_html = ""
    for a in answers:
        is_active = (selected_answer and a["slug"] == selected_answer["slug"])
        active_class = "nav-answer-card nav-answer-card--active" if is_active else "nav-answer-card"
        status_key = a["status"].lower()

        answers_nav_html += f"""
        <div class="{active_class}">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <span class="status-pill status-pill--{status_key}">{a['status']}</span>
            <span style="font-family: var(--atlas-font-mono); font-size: 10px; color: var(--atlas-muted); font-weight: 600;">{html.escape(a.get('category', ''))}</span>
          </div>
          <div style="font-weight: 600; font-size: 13px; line-height: 1.35; margin-bottom: 4px;">
            <a href="/review?slug={a['slug']}" style="color: var(--atlas-ink); text-decoration: none;">{html.escape(a['title'])}</a>
          </div>
          <div style="font-family: var(--atlas-font-mono); font-size: 10px; color: var(--atlas-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            /{a['slug']}
          </div>
        </div>
        """

    edit_title = display_data.get("question") or (selected_answer["title"] if selected_answer else "")
    edit_summary = display_data.get("summary", "")
    edit_code = display_data.get("runnable_python_code", "")
    edit_breakdown = "\n".join(display_data.get("technical_breakdown", []))
    edit_table = json.dumps(display_data.get("comparison_table", []), indent=2, ensure_ascii=False)
    edit_sources = "\n".join(display_data.get("sources", []))

    # Reviewer fields: DISQUALIFICATION GUARDRAIL: Never default to candidate Anshu Raj
    cur_rev = (selected_answer.get("reviewer_name") if selected_answer else "") or ""
    if not cur_rev or cur_rev == CANDIDATE_NAME:
        cur_reviewer_name = REVIEWER_NAME
        cur_reviewer_role = REVIEWER_ROLE
        cur_reviewer_org = REVIEWER_ORG
    else:
        cur_reviewer_name = cur_rev
        cur_reviewer_role = selected_answer.get("reviewer_role") or REVIEWER_ROLE
        cur_reviewer_org = selected_answer.get("reviewer_org") or REVIEWER_ORG

    cur_reviewed_at = (selected_answer.get("reviewed_at") if selected_answer else "") or datetime.now().strftime("%d %B %Y")
    cur_declaration = (selected_answer.get("reviewer_declaration") if selected_answer else "") or "I confirm that I am an independent expert with no financial interest or employment relationship with the commercial AI providers covered in this section."

    is_profile_filled = bool(cur_reviewer_name and cur_reviewer_name.strip() and cur_reviewer_name.strip() != CANDIDATE_NAME)
    profile_display_style = "none" if is_profile_filled else "block"
    profile_toggle_text = "Edit Profile ▾" if is_profile_filled else "Collapse Profile ▴"
    reviewer_display_summary = f"{cur_reviewer_name} — Verified ✓ ({cur_reviewer_role})" if is_profile_filled else "Pending Expert Sign-off (Incomplete)"

    readonly_table_html = _render_readonly_table_html(raw_ai_draft.get("comparison_table", []))

    raw_ai_json_js = json.dumps(raw_ai_draft, ensure_ascii=False)
    initial_table_js = json.dumps(display_data.get("comparison_table", []), ensure_ascii=False)

    status_color = "var(--atlas-signal)" if (selected_answer and selected_answer["status"] == "PENDING_REVIEW") else ("var(--atlas-indic)" if (selected_answer and selected_answer["status"] == "APPROVED") else "var(--atlas-route)")
    status_text_color = "var(--atlas-ink)" if (selected_answer and selected_answer["status"] == "PENDING_REVIEW") else "#FFFFFF"

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-section="indic">
<head>
  <meta charset="UTF-8">
  <title>Human Expert Review Portal — AI Atlas India (Plate 05)</title>
  <link rel="stylesheet" href="/static/tokens.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      font-family: var(--atlas-font-body);
      background: var(--atlas-paper);
      color: var(--atlas-ink);
      height: 100vh;
      overflow: hidden;
    }}

    /* Sub-header Bar */
    .review-subbar {{
      background: #FFFFFF;
      border-bottom: 1px solid #CBD5E1;
      padding: 8px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      height: 48px;
    }}
    .btn-drawer-toggle {{
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      padding: 5px 12px;
      font-family: var(--atlas-font-mono);
      font-size: 12px;
      font-weight: 600;
      color: #0F172A;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}
    .btn-drawer-toggle:hover {{
      background: #E2E8F0;
      color: #000000;
    }}
    .btn-subbar-link {{
      font-family: var(--atlas-font-mono);
      font-size: 12px;
      color: var(--atlas-indic);
      font-weight: 600;
      text-decoration: underline;
    }}

    /* Body Layout: Drawer + 50/50 Workspace */
    .review-body-layout {{
      display: flex;
      height: calc(100vh - 106px);
      overflow: hidden;
      position: relative;
    }}

    /* Collapsible Drawer (Left Queue) */
    .review-drawer {{
      width: 250px;
      min-width: 250px;
      background: #F8FAFC;
      border-right: 1px solid #CBD5E1;
      display: flex;
      flex-direction: column;
      transition: width 0.22s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease;
      overflow: hidden;
      flex-shrink: 0;
      z-index: 10;
    }}
    .review-drawer.collapsed {{
      width: 0 !important;
      min-width: 0 !important;
      border-right: none !important;
      opacity: 0;
      pointer-events: none;
    }}
    .drawer-header {{
      padding: 12px 14px;
      background: #FFFFFF;
      border-bottom: 1px solid #E2E8F0;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .btn-close-drawer {{
      background: none;
      border: none;
      font-size: 14px;
      cursor: pointer;
      color: #64748B;
      padding: 2px 6px;
      border-radius: 4px;
      line-height: 1;
    }}
    .btn-close-drawer:hover {{
      background: #E2E8F0;
      color: #0F172A;
    }}
    .drawer-content {{
      padding: 12px;
      overflow-y: auto;
      flex: 1;
    }}
    .nav-answer-card {{
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      margin-bottom: 8px;
      padding: 10px;
      background: #FFFFFF;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .nav-answer-card:hover {{
      border-color: var(--atlas-indic);
    }}
    .nav-answer-card--active {{
      border-color: var(--atlas-indic);
      background: #FFFBF0;
      box-shadow: 0 0 0 1px var(--atlas-indic);
    }}

    /* 50/50 Split Workspace */
    .review-workspace {{
      flex: 1 1 0%;
      display: grid;
      grid-template-columns: 1fr 1fr;
      overflow: hidden;
      height: 100%;
    }}

    /* Left Pane: Raw AI Draft */
    .pane-draft {{
      background: #F8FAFC;
      border-right: 1px solid #CBD5E1;
      padding: 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }}
    .draft-card {{
      background: #FFFFFF;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 18px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }}
    .draft-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      border-bottom: 1px solid #F1F5F9;
      padding-bottom: 8px;
    }}
    .draft-card-label {{
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      text-transform: uppercase;
      font-weight: 700;
      color: #64748B;
      letter-spacing: 0.08em;
    }}

    /* Right Pane: Expert Verification */
    .pane-expert {{
      background: #FFFFFF;
      padding: 24px 24px 0 24px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      position: relative;
    }}
    .pane-expert .form-group {{
      margin-bottom: 24px;
    }}
    .pane-expert .form-group-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }}
    .pane-expert label {{
      display: block;
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
      color: #334155;
    }}
    .pane-expert .form-control {{
      width: 100%;
      padding: 9px 12px;
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      font-family: var(--atlas-font-body);
      font-size: 13.5px;
      background: #FFFFFF;
      color: var(--atlas-ink);
      line-height: 1.5;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .pane-expert .form-control:focus {{
      outline: none;
      border-color: var(--atlas-indic);
      box-shadow: 0 0 0 3px rgba(138, 90, 28, 0.15);
    }}
    .form-control-mono {{
      font-family: var(--atlas-font-mono) !important;
      font-size: 12px !important;
      line-height: 1.5 !important;
    }}

    /* Policy Pill Badge */
    .policy-pill {{
      display: inline-flex;
      align-items: center;
      background: #FEF9C3;
      color: #854D0E;
      border: 1px solid #FDE047;
      padding: 3px 8px;
      font-size: 11px;
      font-family: var(--atlas-font-mono);
      font-weight: 600;
      border-radius: 4px;
      cursor: help;
    }}
    .human-gate-pill {{
      font-family: var(--atlas-font-mono);
      font-size: 10.5px;
      font-weight: 700;
      color: var(--atlas-route);
      background: #FEE2E2;
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid #FECACA;
    }}

    /* Reviewer Profile Accordion Card */
    .reviewer-profile-card {{
      border: 1px solid #CBD5E1;
      border-radius: 6px;
      padding: 12px 16px;
      background: #F8FAFC;
      margin-bottom: 24px;
    }}
    .reviewer-summary-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      user-select: none;
    }}
    .btn-accordion-toggle {{
      background: #FFFFFF;
      border: 1px solid #CBD5E1;
      border-radius: 4px;
      padding: 4px 10px;
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      font-weight: 600;
      color: #475569;
      cursor: pointer;
    }}
    .btn-accordion-toggle:hover {{
      background: #F1F5F9;
      color: #0F172A;
    }}

    /* Quick Copy & Add Row Buttons */
    .btn-quick-copy {{
      background: #F1F5F9;
      border: 1px solid #CBD5E1;
      color: #475569;
      font-family: var(--atlas-font-mono);
      font-size: 10.5px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 4px;
      cursor: pointer;
      text-transform: uppercase;
      transition: all 0.15s ease;
    }}
    .btn-quick-copy:hover {{
      background: #E2E8F0;
      color: #0F172A;
    }}
    .btn-add-row {{
      background: #F8FAFC;
      color: #0F172A;
      font-family: var(--atlas-font-mono);
      font-size: 11.5px;
      font-weight: 600;
      padding: 8px 14px;
      border: 1px dashed #94A3B8;
      border-radius: 6px;
      cursor: pointer;
      width: 100%;
      text-align: center;
      transition: all 0.15s ease;
    }}
    .btn-add-row:hover {{
      background: #F1F5F9;
      border-color: #64748B;
    }}

    /* Sticky Action Bar */
    .sticky-action-bar {{
      position: sticky;
      bottom: 0;
      background: rgba(255, 255, 255, 0.96);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border-top: 1px solid #CBD5E1;
      padding: 16px 24px;
      margin: 32px -24px 0 -24px;
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 100;
      box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.04);
    }}
    .btn {{
      padding: 10px 22px;
      font-weight: 700;
      font-size: 13.5px;
      border-radius: 6px;
      cursor: pointer;
      font-family: var(--atlas-font-mono);
      text-transform: uppercase;
      border: 1.5px solid var(--atlas-ink);
      transition: all 0.15s ease;
    }}
    .btn-approve {{
      background: var(--atlas-signal);
      color: var(--atlas-ink);
    }}
    .btn-approve:hover {{
      background: #E2B322;
      box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }}
    .btn-reject {{
      background: #FFFFFF;
      color: var(--atlas-route);
      border-color: var(--atlas-route);
    }}
    .btn-reject:hover {{
      background: #FEE2E2;
    }}

    /* Status Pills */
    .status-pill {{
      font-family: var(--atlas-font-mono);
      font-size: 10.5px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
      display: inline-block;
    }}
    .status-pill--pending_review, .status-pill--pending {{
      background: var(--atlas-signal);
      color: var(--atlas-ink);
    }}
    .status-pill--approved {{
      background: var(--atlas-indic);
      color: #FFFFFF;
    }}
    .status-pill--rejected {{
      background: var(--atlas-route);
      color: #FFFFFF;
    }}

    @media (max-width: 992px) {{
      .review-workspace {{
        grid-template-columns: 1fr;
      }}
      .review-body-layout {{
        height: auto;
        overflow: visible;
      }}
      .pane-draft, .pane-expert {{
        overflow: visible;
      }}
    }}
  </style>
</head>
<body>
  {render_admin_nav(active_tab="review")}

  <div class="review-page-wrapper">
    <!-- Sub-header Bar -->
    <div class="review-subbar">
      <div style="display: flex; align-items: center; gap: 12px; min-width: 0;">
        <button type="button" id="sidebarToggleBtn" class="btn-drawer-toggle" onclick="toggleSidebar()" title="Toggle Candidate Queue">
          <span id="drawerIcon">☰</span>
          <span style="font-weight: 600;">Queue ({len(answers)})</span>
        </button>
        <div style="height: 18px; width: 1px; background: #CBD5E1;"></div>
        <span class="atlas-badge atlas-badge--indic" style="font-size: 10px; padding: 2px 7px; flex-shrink: 0;">
          {html.escape(selected_answer.get('category', 'Speech & Voice')) if selected_answer else 'General'}
        </span>
        <span style="font-weight: 700; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
          {html.escape(selected_answer['title'] if selected_answer else 'Select an answer')}
        </span>
      </div>
      <div style="display: flex; align-items: center; gap: 10px; flex-shrink: 0;">
        <span class="status-pill status-pill--{selected_answer['status'].lower() if selected_answer else 'pending'}">
          {selected_answer['status'] if selected_answer else ''}
        </span>
        {f'<a href="/answers/{selected_answer["slug"]}.html" target="_blank" class="btn-subbar-link">Preview Published ↗</a>' if selected_answer else ''}
      </div>
    </div>

    <!-- Main Workspace with Collapsible Drawer and 50/50 Split -->
    <div class="review-body-layout" id="reviewBodyLayout">
      <!-- Collapsible Drawer (Candidate Q&As) -->
      <aside class="review-drawer" id="reviewDrawer">
        <div class="drawer-header">
          <span style="font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; text-transform: uppercase;">
            Candidate Q&As ({len(answers)})
          </span>
          <button type="button" class="btn-close-drawer" onclick="toggleSidebar()" title="Collapse Queue">✕</button>
        </div>
        <div class="drawer-content">
          {answers_nav_html}

          <div style="margin-top: 20px; padding-top: 14px; border-top: 1px solid #CBD5E1;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span style="font-family: var(--atlas-font-mono); font-size: 10px; text-transform: uppercase; color: #475569; font-weight: 700;">
                Discovered Queries ({len(questions)})
              </span>
            </div>
            <div style="max-height: 220px; overflow-y: auto; font-size: 11px;">
              {''.join([f'<div style="padding: 5px 0; border-bottom: 1px solid #E2E8F0; line-height: 1.35;"><span style="color: #64748B; font-weight: 600;">[{html.escape(q["source"])}]</span> {html.escape(q["clean_question"][:55])}...</div>' for q in questions[:15]])}
            </div>
          </div>
        </div>
      </aside>

      <!-- 50/50 Split Workspace -->
      <main class="review-workspace" id="reviewWorkspace">
        <!-- Left Pane: 1. RAW AI DRAFT -->
        <section class="pane-draft" id="paneDraft">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 10px;">
              <span style="font-family: var(--atlas-font-mono); font-size: 13px; font-weight: 700; color: #475569;">
                1. RAW AI DRAFT (GEMINI 2.5 FLASH)
              </span>
              <span style="font-family: var(--atlas-font-mono); font-size: 10px; font-weight: 600; background: #E2E8F0; color: #475569; padding: 2px 6px; border-radius: 4px;">
                UNTOUCHED AUDIT COPY
              </span>
            </div>
            <span style="font-family: var(--atlas-font-mono); font-size: 11px; color: #64748B;">Read-Only Baseline</span>
          </div>

          <!-- Question & Summary Card -->
          <div class="draft-card">
            <div class="draft-card-header">
              <span class="draft-card-label">Draft Question & Answer Guidance</span>
            </div>
            <h2 style="font-family: var(--atlas-font-display); font-size: 18px; line-height: 1.35; margin: 0 0 10px 0; color: #0F172A;">
              {html.escape(raw_ai_draft.get("question", selected_answer["title"] if selected_answer else "Select an answer"))}
            </h2>
            <p style="font-size: 13.5px; line-height: 1.6; color: #334155; margin: 0;">
              {html.escape(raw_ai_draft.get("summary", ""))}
            </p>
          </div>

          <!-- Comparison Table Card -->
          <div class="draft-card">
            <div class="draft-card-header">
              <span class="draft-card-label">AI Comparison Matrix Draft</span>
              <span style="font-size: 11px; color: #64748B; font-family: var(--atlas-font-mono);">{len(raw_ai_draft.get("comparison_table", []))} Providers</span>
            </div>
            {readonly_table_html}
          </div>

          <!-- Code Card -->
          <div class="draft-card">
            <div class="draft-card-header">
              <span class="draft-card-label">AI Runnable Python API Code</span>
              <button type="button" class="btn-quick-copy" onclick="copyToClipboard(RAW_AI.runnable_python_code || '', this)">Copy Code</button>
            </div>
            <pre style="background: #0F172A; color: #F8FAFC; padding: 14px; border-radius: 6px; font-family: var(--atlas-font-mono); font-size: 12px; line-height: 1.5; overflow-x: auto; margin: 0; max-height: 220px;">{html.escape(raw_ai_draft.get("runnable_python_code", ""))}</pre>
          </div>

          <!-- Technical Breakdown Card -->
          <div class="draft-card">
            <div class="draft-card-header">
              <span class="draft-card-label">Technical Breakdown & Trade-Offs</span>
            </div>
            <ul style="font-size: 13px; line-height: 1.6; color: #334155; padding-left: 20px; margin: 0;">
              {''.join([f'<li style="margin-bottom: 6px;">{html.escape(pt)}</li>' for pt in raw_ai_draft.get("technical_breakdown", [])])}
            </ul>
          </div>

          <!-- Sourced URLs Card -->
          <div class="draft-card">
            <div class="draft-card-header">
              <span class="draft-card-label">Authoritative Claim Sourcing URLs</span>
            </div>
            <ul style="font-family: var(--atlas-font-mono); font-size: 11.5px; line-height: 1.6; padding-left: 20px; margin: 0;">
              {''.join([f'<li style="margin-bottom: 4px;"><a href="{html.escape(s)}" target="_blank" rel="noopener" style="color: var(--atlas-indic); text-decoration: underline; word-break: break-all;">{html.escape(s)}</a></li>' for s in raw_ai_draft.get("sources", [])])}
            </ul>
          </div>
        </section>

        <!-- Right Pane: 2. EXPERT VERIFICATION & SIGN-OFF -->
        <section class="pane-expert" id="paneExpert">
          <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #CBD5E1; padding-bottom: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <span style="font-family: var(--atlas-font-mono); font-size: 13px; font-weight: 700; color: var(--atlas-indic);">
                2. EXPERT VERIFICATION & SIGN-OFF
              </span>
              <span class="policy-pill" title="Candidate author {CANDIDATE_NAME} cannot review their own section. Must be independently signed by verified domain expert.">
                Policy Check: Independent Reviewer Required ⓘ
              </span>
            </div>
            <span class="human-gate-pill">HUMAN GATE MANDATORY</span>
          </div>

          <form id="expertForm" onsubmit="handleApprove(event)">
            <input type="hidden" id="answerSlug" value="{selected_answer['slug'] if selected_answer else ''}">

            <!-- Collapsible Reviewer Profile Accordion Card -->
            <div class="reviewer-profile-card">
              <div class="reviewer-summary-bar" onclick="toggleReviewerProfile()">
                <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
                  <span style="font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase;">Reviewer Profile:</span>
                  <span id="reviewerSummaryDisplay" style="font-size: 13px; font-weight: 600; color: #0F172A; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                    {reviewer_display_summary}
                  </span>
                </div>
                <button type="button" class="btn-accordion-toggle" id="reviewerAccordionBtn">
                  {profile_toggle_text}
                </button>
              </div>

              <div id="reviewerFieldsBody" style="display: {profile_display_style}; padding-top: 14px; margin-top: 10px; border-top: 1px solid #E2E8F0;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                  <div class="form-group" style="margin-bottom: 0;">
                    <label>Real Reviewer Name</label>
                    <input type="text" class="form-control" id="reviewerName" value="{html.escape(cur_reviewer_name)}" oninput="updateReviewerSummary()" required>
                  </div>
                  <div class="form-group" style="margin-bottom: 0;">
                    <label>Verified Professional Role</label>
                    <input type="text" class="form-control" id="reviewerRole" value="{html.escape(cur_reviewer_role)}" oninput="updateReviewerSummary()" required>
                  </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                  <div class="form-group" style="margin-bottom: 0;">
                    <label>Organization / Consultancy</label>
                    <input type="text" class="form-control" id="reviewerOrg" value="{html.escape(cur_reviewer_org)}" required>
                  </div>
                  <div class="form-group" style="margin-bottom: 0;">
                    <label>Review Date</label>
                    <input type="text" class="form-control" id="reviewedAt" value="{html.escape(cur_reviewed_at)}" required>
                  </div>
                </div>

                <div class="form-group" style="margin-bottom: 0;">
                  <label>Independence Confirmation Declaration</label>
                  <input type="text" class="form-control" id="reviewerDeclaration" value="{html.escape(cur_declaration)}" required>
                </div>
              </div>
            </div>

            <!-- Approved Question Title -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Approved Question Title</label>
                <button type="button" class="btn-quick-copy" onclick="copyField('question', 'editTitle')">Copy from AI</button>
              </div>
              <input type="text" class="form-control" id="editTitle" value="{html.escape(edit_title)}" required>
            </div>

            <!-- Expert Summary & Decision Guidance -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Expert Summary & Decision Guidance</label>
                <button type="button" class="btn-quick-copy" onclick="copyField('summary', 'editSummary')">Copy from AI</button>
              </div>
              <textarea class="form-control" id="editSummary" rows="3" required>{html.escape(edit_summary)}</textarea>
            </div>

            <!-- Structured Comparison Table -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Comparison Table</label>
                <div style="display: flex; gap: 8px; align-items: center;">
                  <button type="button" class="btn-quick-copy" onclick="resetTableToAI()">Reset to AI Draft</button>
                  <button type="button" class="btn-quick-copy" id="toggleRawJsonBtn" onclick="toggleRawJson()">Toggle Raw JSON</button>
                </div>
              </div>

              <!-- Interactive UI Table Rows -->
              <div id="interactiveTableRows"></div>

              <div style="margin-top: 8px;">
                <button type="button" class="btn-add-row" onclick="addTableRow()">+ Add Provider Row</button>
              </div>

              <!-- Raw JSON Textarea (Hidden by default) -->
              <div id="rawJsonWrapper" style="display: none; margin-top: 10px;">
                <div style="font-size: 11px; font-family: var(--atlas-font-mono); color: #64748B; margin-bottom: 4px;">Direct JSON Array Editing (Synced with visual table):</div>
                <textarea class="form-control form-control-mono" id="editTable" rows="7" required onchange="syncJsonToTable()">{html.escape(edit_table)}</textarea>
              </div>
            </div>

            <!-- Working Python API Code -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Working Python API Code</label>
                <button type="button" class="btn-quick-copy" onclick="copyField('runnable_python_code', 'editCode')">Copy from AI</button>
              </div>
              <textarea class="form-control form-control-mono" id="editCode" rows="6" required>{html.escape(edit_code)}</textarea>
            </div>

            <!-- Technical Trade-Offs -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Technical Trade-Offs (One per line)</label>
                <button type="button" class="btn-quick-copy" onclick="copyBreakdownFromAI()">Copy from AI</button>
              </div>
              <textarea class="form-control" id="editBreakdown" rows="3" required>{html.escape(edit_breakdown)}</textarea>
            </div>

            <!-- Verified Sourced URLs -->
            <div class="form-group">
              <div class="form-group-header">
                <label>Verified Sourced URLs (One per line)</label>
                <button type="button" class="btn-quick-copy" onclick="copySourcesFromAI()">Copy from AI</button>
              </div>
              <textarea class="form-control form-control-mono" id="editSources" rows="2" required>{html.escape(edit_sources)}</textarea>
            </div>

            <!-- Sticky Action Footer -->
            <div class="sticky-action-bar">
              <button type="submit" class="btn btn-approve" id="approveSubmitBtn">
                Approve & Publish with Expert Byline
              </button>
              <button type="button" class="btn btn-reject" onclick="handleReject()">
                Reject Draft
              </button>
              <span id="saveStatusIndicator" style="font-size: 12px; font-family: var(--atlas-font-mono); color: #64748B; margin-left: auto;"></span>
            </div>
          </form>
        </section>
      </main>
    </div>
  </div>

  <script>
    const RAW_AI = {raw_ai_json_js};
    let currentTableData = {initial_table_js};
    if (!Array.isArray(currentTableData)) currentTableData = [];

    function escapeHtml(str) {{
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    function toggleSidebar() {{
      const drawer = document.getElementById('reviewDrawer');
      const icon = document.getElementById('drawerIcon');
      drawer.classList.toggle('collapsed');
      const isCollapsed = drawer.classList.contains('collapsed');
      if (icon) {{
        icon.innerText = isCollapsed ? '☰' : '✕';
      }}
      try {{
        localStorage.setItem('atlas_review_drawer_collapsed', isCollapsed ? 'true' : 'false');
      }} catch(e) {{}}
    }}

    function toggleReviewerProfile() {{
      const body = document.getElementById('reviewerFieldsBody');
      const btn = document.getElementById('reviewerAccordionBtn');
      if (body.style.display === 'none') {{
        body.style.display = 'block';
        btn.innerText = 'Collapse Profile ▴';
      }} else {{
        body.style.display = 'none';
        btn.innerText = 'Edit Profile ▾';
      }}
    }}

    function updateReviewerSummary() {{
      const name = document.getElementById('reviewerName').value.trim();
      const role = document.getElementById('reviewerRole').value.trim();
      const summaryEl = document.getElementById('reviewerSummaryDisplay');
      if (name && name.toLowerCase() !== '{CANDIDATE_NAME.lower()}') {{
        summaryEl.innerHTML = `${{escapeHtml(name)}} — Verified ✓ (${{escapeHtml(role || 'Expert')}})`;
      }} else {{
        summaryEl.innerHTML = '<span style="color: var(--atlas-route);">Pending Expert Sign-off (Incomplete)</span>';
      }}
    }}

    function renderInteractiveTable() {{
      const container = document.getElementById('interactiveTableRows');
      if (!container) return;

      if (!currentTableData || currentTableData.length === 0) {{
        container.innerHTML = '<div style="padding: 16px; text-align: center; color: #64748B; font-size: 13px; border: 1px dashed #CBD5E1; border-radius: 6px; background: #F8FAFC;">No providers in comparison table. Click "+ Add Provider Row" below or "Reset to AI Draft".</div>';
        return;
      }}

      let html = '';
      currentTableData.forEach((row, idx) => {{
        const provName = row.provider || ('Provider #' + (idx + 1));
        html += `
          <div class="table-row-card" data-index="${{idx}}" style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 14px; margin-bottom: 12px; background: #F8FAFC;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <strong style="font-size: 13px; color: #0F172A;">Row ${{idx + 1}}: <span style="color: var(--atlas-indic);">${{escapeHtml(provName)}}</span></strong>
              <button type="button" onclick="removeTableRow(${{idx}})" style="background: none; border: 1px solid #FCA5A5; color: #DC2626; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; font-family: var(--atlas-font-mono);">
                ✕ Remove
              </button>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Provider Name</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.provider || '')}}" oninput="updateTableRow(${{idx}}, 'provider', this.value)" placeholder="e.g. Sarvam AI (Saaras)">
              </div>
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Price in India (INR / GST)</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.price_inr || row.price || '')}}" oninput="updateTableRow(${{idx}}, 'price_inr', this.value)" placeholder="● ₹0.40 / min · checked [DATE]">
              </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 8px;">
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Supported Languages</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.languages || '')}}" oninput="updateTableRow(${{idx}}, 'languages', this.value)" placeholder="● 10 languages + English · checked [DATE]">
              </div>
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Observed Latency</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.latency || '')}}" oninput="updateTableRow(${{idx}}, 'latency', this.value)" placeholder="● ~500ms streaming or ◌ Not yet sourced">
              </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Data Residency</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.data_residency || '')}}" oninput="updateTableRow(${{idx}}, 'data_residency', this.value)" placeholder="● AWS Mumbai (India) · checked [DATE]">
              </div>
              <div>
                <label style="display: block; font-size: 10px; font-family: var(--atlas-font-mono); text-transform: uppercase; color: #475569; margin-bottom: 4px; font-weight: 600;">Setup & Onboarding</label>
                <input type="text" class="form-control" value="${{escapeHtml(row.onboarding || '')}}" oninput="updateTableRow(${{idx}}, 'onboarding', this.value)" placeholder="e.g. Instant self-serve API key">
              </div>
            </div>
          </div>
        `;
      }});
      container.innerHTML = html;
    }}

    function updateTableRow(rowIdx, key, value) {{
      if (currentTableData[rowIdx]) {{
        currentTableData[rowIdx][key] = value;
        syncTableToJson();
      }}
    }}

    function addTableRow() {{
      currentTableData.push({{
        provider: "",
        price_inr: "● ₹... · checked 23 November 2026",
        languages: "● 10 languages · checked 23 November 2026",
        latency: "◌ Not yet sourced",
        data_residency: "● India Cloud · checked 23 November 2026",
        onboarding: "Self-serve API"
      }});
      renderInteractiveTable();
      syncTableToJson();
    }}

    function removeTableRow(idx) {{
      if (confirm("Remove this provider row from comparison table?")) {{
        currentTableData.splice(idx, 1);
        renderInteractiveTable();
        syncTableToJson();
      }}
    }}

    function syncTableToJson() {{
      const jsonEl = document.getElementById('editTable');
      if (jsonEl) {{
        jsonEl.value = JSON.stringify(currentTableData, null, 2);
      }}
    }}

    function syncJsonToTable() {{
      const jsonEl = document.getElementById('editTable');
      if (!jsonEl) return;
      try {{
        const parsed = JSON.parse(jsonEl.value);
        if (Array.isArray(parsed)) {{
          currentTableData = parsed;
          renderInteractiveTable();
        }}
      }} catch(e) {{
        console.error('Invalid JSON in textarea:', e);
      }}
    }}

    function toggleRawJson() {{
      const rawBox = document.getElementById('rawJsonWrapper');
      const btn = document.getElementById('toggleRawJsonBtn');
      if (rawBox.style.display === 'none') {{
        rawBox.style.display = 'block';
        btn.innerText = 'Hide Raw JSON';
      }} else {{
        syncJsonToTable();
        rawBox.style.display = 'none';
        btn.innerText = 'Toggle Raw JSON';
      }}
    }}

    function copyField(rawKey, targetId) {{
      if (!RAW_AI || RAW_AI[rawKey] === undefined) {{
        alert('No draft content found for this field.');
        return;
      }}
      const target = document.getElementById(targetId);
      if (target) {{
        target.value = RAW_AI[rawKey];
        flashField(targetId);
      }}
    }}

    function resetTableToAI() {{
      if (!RAW_AI.comparison_table || !Array.isArray(RAW_AI.comparison_table)) {{
        alert('No comparison table in raw draft.');
        return;
      }}
      if (confirm('Reset comparison table to initial AI draft?')) {{
        currentTableData = JSON.parse(JSON.stringify(RAW_AI.comparison_table));
        renderInteractiveTable();
        syncTableToJson();
        flashField('interactiveTableRows');
      }}
    }}

    function copyBreakdownFromAI() {{
      if (!RAW_AI.technical_breakdown) return;
      document.getElementById('editBreakdown').value = RAW_AI.technical_breakdown.join('\\n');
      flashField('editBreakdown');
    }}

    function copySourcesFromAI() {{
      if (!RAW_AI.sources) return;
      document.getElementById('editSources').value = RAW_AI.sources.join('\\n');
      flashField('editSources');
    }}

    function copyToClipboard(text, btn) {{
      if (!text) return;
      navigator.clipboard.writeText(text).then(() => {{
        const orig = btn.innerText;
        btn.innerText = 'Copied!';
        setTimeout(() => {{ btn.innerText = orig; }}, 1200);
      }}).catch(err => {{
        alert('Failed to copy: ' + err);
      }});
    }}

    function flashField(id) {{
      const el = document.getElementById(id);
      if (!el) return;
      const origBg = el.style.backgroundColor;
      el.style.backgroundColor = '#FEF9C3';
      setTimeout(() => {{ el.style.backgroundColor = origBg; }}, 350);
    }}

    async function handleApprove(event) {{
      event.preventDefault();
      const slug = document.getElementById('answerSlug').value;
      if (!slug) return alert('No answer selected.');

      const reviewerName = document.getElementById('reviewerName').value.trim();
      if (reviewerName.toLowerCase() === '{CANDIDATE_NAME.lower()}') {{
        return alert('DISQUALIFICATION GUARDRAIL: Candidate author {CANDIDATE_NAME} cannot review their own section. Please enter the name of the independent domain expert.');
      }}

      // Ensure interactive table is serialized to textarea
      syncTableToJson();

      let compTable = [];
      try {{
        compTable = JSON.parse(document.getElementById('editTable').value);
      }} catch(e) {{
        return alert('Comparison Table must be valid JSON: ' + e);
      }}

      const breakdown = document.getElementById('editBreakdown').value
        .split('\\n').map(s => s.trim()).filter(Boolean);
      const sources = document.getElementById('editSources').value
        .split('\\n').map(s => s.trim()).filter(Boolean);

      const expertFinalJson = {{
        question: document.getElementById('editTitle').value,
        summary: document.getElementById('editSummary').value,
        comparison_table: compTable,
        runnable_python_code: document.getElementById('editCode').value,
        technical_breakdown: breakdown,
        sources: sources,
        faq_schema: {{
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [{{
            "@type": "Question",
            "name": document.getElementById('editTitle').value,
            "acceptedAnswer": {{
              "@type": "Answer",
              "text": document.getElementById('editSummary').value
            }}
          }}]
        }}
      }};

      const payload = {{
        reviewer_name: reviewerName,
        reviewer_role: document.getElementById('reviewerRole').value,
        reviewer_org: document.getElementById('reviewerOrg').value,
        reviewed_at: document.getElementById('reviewedAt').value,
        reviewer_declaration: document.getElementById('reviewerDeclaration').value,
        expert_final_json: expertFinalJson
      }};

      const submitBtn = document.getElementById('approveSubmitBtn');
      const statusInd = document.getElementById('saveStatusIndicator');
      submitBtn.disabled = true;
      submitBtn.innerText = 'Publishing...';
      if (statusInd) statusInd.innerText = 'Saving and compiling static site...';

      try {{
        const res = await fetch('/api/answers/' + encodeURIComponent(slug) + '/approve', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload)
        }});
        if (res.ok) {{
          alert('Approved successfully! Static site re-exported.');
          window.location.reload();
        }} else {{
          const err = await res.text();
          alert('Error approving draft: ' + err);
          submitBtn.disabled = false;
          submitBtn.innerText = 'Approve & Publish with Expert Byline';
          if (statusInd) statusInd.innerText = '';
        }}
      }} catch(err) {{
        alert('Network error: ' + err);
        submitBtn.disabled = false;
        submitBtn.innerText = 'Approve & Publish with Expert Byline';
        if (statusInd) statusInd.innerText = '';
      }}
    }}

    async function handleReject() {{
      const slug = document.getElementById('answerSlug').value;
      if (!slug) return;
      if (!confirm('Are you sure you want to REJECT this candidate draft?')) return;

      try {{
        const res = await fetch('/api/answers/' + encodeURIComponent(slug) + '/reject', {{
          method: 'POST'
        }});
        if (res.ok) {{
          alert('Draft rejected.');
          window.location.reload();
        }} else {{
          alert('Error rejecting draft.');
        }}
      }} catch(e) {{
        alert('Error: ' + e);
      }}
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      try {{
        if (localStorage.getItem('atlas_review_drawer_collapsed') === 'true') {{
          const drawer = document.getElementById('reviewDrawer');
          if (drawer) drawer.classList.add('collapsed');
          const icon = document.getElementById('drawerIcon');
          if (icon) icon.innerText = '☰';
        }}
      }} catch(e) {{}}
      renderInteractiveTable();
    }});
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# ==============================================================================
# 2. BEFORE / AFTER DIFFS AUDIT PORTAL (/admin/diffs)
# ==============================================================================
@app.get("/admin/diffs", response_class=HTMLResponse)
def admin_diffs_view():
    """Side-by-side audit view comparing Raw AI Draft vs Expert Final."""
    answers = get_answers_by_status("APPROVED")

    rows_html = ""
    for a in answers:
        raw_json = {}
        expert_json = {}
        try:
            raw_json = json.loads(a.get("ai_draft_json") or "{}")
        except Exception:
            pass
        try:
            expert_json = json.loads(a.get("expert_final_json") or "{}")
        except Exception:
            pass

        rows_html += f"""
        <div style="border: var(--atlas-border); margin-bottom: 32px; background: var(--atlas-paper);">
          <div style="background: var(--atlas-wash); padding: 12px 20px; border-bottom: var(--atlas-border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <span class="atlas-badge atlas-badge--indic">APPROVED</span>
              <strong style="font-size: 16px; margin-left: 8px;">{html.escape(a['title'])}</strong>
            </div>
            <div style="font-family: var(--atlas-font-mono); font-size: 12px; color: var(--atlas-muted);">
              Reviewed by <strong>{html.escape(a.get('reviewer_name') or 'Independent Expert')}</strong> ({html.escape(a.get('reviewer_role') or '')}) on {html.escape(a.get('reviewed_at') or '')}
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; border-bottom: var(--atlas-border);">
            <div style="padding: 16px; border-right: var(--atlas-border); background: #fdfefe;">
              <span class="atlas-label" style="color: var(--atlas-muted); font-weight: 700;">RAW AI DRAFT (GEMINI 2.5 FLASH)</span>
              <h4 style="margin: 8px 0 4px 0;">{html.escape(raw_json.get('question', ''))}</h4>
              <p style="font-size: 13px; line-height: 1.6; color: var(--atlas-muted);">{html.escape(raw_json.get('summary', ''))}</p>
              
              <div style="font-family: var(--atlas-font-mono); font-size: 11px; background: var(--atlas-wash); padding: 8px; border: 1px solid #ddd; max-height: 120px; overflow-y: auto;">
                <pre style="margin: 0;">{html.escape(json.dumps(raw_json.get('comparison_table', []), indent=2))}</pre>
              </div>
            </div>

            <div style="padding: 16px; background: #fafbfc;">
              <span class="atlas-label" style="color: var(--atlas-indic); font-weight: 700;">HUMAN EXPERT FINAL (VERIFIED)</span>
              <h4 style="margin: 8px 0 4px 0;">{html.escape(expert_json.get('question', a['title']))}</h4>
              <p style="font-size: 13px; line-height: 1.6; color: var(--atlas-ink);">{html.escape(expert_json.get('summary', ''))}</p>
              
              <div style="font-family: var(--atlas-font-mono); font-size: 11px; background: var(--atlas-wash); padding: 8px; border: 1px solid var(--atlas-rule); max-height: 120px; overflow-y: auto;">
                <pre style="margin: 0;">{html.escape(json.dumps(expert_json.get('comparison_table', []), indent=2))}</pre>
              </div>
            </div>
          </div>

          <div style="padding: 10px 20px; background: var(--atlas-paper); font-size: 12px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-family: var(--atlas-font-mono); color: var(--atlas-muted);">Independence Declaration: {html.escape(a.get('reviewer_declaration') or 'Verified independent domain expert.')}</span>
            <a href="/answers/{a['slug']}.html" target="_blank" style="font-weight: 600;">View Published Page ↗</a>
          </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-section="indic">
<head>
  <meta charset="UTF-8">
  <title>Before / After Diffs — AI Atlas India (Plate 05)</title>
  <link rel="stylesheet" href="/static/tokens.css">
  <style>
    body {{ margin: 0; font-family: var(--atlas-font-body); background: var(--atlas-paper); color: var(--atlas-ink); }}
    .container {{ max-width: 1200px; margin: 32px auto; padding: 0 24px; }}
    .atlas-badge {{ display: inline-block; padding: 2px 6px; font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; border: 1.5px solid var(--atlas-ink); }}
    .atlas-badge--indic {{ background: var(--atlas-indic); color: #fff; border-color: var(--atlas-indic); }}
  </style>
</head>
<body>
  {render_admin_nav(active_tab="diffs")}

  <div class="container">
    <div style="margin-bottom: 24px;">
      <span class="atlas-label" style="color: var(--atlas-indic); font-weight: 700;">AUDIT TRAIL</span>
      <h1 style="font-family: var(--atlas-font-display); font-size: 32px; margin: 4px 0 8px 0;">Raw AI Draft vs Expert Final Diffs</h1>
      <p style="color: var(--atlas-muted); max-width: 800px; margin: 0;">
        Full side-by-side verification proving that every published answer was inspected and refined by an independent domain expert.
      </p>
    </div>

    {rows_html if rows_html else '<p style="font-family: var(--atlas-font-mono); color: var(--atlas-muted);">No approved answers found to display diffs.</p>'}
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# ==============================================================================
# 3. ANALYTICS & A/B EXPERIMENT DASHBOARD (/analytics)
# ==============================================================================
@app.get("/analytics", response_class=HTMLResponse)
def analytics_dashboard():
    """Level 6 Traffic & Crawler Analytics and Level 7 A/B Experiment Monitor."""
    summary = get_analytics_summary()

    # Recommendations from database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM topic_recommendations ORDER BY id DESC")
    db_recs = [dict(r) for r in cur.fetchall()]
    conn.close()

    if not db_recs:
        recommend_next_topics()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM topic_recommendations ORDER BY id DESC")
        db_recs = [dict(r) for r in cur.fetchall()]
        conn.close()

    # Top queries table rows
    gsc_rows = ""
    for q in summary.get("top_queries", []):
        gsc_rows += f"""
        <tr>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); font-family: var(--atlas-font-mono); font-size: 13px;">{html.escape(q['query'])}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); text-align: right; font-weight: 600;">{q['clicks']}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); text-align: right;">{q['impressions']}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); text-align: right; font-family: var(--atlas-font-mono);">{q['position']:.1f}</td>
        </tr>
        """

    # Crawler rows
    bot_rows = ""
    for b in summary.get("ai_crawler_breakdown", []):
        bot_rows += f"""
        <tr>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); font-family: var(--atlas-font-mono);">{html.escape(b['bot_name'] or 'Unknown AI Bot')}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid var(--atlas-rule); text-align: right; font-weight: 700;">{b['hits']}</td>
        </tr>
        """

    # Topic recommendations rows
    topic_rows = ""
    for tr in db_recs:
        status_color = "var(--atlas-signal)" if tr["status"] == "PENDING_APPROVAL" else "var(--atlas-indic)"
        btn_action = f"""
        <button onclick="approveTopic({tr['id']})" style="background: var(--atlas-signal); border: 1.5px solid var(--atlas-ink); padding: 4px 10px; font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; cursor: pointer;">
          Approve Topic →
        </button>
        """ if tr["status"] == "PENDING_APPROVAL" else f"<span style='font-family: var(--atlas-font-mono); font-size: 11px; color: var(--atlas-indic); font-weight: 700;'>{tr['status']}</span>"

        topic_rows += f"""
        <div style="border: var(--atlas-border); padding: 16px; margin-bottom: 12px; background: var(--atlas-paper); display: flex; justify-content: space-between; align-items: center; gap: 16px;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
              <span style="font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; background: {status_color}; padding: 2px 6px;">{tr['status']}</span>
              <span style="font-family: var(--atlas-font-mono); font-size: 11px; color: var(--atlas-muted);">Est. Demand Score: {tr['estimated_demand']}</span>
            </div>
            <strong style="font-size: 15px;">{html.escape(tr['suggested_title'])}</strong>
            <p style="font-size: 13px; color: var(--atlas-muted); margin: 4px 0 0 0;">{html.escape(tr['rationale'])}</p>
          </div>
          <div>
            {btn_action}
          </div>
        </div>
        """

    ab = summary.get("ab_experiment", {})
    ab_verdict = ab.get("verdict", "Not enough data to call it")
    ab_sessions = ab.get("total_sessions", 0)

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-section="indic">
<head>
  <meta charset="UTF-8">
  <title>Analytics & A/B Experiment Dashboard — AI Atlas India (Plate 05)</title>
  <link rel="stylesheet" href="/static/tokens.css">
  <style>
    body {{ margin: 0; font-family: var(--atlas-font-body); background: var(--atlas-paper); color: var(--atlas-ink); }}
    .container {{ max-width: 1200px; margin: 32px auto; padding: 0 24px; }}
    .stat-card {{
      border: var(--atlas-border);
      background: var(--atlas-wash);
      padding: 20px;
    }}
    .stat-num {{
      font-family: var(--atlas-font-mono);
      font-size: 32px;
      font-weight: 700;
      color: var(--atlas-indic);
      margin: 4px 0;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      text-align: left;
      padding: 8px 12px;
      border-bottom: 2px solid var(--atlas-ink);
    }}
  </style>
</head>
<body>
  {render_admin_nav(active_tab="analytics")}

  <div class="container">
    <div style="margin-bottom: 24px;">
      <span class="atlas-label" style="color: var(--atlas-indic); font-weight: 700;">LEVEL 6 & 7 MEASUREMENT</span>
      <h1 style="font-family: var(--atlas-font-display); font-size: 32px; margin: 4px 0 8px 0;">Traffic, AI Crawlers & A/B Experiments</h1>
      <p style="color: var(--atlas-muted); max-width: 800px; margin: 0;">
        Real-time telemetry tracking AI search engines, verified human visitors, Google Search Console query impressions, and presentation experiment validity.
      </p>
    </div>

    <!-- Stat KPI Cards -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px;">
      <div class="stat-card">
        <div class="atlas-label">TOTAL SERVER HITS</div>
        <div class="stat-num">{summary.get('total_requests', 0)}</div>
        <div style="font-size: 12px; color: var(--atlas-muted);">Web and API requests</div>
      </div>
      <div class="stat-card">
        <div class="atlas-label">AI CRAWLER HITS</div>
        <div class="stat-num" style="color: var(--atlas-route);">{summary.get('ai_crawler_hits', 0)}</div>
        <div style="font-size: 12px; color: var(--atlas-muted);">GPTBot, ClaudeBot, PerplexityBot</div>
      </div>
      <div class="stat-card">
        <div class="atlas-label">AI REFERRALS</div>
        <div class="stat-num">{summary.get('ai_referrals_count', 0)}</div>
        <div style="font-size: 12px; color: var(--atlas-muted);">ChatGPT & Perplexity citations</div>
      </div>
      <div class="stat-card">
        <div class="atlas-label">GSC QUERIES TRACKED</div>
        <div class="stat-num">{summary.get('gsc_queries_tracked', 0)}</div>
        <div style="font-size: 12px; color: var(--atlas-muted);">{summary.get('gsc_impressions', 0)} organic impressions</div>
      </div>
    </div>

    <!-- Bonus Level 7 A/B Experiment Status Card -->
    <div style="border: 1.5px solid var(--atlas-indic); background: var(--atlas-sea); padding: 24px; margin-bottom: 32px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span class="atlas-label" style="font-weight: 700; color: var(--atlas-indic);">BONUS LEVEL 7: PRESENTATION A/B EXPERIMENT</span>
        <span style="font-family: var(--atlas-font-mono); font-size: 11px; background: var(--atlas-paper); border: 1px solid var(--atlas-ink); padding: 2px 8px; font-weight: 700;">
          POSTHOG EXPERIMENT
        </span>
      </div>
      <h3 style="font-family: var(--atlas-font-display); font-size: 20px; margin: 0 0 8px 0;">
        Section Ordering: Code First vs Table First (Control)
      </h3>
      <p style="font-size: 14px; line-height: 1.6; margin: 0 0 16px 0;">
        <strong>Statistical Status:</strong> <span style="font-family: var(--atlas-font-mono); font-weight: 700; color: var(--atlas-route);">{ab_verdict}</span> (Total sessions: {ab_sessions} / Minimum 100 required).
      </p>
      <div style="background: var(--atlas-paper); padding: 12px; border: var(--atlas-border); font-size: 13px;">
        <strong>Disqualification Prevention Rule:</strong> We honestly report <em>"Not enough data to call it"</em> until statistical significance is achieved. Both variants present identical facts with <code>rel="canonical"</code> to avoid cloaking or dual content penalties.
      </div>
    </div>

    <!-- Data Tables Grid -->
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px;">
      <!-- AI Bots Table -->
      <div style="border: var(--atlas-border); padding: 20px; background: var(--atlas-paper);">
        <h3 style="font-family: var(--atlas-font-display); font-size: 18px; margin: 0 0 12px 0;">AI Crawler Activity</h3>
        <table>
          <thead>
            <tr>
              <th>Crawler Name</th>
              <th style="text-align: right;">Hits</th>
            </tr>
          </thead>
          <tbody>
            {bot_rows if bot_rows else '<tr><td colspan="2" style="padding: 12px; text-align: center; color: #888;">No crawler hits logged yet.</td></tr>'}
          </tbody>
        </table>
      </div>

      <!-- Top Search Console Queries -->
      <div style="border: var(--atlas-border); padding: 20px; background: var(--atlas-paper);">
        <h3 style="font-family: var(--atlas-font-display); font-size: 18px; margin: 0 0 12px 0;">Top Search Console Queries</h3>
        <table>
          <thead>
            <tr>
              <th>Query</th>
              <th style="text-align: right;">Clicks</th>
              <th style="text-align: right;">Impressions</th>
              <th style="text-align: right;">Avg Pos</th>
            </tr>
          </thead>
          <tbody>
            {gsc_rows if gsc_rows else '<tr><td colspan="4" style="padding: 12px; text-align: center; color: #888;">No GSC data imported yet.</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>

    <!-- Level 6 AI Next-Topic Recommender -->
    <div style="border: var(--atlas-border); padding: 24px; background: var(--atlas-wash);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <div>
          <span class="atlas-label" style="color: var(--atlas-indic); font-weight: 700;">LEVEL 6 AI RECOMMENDATIONS</span>
          <h2 style="font-family: var(--atlas-font-display); font-size: 24px; margin: 4px 0 0 0;">
            Next High-Impact Questions to Cover
          </h2>
        </div>
      </div>
      <p style="font-size: 14px; color: var(--atlas-muted); margin: 0 0 20px 0;">
        Gemini analyzes traffic patterns and generative engine searches to suggest the next topics to write. Review the rationale and click "Approve Topic" to queue it directly into questions for automated drafting.
      </p>

      {topic_rows}
    </div>
  </div>

  <script>
    async function approveTopic(topicId) {{
      try {{
        const res = await fetch('/admin/topics/' + topicId + '/approve', {{ method: 'POST' }});
        if (res.ok) {{
          alert('Topic approved and queued into questions table!');
          window.location.reload();
        }} else {{
          alert('Error approving topic.');
        }}
      }} catch(e) {{
        alert('Network error: ' + e);
      }}
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


@app.post("/admin/topics/{topic_id}/approve")
def api_approve_topic(topic_id: int):
    """Approve AI suggested topic into questions table."""
    success = approve_topic_recommendation(topic_id)
    if not success:
        raise HTTPException(status_code=404, detail="Topic ID not found")
    return {"status": "SUCCESS", "topic_id": topic_id}


# ==============================================================================
# 4. SOCIAL AUTOMATION & REPLY QUEUE (/admin/social)
# ==============================================================================
@app.get("/admin/social", response_class=HTMLResponse)
def admin_social_view():
    """Human-in-the-Loop review queue for Bluesky replies and scheduled posts."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM social_replies ORDER BY id DESC")
    replies = [dict(r) for r in cur.fetchall()]
    conn.close()

    posts = get_all_social_posts()

    # Replies queue
    replies_html = ""
    for rep in replies:
        status_color = "var(--atlas-signal)" if rep["status"] == "PENDING_APPROVAL" else "var(--atlas-indic)"
        is_pending = (rep["status"] == "PENDING_APPROVAL")
        rep_id = rep["id"]

        actions = f"""
        <div style="margin-top: 12px; display: flex; gap: 10px;">
          <button onclick="approveReply({rep_id})" style="background: var(--atlas-signal); border: 1.5px solid var(--atlas-ink); padding: 6px 14px; font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; cursor: pointer;">
            Approve & Send to Bluesky
          </button>
          <button onclick="rejectReply({rep_id})" style="background: var(--atlas-paper); border: 1.5px solid var(--atlas-route); color: var(--atlas-route); padding: 6px 14px; font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; cursor: pointer;">
            Reject Reply
          </button>
        </div>
        """ if is_pending else f"<div style='font-family: var(--atlas-font-mono); font-size: 12px; color: var(--atlas-muted); margin-top: 8px;'>Status: <strong>{rep['status']}</strong> (Signed by: {html.escape(rep.get('reviewer_name') or 'N/A')})</div>"

        replies_html += f"""
        <div style="border: var(--atlas-border); padding: 16px; margin-bottom: 16px; background: var(--atlas-paper);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700; background: {status_color}; padding: 2px 6px;">
              {rep['status']}
            </span>
            <span style="font-family: var(--atlas-font-mono); font-size: 11px; color: var(--atlas-muted);">
              Author DID: {mask_sensitive(rep['author_did'])}
            </span>
          </div>
          <div style="margin-bottom: 10px;">
            <span class="atlas-label">INCOMING USER INQUIRY:</span>
            <p style="font-size: 14px; font-weight: 600; margin: 4px 0;">"{html.escape(rep['post_text'])}"</p>
          </div>
          <div>
            <span class="atlas-label" style="color: var(--atlas-indic);">AI SUGGESTED REPLY DRAFT:</span>
            <textarea id="replyText_{rep_id}" style="width: 100%; padding: 8px; border: var(--atlas-border); font-family: var(--atlas-font-body); font-size: 13px; margin-top: 4px;" rows="3" {'readonly' if not is_pending else ''}>{html.escape(rep['ai_draft_reply'])}</textarea>
          </div>
          {actions}
        </div>
        """

    # Posts queue
    posts_html = ""
    for p in posts[:8]:
        posts_html += f"""
        <div style="border: var(--atlas-border); padding: 12px; margin-bottom: 8px; background: var(--atlas-wash); font-size: 13px;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span style="font-family: var(--atlas-font-mono); font-size: 11px; font-weight: 700;">{p['status']}</span>
            <span style="font-family: var(--atlas-font-mono); font-size: 11px; color: var(--atlas-muted);">{p.get('scheduled_at') or p.get('created_at')}</span>
          </div>
          <p style="margin: 4px 0; font-family: var(--atlas-font-mono); font-size: 11px; white-space: pre-wrap;">{html.escape(p['content'][:140])}...</p>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en" data-section="indic">
<head>
  <meta charset="UTF-8">
  <title>Social Automation & Reply Queue — AI Atlas India (Plate 05)</title>
  <link rel="stylesheet" href="/static/tokens.css">
  <style>
    body {{ margin: 0; font-family: var(--atlas-font-body); background: var(--atlas-paper); color: var(--atlas-ink); }}
    .container {{ max-width: 1200px; margin: 32px auto; padding: 0 24px; }}
  </style>
</head>
<body>
  {render_admin_nav(active_tab="social")}

  <div class="container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
      <div>
        <span class="atlas-label" style="color: var(--atlas-indic); font-weight: 700;">LEVEL 5 SOCIAL AUTOMATION</span>
        <h1 style="font-family: var(--atlas-font-display); font-size: 32px; margin: 4px 0 8px 0;">Bluesky Distribution & Human-Approved Reply Queue</h1>
        <p style="color: var(--atlas-muted); max-width: 800px; margin: 0;">
          Distributing verified answers to <code>@{BLUESKY_HANDLE}</code>. Replies require explicit human approval before sending.
        </p>
      </div>
      <div>
        <button onclick="purgeCommenters()" style="background: var(--atlas-paper); border: 1.5px solid var(--atlas-route); color: var(--atlas-route); padding: 8px 16px; font-family: var(--atlas-font-mono); font-size: 12px; font-weight: 700; cursor: pointer;">
          Purge All Commenter Records (Privacy Rule)
        </button>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 24px;">
      <!-- Mentions and Human Gate Queue -->
      <div>
        <h3 style="font-family: var(--atlas-font-display); font-size: 20px; margin-bottom: 12px;">
          Human-in-the-Loop Reply Queue ({len(replies)})
        </h3>
        {replies_html if replies_html else '<p style="color: var(--atlas-muted); font-family: var(--atlas-font-mono);">No replies in queue. Run python engine/5_social.py --fetch-mentions to simulate or poll mentions.</p>'}
      </div>

      <!-- Outbound Posts Stream -->
      <div>
        <h3 style="font-family: var(--atlas-font-display); font-size: 20px; margin-bottom: 12px;">
          Scheduled & Published Posts
        </h3>
        {posts_html}
      </div>
    </div>
  </div>

  <script>
    async function approveReply(id) {{
      const text = document.getElementById('replyText_' + id).value;
      const reviewer = prompt('Enter your name to sign off on this reply:', 'Moksh Desai');
      if (!reviewer) return;

      try {{
        const res = await fetch('/admin/social/' + id + '/approve', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ reviewer_name: reviewer, edited_text: text }})
        }});
        if (res.ok) {{
          alert('Reply approved and sent!');
          window.location.reload();
        }} else {{
          alert('Error approving reply.');
        }}
      }} catch(e) {{
        alert('Network error: ' + e);
      }}
    }}

    async function rejectReply(id) {{
      if (!confirm('Reject this reply suggestion?')) return;
      try {{
        const res = await fetch('/admin/social/' + id + '/reject', {{ method: 'POST' }});
        if (res.ok) {{
          window.location.reload();
        }}
      }} catch(e) {{
        alert('Error: ' + e);
      }}
    }}

    async function purgeCommenters() {{
      if (!confirm('DISQUALIFICATION GUARDRAIL: Are you sure you want to permanently wipe all commenter and reply records from the database?')) return;
      try {{
        const res = await fetch('/admin/social/purge', {{ method: 'POST' }});
        const data = await res.json();
        alert('Successfully purged ' + data.purged + ' commenter records. Privacy preserved.');
        window.location.reload();
      }} catch(e) {{
        alert('Error purging records: ' + e);
      }}
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


class SocialApprovePayload(BaseModel):
    reviewer_name: str
    edited_text: Optional[str] = None


@app.post("/admin/social/{reply_id}/approve")
def api_approve_social_reply(reply_id: int, payload: SocialApprovePayload):
    """Human approval gate for sending a reply."""
    success = approve_and_send_reply(reply_id, payload.reviewer_name, payload.edited_text)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve reply")
    return {"status": "SENT", "reply_id": reply_id}


@app.post("/admin/social/{reply_id}/reject")
def api_reject_social_reply(reply_id: int):
    """Mark a reply as rejected."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE social_replies SET status = 'REJECTED' WHERE id = ?", (reply_id,))
    conn.commit()
    conn.close()
    return {"status": "REJECTED", "reply_id": reply_id}


@app.post("/admin/social/purge")
def api_purge_social_commenters():
    """Wipe all commenter records to protect user data."""
    count = purge_all_commenters()
    return {"status": "PURGED", "purged": count}


# ==============================================================================
# REST API ENDPOINTS
# ==============================================================================
@app.get("/api/answers")
def list_answers(status: Optional[str] = None):
    return get_answers_by_status(status)


@app.get("/api/answers/{slug}")
def get_answer(slug: str):
    ans = get_answer_by_slug(slug)
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found")
    return ans


@app.post("/api/answers/{slug}/approve")
def api_approve_answer(slug: str, req: ApproveRequest):
    """
    Save expert edits, update status to APPROVED, and re-export static frontend.
    Strictly checks that the reviewer is NOT Candidate Anshu Raj (Self-Review Guardrail).
    """
    if req.reviewer_name.strip().lower() == CANDIDATE_NAME.lower():
        raise HTTPException(
            status_code=400,
            detail=f"Disqualification guardrail: Candidate author {CANDIDATE_NAME} cannot review their own section. Independent domain expert required."
        )

    success = approve_answer(
        slug=slug,
        expert_final_json=req.expert_final_json,
        reviewer_name=req.reviewer_name,
        reviewer_role=req.reviewer_role,
        reviewer_org=req.reviewer_org,
        reviewed_at=req.reviewed_at,
        reviewer_declaration=req.reviewer_declaration
    )
    if not success:
        raise HTTPException(status_code=404, detail="Answer slug not found or update failed")

    export_stats = run_export()
    return {"status": "APPROVED", "slug": slug, "export_stats": export_stats}


@app.post("/api/answers/{slug}/reject")
def api_reject_answer(slug: str):
    success = reject_answer(slug)
    if not success:
        raise HTTPException(status_code=404, detail="Answer not found")
    return {"status": "REJECTED", "slug": slug}


@app.get("/api/questions")
def list_questions(limit: int = 100):
    return get_all_questions(limit)


@app.get("/api/providers")
def list_providers():
    return get_all_providers()


@app.post("/api/export")
def trigger_export():
    stats = run_export()
    return {"status": "SUCCESS", "stats": stats}


# ==============================================================================
# CLI DISPATCHER
# ==============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Atlas India Indic Pipeline Server & Exporter")
    parser.add_argument("--export", action="store_true", help="Compile static site to frontend/ and exit")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="FastAPI host")
    parser.add_argument("--port", type=int, default=8000, help="FastAPI port")
    args = parser.parse_args()

    init_db()

    if args.export:
        print("[CLI] Running static site export...")
        run_export()
        print("[CLI] Export complete.")
    else:
        import uvicorn
        print(f"[Server] Starting FastAPI server on http://{args.host}:{args.port}/review")
        uvicorn.run("engine.main:app", host=args.host, port=args.port, reload=False)
