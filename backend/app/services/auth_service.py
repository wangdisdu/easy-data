"""
认证服务层
"""

import time
import uuid
from datetime import timedelta
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.dao.models import TbUser

logger = get_logger("auth_service")


class UserCreate(BaseModel):
    """用户创建模型"""

    account: str
    name: str
    passwd: str
    email: Optional[str] = None
    phone: Optional[str] = None


class Token(BaseModel):
    """令牌响应模型"""

    access_token: str
    token_type: str = "bearer"


class AuthService:
    """认证服务"""

    @staticmethod
    def register(db: Session, user_data: UserCreate) -> TbUser:
        """
        用户注册

        Args:
            db: 数据库会话
            user_data: 用户创建数据

        Returns:
            创建的用户对象

        Raises:
            BizError: 如果账号已存在
        """
        # 检查账号是否已存在
        existing_user = db.query(TbUser).filter(TbUser.account == user_data.account).first()
        if existing_user:
            raise BizError(BizErrorCode.USER_ALREADY_EXISTS, "账号已存在")

        # 创建新用户
        current_time = int(time.time() * 1000)
        new_user = TbUser(
            guid=str(uuid.uuid4()),
            account=user_data.account,
            name=user_data.name,
            passwd=get_password_hash(user_data.passwd),
            email=user_data.email,
            phone=user_data.phone,
            create_time=current_time,
            update_time=current_time,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(db: Session, account: str, password: str) -> Token:
        """
        用户登录

        Args:
            db: 数据库会话
            account: 账号
            password: 密码

        Returns:
            Token对象

        Raises:
            BizError: 如果账号或密码错误
        """
        user = db.query(TbUser).filter(TbUser.account == account).first()

        if not user or not verify_password(password, user.passwd):
            raise BizError(BizErrorCode.INVALID_CREDENTIALS, "账号或密码错误")

        access_token = create_access_token(
            data={"sub": str(user.id)},  # JWT 标准要求 sub 必须是字符串
            expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        return Token(access_token=access_token, token_type="bearer")

    @staticmethod
    def get_user_by_token(db: Session, token: str) -> TbUser:
        """
        根据token获取用户

        Args:
            db: 数据库会话
            token: JWT token

        Returns:
            用户对象

        Raises:
            BizError: 如果token无效或用户不存在
        """
        logger.debug(f"收到 token: {token[:20]}...")

        payload = decode_access_token(token)
        if payload is None:
            logger.warning("Token 解码失败")
            raise BizError(BizErrorCode.INVALID_TOKEN, "无效的认证凭据")

        user_id_str = payload.get("sub")
        if user_id_str is None:
            logger.warning(f"Token payload 中没有 sub 字段：{payload}")
            raise BizError(BizErrorCode.INVALID_TOKEN, "无效的认证凭据")

        # 将字符串转换为整数
        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            logger.warning(f"无法将 sub 转换为整数：{user_id_str}")
            raise BizError(BizErrorCode.INVALID_TOKEN, "无效的认证凭据") from None

        user = db.query(TbUser).filter(TbUser.id == user_id).first()
        if user is None:
            logger.warning(f"用户不存在：user_id={user_id}")
            raise BizError(BizErrorCode.USER_NOT_FOUND, "用户不存在")

        return user
