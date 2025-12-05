"""
User and authentication models
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, DECIMAL, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import uuid
import bcrypt
import secrets

from .database import Base

class SubscriptionTier(Base):
    __tablename__ = "subscription_tiers"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text)
    price_monthly = Column(DECIMAL(10, 2), default=0)
    price_yearly = Column(DECIMAL(10, 2), default=0)
    credits_per_month = Column(Integer, default=0)
    max_video_length_seconds = Column(Integer, default=300)
    max_file_size_mb = Column(Integer, default=500)
    max_concurrent_jobs = Column(Integer, default=1)
    api_access = Column(Boolean, default=False)
    priority_processing = Column(Boolean, default=False)
    features = Column(JSONB, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="subscription_tier")

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    company = Column(String(255))
    phone = Column(String(20))
    profile_picture_url = Column(Text)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255))
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)
    subscription_tier_id = Column(Integer, ForeignKey("subscription_tiers.id"), default=1)
    credits_balance = Column(Integer, default=100)
    status = Column(String(20), default="active")  # active, suspended, deleted
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    login_count = Column(Integer, default=0)
    preferences = Column(JSONB, default=dict)
    user_metadata = Column(JSONB, default=dict)
    
    # Relationships
    subscription_tier = relationship("SubscriptionTier", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
    video_jobs = relationship("VideoJob", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """Hash and set user password"""
        from backend.auth.jwt_handler import JWTHandler
        self.password_hash = JWTHandler.hash_password(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash"""
        from backend.auth.jwt_handler import JWTHandler
        return JWTHandler.verify_password(password, self.password_hash)
    
    def generate_email_verification_token(self) -> str:
        """Generate email verification token"""
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token
    
    def generate_password_reset_token(self) -> str:
        """Generate password reset token with expiry"""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return self.password_reset_token
    
    def is_password_reset_valid(self) -> bool:
        """Check if password reset token is still valid"""
        return (self.password_reset_token is not None and 
                self.password_reset_expires is not None and
                datetime.utcnow() < self.password_reset_expires)
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email
    
    @property
    def is_premium(self) -> bool:
        """Check if user has premium subscription"""
        return self.subscription_tier and self.subscription_tier.name != 'free'
    
    def can_process_video(self, video_duration_seconds: int, file_size_mb: int) -> tuple[bool, str]:
        """Check if user can process a video based on their subscription"""
        if not self.subscription_tier:
            return False, "No subscription tier found"
        
        if video_duration_seconds > self.subscription_tier.max_video_length_seconds:
            return False, f"Video too long. Maximum: {self.subscription_tier.max_video_length_seconds}s"
        
        if file_size_mb > self.subscription_tier.max_file_size_mb:
            return False, f"File too large. Maximum: {self.subscription_tier.max_file_size_mb}MB"
        
        return True, "OK"
    
    def has_sufficient_credits(self, required_credits: int) -> bool:
        """Check if user has enough credits"""
        return self.credits_balance >= required_credits
    
    def deduct_credits(self, amount: int, description: str = None):
        """Deduct credits from user balance"""
        if self.credits_balance >= amount:
            self.credits_balance -= amount
            return True
        return False

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True)
    ip_address = Column(INET)
    user_agent = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    @classmethod
    def create_session(cls, user_id: uuid.UUID, ip_address: str = None, user_agent: str = None):
        """Create a new user session"""
        session = cls(
            user_id=user_id,
            session_token=secrets.token_urlsafe(32),
            refresh_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(days=30)  # 30 day session
        )
        return session
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return datetime.utcnow() < self.expires_at
    
    def refresh(self):
        """Refresh session expiry"""
        self.expires_at = datetime.utcnow() + timedelta(days=30)
        self.last_accessed_at = datetime.utcnow()

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # purchase, usage, refund, bonus, expiration
    amount = Column(Integer, nullable=False)  # Positive for credit, negative for debit
    balance_after = Column(Integer, nullable=False)
    description = Column(Text)
    reference_type = Column(String(50))  # payment, video_job, manual_adjustment
    reference_id = Column(String(255))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    transaction_metadata = Column(JSONB, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="credit_transactions")

class CreditPackage(Base):
    __tablename__ = "credit_packages"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    credits = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    bonus_credits = Column(Integer, default=0)
    expiry_days = Column(Integer)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key_name = Column(String(100), nullable=False)
    api_key_hash = Column(String(255), nullable=False)
    api_key_prefix = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSONB, default=list)
    rate_limit_per_hour = Column(Integer, default=100)
    allowed_ips = Column(JSONB)
    last_used_at = Column(DateTime)
    total_requests = Column(Integer, default=0)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    @classmethod
    def create_api_key(cls, user_id: uuid.UUID, key_name: str):
        """Create a new API key for user"""
        api_key = secrets.token_urlsafe(32)
        api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        key = cls(
            user_id=user_id,
            key_name=key_name,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key[:8],
            expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year validity
        )
        
        return key, api_key  # Return both the model and the plain key
    
    def verify_key(self, api_key: str) -> bool:
        """Verify API key against hash"""
        return bcrypt.checkpw(api_key.encode('utf-8'), self.api_key_hash.encode('utf-8'))
    
    def is_valid(self) -> bool:
        """Check if API key is still valid"""
        return (self.is_active and 
                (self.expires_at is None or datetime.utcnow() < self.expires_at))

# Import other models to ensure they're registered
from .job import VideoJob
from .file import File