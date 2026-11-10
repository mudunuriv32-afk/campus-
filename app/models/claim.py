from datetime import datetime, timezone
from app.extensions import db


class Claim(db.Model):
    __tablename__ = 'claims'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    claim_description = db.Column(db.Text, nullable=False)
    verification_details = db.Column(db.Text, nullable=False)
    proof_image = db.Column(db.String(255), nullable=True)
    
    status = db.Column(db.String(20), default='PENDING', nullable=False, index=True)  # 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'
    
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    review_remarks = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    item = db.relationship('Item', back_populates='claims')
    claimant = db.relationship('User', foreign_keys=[claimant_id], back_populates='claims')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], back_populates='reviewed_claims')

    __table_args__ = (
        db.Index('idx_claim_item_claimant_status', 'item_id', 'claimant_id', 'status'),
    )

    @property
    def is_pending(self) -> bool:
        return self.status == 'PENDING'

    @property
    def is_approved(self) -> bool:
        return self.status == 'APPROVED'

    @property
    def is_rejected(self) -> bool:
        return self.status == 'REJECTED'

    def __repr__(self):
        return f"<Claim {self.id} on Item {self.item_id} by User {self.claimant_id} [{self.status}]>"
