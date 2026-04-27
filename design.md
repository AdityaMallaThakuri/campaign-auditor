# Smartlead Audit Tool — System Design

## Stack
- Frontend: Next.js 15, React 19, Tailwind CSS, shadcn/ui, Recharts
- Backend: FastAPI (Python 3.11+), SQLModel (SQLite)
- AI: Anthropic SDK (claude-sonnet-4-5), called on-demand only
- Dev: Docker Compose (one command startup)

## Core Philosophy
- Diagnostic tool, not a dashboard — every feature answers "why is this broken"
- Cache Smartlead data locally (30 min TTL) — never hammer the API
- Claude calls are opt-in only — user must explicitly request diagnosis/rewrite
- SQLite now, Postgres-ready later (SQLModel abstracts the difference)

## Database Schema
## Database Schema

### Table: campaigns
| Column         | Type      | Notes                        |
|----------------|-----------|------------------------------|
| id             | INTEGER   | PK, autoincrement            |
| smartlead_id   | TEXT      | Unique ID from Smartlead     |
| name           | TEXT      | Campaign name                |
| status         | TEXT      | active / paused / completed  |
| total_leads    | INTEGER   | Total leads in campaign      |
| fetched_at     | DATETIME  | Last time data was pulled    |
| created_at     | DATETIME  | Row creation timestamp       |

### Table: audit_snapshots
| Column            | Type      | Notes                                      |
|-------------------|-----------|--------------------------------------------|
| id                | INTEGER   | PK, autoincrement                          |
| campaign_id       | INTEGER   | FK → campaigns.id                          |
| open_rate         | FLOAT     | % of emails opened                         |
| reply_rate        | FLOAT     | % of emails replied to                     |
| bounce_rate       | FLOAT     | % of emails bounced                        |
| health_score      | INTEGER   | Composite score 0–100                      |
| root_cause        | TEXT      | deliverability / subject / copy / targeting|
| root_cause_detail | TEXT      | Human-readable explanation                 |
| step_dropoff      | JSON      | Per-step open+reply rates array            |
| subject_patterns  | JSON      | Subject line style analysis                |
| audited_at        | DATETIME  | When this snapshot was taken               |

### Table: reply_clusters
| Column        | Type     | Notes                                             |
|---------------|----------|---------------------------------------------------|
| id            | INTEGER  | PK, autoincrement                                 |
| campaign_id   | INTEGER  | FK → campaigns.id                                 |
| category      | TEXT     | interested / price_objection / timing / wrong_person / not_relevant / competitor |
| count         | INTEGER  | Number of replies in this category                |
| percentage    | FLOAT    | % of total replies                                |
| sample_replies| JSON     | Array of 3–5 example reply texts                  |
| themes        | JSON     | Key phrases extracted from this cluster           |
| clustered_at  | DATETIME | When clustering was last run                      |

### Table: sequence_steps
| Column       | Type     | Notes                              |
|--------------|----------|------------------------------------|
| id           | INTEGER  | PK, autoincrement                  |
| campaign_id  | INTEGER  | FK → campaigns.id                  |
| step_number  | INTEGER  | 1-indexed position in sequence     |
| subject      | TEXT     | Email subject line                 |
| body         | TEXT     | Full email body                    |
| open_rate    | FLOAT    | Open rate for this specific step   |
| reply_rate   | FLOAT    | Reply rate for this specific step  |
| word_count   | INTEGER  | Word count of body                 |
| cta_detected | TEXT     | Detected call-to-action text       |

### Table: ai_rewrites
| Column         | Type     | Notes                                  |
|----------------|----------|----------------------------------------|
| id             | INTEGER  | PK, autoincrement                      |
| step_id        | INTEGER  | FK → sequence_steps.id                 |
| campaign_id    | INTEGER  | FK → campaigns.id                      |
| diagnosis      | TEXT     | Claude's diagnosis of why it's failing |
| original_copy  | TEXT     | Copy that was sent for rewriting       |
| rewritten_copy | TEXT     | Claude's rewritten version             |
| suggestions    | JSON     | Array of specific improvement notes    |
| model_used     | TEXT     | e.g. claude-sonnet-4-5                 |
| generated_at   | DATETIME | When this rewrite was generated        |

### Relationships
- campaigns → audit_snapshots   (one to many)
- campaigns → reply_clusters    (one to many)
- campaigns → sequence_steps    (one to many)
- sequence_steps → ai_rewrites  (one to many)

## API Endpoints
## API Endpoints

Base URL: http://localhost:8000

---

### Campaigns

#### GET /campaigns
List all campaigns with their latest health score.

Response:
{
  "campaigns": [
    {
      "id": 1,
      "smartlead_id": "abc123",
      "name": "Q1 SaaS Outreach",
      "status": "active",
      "health_score": 62,
      "root_cause": "copy",
      "audited_at": "2025-04-27T10:00:00Z"
    }
  ]
}

---

#### GET /campaigns/{id}
Full detail for a single campaign including sequences and reply clusters.

Response:
{
  "campaign": { ...campaign fields... },
  "latest_audit": { ...audit_snapshot fields... },
  "sequences": [ ...sequence_steps array... ],
  "reply_clusters": [ ...reply_clusters array... ]
}

---

#### POST /campaigns/sync
Force re-fetch all campaign data from Smartlead, bypassing the cache.

Response:
{
  "synced": 8,
  "duration_ms": 1240
}

---

### Audit

