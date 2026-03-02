"""
用户管理API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.biz_error import BizError, BizErrorCode
from app.core.models import PagedResp, Resp
from app.dao.database import get_db
from app.dao.models import TbUser
from app.service.user_service import UserResponse, UserService, UserUpdate

router = APIRouter()


@router.get("/users", response_model=PagedResp[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: TbUser = Depends(get_current_user),
):
    """获取用户列表"""
    users, total = UserService.get_users(db=db, skip=skip, limit=limit)
    return PagedResp(data=users, total=total)


@router.get("/users/{user_id}", response_model=Resp[UserResponse])
async def get_user(
    user_id: int, db: Session = Depends(get_db), current_user: TbUser = Depends(get_current_user)
):
    """获取用户详情"""
    user = UserService.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise BizError(BizErrorCode.USER_NOT_EXIST, "用户不存在")
    return Resp(data=user)


@router.put("/users/{user_id}", response_model=Resp[UserResponse])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: TbUser = Depends(get_current_user),
):
    """更新用户信息"""
    user = UserService.update_user(
        db=db, user_id=user_id, user_update=user_update, update_user_id=current_user.id
    )
    return Resp(data=user)


@router.delete("/users/{user_id}", response_model=Resp[UserResponse])
async def delete_user(
    user_id: int, db: Session = Depends(get_db), current_user: TbUser = Depends(get_current_user)
):
    """删除用户"""
    user = UserService.delete_user(db=db, user_id=user_id)
    return Resp(data=user)
