from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)

    users = db.relationship('User', back_populates='role', lazy='dynamic')

    def __repr__(self):
        return f"<Role {self.name}>"


class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)

    users = db.relationship('User', back_populates='department', lazy='dynamic')

    def __repr__(self):
        return f"<Department {self.code}: {self.name}>"


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    campus_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False, index=True)
    designation_or_year = db.Column(db.String(50), nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)
    profile_photo = db.Column(db.String(255), nullable=True)
    force_password_change = db.Column(db.Boolean, default=False, nullable=False)
    temp_password_hash = db.Column(db.String(255), nullable=True)
    temp_password_expires_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    role = db.relationship('Role', back_populates='users')
    department = db.relationship('Department', back_populates='users')
    reported_items = db.relationship('Item', back_populates='reporter', lazy='dynamic', cascade='all, delete-orphan')
    claims = db.relationship('Claim', foreign_keys='Claim.claimant_id', back_populates='claimant', lazy='dynamic')
    reviewed_claims = db.relationship('Claim', foreign_keys='Claim.reviewer_id', back_populates='reviewer', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def must_change_password(self) -> bool:
        return self.force_password_change

    @must_change_password.setter
    def must_change_password(self, value: bool):
        self.force_password_change = value

    def set_temp_password(self, temp_password: str, expires_in_minutes: int = 15):
        """Set securely hashed temporary password, 15m expiration, and invalidate standard password."""
        self.temp_password_hash = generate_password_hash(temp_password)
        self.temp_password_expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
        self.force_password_change = True
        self.password_hash = "INVALIDATED_BY_ADMIN_RESET"

    def verify_temp_password(self, temp_password: str) -> tuple[bool, str]:
        """Verify temporary password validity and expiration."""
        if not self.temp_password_hash or not self.temp_password_expires_at:
            return False, "No active temporary password found."
        now = datetime.now(timezone.utc)
        expires_at = self.temp_password_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            return False, "Temporary password has expired."
        if not check_password_hash(self.temp_password_hash, temp_password):
            return False, "Invalid temporary password."
        return True, "Valid"

    def clear_temp_password(self):
        """Clear temporary password state upon successful permanent password change."""
        self.temp_password_hash = None
        self.temp_password_expires_at = None
        self.force_password_change = False

    def has_role(self, *role_names) -> bool:
        if not self.role:
            return False
        return self.role.name in role_names

    @property
    def is_admin(self) -> bool:
        return self.has_role('admin')

    @property
    def is_staff(self) -> bool:
        return self.has_role('staff')

    @property
    def is_student(self) -> bool:
        return self.has_role('student')

    @property
    def profile_photo_url(self) -> str:
        """Returns web URL for avatar (supports local upload path or Cloudinary URL)."""
        if not self.profile_photo:
            return "/static/images/default-avatar.svg"
        if self.profile_photo.startswith('http://') or self.profile_photo.startswith('https://'):
            return self.profile_photo
        return f"/static/uploads/{self.profile_photo}"

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'campus_id': self.campus_id,
            'role': self.role.name if self.role else None,
            'department': self.department.name if self.department else None,
            'designation_or_year': self.designation_or_year,
            'is_active': self.is_active,
            'is_approved': self.is_approved,
            'profile_photo': self.profile_photo,
            'force_password_change': self.force_password_change,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f"<User {self.email} ({self.campus_id})>"
