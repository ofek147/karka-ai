"""
worker.py — background thread that processes report_jobs one at a time.

Flow:
  every 10s → pick oldest pending job → mark processing →
  generate report → send email/SMS → mark done
  on error → mark failed + store error_msg

Stuck recovery: jobs stuck in `processing` for >15min are reset to `pending`.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.report_job import ReportJob
import traceback
from ..services.report_service import generate_report_text
from ..services.email_service import send_report_ready

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10        # seconds between queue checks
STUCK_TIMEOUT = 15 * 60  # seconds before resetting stuck jobs


async def _process_one(db: AsyncSession, job: ReportJob, WorkerSession) -> None:
    """Process a single report job end-to-end."""
    now = datetime.now(timezone.utc)

    # Mark as processing
    await db.execute(
        update(ReportJob)
        .where(ReportJob.id == job.id)
        .values(status="processing", started_at=now)
    )
    await db.commit()

    try:
        logger.info(f"[worker] Processing job #{job.id} — גוש {job.gush} חלקה {job.helka}")

        # Open a dedicated session for report_service (plan_cache reads/writes)
        async with WorkerSession() as report_db:
            text = await generate_report_text(job.gush, job.helka, db=report_db)

        # Send to email and/or phone
        sent = False
        if job.email:
            sent = await send_report_ready(
                email=job.email,
                name=job.name,
                gush=job.gush,
                helka=job.helka,
                text=text,
            )

        # TODO: SMS via Twilio/Vonage when phone-only (job.phone and not job.email)
        # Until SMS is implemented, phone-only jobs are marked "done_no_delivery"
        # so the report is generated but we have visibility that it never reached the user.
        if not sent and not job.email:
            final_status = "done_no_delivery"
            final_error = "phone-only delivery not yet implemented (SMS pending)"
            logger.warning(f"[worker] Job #{job.id} — report generated but NOT delivered (phone-only, no email)")
        elif not sent:
            # email was set but send failed — treat as failed
            final_status = "failed"
            final_error = "email delivery failed"
            logger.error(f"[worker] Job #{job.id} — email delivery failed")
        else:
            final_status = "done"
            final_error = None

        await db.execute(
            update(ReportJob)
            .where(ReportJob.id == job.id)
            .values(
                status=final_status,
                completed_at=datetime.now(timezone.utc),
                error_msg=final_error,
            )
        )
        await db.commit()
        logger.info(f"[worker] Job #{job.id} {final_status} — sent={sent}")

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[worker] Job #{job.id} failed: {e}\n{tb}")
        await db.execute(
            update(ReportJob)
            .where(ReportJob.id == job.id)
            .values(
                status="failed",
                completed_at=datetime.now(timezone.utc),
                error_msg=tb[-1000:],
            )
        )
        await db.commit()


async def _reset_stuck_jobs(db: AsyncSession) -> None:
    """
    Reset jobs stuck in `processing` for too long (e.g. server crash mid-job).

    ASSUMPTION: single Railway replica only.
    TODO(multi-replica): if Railway runs >1 replica, two instances can both
    pick up the same job — instance B resets a job that instance A is still
    actively processing → duplicate emails + double DB writes.
    Fix: replace status filter with SELECT ... FOR UPDATE SKIP LOCKED.
    Until then, ensure Railway service is configured with replicas=1.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=STUCK_TIMEOUT)
    result = await db.execute(
        update(ReportJob)
        .where(ReportJob.status == "processing", ReportJob.started_at < cutoff)
        .values(status="pending", started_at=None)
        .returning(ReportJob.id)
    )
    stuck = result.fetchall()
    if stuck:
        await db.commit()
        logger.warning(f"[worker] Reset {len(stuck)} stuck jobs: {[r[0] for r in stuck]}")


async def _worker_loop() -> None:
    """Main async loop — runs forever inside the worker thread."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from ..db import _build_url
    from ..config import settings

    # Create engine + session factory local to this thread's event loop
    engine = create_async_engine(_build_url(settings.database_url), echo=False)
    WorkerSession = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    logger.info("[worker] Started")

    while True:
        try:
            async with WorkerSession() as db:
                # 1. Reset stuck jobs
                await _reset_stuck_jobs(db)

                # 2. Pick oldest pending job
                result = await db.execute(
                    select(ReportJob)
                    .where(ReportJob.status == "pending")
                    .order_by(ReportJob.created_at.asc())
                    .limit(1)
                )
                job = result.scalar_one_or_none()

                if job:
                    await _process_one(db, job, WorkerSession)
                else:
                    # No pending jobs — wait before next poll
                    await asyncio.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error(f"[worker] Loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


def start_worker() -> threading.Thread:
    """
    Start the worker in a dedicated daemon thread with its own asyncio event loop.
    Call once from FastAPI lifespan.
    """
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_worker_loop())

    t = threading.Thread(target=_run, name="report-worker", daemon=True)
    t.start()
    logger.info("[worker] Thread started")
    return t
