from datetime import datetime
from flask_login import UserMixin
from app import db
import secrets

# User Account
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Subscriber
class Subscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default="active")

    # Email marketing consent
    email_consent = db.Column(db.Boolean, default=False, nullable=False)
    consent_at = db.Column(db.DateTime, nullable=True)
    unsubscribed_at = db.Column(db.DateTime, nullable=True)

    # Secure unsubscribe token
    unsubscribe_token = db.Column(
        db.String(64),
        unique=True,
        nullable=True,
        default=lambda: secrets.token_urlsafe(32)
    )

    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)

# Segment
class Segment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)


# Subscriber-Segment relationship
subscriber_segments = db.Table(
    "subscriber_segments",
    db.Column("subscriber_id", db.Integer,
              db.ForeignKey("subscriber.id"), primary_key=True),
    db.Column("segment_id", db.Integer,
              db.ForeignKey("segment.id"), primary_key=True)
)


# Email Template
class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Campaign
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("email_template.id"))
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="draft")
    scheduled_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Campaign Recipients
class CampaignRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("subscriber.id"), nullable=False)
    status = db.Column(db.String(30), default="pending")
    sent_at = db.Column(db.DateTime)


# Email Opens
class CampaignOpen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("subscriber.id"), nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)


# Email Clicks
class CampaignClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("subscriber.id"), nullable=False)
    link_url = db.Column(db.Text, nullable=False)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)


# Conversions
class CampaignConversion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaign.id"), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey("subscriber.id"), nullable=False)
    conversion_value = db.Column(db.Float, default=0.0)
    converted_at = db.Column(db.DateTime, default=datetime.utcnow)


# Automation Sequence
class AutomationSequence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    trigger_event = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Emails inside an automation sequence
class SequenceEmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey("automation_sequence.id"), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey("email_template.id"))
    delay_hours = db.Column(db.Integer, default=0)
    sequence_order = db.Column(db.Integer, default=1)
