from datetime import datetime, timezone
from app.extensions import db


class ItemCategory(db.Model):
    __tablename__ = 'item_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(50), default='bi-tag', nullable=False)

    items = db.relationship('Item', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f"<ItemCategory {self.name}>"


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False, index=True)
    item_type = db.Column(db.String(10), nullable=False, index=True)  # 'LOST' or 'FOUND'
    description = db.Column(db.Text, nullable=False)
    
    # Private identifying details (not shown to general public on found items)
    identifying_features = db.Column(db.Text, nullable=True)
    
    location = db.Column(db.String(150), nullable=False, index=True)
    incident_date = db.Column(db.Date, nullable=False, index=True)
    incident_time = db.Column(db.Time, nullable=True)
    
    contact_preference = db.Column(db.String(20), default='IN_APP', nullable=False)  # 'IN_APP', 'EMAIL', 'PHONE'
    status = db.Column(db.String(20), default='OPEN', nullable=False, index=True)  # 'OPEN', 'CLAIM_PENDING', 'RETURNED', 'CLOSED', 'FLAGGED'
    
    category_id = db.Column(db.Integer, db.ForeignKey('item_categories.id'), nullable=False, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    flagged_reason = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    category = db.relationship('ItemCategory', back_populates='items')
    reporter = db.relationship('User', back_populates='reported_items')
    images = db.relationship('ItemImage', back_populates='item', cascade='all, delete-orphan', lazy='joined')
    claims = db.relationship('Claim', back_populates='item', cascade='all, delete-orphan', lazy='dynamic')

    @property
    def primary_image(self):
        if self.images:
            for img in self.images:
                if img.is_primary:
                    return img.filename
            return self.images[0].filename
        return None

    @property
    def primary_image_url(self):
        """Returns direct web URL (works for both local static uploads and Cloudinary URLs)."""
        img_name = self.primary_image
        if not img_name:
            return None
        if img_name.startswith('http://') or img_name.startswith('https://'):
            return img_name
        return f"/static/uploads/{img_name}"

    @property
    def is_lost(self) -> bool:
        return self.item_type == 'LOST'

    @property
    def is_found(self) -> bool:
        return self.item_type == 'FOUND'

    @property
    def is_open(self) -> bool:
        return self.status == 'OPEN'

    @property
    def is_returned(self) -> bool:
        return self.status == 'RETURNED'

    def __repr__(self):
        return f"<Item {self.id}: [{self.item_type}] {self.title}>"


class ItemImage(db.Model):
    __tablename__ = 'item_images'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    item = db.relationship('Item', back_populates='images')

    def __repr__(self):
        return f"<ItemImage {self.filename} for Item {self.item_id}>"
