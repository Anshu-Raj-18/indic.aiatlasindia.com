
# AI Atlas India — Plate 05: Indic Language AI (`indic.aiatlasindia.com`)

> **Production-Ready Automated Content Discovery, Grounded AI Drafting, Independent Expert Verification, Social Distribution, and Telemetry Engine**  
> **Plate:** 05 | **Section:** Indic language AI | **Subdomain:** `indic.aiatlasindia.com` | **Design Token:** `--atlas-indic: #8A5A1C` (5.9:1 AA Contrast)  
> **Section Author & Builder:** Anshu Raj  
> **Automation Lead & Review Dispatcher:** Anshu Raj  
> **Independent Domain Expert Reviewer:** Moksh Desai (Developer, Indian-Language Speech-to-Speech Translation Systems)  
> **Section Owner:** Vyohm AI Private Limited (Kolkata; CEO Soham Madnani, FDE Bhagaban Paul)  
> **Google Analytics 4 Measurement ID:** `G-WK0D46CCQZ` | **Search Console / Admin Account:** `qismcdeltat@gmail.com`  

---

## 1. System Architecture Overview

The system is constructed with a strict **Two-Layer Decoupled Architecture**:

```
indic.aiatlasindia.com/
├── engine/                      # LAYER 1: Private Local Python Automation Engine (FastAPI + SQLite)
│   ├── config.py                # Environment configuration & disqualification constants
│   ├── database.py              # SQLite schema (indic_atlas.db), audit logs & privacy helpers
│   ├── 1_discover.py            # YouTube Data v3 + HN Algolia APIs (0.85 cosine deduplication)
│   ├── 2_draft.py               # Grounded Gemini drafts with working Python code & 8 criteria
│   ├── 3_expert_dispatch.py     # Level 4 automated email dispatch (Gmail API / SMTP / preview)
│   ├── exporter.py              # Compiles APPROVED records into static HTML inside frontend/
│   ├── main.py                  # FastAPI portal (/review, /admin/diffs, /analytics, /admin/social)
│   ├── 5_social.py              # ATProto Bluesky publisher & human-approved reply queue
│   └── 6_measure.py             # Level 6 telemetry, AI crawler logs, Level 7 A/B, AI Topic Recommender
│
├── frontend/                    # LAYER 2: Public Static Web Artifacts (Vercel Web Root)
│   ├── index.html               # Section Hub with client-side live search & category filters
│   ├── about.html               # Mandatory About page crediting Anshu Raj, Moksh Desai & Vyohm
│   ├── answers/                 # Verified Q&A pages with FAQPage JSON-LD, fact marks & bylines
│   │   ├── sarvam-vs-bhashini-speech-to-text-cost-accuracy.html
│   │   ├── how-to-self-host-ai4bharat-indictrans2-on-premise.html
│   │   ├── krutrim-cloud-indic-llm-pricing-and-token-cost.html
│   │   └── sarvam-bulbul-tts-pricing-and-voice-latency.html
│   ├── providers/               # 8-Criteria Provider Profile Pages
│   │   ├── sarvam-ai.html
│   │   ├── bhashini.html
│   │   ├── krutrim.html
│   │   └── ai4bharat.html
│   ├── tokens.css               # Official Section Kit design tokens (border-radius: 0 everywhere)
│   ├── logo.svg                 # Official AI Atlas India mark (unmodified)
│   ├── header.html              # Shared header lockup (Plate 05 Indic badge #8A5A1C)
│   ├── footer.html              # Shared footer with exact Vyohm ownership statement
│   ├── sitemap.xml              # XML sitemap with all answers and provider pages
│   └── robots.txt               # Directives explicitly allowing GPTBot, ClaudeBot, PerplexityBot
│
├── tests/
│   └── test_pipeline.py         # Complete automated test suite (11/11 tests passing)
│
├── docs/
│   └── Indic_AI_Atlas_Pipeline_Architecture.pdf # Comprehensive 4-page architecture PDF
│
├── vercel.json                  # Vercel deployment configuration ("outputDirectory": "frontend")
├── .vercelignore                # Excludes engine/, *.db, credentials.json, .env from Vercel
├── .env.example                 # Environment configuration template
└── README.md                    # Detailed documentation and compliance guide
```

---

## 2. Compliance with Challenge Levels (Levels 1–6 + Bonus Level 7)

