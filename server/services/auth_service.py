from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from uuid import UUID
import secrets

from config import settings
from db.models import User, RefreshToken

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: UUID, db: Session) -> str:
    """Create and store refresh token"""
    # Generate random token
    token = secrets.token_urlsafe(32)
    token_hash = get_password_hash(token)
    
    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    # Store in database
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    
    return token


def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if payload.get("type") != token_type:
            return None
            
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


def revoke_refresh_token(db: Session, token: str) -> bool:
    """Revoke a refresh token"""
    # Find all refresh tokens and check hash
    tokens = db.query(RefreshToken).filter(RefreshToken.revoked == False).all()
    
    for db_token in tokens:
        if verify_password(token, db_token.token_hash):
            db_token.revoked = True
            db.commit()
            return True
    
    return False


def verify_refresh_token(db: Session, token: str) -> Optional[UUID]:
    """Verify refresh token and return user_id"""
    # Find all non-revoked, non-expired tokens
    tokens = db.query(RefreshToken).filter(
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow()
    ).all()
    
    for db_token in tokens:
        if verify_password(token, db_token.token_hash):
            return db_token.user_id
    
    return None
