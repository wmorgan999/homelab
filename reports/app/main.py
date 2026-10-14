import os
from datetime import date, datetime

from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
app = FastAPI(title="Lab Reports", version="0.1.0")


class Summary(BaseModel):
    total_customers: int
    first_created: datetime | None
    latest_created: datetime | None


class DailySignups(BaseModel):
    day: date
    signups: int


class AuditEvent(BaseModel):
    id: int
    event_type: str
    payload: dict
    received_at: datetime


@app.get("/health")
def health() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "UP"}


@app.get("/reports/summary", response_model=Summary)
def summary() -> Summary:
    sql = text(
        "SELECT count(*) AS total_customers, "
        "min(created_at) AS first_created, "
        "max(created_at) AS latest_created FROM customers"
    )
    with engine.connect() as conn:
        row = conn.execute(sql).mappings().one()
    return Summary(**row)


@app.get("/reports/signups-by-day", response_model=list[DailySignups])
def signups_by_day() -> list[DailySignups]:
    sql = text(
        "SELECT created_at::date AS day, count(*) AS signups "
        "FROM customers GROUP BY 1 ORDER BY 1 DESC"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [DailySignups(**r) for r in rows]


@app.get("/reports/audit", response_model=list[AuditEvent])
def audit(limit: int = Query(20, ge=1, le=200)) -> list[AuditEvent]:
    sql = text(
        "SELECT id, event_type, payload, received_at "
        "FROM customer_audit ORDER BY id DESC LIMIT :limit"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit": limit}).mappings().all()
    return [AuditEvent(**r) for r in rows]
