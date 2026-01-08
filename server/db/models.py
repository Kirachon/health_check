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


# Association table for direct device-to-template assignments (overrides hostgroup)
device_template = Table(
    'device_template',
    Base.metadata,
    Column('device_id', GUID(), ForeignKey('devices.id'), primary_key=True),
    Column('template_id', GUID(), ForeignKey('templates.id'), primary_key=True),
    Column('priority', Integer, default=0),  # Higher priority = applied later (overrides)
    Column('assigned_at', DateTime(timezone=True), default=datetime.utcnow)
)


class Template(Base):
    """Monitoring template containing items, triggers, and discovery rules."""
    __tablename__ = "templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    template_type = Column(String(50), default="agent")  # agent, snmp, jmx, http
    
    # Template inheritance
    parent_template_id = Column(GUID(), ForeignKey('templates.id'), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("TemplateItem", back_populates="template", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="template", cascade="all, delete-orphan")
    host_groups = relationship("HostGroup", secondary=template_hostgroup, back_populates="templates")
    
    # Self-referential for inheritance
    parent_template = relationship("Template", remote_side=[id], backref="child_templates")
    
    # Direct device assignments
    assigned_devices = relationship("Device", secondary=device_template, backref="direct_templates")


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
    
    # Advanced Trigger Engine fields
    expression_type = Column(String(20), default="simple")  # simple, compound, calculated
    compound_expression = Column(Text)  # JSON: {"operator": "and", "conditions": [...]}
    
    # Time-based conditions (Zabbix-style)
    time_window = Column(Integer)  # Aggregation window in seconds (e.g., 300 for 5m avg)
    time_function = Column(String(50))  # avg, min, max, last, count, sum
    
    # Duration requirement (must be true for X seconds before firing)
    duration = Column(Integer, default=0)  # seconds; 0 = immediate
    
    # Hysteresis to prevent flapping
    recovery_expression = Column(Text)  # Optional separate expression for recovery
    
    # Dependencies (don't alert if parent trigger is in PROBLEM state)
    parent_trigger_id = Column(GUID(), ForeignKey('triggers.id'), nullable=True)
    
    # Evaluation metadata
    last_evaluated_at = Column(DateTime(timezone=True))
    last_state = Column(String(20))  # OK, PROBLEM, UNKNOWN
    state_since = Column(DateTime(timezone=True))  # When current state started
    
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template = relationship("Template", back_populates="triggers")
    alert_events = relationship("AlertEvent", back_populates="trigger", cascade="all, delete-orphan")
    parent_trigger = relationship("Trigger", remote_side=[id], backref="dependent_triggers")


class AlertEvent(Base):
    """Individual alert event when a trigger fires or recovers."""
    __tablename__ = "alert_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    trigger_id = Column(GUID(), ForeignKey('triggers.id'), nullable=False)
    device_id = Column(GUID(), ForeignKey('devices.id'), nullable=True)
    status = Column(String(20), nullable=False)  # PROBLEM, OK
    value = Column(DECIMAL(10, 2))  # The metric value that triggered this
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(GUID())
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    trigger = relationship("Trigger", back_populates="alert_events")
    device = relationship("Device")


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


class MaintenanceWindow(Base):
    """Scheduled maintenance window for alert suppression."""
    __tablename__ = "maintenance_windows"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    
    # Time specification
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    recurrence = Column(String(100))  # Cron expression (e.g., "0 2 * * 0") or null for one-time
    
    # Scope: device, hostgroup, or all
    scope_type = Column(String(50), nullable=False, default="all")  # device, hostgroup, all
    device_id = Column(GUID(), ForeignKey('devices.id'), nullable=True)
    hostgroup_id = Column(GUID(), ForeignKey('host_groups.id'), nullable=True)
    
    # Data collection behavior (Zabbix pattern)
    collect_data = Column(Boolean, default=True)  # If False, no metrics collected during window
    
    # Status
    active = Column(Boolean, default=True)
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    device = relationship("Device", foreign_keys=[device_id])
    hostgroup = relationship("HostGroup", foreign_keys=[hostgroup_id])
    creator = relationship("User", foreign_keys=[created_by])


class DiscoveryJob(Base):
    """Network discovery job for scanning IP ranges."""
    __tablename__ = "discovery_jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # IP ranges to scan (CIDR notation, comma-separated)
    ip_ranges = Column(Text, nullable=False)  # e.g., "192.168.1.0/24,10.0.0.0/16"
    
    # Scan methods
    scan_icmp = Column(Boolean, default=True)  # Ping sweep
    scan_snmp = Column(Boolean, default=False)  # SNMP discovery
    snmp_community = Column(String(255))  # SNMP community string (encrypted in production)
    snmp_version = Column(String(10), default="2c")  # 1, 2c, 3
    scan_ports = Column(String(255))  # Comma-separated ports to check
    
    # Schedule
    schedule_type = Column(String(20), default="manual")  # manual, scheduled, recurring
    schedule_cron = Column(String(100))  # Cron expression for recurring
    next_run_at = Column(DateTime(timezone=True))
    
    # Status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    progress_percent = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Auto-add settings
    auto_add_devices = Column(Boolean, default=False)
    auto_add_hostgroup_id = Column(GUID(), ForeignKey('host_groups.id'), nullable=True)
    
    # Metadata
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    auto_add_hostgroup = relationship("HostGroup", foreign_keys=[auto_add_hostgroup_id])
    results = relationship("DiscoveryResult", back_populates="job", cascade="all, delete-orphan")


class DiscoveryResult(Base):
    """Individual discovered host from a discovery job."""
    __tablename__ = "discovery_results"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID(), ForeignKey('discovery_jobs.id'), nullable=False)
    
    # Discovered host info
    ip_address = Column(String(45), nullable=False)  # IPv4 or IPv6
    hostname = Column(String(255))  # Resolved hostname
    mac_address = Column(String(17))  # MAC if available
    
    # Discovery method results
    icmp_reachable = Column(Boolean)
    icmp_latency_ms = Column(Integer)  # Round-trip time
    snmp_reachable = Column(Boolean)
    snmp_sysname = Column(String(255))
    snmp_sysdescr = Column(Text)
    snmp_sysobjectid = Column(String(255))
    
    # Port scan results
    open_ports = Column(String(500))  # JSON: {"22": "ssh", "80": "http"}
    
    # Status
    status = Column(String(20), default="new")  # new, added, ignored, existing
    device_id = Column(GUID(), ForeignKey('devices.id'), nullable=True)  # If added as device
    
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    job = relationship("DiscoveryJob", back_populates="results")
    device = relationship("Device", foreign_keys=[device_id])


