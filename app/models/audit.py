from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    
    action = db.Column(db.String(100), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=True)  # 'User', 'Item', 'Claim', 'Setting'
    target_id = db.Column(db.Integer, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    details = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = db.relationship('User', back_populates='audit_logs')

    @classmethod
    def log(cls, action: str, user_id=None, target_type=None, target_id=None, ip_address=None, details=None):
        entry = cls(
            action=action,
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            ip_address=ip_address,
            details=details
        )
        db.session.add(entry)
        return entry

    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} by User {self.user_id}>"
