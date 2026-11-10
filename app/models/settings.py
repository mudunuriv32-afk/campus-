from datetime import datetime, timezone
from app.extensions import db


class PlatformSetting(db.Model):
    __tablename__ = 'platform_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @classmethod
    def get(cls, key: str, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key: str, value: str, description=None):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=value, description=description)
            db.session.add(setting)
        else:
            setting.value = value
            if description:
                setting.description = description
        return setting

    def __repr__(self):
        return f"<PlatformSetting {self.key}={self.value}>"
