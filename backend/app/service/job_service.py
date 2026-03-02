"""
作业服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.logging import get_logger
from app.dao.models import TbJob, TbJobLog

logger = get_logger(__name__)

# 日志单条入库最大长度
JOB_LOG_CHUNK_SIZE = 1024


class JobResponse(BaseModel):
    """作业响应模型"""

    id: int
    type: str
    status: str
    setting: Optional[str] = None
    description: Optional[str] = None
    extend: Optional[str] = None
    begin_time: Optional[int] = None
    end_time: Optional[int] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


class JobLogResponse(BaseModel):
    """作业日志响应模型"""

    id: int
    job_id: int
    content: str
    create_time: int

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    """作业创建模型"""

    type: str = "agent"
    setting: str
    description: Optional[str] = None


class JobService:
    """作业服务"""

    @staticmethod
    def create_job(
        db: Session,
        job_data: JobCreate,
        create_user_id: Optional[int] = None,
    ) -> JobResponse:
        """创建作业（status=waiting，由扫描器抢占执行）"""
        current_time = int(time.time() * 1000)
        job = TbJob(
            type=job_data.type,
            status="waiting",
            setting=job_data.setting,
            description=job_data.description,
            extend=None,
            begin_time=None,
            end_time=None,
            create_time=current_time,
            update_time=current_time,
            create_user=create_user_id,
            update_user=create_user_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return JobResponse.model_validate(job)

    @staticmethod
    def get_jobs(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[JobResponse], int]:
        """获取作业列表（分页）"""
        rows = db.query(TbJob).order_by(TbJob.id.desc()).offset(skip).limit(limit).all()
        total = db.query(TbJob).count()
        return [JobResponse.model_validate(r) for r in rows], total

    @staticmethod
    def get_job_by_id(db: Session, job_id: int) -> Optional[JobResponse]:
        """根据 ID 获取作业"""
        job = db.query(TbJob).filter(TbJob.id == job_id).first()
        if not job:
            return None
        return JobResponse.model_validate(job)

    @staticmethod
    def delete_job(db: Session, job_id: int) -> JobResponse:
        """删除作业（同时删除关联日志）"""
        job = db.query(TbJob).filter(TbJob.id == job_id).first()
        if not job:
            raise BizError(BizErrorCode.JOB_NOT_EXIST, "作业不存在")
        result = JobResponse.model_validate(job)
        db.query(TbJobLog).filter(TbJobLog.job_id == job_id).delete()
        db.delete(job)
        db.commit()
        return result

    @staticmethod
    def get_job_logs(db: Session, job_id: int) -> list[JobLogResponse]:
        """获取作业日志列表（按 create_time 升序）"""
        rows = (
            db.query(TbJobLog).filter(TbJobLog.job_id == job_id).order_by(TbJobLog.id.asc()).all()
        )
        return [JobLogResponse.model_validate(r) for r in rows]

    @staticmethod
    def append_job_log(db: Session, job_id: int, content: str) -> None:
        """追加作业日志，按 1024 字符切分后入库"""
        current_time = int(time.time() * 1000)
        for i in range(0, len(content), JOB_LOG_CHUNK_SIZE):
            chunk = content[i : i + JOB_LOG_CHUNK_SIZE]
            log_row = TbJobLog(
                job_id=job_id,
                content=chunk,
                create_time=current_time,
                update_time=current_time,
                create_user=None,
                update_user=None,
            )
            db.add(log_row)
        db.commit()

    @staticmethod
    def try_acquire_job(db: Session, job_id: int) -> bool:
        """
        原子抢占作业：仅当 status=waiting 时更新为 running。
        返回 True 表示抢占成功，否则未抢到。
        """
        updated = (
            db.query(TbJob)
            .filter(TbJob.id == job_id, TbJob.status == "waiting")
            .update({"status": "running", "update_time": int(time.time() * 1000)})
        )
        db.commit()
        return updated > 0

    @staticmethod
    def set_job_begin_time(db: Session, job_id: int) -> None:
        """设置作业开始时间"""
        t = int(time.time() * 1000)
        db.query(TbJob).filter(TbJob.id == job_id).update({"begin_time": t, "update_time": t})
        db.commit()

    @staticmethod
    def set_job_end_time_and_status(db: Session, job_id: int, status: str = "success") -> None:
        """设置作业结束时间和状态"""
        t = int(time.time() * 1000)
        db.query(TbJob).filter(TbJob.id == job_id).update(
            {"end_time": t, "status": status, "update_time": t}
        )
        db.commit()
