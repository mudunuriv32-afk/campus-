from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link_url = db.Column(db.String(255), nullable=True)
    notification_type = db.Column(db.String(40), default='GENERAL', nullable=False)
    # Types: 'CLAIM_SUBMITTED', 'CLAIM_APPROVED', 'CLAIM_REJECTED', 'ITEM_CLOSED', 'ANNOUNCEMENT'
    
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = db.relationship('User', back_populates='notifications')

    def mark_read(self):
        self.is_read = True

    def __repr__(self):
        return f"<Notification {self.id} for User {self.user_id} - Read: {self.is_read}>"