class CommandTemplate(Base):
    """Predefined command template for remote execution."""
    __tablename__ = "command_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    
    # Command definition
    command = Column(Text, nullable=False)  # Command with {{variable}} placeholders
    command_type = Column(String(50), default="shell")  # shell, powershell, python, script
    
    # Security
    requires_approval = Column(Boolean, default=True)  # Needs admin approval before execution
    allowed_roles = Column(String(255), default="admin")  # Comma-separated roles
    max_execution_time = Column(Integer, default=300)  # seconds
    
    # Parameters (JSON schema)
    parameters = Column(Text)  # JSON: [{"name": "path", "type": "string", "required": true}]
    
    # Scope restrictions
    allowed_hostgroups = Column(Text)  # Comma-separated hostgroup IDs (null = all)
    
    # Metadata
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("CommandExecution", back_populates="template", cascade="all, delete-orphan")


class CommandExecution(Base):
    """Individual command execution instance."""
    __tablename__ = "command_executions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    template_id = Column(GUID(), ForeignKey('command_templates.id'), nullable=True)
    device_id = Column(GUID(), ForeignKey('devices.id'), nullable=False)
    
    # Execution details
    command = Column(Text, nullable=False)  # Resolved command (placeholders filled)
    parameters = Column(Text)  # JSON: parameters used
    
    # Status tracking
    status = Column(String(20), default="pending")  # pending, approved, running, completed, failed, cancelled
    queued_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Results
    exit_code = Column(Integer)
    stdout = Column(Text)
    stderr = Column(Text)
    
    # Approval workflow
    approved_by = Column(GUID(), ForeignKey('users.id'), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    
    # Source tracking
    source = Column(String(50), default="manual")  # manual, remediation, scheduled
    remediation_rule_id = Column(GUID(), ForeignKey('remediation_rules.id'), nullable=True)
    
    # User tracking
    requested_by = Column(GUID(), ForeignKey('users.id'))
    
    # Relationships
    template = relationship("CommandTemplate", back_populates="executions")
    device = relationship("Device", foreign_keys=[device_id])
    requestor = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])


