"""
作业执行器：按作业类型派发到具体执行器执行
"""

import json
import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.agent.agent_executor import AgentExecutor
from app.agent.deep_agent import DeepAgent
from app.core.biz_error import BizError
from app.core.logging import get_logger
from app.service.job_service import JOB_LOG_CHUNK_SIZE, JobService

logger = get_logger(__name__)


def _is_numeric_agent_id(agent_id: object) -> bool:
    """agent_id 为数字或数字字符串则从数据库加载，否则从 agents 目录加载。"""
    return isinstance(agent_id, int) or (isinstance(agent_id, str) and agent_id.strip().isdigit())


class JobExecutor(ABC):
    """作业执行器基类"""

    @abstractmethod
    async def execute(self, job_id: int, setting: str, db: Session) -> None:
        """执行作业。setting 为 JSON 字符串。"""


def _create_runner(agent_id: object, db: Session, job_id: int):
    """创建 runner（AgentExecutor 或 DeepAgent），失败时写日志并返回 None。"""
    if _is_numeric_agent_id(agent_id):
        try:
            runner = AgentExecutor(
                db,
                int(agent_id) if isinstance(agent_id, str) else agent_id,
                user_id=None,
            )
            runner.build()
            return runner
        except BizError as e:
            JobService.append_job_log(db, job_id, f"[error] 智能体初始化失败: {e.message}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return None
        except Exception as e:
            JobService.append_job_log(db, job_id, f"[error] 智能体初始化失败: {e!s}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return None
    try:
        return DeepAgent(str(agent_id).strip(), user_id=None)
    except ValueError as e:
        JobService.append_job_log(db, job_id, f"[error] {e}\n")
        JobService.set_job_end_time_and_status(db, job_id, status="failed")
        return None


class AgentJobExecutor(JobExecutor):
    """Agent 类型作业执行器：根据 setting 中的 agent_id、input 执行智能体并写日志。

    - agent_id 为数字或数字字符串：从 tb_agent 加载（AgentExecutor）。
    - agent_id 为非数字字符串：从 agents 目录按名称加载（DeepAgent，如 admin、text_to_sql）。
    """

    async def execute(self, job_id: int, setting: str, db: Session) -> None:
        try:
            params = json.loads(setting or "{}")
            agent_id = params.get("agent_id")
            input_text = params.get("input", "")
            if agent_id is None:
                JobService.append_job_log(db, job_id, "[error] setting 缺少 agent_id\n")
                JobService.set_job_end_time_and_status(db, job_id, status="failed")
                return
        except json.JSONDecodeError as e:
            JobService.append_job_log(db, job_id, f"[error] setting 不是合法 JSON: {e}\n")
            JobService.set_job_end_time_and_status(db, job_id, status="failed")
            return

        JobService.set_job_begin_time(db, job_id)
        session_id = str(uuid.uuid4())

        runner = _create_runner(agent_id, db, job_id)
        if runner is None:
            return

        success = await self._collect_stream(runner, session_id, input_text, db, job_id)
        JobService.set_job_end_time_and_status(
            db, job_id, status="success" if success else "failed"
        )

    async def _collect_stream(
        self,
        runner,
        session_id: str,
        input_text: str,
        db: Session,
        job_id: int,
    ) -> bool:
        """从 runner 流式收集并写日志。"""
        buffer: list[str] = []
        buffer_len = 0
        try:
            async for chunk_dict in runner.astream(session_id=session_id, message=input_text):
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
            if buffer:
                JobService.append_job_log(db, job_id, "".join(buffer))
            return True
        except Exception as e:
            if buffer:
                JobService.append_job_log(db, job_id, "".join(buffer))
            JobService.append_job_log(db, job_id, f"\n[error] 执行异常: {e!s}\n")
            logger.exception("AgentJobExecutor 执行失败 job_id=%s", job_id)
            return False


# 按 type 注册执行器
_EXECUTORS: dict[str, type[JobExecutor]] = {
    "agent": AgentJobExecutor,
}


def get_executor(job_type: str) -> JobExecutor | None:
    """根据作业类型获取执行器实例"""
    cls = _EXECUTORS.get(job_type)
    return cls() if cls else None
