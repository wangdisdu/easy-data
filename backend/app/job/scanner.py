"""
作业扫描器：每秒扫描 tb_job 中 status=waiting 的作业，原子抢占后交给对应执行器执行。
每种作业类型有独立的并行度上限，由 JOB_MAX_CONCURRENT_DEFAULT 与 JOB_MAX_CONCURRENT_<TYPE> 配置。
"""

import asyncio

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_job_max_concurrent, settings
from app.core.logging import get_logger
from app.dao.database import SessionLocal
from app.dao.models import TbJob
from app.job.executor import get_executor
from app.service.job_service import JobService

logger = get_logger(__name__)

SCAN_INTERVAL_SECONDS = 1
# 持有 create_task 返回的引用，避免被 GC 回收（满足 RUF006）
_background_tasks: list[asyncio.Task[None]] = []


async def _run_job(job_id: int, job_type: str, setting: str | None) -> None:
    """在独立 session 中执行单个作业（避免阻塞扫描循环）"""
    db: Session = SessionLocal()
    try:
        executor = get_executor(job_type)
        if not executor:
            logger.warning("未知作业类型 type=%s job_id=%s", job_type, job_id)
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return
        await executor.execute(job_id=job_id, setting=setting or "{}", db=db)
    except Exception as e:
        logger.exception("作业执行异常 job_id=%s", job_id)
        try:
            JobService.append_job_log(db, job_id, f"\n[error] {e!s}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
        except Exception:
            pass
    finally:
        db.close()


def _get_running_count_by_type(db: Session, job_type: str) -> int:
    """统计指定类型当前处于 running 的作业数"""
    return (
        db.query(func.count(TbJob.id))
        .filter(TbJob.type == job_type, TbJob.status == "running")
        .scalar()
        or 0
    )


async def _scan_once() -> None:
    """扫描一次：获取 waiting 作业，按类型检查该类型并行度上限后原子抢占并派发执行"""
    db = SessionLocal()
    try:
        waiting = db.query(TbJob).filter(TbJob.status == "waiting").order_by(TbJob.id.asc()).all()
        for job in waiting:
            job_type = job.type or "agent"
            max_concurrent = get_job_max_concurrent(job_type)
            running_count = _get_running_count_by_type(db, job_type)
            if running_count >= max_concurrent:
                continue
            acquired = JobService.try_acquire_job(db, job.id)
            if not acquired:
                continue
            setting = job.setting
            task = asyncio.create_task(_run_job(job.id, job_type, setting))
            _background_tasks.append(task)
    finally:
        db.close()


async def _scan_loop() -> None:
    """循环：每隔 SCAN_INTERVAL_SECONDS 秒扫描一次"""
    while True:
        try:
            await _scan_once()
        except Exception:
            logger.exception("作业扫描异常")
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


def start_job_scanner() -> None:
    """在事件循环中启动作业扫描任务（由 main 在 lifespan 或 startup 时调用）"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(_scan_loop())
    _background_tasks.append(task)
    default_limit = settings.JOB_MAX_CONCURRENT_DEFAULT
    agent_limit = get_job_max_concurrent("agent")
    logger.info(
        "作业扫描器已启动，间隔 %s 秒，并行度默认 %s，agent=%s",
        SCAN_INTERVAL_SECONDS,
        default_limit,
        agent_limit,
    )
