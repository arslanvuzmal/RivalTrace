import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks
from sqlalchemy.orm import Session
from deepdiff import DeepDiff
import json

import structlog

from app.core.database import SessionLocal
from app.models.client import Client
from app.models.snapshot import Snapshot
from app.models.briefing_history import BriefingHistory, DeliveryStatus
from app.schemas.insights import CompetitorInsight
from app.services.data_sanitizer import sanitize_delta_for_llm
from app.services.claude_service import generate_strategic_insights
from app.services.template_service import render_briefing_email
from app.services.email_service import send_briefing
from app.services.slack_service import send_slack_briefing

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/orchestrate", tags=["orchestration"])

def _parse_diff(diff_obj: DeepDiff, *keys: str) -> dict:
    """Helper to parse DeepDiff objects."""
    res = {}
    for k in keys:
        if k in diff_obj:
            if isinstance(diff_obj[k], dict):
                res.update(diff_obj[k])
            else:
                res[k] = list(diff_obj[k])
    
    parsed_json = json.loads(diff_obj.to_json())
    return parsed_json.get(keys[0], {}) if keys and keys[0] in parsed_json else res


def run_briefings(client_id: Optional[int] = None):
    """
    Background task: opens its own session (the request's is closed by then) and runs the briefings
    for every active client, or for one.
    """
    db = SessionLocal()
    try:
        _process_weekly_briefings(db, client_id)
    finally:
        db.close()


def _process_weekly_briefings(db: Session, client_id: Optional[int] = None):
    """
    Process all active clients (or one), generate insights,
    render the email, and send it.
    """
    logger.info("Starting weekly briefing orchestration...", client_id=client_id)
    query = db.query(Client).filter(Client.is_active == True)
    if client_id is not None:
        query = query.filter(Client.id == client_id)
    clients = query.all()
    
    for client in clients:
        client_log = logger.bind(client_id=client.id, client_name=client.name)
        insights_list: List[Dict[str, Any]] = []
        history_records: List[BriefingHistory] = []
        
        for competitor in client.competitors:
            comp_log = client_log.bind(competitor_id=competitor.id, competitor_name=competitor.name)
            
            # Fetch latest 2 snapshots
            snapshots = (
                db.query(Snapshot)
                .filter(Snapshot.competitor_id == competitor.id)
                .order_by(Snapshot.scrape_date.desc())
                .limit(2)
                .all()
            )
            
            if not snapshots:
                comp_log.info("Skipping competitor - No snapshots found.")
                continue
                
            if len(snapshots) < 2:
                raw_delta = {
                    "added_items": snapshots[0].raw_data,
                    "removed_items": {},
                    "modified_items": {}
                }
            else:
                diff = DeepDiff(snapshots[1].raw_data, snapshots[0].raw_data, ignore_order=True, report_repetition=True)
                raw_delta = {
                    "added_items": _parse_diff(diff, 'dictionary_item_added', 'iterable_item_added'),
                    "removed_items": _parse_diff(diff, 'dictionary_item_removed', 'iterable_item_removed'),
                    "modified_items": _parse_diff(diff, 'values_changed', 'type_changes')
                }
                
            is_empty = not raw_delta.get("added_items") and not raw_delta.get("removed_items") and not raw_delta.get("modified_items")
            
            if is_empty:
                comp_log.info("Skipping competitor - No changes.")
                continue
                
            sanitized_text = sanitize_delta_for_llm(raw_delta)
            
            insight: CompetitorInsight = generate_strategic_insights(
                competitor_name=competitor.name, 
                sanitized_delta=sanitized_text
            )
            
            # Only append if valid insights were generated (threat level won't be LOW just cause of error, but we skip empties)
            if insight.what_changed or insight.what_it_means or insight.what_to_do:
                insights_list.append({
                    "competitor_name": competitor.name,
                    "insight": insight
                })
                
                # Save to BriefingHistory
                history_record = BriefingHistory(
                    client_id=client.id,
                    competitor_id=competitor.id,
                    insight_json=insight.model_dump(mode="json"),
                    delivery_status=DeliveryStatus.SENT
                )
                db.add(history_record)
                history_records.append(history_record)
        
        # Commit histories
        db.commit()
                
        # Send Email if there are insights
        if insights_list:
            # Try Slack
            if client.slack_webhook_url:
                slack_success = send_slack_briefing(client.slack_webhook_url, client.name, insights_list)
                if slack_success:
                    client_log.info("Briefing sent successfully via Slack")
                else:
                    client_log.error("Failed to send briefing via Slack")
                    
            # Always Try Email
            html_content = render_briefing_email(client.name, insights_list)
            email_success = send_briefing(client.email_address, client.name, html_content)
            if email_success:
                client_log.info("Briefing sent successfully via Email")
            else:
                client_log.error("Failed to send briefing via Email")
                # The records were saved as SENT before sending; a failed email used to leave them that way.
                for record in history_records:
                    record.delivery_status = DeliveryStatus.FAILED
                db.commit()
                
        else:
            client_log.info("No insights to send for client")

@router.post("/weekly-briefings", status_code=202)
def trigger_weekly_briefings(
    background_tasks: BackgroundTasks,
):
    """
    Triggers the generation and sending of weekly briefings for all active clients.
    Runs asynchronously in the background.
    """
    background_tasks.add_task(run_briefings)
    return {"message": "Weekly briefing orchestration started in the background."}
