"""
应用配置
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # 应用基础配置
    APP_NAME: str = "Easy Data"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./easy_data.db"
    SQLALCHEMY_ECHO: bool = False  # 为 True 时打印每条 SQL，排障时可开启，平时建议关闭

    # JWT配置
    JWT_SECRET_KEY: str = "easy-data"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # CORS配置
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # LLM配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = ""

    # LangSmith配置
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""

    # 作业执行并行度：按类型配置同时运行上限，未单独配置的类型使用 JOB_MAX_CONCURRENT_DEFAULT
    JOB_MAX_CONCURRENT_DEFAULT: int = 3
    JOB_MAX_CONCURRENT_AGENT: int | None = None  # agent 类型独立上限，不设则用 DEFAULT

    model_config = {"env_file": ".env", "case_sensitive": True}


def get_job_max_concurrent(job_type: str) -> int:
    """按作业类型取并行度上限，未配置的类型使用 JOB_MAX_CONCURRENT_DEFAULT"""
    key = f"JOB_MAX_CONCURRENT_{job_type.upper()}"
    val = getattr(settings, key, None)
    if val is not None:
        return val
    return settings.JOB_MAX_CONCURRENT_DEFAULT


settings = Settings()
