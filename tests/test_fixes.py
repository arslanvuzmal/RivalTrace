"""Tests for the fixes on the demo/site-proof branch."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1 import orchestration
from app.api.v1.auth import create_access_token, hash_password, verify_password
from app.core.database import Base, get_db
from app.main import app
from app.models.briefing_history import BriefingHistory, DeliveryStatus
from app.models.client import Client
from app.models.competitor import Competitor
from app.models.snapshot import Snapshot
from app.services import claude_service
from app.services.demo_insights import demo_insight


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    a = Client(name="A", email_address="a@example.com", password_hash=hash_password("pw-a"))
    b = Client(name="B", email_address="b@example.com", password_hash=hash_password("pw-b"))
    session.add_all([a, b])
    session.flush()
    session.add_all([
        Competitor(client_id=a.id, name="A's rival", website_url="https://a.example", apify_actor_id="x"),
        Competitor(client_id=b.id, name="B's rival", website_url="https://b.example", apify_actor_id="x"),
    ])
    session.commit()
    yield session
    session.close()


@pytest.fixture()
def api(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def token(client_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': str(client_id)})}"}


def test_dashboard_needs_a_token(api):
    assert api.get("/api/v1/dashboard/briefings").status_code == 401
    # The old guard trusted this header; it must not grant access any more.
    assert api.get("/api/v1/dashboard/briefings", headers={"X-Client-Id": "1"}).status_code == 401
    assert api.get("/api/v1/dashboard/briefings", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_dashboard_only_shows_own_competitors(api, db):
    a = db.query(Client).filter_by(name="A").one()
    names = [c["name"] for c in api.get("/api/v1/dashboard/competitors", headers=token(a.id)).json()]
    assert names == ["A's rival"]


def test_portal_add_competitor_uses_token_client(api, db):
    a = db.query(Client).filter_by(name="A").one()
    res = api.post("/api/v1/dashboard/competitors", headers=token(a.id),
                   json={"name": "New rival", "website_url": "https://new.example"})
    assert res.status_code == 201
    assert res.json()["client_id"] == a.id


def test_login_works_with_current_bcrypt(api):
    assert verify_password("pw-a", hash_password("pw-a"))
    assert not verify_password("wrong", hash_password("pw-a"))
    res = api.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "pw-a"})
    assert res.status_code == 200 and res.json()["access_token"]
    assert api.post("/api/v1/auth/login", data={"username": "a@example.com", "password": "no"}).status_code == 401


def test_failed_email_marks_briefings_failed(db):
    b = db.query(Client).filter_by(name="B").one()
    b.is_active = False
    comp = db.query(Competitor).filter_by(name="A's rival").one()
    db.add_all([
        Snapshot(competitor_id=comp.id, raw_data={"price": "£10"}),
        Snapshot(competitor_id=comp.id, raw_data={"price": "£12"}),
    ])
    db.commit()
    # Make the newer snapshot unambiguous.
    snaps = db.query(Snapshot).order_by(Snapshot.id).all()
    snaps[0].scrape_date = snaps[0].scrape_date.replace(year=2020)
    db.commit()
    with patch.object(orchestration, "send_briefing", return_value=False), \
         patch.object(claude_service.settings, "demo_mode", True):
        orchestration._process_weekly_briefings(db)
    statuses = [h.delivery_status for h in db.query(BriefingHistory).all()]
    assert statuses == [DeliveryStatus.FAILED]


def test_claude_reply_read_from_text_block_after_thinking():
    answer = ('{"executive_summary": "s", "threat_level": "LOW", "what_changed": [], '
              '"what_it_means": [], "what_to_do": []}')
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="thinking", thinking="..."), SimpleNamespace(type="text", text=answer)],
    )
    fake = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: response))
    with patch.object(claude_service, "get_claude_client", return_value=fake):
        assert claude_service._call_claude.__wrapped__("Rival", "delta").executive_summary == "s"


def test_demo_insight_pairs_old_and_new_values():
    delta = (
        "modified_items -> root['plans'][0]['price'] -> new_value: £49\n"
        "modified_items -> root['plans'][0]['price'] -> old_value: £55\n"
        "added_items -> root['services'][2]: Online booking"
    )
    insight = demo_insight("Rival", delta)
    descriptions = [c.description for c in insight.what_changed]
    assert "plans 1 price: £55 → £49" in descriptions
    assert "Added to services: Online booking" in descriptions
    assert insight.executive_summary.startswith("Demo mode (rules, no model)")
