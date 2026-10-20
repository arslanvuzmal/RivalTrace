"""Seed a local database with sample data for the demo.

Everything here is invented: one client, three fictional competitors, and two snapshots of each
competitor's site (last week and this week), shaped like a scraper's output. Run from the repository
root with DEMO_MODE=true; see README "Run the demo".

    python -m demo.seed            # creates/refreshes the SQLite demo database
"""

from datetime import datetime, timedelta

from app.api.v1.auth import hash_password
from app.core.database import Base, SessionLocal, engine
from app.models.briefing_history import BriefingHistory
from app.models.client import Client
from app.models.competitor import Competitor
from app.models.snapshot import Snapshot

DEMO_EMAIL = "demo@rivaltrace.local"
DEMO_PASSWORD = "DemoMode2026"

# (name, url, last week, this week). Fictional businesses; the changes are what the diff should find.
COMPETITORS = [
    (
        "Harbourside Physio (sample)",
        "https://harbourside-physio.example",
        {
            "headline": "Physiotherapy in the city centre",
            "plans": [
                {"name": "Initial assessment", "price": "£55"},
                {"name": "Follow-up session", "price": "£45"},
            ],
            "services": ["Sports injuries", "Back and neck pain"],
        },
        {
            "headline": "Physiotherapy in the city centre, now open Saturdays",
            "plans": [
                {"name": "Initial assessment", "price": "£49"},
                {"name": "Follow-up session", "price": "£45"},
                {"name": "Five-session pack", "price": "£199"},
            ],
            "services": ["Sports injuries", "Back and neck pain", "Pre- and post-natal physio"],
        },
    ),
    (
        "Kinetic Clinic (sample)",
        "https://kinetic-clinic.example",
        {
            "headline": "Move better, feel better",
            "plans": [{"name": "Assessment", "price": "£60"}],
            "services": ["Sports massage", "Rehab programmes", "Online consultations"],
        },
        {
            "headline": "Move better, feel better",
            "plans": [{"name": "Assessment", "price": "£60"}],
            "services": ["Sports massage", "Rehab programmes"],
        },
    ),
    (
        "Westgate Wellbeing (sample)",
        "https://westgate-wellbeing.example",
        {
            "headline": "Your local wellbeing team",
            "plans": [{"name": "Consultation", "price": "£50"}],
            "services": ["Physiotherapy", "Acupuncture"],
        },
        {
            "headline": "Your local wellbeing team",
            "plans": [{"name": "Consultation", "price": "£50"}],
            "services": ["Physiotherapy", "Acupuncture"],
        },
    ),
]


def seed() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        client = Client(
            name="Demo Physio Studio (sample)",
            email_address=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            is_active=True,
        )
        db.add(client)
        db.flush()
        now = datetime.utcnow()
        for name, url, before, after in COMPETITORS:
            competitor = Competitor(
                client_id=client.id, name=name, website_url=url, apify_actor_id="apify/website-content-crawler"
            )
            db.add(competitor)
            db.flush()
            db.add(Snapshot(competitor_id=competitor.id, scrape_date=now - timedelta(days=7), raw_data=before))
            db.add(Snapshot(competitor_id=competitor.id, scrape_date=now, raw_data=after))
        db.commit()
        print(f"Seeded 1 client ({DEMO_EMAIL}), {len(COMPETITORS)} competitors, {2 * len(COMPETITORS)} snapshots.")
        assert db.query(BriefingHistory).count() == 0
    finally:
        db.close()


if __name__ == "__main__":
    seed()
