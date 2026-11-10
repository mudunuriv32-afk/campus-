from datetime import datetime, timezone
from app.extensions import db


class PasswordResetRecord(db.Model):
    __tablename__ = 'password_reset_records'

    id = db.Column(db.Integer, primary_key=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reset_timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE', nullable=False)  # ACTIVE, COMPLETED, EXPIRED, SUPERSEDED
    completed_at = db.Column(db.DateTime, nullable=True)

    target_user = db.relationship('User', foreign_keys=[target_user_id], backref=db.backref('reset_records', lazy='dynamic'))
    admin = db.relationship('User', foreign_keys=[admin_id], backref=db.backref('initiated_resets', lazy='dynamic'))

    @property
    def is_expired(self) -> bool:
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    def to_dict(self):
        return {
            'id': self.id,
            'target_user_id': self.target_user_id,
            'target_user_name': self.target_user.full_name if self.target_user else None,
            'target_campus_id': self.target_user.campus_id if self.target_user else None,
            'admin_id': self.admin_id,
            'admin_name': self.admin.full_name if self.admin else None,
            'reset_timestamp': self.reset_timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'status': self.status,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f"<PasswordResetRecord #{self.id} for User {self.target_user_id} Status: {self.status}>"
