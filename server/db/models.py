from sqlalchemy import create_engine, Column, String, Boolean, DateTime, DECIMAL, text, ForeignKey, Integer, Text, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from datetime import datetime
import uuid

from config import settings

# Database engine
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise stores UUIDs as 36-char strings.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value) if dialect.name != "postgresql" else value
        parsed = uuid.UUID(str(value))
        return str(parsed) if dialect.name != "postgresql" else parsed

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# Database models
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="admin")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Device(Base):
    __tablename__ = "devices"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    hostname = Column(String(255), nullable=False)
    ip = Column(String(45), nullable=False)
    os = Column(String(255))
    token_hash = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), default="offline")
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    host_groups = relationship("HostGroup", secondary="device_hostgroup", back_populates="devices")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    revoked = Column(Boolean, default=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    device_id = Column(GUID())
    metric = Column(String(100), nullable=False)
    value = Column(DECIMAL(10, 2))
    threshold = Column(DECIMAL(10, 2))
    severity = Column(String(20), nullable=False)
    message = Column(String)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(GUID())
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


# Association tables for many-to-many relationships
device_hostgroup = Table(
    'device_hostgroup',
    Base.metadata,
    Column('device_id', GUID(), ForeignKey('devices.id'), primary_key=True),
    Column('hostgroup_id', GUID(), ForeignKey('host_groups.id'), primary_key=True)
)

template_hostgroup = Table(
    'template_hostgroup',
    Base.metadata,
    Column('template_id', GUID(), ForeignKey('templates.id'), primary_key=True),
    Column('hostgroup_id', GUID(), ForeignKey('host_groups.id'), primary_key=True)
)


class HostGroup(Base):
    """Logical grouping for devices/hosts."""
    __tablename__ = "host_groups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    devices = relationship("Device", secondary=device_hostgroup, back_populates="host_groups")
    templates = relationship("Template", secondary=template_hostgroup, back_populates="host_groups")


class Template(Base):
    """Monitoring template containing items, triggers, and discovery rules."""
    __tablename__ = "templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    template_type = Column(String(50), default="agent")  # agent, snmp, jmx, http
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("TemplateItem", back_populates="template", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="template", cascade="all, delete-orphan")
    host_groups = relationship("HostGroup", secondary=template_hostgroup, back_populates="templates")


class TemplateItem(Base):
    """Individual metric/item within a template."""
    __tablename__ = "template_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    template_id = Column(GUID(), ForeignKey('templates.id'), nullable=False)
    name = Column(String(255), nullable=False)
    key = Column(String(255), nullable=False)  # e.g., "system.cpu.load[avg1]"
    value_type = Column(String(50), default="numeric")  # numeric, text, log
    units = Column(String(50))  # %, bytes, ms
    update_interval = Column(Integer, default=60)  # seconds
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationship
    template = relationship("Template", back_populates="items")


class Trigger(Base):
    """Alert trigger with expression and severity."""
    __tablename__ = "triggers"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    template_id = Column(GUID(), ForeignKey('templates.id'), nullable=True)  # Can be standalone
    name = Column(String(255), nullable=False)
    expression = Column(Text, nullable=False)  # e.g., "{host:cpu.load.avg(5m)}>80"
    severity = Column(String(50), nullable=False, default="average")  # disaster, high, average, warning, info
    enabled = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    template = relationship("Template", back_populates="triggers")


class Action(Base):
    """Action executed when a trigger fires."""
    __tablename__ = "actions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, default="notification")  # notification, remediation, script
    conditions = Column(Text)  # JSON encoded conditions, e.g., {"severity": ">=high"}
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ActionOperation(Base):
    """Individual step within an action workflow."""
    __tablename__ = "action_operations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    action_id = Column(GUID(), ForeignKey('actions.id'), nullable=False)
    step_number = Column(Integer, nullable=False, default=1)
    operation_type = Column(String(50), nullable=False)  # send_email, send_telegram, run_script
    parameters = Column(Text)  # JSON encoded parameters
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
