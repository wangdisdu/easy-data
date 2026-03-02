"""
用户服务层
"""

import time
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.biz_error import BizError, BizErrorCode
from app.dao.models import TbUser


class UserUpdate(BaseModel):
    """用户更新模型"""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型"""

    id: int
    guid: str
    account: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    create_time: int
    update_time: int

    class Config:
        from_attributes = True


class UserService:
    """用户服务"""

    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[TbUser], int]:
        """
        获取用户列表

        Args:
            db: 数据库会话
            skip: 跳过记录数
            limit: 限制记录数

        Returns:
            （用户列表，总记录数）
        """
        users = db.query(TbUser).offset(skip).limit(limit).all()
        total = db.query(TbUser).count()
        return users, total

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[TbUser]:
        """
        根据ID获取用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            用户对象，如果不存在返回None
        """
        return db.query(TbUser).filter(TbUser.id == user_id).first()

    @staticmethod
    def update_user(
        db: Session, user_id: int, user_update: UserUpdate, update_user_id: int
    ) -> TbUser:
        """
        更新用户信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            user_update: 用户更新数据
            update_user_id: 更新用户ID

        Returns:
            更新后的用户对象

        Raises:
            ValueError: 如果用户不存在
        """
        user = db.query(TbUser).filter(TbUser.id == user_id).first()
        if not user:
            raise BizError(BizErrorCode.USER_NOT_EXIST, "用户不存在")

        current_time = int(time.time() * 1000)

        if user_update.name is not None:
            user.name = user_update.name
        if user_update.email is not None:
            user.email = user_update.email
        if user_update.phone is not None:
            user.phone = user_update.phone

        user.update_time = current_time
        user.update_user = update_user_id

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> TbUser:
        """
        删除用户

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            被删除的用户对象

        Raises:
            ValueError: 如果用户不存在
        """
        user = db.query(TbUser).filter(TbUser.id == user_id).first()
        if not user:
            raise BizError(BizErrorCode.USER_NOT_EXIST, "用户不存在")

        db.delete(user)
        db.commit()
        return user