#### POST /audit/run
Run a full audit. Pass campaign_ids to audit specific ones, or omit to audit all.

Request body:
{
  "campaign_ids": [1, 2, 3]   // optional — omit for all
}

Response:
{
  "audit_id": "audit_20250427_001",
  "campaigns_audited": 3,
  "flags": [
    {
      "campaign_id": 2,
      "name": "Cold Outreach April",
      "root_cause": "subject",
      "health_score": 34
    }
  ]
}

---

#### GET /audit/history/{campaign_id}
All past audit snapshots for a campaign. Used to render the decay trend chart.

Response:
{
  "campaign_id": 2,
  "snapshots": [
    {
      "audited_at": "2025-04-20T10:00:00Z",
      "health_score": 71,
      "open_rate": 0.38,
      "reply_rate": 0.06,
      "bounce_rate": 0.02
    },
    {
      "audited_at": "2025-04-27T10:00:00Z",
      "health_score": 34,
      "open_rate": 0.21,
      "reply_rate": 0.018,
      "bounce_rate": 0.03
    }
  ]
}

---

#### GET /audit/cross-campaign
Aggregate patterns across all campaigns. Powers the overview intelligence panel.

Response:
{
  "best_subject_styles": [
    { "style": "question", "avg_open_rate": 0.42 },
    { "style": "number_lead", "avg_open_rate": 0.38 }
  ],
  "top_reply_themes": [
    { "theme": "pricing concern", "count": 47, "campaigns_affected": 3 }
  ],
  "worst_step_positions": [
    { "step_number": 3, "avg_reply_rate": 0.008, "campaigns_affected": 5 }
  ]
}

---

### Replies

#### GET /replies/{campaign_id}/clusters
Clustered reply themes for a single campaign.

Response:
{
  "campaign_id": 2,
  "total_replies": 84,
  "clusters": [
    {
      "category": "interested",
      "count": 18,
      "percentage": 21.4,
      "themes": ["let's chat", "send more info", "book a call"],
      "samples": ["Hey, this looks interesting...", "Can you send over a deck?"]
    },
    {
      "category": "price_objection",
      "count": 31,
      "percentage": 36.9,
      "themes": ["too expensive", "budget", "cost"],
      "samples": ["We don't have budget for this right now..."]
    }
  ]
}

---

#### POST /replies/{campaign_id}/recluster
Re-run reply clustering after new replies have come in.

Response:
{
  "clusters_updated": 6
}

---

### AI Optimization

#### POST /optimize/diagnose
Ask Claude to diagnose why a campaign is underperforming.

Request body:
{
  "campaign_id": 2
}

Response:
{
  "campaign_id": 2,
  "diagnosis": "The primary issue is copy — your open rate (21%) is acceptable but reply rate (1.8%) indicates the body copy is not compelling. Step 3 has the steepest drop-off. The CTA is vague and the value proposition appears in paragraph 3 instead of the opening line.",
  "root_cause": "copy",
  "confidence": "high",
  "evidence": [
    "Open rate 21% rules out deliverability and subject line as primary cause",
    "Reply rate 1.8% on 21% open rate = 8.6% open-to-reply, well below 20% benchmark",
    "62% of negative replies contain no objection — silent disengagement pattern",
    "Step 3 reply rate (0.4%) is 5x lower than Step 1 (2.1%)"
  ]
}

---

#### POST /optimize/rewrite
Ask Claude to rewrite a specific sequence step.

Request body:
{
  "campaign_id": 2,
  "step_id": 7,
  "instruction": "Make it shorter and lead with the value prop"  // optional
}

Response:
{
  "step_id": 7,
  "step_number": 3,
  "original": "Hi {{first_name}}, I wanted to follow up on my previous email...",
  "rewrite": "{{first_name}} — most {{job_title}}s at {{company_size}} companies are losing 6 hours a week on manual reporting. We fix that in one integration. Worth 15 mins?",
  "subject_alternatives": [
    "Quick question {{first_name}}",
    "6 hours a week — {{company}}?",
    "Manual reporting fix for {{company}}"
  ],
  "rationale": "Moved value prop to line 1, added specific pain point with a number, reduced from 94 to 31 words, replaced vague CTA with a time-bound ask"
}

---

#### GET /optimize/rewrites/{campaign_id}
All previously generated rewrites for a campaign.

Response:
{
  "campaign_id": 2,
  "rewrites": [
    {
      "step_number": 3,
      "original": "...",
      "rewrite": "...",
      "generated_at": "2025-04-27T11:30:00Z"
    }
  ]
}

---

### Config

#### GET /config/thresholds
Retrieve current scoring thresholds used by the audit engine.

Response:
{
  "open_rate_warn": 0.25,
  "open_rate_critical": 0.15,
  "reply_rate_warn": 0.03,
  "reply_rate_critical": 0.01,
  "bounce_rate_warn": 0.03,
  "bounce_rate_critical": 0.05,
  "cache_ttl_minutes": 30
}

---

#### POST /config/thresholds
Update thresholds from the UI settings panel.

Request body:
{
  "reply_rate_warn": 0.04,
  "cache_ttl_minutes": 60
}

Response:
{
  "updated": true
}

## Features (V1)
1. Campaign health score (0-100)
2. Root cause diagnosis (deliverability / subject / copy / targeting)
3. Sequence drop-off analysis
4. Reply sentiment clustering
5. Cross-campaign subject line patterns
6. Campaign decay detection
7. On-demand Claude diagnosis + rewrite