class RemediationRule(Base):
    """Auto-remediation rule linking triggers to commands."""
    __tablename__ = "remediation_rules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Trigger condition
    trigger_id = Column(GUID(), ForeignKey('triggers.id'), nullable=False)
    
    # Command to execute
    command_template_id = Column(GUID(), ForeignKey('command_templates.id'), nullable=False)
    
    # Execution settings
    enabled = Column(Boolean, default=True)
    auto_approve = Column(Boolean, default=False)  # Skip approval (use with caution!)
    max_executions_per_hour = Column(Integer, default=3)  # Rate limit
    cooldown_minutes = Column(Integer, default=15)  # Wait time between executions
    
    # State tracking
    last_executed_at = Column(DateTime(timezone=True))
    execution_count_hour = Column(Integer, default=0)
    
    # Metadata
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    trigger = relationship("Trigger", foreign_keys=[trigger_id])
    command_template = relationship("CommandTemplate", foreign_keys=[command_template_id])
    creator = relationship("User", foreign_keys=[created_by])
    executions = relationship("CommandExecution", backref="remediation_rule")


class NetworkMap(Base):
    """Network visualization map."""
    __tablename__ = "network_maps"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Appearance
    background_image = Column(Text)  # Base64 or URL
    width = Column(Integer, default=1920)
    height = Column(Integer, default=1080)
    
    # Metadata
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    elements = relationship("MapElement", back_populates="map", cascade="all, delete-orphan")
    links = relationship("MapLink", back_populates="map", cascade="all, delete-orphan")


class MapElement(Base):
    """Node on a network map."""
    __tablename__ = "map_elements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    map_id = Column(GUID(), ForeignKey('network_maps.id'), nullable=False)
    
    # Content
    element_type = Column(String(50))  # device, hostgroup, label, shape
    device_id = Column(GUID(), ForeignKey('devices.id'), nullable=True)
    hostgroup_id = Column(GUID(), ForeignKey('host_groups.id'), nullable=True)
    
    # Display
    label = Column(String(255))
    icon = Column(String(100))  # server, router, switch, cloud, etc.
    
    # Position & Size
    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)
    width = Column(Integer, default=64)
    height = Column(Integer, default=64)
    
    # Extra data (JSON)
    data = Column(Text)
    
    # Relationships
    map = relationship("NetworkMap", back_populates="elements")
    device = relationship("Device", foreign_keys=[device_id])
    hostgroup = relationship("HostGroup", foreign_keys=[hostgroup_id])


class MapLink(Base):
    """Edge/Link between map elements."""
    __tablename__ = "map_links"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    map_id = Column(GUID(), ForeignKey('network_maps.id'), nullable=False)
    
    # Connection
    source_element_id = Column(GUID(), ForeignKey('map_elements.id'), nullable=False)
    target_element_id = Column(GUID(), ForeignKey('map_elements.id'), nullable=False)
    
    # Style
    link_type = Column(String(50), default="network")  # network, dependency
    color = Column(String(20), default="#666666")
    width = Column(Integer, default=2)
    label = Column(String(255))
    
    # Relationships
    map = relationship("NetworkMap", back_populates="links")
    source_element = relationship("MapElement", foreign_keys=[source_element_id])
    target_element = relationship("MapElement", foreign_keys=[target_element_id])


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

