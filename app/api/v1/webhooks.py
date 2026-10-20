import structlog
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException

from app.core.security import verify_webhook_secret
from app.api.v1.orchestration import run_briefings

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post(
    "/n8n/trigger-all", 
    status_code=202,
    dependencies=[Depends(verify_webhook_secret)]
)
def trigger_all_briefings_webhook(
    background_tasks: BackgroundTasks
):
    """
    Secure webhook for n8n to trigger weekly briefings for all active clients.
    """
    logger.info("Webhook triggered: trigger-all briefings")
    background_tasks.add_task(run_briefings)
    return {"message": "Weekly briefing orchestration started in the background."}


@router.post(
    "/n8n/trigger-client/{client_id}", 
    status_code=202,
    dependencies=[Depends(verify_webhook_secret)]
)
def trigger_client_briefings_webhook(
    client_id: int,
    background_tasks: BackgroundTasks
):
    """
    Secure webhook for n8n to trigger a weekly briefing for a specific active client.
    """
    logger.info("Webhook triggered: trigger-client briefing", client_id=client_id)
    background_tasks.add_task(run_briefings, client_id)
    return {"message": f"Weekly briefing orchestration started for client {client_id}."}
