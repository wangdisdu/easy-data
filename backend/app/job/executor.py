"""
作业执行器：按作业类型派发到具体执行器执行
"""

import json
import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.agent.agent_executor import AgentExecutor
from app.core.biz_error import BizError
from app.core.logging import get_logger
from app.service.job_service import JOB_LOG_CHUNK_SIZE, JobService

logger = get_logger(__name__)


class JobExecutor(ABC):
    """作业执行器基类"""

    @abstractmethod
    async def execute(self, job_id: int, setting: str, db: Session) -> None:
        """执行作业。setting 为 JSON 字符串。"""


class AgentJobExecutor(JobExecutor):
    """Agent 类型作业执行器：根据 setting 中的 agent_id、input 执行智能体并写日志"""

    async def execute(self, job_id: int, setting: str, db: Session) -> None:
        try:
            params = json.loads(setting or "{}")
            agent_id = params.get("agent_id")
            input_text = params.get("input", "")
            if not agent_id:
                JobService.append_job_log(db, job_id, "[error] setting 缺少 agent_id\n")
                JobService.set_job_end_time_and_status(db, job_id, status="failed")
                return
        except json.JSONDecodeError as e:
            JobService.append_job_log(db, job_id, f"[error] setting 不是合法 JSON: {e}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return

        JobService.set_job_begin_time(db, job_id)
        session_id = str(uuid.uuid4())
        buffer: list[str] = []
        buffer_len = 0

        def flush_log(force: bool = False) -> None:
            nonlocal buffer_len
            if not buffer and not force:
                return
            text = "".join(buffer)
            buffer.clear()
            buffer_len = 0
            if text:
                JobService.append_job_log(db, job_id, text)

        try:
            executor = AgentExecutor(db, agent_id, user_id=None)
            executor.build()
        except BizError as e:
            JobService.append_job_log(db, job_id, f"[error] 智能体初始化失败: {e.message}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return
        except Exception as e:
            JobService.append_job_log(db, job_id, f"[error] 智能体初始化失败: {e!s}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return

        try:
            async for chunk_dict in executor.astream(session_id=session_id, message=input_text):
                if isinstance(chunk_dict, dict) and "chunk" in chunk_dict:
                    part = chunk_dict.get("chunk") or ""
                    if isinstance(part, str):
                        buffer.append(part)
                        buffer_len += len(part)
                        while buffer_len >= JOB_LOG_CHUNK_SIZE:
                            acc: list[str] = []
                            n = 0
                            while buffer and n < JOB_LOG_CHUNK_SIZE:
                                s = buffer.pop(0)
                                acc.append(s)
                                n += len(s)
                            buffer_len -= n
                            JobService.append_job_log(db, job_id, "".join(acc))
            flush_log(force=True)
            JobService.set_job_end_time_and_status(db, job_id, status="success")
        except Exception as e:
            flush_log()
            JobService.append_job_log(db, job_id, f"\n[error] 执行异常: {e!s}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            logger.exception("AgentJobExecutor 执行失败 job_id=%s", job_id)


# 按 type 注册执行器
_EXECUTORS: dict[str, type[JobExecutor]] = {
    "agent": AgentJobExecutor,
}


def get_executor(job_type: str) -> JobExecutor | None:
    """根据作业类型获取执行器实例"""
    cls = _EXECUTORS.get(job_type)
    return cls() if cls else None
