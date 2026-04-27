from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"

    id: Optional[int] = Field(default=None, primary_key=True)
    smartlead_id: str = Field(unique=True, index=True)
    name: str
    status: str  # active / paused / completed
    total_leads: int = 0
    fetched_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditSnapshot(SQLModel, table=True):
    __tablename__ = "audit_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)
    open_rate: float = 0.0
    reply_rate: float = 0.0
    bounce_rate: float = 0.0
    health_score: int = 0
    root_cause: Optional[str] = None  # deliverability / subject / copy / targeting
    root_cause_detail: Optional[str] = None
    step_dropoff: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    subject_patterns: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    audited_at: datetime = Field(default_factory=datetime.utcnow)


class ReplyCluster(SQLModel, table=True):
    __tablename__ = "reply_clusters"

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)
    category: str  # interested / price_objection / timing / wrong_person / not_relevant / competitor / other
    count: int = 0
    percentage: float = 0.0
    sample_replies: Optional[list] = Field(default=None, sa_column=Column(JSON))
    themes: Optional[list] = Field(default=None, sa_column=Column(JSON))
    clustered_at: datetime = Field(default_factory=datetime.utcnow)


class SequenceStep(SQLModel, table=True):
    __tablename__ = "sequence_steps"

    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)
    step_number: int
    subject: Optional[str] = None
    body: Optional[str] = None
    open_rate: float = 0.0
    reply_rate: float = 0.0
    word_count: int = 0
    cta_detected: Optional[str] = None


class AIRewrite(SQLModel, table=True):
    __tablename__ = "ai_rewrites"

    id: Optional[int] = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="sequence_steps.id", index=True)
    campaign_id: int = Field(foreign_key="campaigns.id", index=True)
    diagnosis: Optional[str] = None
    original_copy: Optional[str] = None
    rewritten_copy: Optional[str] = None
    suggestions: Optional[list] = Field(default=None, sa_column=Column(JSON))
    model_used: str = "claude-sonnet-4-5"
    generated_at: datetime = Field(default_factory=datetime.utcnow)
