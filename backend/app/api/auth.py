"""
认证相关API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.biz_error import BizError
from app.core.logging import get_logger
from app.core.models import Resp
from app.dao.database import get_db
from app.dao.models import TbUser
from app.service.auth_service import AuthService, Token, UserCreate
from app.service.user_service import UserResponse

logger = get_logger("auth")

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> TbUser:
    """获取当前用户"""
    # 注意：这里将BizError转换为HTTPException，因为FastAPI的OAuth2需要HTTP 401状态码
    try:
        return AuthService.get_user_by_token(db=db, token=token)
    except BizError as e:
        # 将BizError转换为HTTPException以符合OAuth2规范
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.post("/auth/register", response_model=Resp[UserResponse])
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    new_user = AuthService.register(db=db, user_data=user_data)
    return Resp(data=new_user)


@router.post("/auth/login", response_model=Resp[Token])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    try:
        token = AuthService.login(db=db, account=form_data.username, password=form_data.password)
        return Resp(data=token)
    except BizError as e:
        # 将BizError转换为HTTPException以符合OAuth2规范
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


@router.get("/auth/me", response_model=Resp[UserResponse])
async def get_current_user_info(current_user: TbUser = Depends(get_current_user)):
    """获取当前用户信息"""
    return Resp(data=current_user)