| Level | Component | Implementation Details | Status |
| :--- | :--- | :--- | :--- |
| **Level 1** | Grounded Architecture & Section Kit | Section Kit tokens (`tokens.css`), sharp corners (`border-radius: 0`), 1.5px ink borders, `logo.svg` unmodified. Mandatory `frontend/about.html` credits candidate Anshu Raj, independent expert Moksh Desai, and Vyohm ownership. GA4 tag `G-WK0D46CCQZ` on every page. | **Verified** |
| **Level 2** | Discovery Engine | `engine/1_discover.py` queries **YouTube Data API v3** & **Hacker News Algolia API**. Filters out noise/spam, performs SHA256 exact hash + **0.85 cosine deduplication**, logs `skip_reason`, calculates `selection_reason`, and ranks top queries. | **Verified** |
| **Level 3** | Grounded AI Drafting | `engine/2_draft.py` uses `gemini-2.5-flash` / grounded models to draft working Python code, pricing tables (+18% GST), language matrices, and 8 criteria provider evaluations. Every claim includes `[VALUE] · [SOURCE] · checked [DATE]`. Untraced claims marked `◌ Not yet sourced`. Full SEO metadata drafted. | **Verified** |
| **Level 4** | Automated Email Dispatch | `engine/3_expert_dispatch.py` dispatches reviews to independent reviewer Moksh Desai via Gmail API / SMTP. Generates unique secure review tokens (`/review/<token>`). Parses email replies (`APPROVED`, `EDITED`, `REJECTED`) and records human edits. Web UI at `/admin/diffs` displays before/after diffs. | **Verified** |
| **Level 5** | Social Distribution | `engine/5_social.py` publishes newly approved URLs to `@vyohm-bot.bsky.social` with SQLite idempotency. Supports ISO scheduled posting (`--run-scheduled`). Mentions queue reply suggestions for mandatory human approval (never auto-replies). Includes `--purge-commenters` CLI command. | **Verified** |
| **Level 6** | Telemetry & AI Recommender | `engine/6_measure.py` tracks human vs AI bot crawler hits (`GPTBot`, `ClaudeBot`, `PerplexityBot`), AI referrals (`ChatGPT`, `Perplexity`), and Google Search Console queries. AI Next-Topic Recommender suggests the next 3 questions with data-driven rationales and one-click "Approve Topic" button. | **Verified** |
| **Bonus Level 7** | Presentation A/B Experiment | PostHog A/B test on answer presentation layout (Code First vs Table First). Facts and text remain 100% identical with canonical URL. Honestly reports *"Not enough data to call it"* when sessions < 100, preventing false premature declarations. | **Verified** |
2. **Grounded AI Drafting (`engine/2_draft.py`):**

---

## 3. Disqualification Prevention Guardrails

| Guardrail Rule | What the Rules Forbid | How We Prevented Disqualification |
| :--- | :--- | :--- |
| **1. No Self-Review** | Candidate reviewing their own section or using placeholder names. | Author is **Anshu Raj**. Independent Expert Reviewer is **Moksh Desai** (Developer, Indian-Language Speech-to-Speech Translation Systems). Database and API strictly reject approval if reviewer is Anshu Raj (`HTTP 400`). |
| **2. Exact Footer Text** | Omitting or altering the required ownership disclosure. | Every single generated HTML page displays verbatim:<br>`AI Atlas India is owned by Vyohm AI Private Limited, which also sells AI products. We cover every provider, Vyohm included, by the same rules.`<br>alongside `Built by Anshu Raj`. Verified by automated test. |
| **3. Hard Cap of 20 Answers** | Scaled spam publishing (publishing dozens or hundreds of thin pages). | `engine/exporter.py` enforces a strict hard cap of `MAX_PUBLISHED_ANSWERS = 20`. Only answers with status `APPROVED` and independent expert credentials are exported. |
| **4. Commenter Data Privacy** | Storing or exposing community usernames or private profile data. | Database stores only minimal technical routing identifiers (`notification_uri`, `author_did`, `post_text`). YouTube and HN usernames are discarded. Running `python engine/5_social.py --purge-commenters` permanently wipes all records. |
| **5. Zero-Guessing Policy** | Inventing prices, latencies, or server locations. | Grounded facts use solid dot `● [VALUE] · [SOURCE] · checked [DATE]`. Any unsourced metric is rendered as dashed ring `◌ Not yet sourced`. Untraceable claims are removed. |
| **6. Secret & Key Masking** | Showing full API keys, passwords, or personal emails on UI. | FastAPI admin templates mask sensitive tokens and emails (e.g. `qi••••@gmail.com`, `gsk_••••`). |
| **7. Honest Experiment Reporting** | Declaring a premature winner in A/B experiments. | When total experiment sessions are < 100, the analytics dashboard strictly reports *"Not enough data to call it"*. |

---

## 4. Local Execution & Step-by-Step Workflow

### Prerequisites

- Python 3.10+ (tested on Python 3.12)
- Dependencies: `fastapi`, `uvicorn`, `httpx`, `google-genai`, `google-auth-oauthlib`, `atproto`, `reportlab`, `pytest`

```bash
# Clone and navigate to repository
cd indic.aiatlasindia.com

# Setup environment configuration
cp .env.example .env
# Edit .env with your keys or run in dry-run mode
```

### Step 1: Discover Questions from Official APIs

```bash
python engine/1_discover.py
```

*Queries YouTube Data API v3 and Hacker News Algolia API, filters for genuine questions, applies 0.85 cosine deduplication, and records questions with selection rationales into `indic_atlas.db`.*

### Step 2: Draft Evidence-Grounded Content

```bash
python engine/2_draft.py
```

