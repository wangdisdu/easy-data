"""
作业管理 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.service.job_service import JobCreate, JobLogResponse, JobResponse, JobService

router = APIRouter()


@router.post("/jobs", response_model=Resp[JobResponse])
async def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建作业（status=waiting，由扫描器抢占执行）"""
    job = JobService.create_job(db=db, job_data=job_data, create_user_id=current_user.id)
    return Resp(data=job)


@router.get("/jobs", response_model=PagedResp[JobResponse])
async def get_jobs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取作业列表"""
    jobs, total = JobService.get_jobs(db=db, skip=skip, limit=limit)
    return PagedResp(data=jobs, total=total)


@router.get("/jobs/{job_id}", response_model=Resp[JobResponse])
async def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取作业详情"""
    job = JobService.get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise BizError(BizErrorCode.JOB_NOT_EXIST, "作业不存在")
    return Resp(data=job)


@router.delete("/jobs/{job_id}", response_model=Resp[JobResponse])
async def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除作业"""
    job = JobService.delete_job(db=db, job_id=job_id)
    return Resp(data=job)


@router.get("/jobs/{job_id}/logs", response_model=Resp[list[JobLogResponse]])
async def get_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取作业日志"""
    job = JobService.get_job_by_id(db=db, job_id=job_id)
    if not job:
        raise BizError(BizErrorCode.JOB_NOT_EXIST, "作业不存在")
    logs = JobService.get_job_logs(db=db, job_id=job_id)
    return Resp(data=logs)