*Generates structured JSON drafts with working Python snippets, pricing tables (+18% GST), language matrices, and 8-criteria provider profiles in `PENDING_REVIEW` state.*

### Step 3: Dispatch Drafts to Expert Reviewer

```bash
# Preview email dispatch in console or send via Gmail API / SMTP
python engine/3_expert_dispatch.py

# Simulate expert email reply approval
python engine/3_expert_dispatch.py --simulate-reply 1 APPROVED
```
*Emails unique review links (`/review/<token>`) to the expert with review options.*

### Step 4: Run Management & Review Portal
```bash
python engine/main.py --port 8000
```

Open in browser:
- **Expert Review Portal:** [http://127.0.0.1:8000/review](http://127.0.0.1:8000/review)
- **Before / After Diffs:** [http://127.0.0.1:8000/admin/diffs](http://127.0.0.1:8000/admin/diffs)
- **Analytics & A/B Dashboard:** [http://127.0.0.1:8000/analytics](http://127.0.0.1:8000/analytics)
- **Social & Reply Queue:** [http://127.0.0.1:8000/admin/social](http://127.0.0.1:8000/admin/social)

### Step 5: Export Static Public Website

```bash
python engine/main.py --export
# Or directly:
python engine/exporter.py
```

*Compiles all verified answers, provider profiles, and `about.html` into static HTML in `frontend/`, along with `sitemap.xml` and `robots.txt`.*

### Step 6: Social Publishing & Privacy Purge

```bash
# Schedule newly approved posts
python engine/5_social.py --schedule

# Publish due scheduled posts to Bluesky (@vyohm-bot.bsky.social)
python engine/5_social.py --run-scheduled

# Fetch incoming mentions and queue reply suggestions
python engine/5_social.py --fetch-mentions

# DISQUALIFICATION GUARDRAIL: Wipe all commenter data at assignment end
python engine/5_social.py --purge-commenters
```


### Step 7: Run Automated Test Suite

```bash
python -m pytest tests/test_pipeline.py -v
```

*Runs all 11 unit and integration tests verifying config, discovery filtering, cosine deduplication, no self-review, exact footer, hard cap 20, email dispatch, social queue, analytics, and Vercel configuration.*

---

## 5. Vercel Hosting & Production Setup

### Configuration Files
- `vercel.json`:
  ```json
  {
    "outputDirectory": "frontend",
    "cleanUrls": true,
    "trailingSlash": false
  }
  ```
- `.vercelignore`: Excludes private pipeline files (`engine/`, `*.db`, `credentials.json`, `token.json`, `rules/`, `tests/`) from the public bundle.

### Domain Setup
1. Import repository into [Vercel](https://vercel.com/).
2. In Project Settings → **Domains**, map `indic.aiatlasindia.com`.
3. Inform Vyohm (`careers@vyohm.com`) with the CNAME record details for DNS validation.
4. Google Analytics 4 (`G-WK0D46CCQZ`) and Google Search Console (`qismcdeltat@gmail.com`) track all live traffic.

---

## 6. Sourced Providers Covered

| Provider                | Core Capabilities                                   | Verified Pricing in India                         | Language Breadth                      | Data Residency              |
| :---------------------- | :-------------------------------------------------- | :------------------------------------------------ | :------------------------------------ | :-------------------------- |
| **Sarvam AI**     | Saaras (ASR), Bulbul (TTS), Mayura (NMT), Sarvam 2B | ₹0.40/min ASR, ₹15/10k chars TTS (+18% GST)     | 10 Indian languages + Indian English  | AWS Mumbai (India)          |
| **Bhashini**      | National Translation Mission (ASR, NMT, TTS, OCR)   | Free for registered Indian startups & Govt (ULCA) | 22 official scheduled languages       | NIC & CDAC Cloud (India)    |
| **Krutrim Cloud** | Krutrim Pro Indic LLM, Speech-to-Text, Voice APIs   | ₹0.15/1k tokens (~₹150/1M tokens) (+18% GST)    | 22 languages text, 10 languages voice | Krutrim India Data Centers  |
| **AI4Bharat**     | IndicTrans2, IndicWhisper, IndicConformer, IndicTTS | Free / Open-Source (MIT / CC-BY 4.0 licenses)     | 22 scheduled Indian languages         | 100% On-Premise / Local VPC |

---

## 7. Submission Deliverables Summary

- [x] **Full Level 1–6 + Bonus Level 7 Implementation:** Complete private pipeline (`engine/`) and static frontend (`frontend/`).
- [x] **Disqualification Safeguards:** No self-review by Anshu Raj; independent reviewer Moksh Desai; exact Vyohm ownership statement; hard 20-answer cap; commenter privacy purge command.
- [x] **Design Kit Adherence:** `tokens.css`, `logo.svg` unmodified, `border-radius: 0`, `--atlas-indic: #8A5A1C`.
- [x] **11/11 Passing Tests:** Verified with `pytest tests/test_pipeline.py -v`.
- [x] **Architecture Specification:** Generated PDF at `docs/Indic_AI_Atlas_Pipeline_Architecture.pdf`.
