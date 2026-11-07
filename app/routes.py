from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from html.parser import HTMLParser
from html import escape
import csv
import io
from flask_login import login_required, current_user
from flask_mail import Message
from app import db, mail
from datetime import datetime
from app.models import (
    Subscriber,
    EmailTemplate,
    Campaign,
    SequenceEmail,
    CampaignRecipient,
    CampaignOpen,
    CampaignClick,
    CampaignConversion
)

main = Blueprint("main", __name__)


@main.route("/dashboard")
@login_required
def dashboard():

    campaigns = Campaign.query.filter_by(
        user_id=current_user.id
    ).all()

    total_campaigns = len(campaigns)

    total_sent = CampaignRecipient.query.join(
        Campaign,
        CampaignRecipient.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id,
        CampaignRecipient.status == "sent"
    ).count()

    total_opens = CampaignOpen.query.join(
        Campaign,
        CampaignOpen.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id
    ).count()

    total_clicks = CampaignClick.query.join(
        Campaign,
        CampaignClick.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id
    ).count()

    unique_opens = CampaignOpen.query.join(
        Campaign,
        CampaignOpen.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id
    ).with_entities(
        CampaignOpen.campaign_id,
        CampaignOpen.subscriber_id
    ).distinct().count()

    unique_clickers = CampaignClick.query.join(
        Campaign,
        CampaignClick.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id
    ).with_entities(
        CampaignClick.campaign_id,
        CampaignClick.subscriber_id
    ).distinct().count()

    total_conversions = CampaignConversion.query.join(
        Campaign,
        CampaignConversion.campaign_id == Campaign.id
    ).filter(
        Campaign.user_id == current_user.id
    ).count()

    open_rate = (
        (unique_opens / total_sent) * 100
        if total_sent > 0 else 0
    )

    click_rate = (
        (unique_clickers / total_sent) * 100
        if total_sent > 0 else 0
    )

    return render_template(
        "dashboard.html",
        user=current_user,
        total_campaigns=total_campaigns,
        total_sent=total_sent,
        total_opens=total_opens,
        total_clicks=total_clicks,
        total_conversions=total_conversions,
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2)
    )

@main.route("/analytics")
@login_required
def analytics():

    campaigns = Campaign.query.filter_by(
        user_id=current_user.id
    ).order_by(Campaign.created_at.desc()).all()

    campaign_analytics = []

    for campaign in campaigns:

        sent = CampaignRecipient.query.filter_by(
            campaign_id=campaign.id,
            status="sent"
        ).count()

        opens = CampaignOpen.query.filter_by(
            campaign_id=campaign.id
        ).with_entities(
            CampaignOpen.subscriber_id
        ).distinct().count()

        clicks = CampaignClick.query.filter_by(
            campaign_id=campaign.id
        ).with_entities(
            CampaignClick.subscriber_id
        ).distinct().count()

        conversions = CampaignConversion.query.filter_by(
            campaign_id=campaign.id
        ).count()

        open_rate = (opens / sent * 100) if sent else 0
        click_rate = (clicks / sent * 100) if sent else 0

        campaign_analytics.append({
            "name": campaign.name,
            "status": campaign.status,
            "sent": sent,
            "opens": opens,
            "clicks": clicks,
            "conversions": conversions,
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2)
        })

    return render_template(
        "analytics.html",
        campaigns=campaign_analytics
    )

@main.route("/subscribers")
@login_required
def subscribers():
    subscriber_list = Subscriber.query.filter_by(
        user_id=current_user.id
    ).order_by(Subscriber.id.desc()).all()

    return render_template(
        "subscribers.html",
        subscribers=subscriber_list
    )

@main.route("/subscribers/add", methods=["GET", "POST"])
@login_required
def add_subscriber():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        # Check email consent
        email_consent = request.form.get("email_consent") == "yes"

        if not email:
            flash("Email address is required.", "danger")
            return redirect(url_for("main.add_subscriber"))

        existing_subscriber = Subscriber.query.filter_by(
            user_id=current_user.id,
            email=email
        ).first()

        if existing_subscriber:
            flash("This email is already in your subscriber list.", "danger")
            return redirect(url_for("main.add_subscriber"))

        new_subscriber = Subscriber(
            user_id=current_user.id,
            name=name or None,
            email=email,
            status="active",
            email_consent=email_consent,
            consent_at=datetime.utcnow() if email_consent else None
        )

        db.session.add(new_subscriber)
        db.session.commit()

        flash("Subscriber added successfully!", "success")
        return redirect(url_for("main.subscribers"))

    return render_template("add_subscriber.html")


# ==============================
# EDIT SUBSCRIBER
# ==============================


@main.route("/subscribers/edit/<int:subscriber_id>", methods=["GET", "POST"])
@login_required
def edit_subscriber(subscriber_id):

    subscriber = Subscriber.query.filter_by(
        id=subscriber_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()

        # Read consent checkbox
        email_consent = request.form.get("email_consent") == "yes"

        if not email:
            flash("Email address is required.", "danger")
            return redirect(url_for(
                "main.edit_subscriber",
                subscriber_id=subscriber.id
            ))

        duplicate = Subscriber.query.filter(
            Subscriber.user_id == current_user.id,
            Subscriber.email == email,
            Subscriber.id != subscriber.id
        ).first()

        if duplicate:
            flash("This email is already registered.", "danger")
            return redirect(url_for(
                "main.edit_subscriber",
                subscriber_id=subscriber.id
            ))

        # Update subscriber details
        subscriber.name = name or None
        subscriber.email = email

        # Update email marketing consent
        if email_consent and not subscriber.email_consent:
            subscriber.email_consent = True
            subscriber.consent_at = datetime.utcnow()

        elif not email_consent:
            subscriber.email_consent = False
            subscriber.consent_at = None

        db.session.commit()

        flash("Subscriber updated successfully!", "success")
        return redirect(url_for("main.subscribers"))

    return render_template(
        "edit_subscriber.html",
        subscriber=subscriber
    )


# ==============================
# DELETE SUBSCRIBER
# ==============================

@main.route("/subscribers/delete/<int:subscriber_id>", methods=["POST"])
@login_required
def delete_subscriber(subscriber_id):
    subscriber = Subscriber.query.filter_by(
        id=subscriber_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(subscriber)
    db.session.commit()

    flash("Subscriber deleted successfully!", "success")
    return redirect(url_for("main.subscribers"))


# ==============================
# IMPORT SUBSCRIBERS
# ==============================

@main.route("/subscribers/import", methods=["GET", "POST"])
@login_required
def import_subscribers():

    if request.method == "POST":
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("Please select a CSV file.", "danger")
            return redirect(url_for("main.import_subscribers"))

        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are allowed.", "danger")
            return redirect(url_for("main.import_subscribers"))

        try:
            content = file.stream.read().decode("utf-8-sig")
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)

            if not reader.fieldnames or not {"name", "email"}.issubset(
                {field.strip().lower() for field in reader.fieldnames}
            ):
                flash("CSV must contain name and email columns.", "danger")
                return redirect(url_for("main.import_subscribers"))

            added = 0
            skipped = 0

            for row in reader:
                normalized_row = {
                    (key.strip().lower() if key else ""): value
                    for key, value in row.items()
                }

                name = (normalized_row.get("name") or "").strip()
                email = (normalized_row.get("email") or "").strip().lower()

                if not email or "@" not in email:
                    skipped += 1
                    continue

                existing = Subscriber.query.filter_by(
                    user_id=current_user.id,
                    email=email
                ).first()

                if existing:
                    skipped += 1
                    continue

                subscriber = Subscriber(
                    user_id=current_user.id,
                    name=name or None,
                    email=email,
                    status="active",
                    email_consent=False,
                    consent_at=None
                )

                db.session.add(subscriber)
                added += 1

            db.session.commit()

            flash(
                f"Import completed! Added: {added}, Skipped: {skipped}",
                "success"
            )

            return redirect(url_for("main.subscribers"))

        except (UnicodeDecodeError, csv.Error):
            db.session.rollback()
            flash("Invalid CSV file. Please check its format.", "danger")
            return redirect(url_for("main.import_subscribers"))

        except Exception:
            db.session.rollback()
            flash(
                "Import failed. Please check your CSV file and try again.",
                "danger"
            )
            return redirect(url_for("main.import_subscribers"))

    return render_template("import_subscribers.html")


# ==============================
# SECURE UNSUBSCRIBE
# ==============================

@main.route("/unsubscribe/<string:token>", methods=["GET", "POST"])
def unsubscribe(token):

    subscriber = Subscriber.query.filter_by(
        unsubscribe_token=token
    ).first_or_404()

    if request.method == "POST":

        if subscriber.status != "unsubscribed":
            subscriber.email_consent = False
            subscriber.status = "unsubscribed"
            subscriber.unsubscribed_at = datetime.utcnow()

            db.session.commit()

        return render_template("unsubscribe_success.html")

    return render_template(
        "unsubscribe.html",
        subscriber=subscriber
    )


# ==============================
# EMAIL TEMPLATE MANAGEMENT
# ==============================

@main.route("/templates")
@login_required
def email_templates():

    templates = EmailTemplate.query.filter_by(
        user_id=current_user.id
    ).order_by(EmailTemplate.id.desc()).all()

    return render_template(
        "email_templates.html",
        templates=templates
    )


@main.route("/templates/add", methods=["GET", "POST"])
@login_required
def add_email_template():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not name or not subject or not body:
            flash("All fields are required.", "danger")
            return redirect(url_for("main.add_email_template"))

        new_template = EmailTemplate(
            user_id=current_user.id,
            name=name,
            subject=subject,
            body=body
        )

        db.session.add(new_template)
        db.session.commit()

        flash("Email template created successfully!", "success")

        return redirect(url_for("main.email_templates"))

    return render_template("add_email_template.html")


@main.route("/templates/edit/<int:template_id>", methods=["GET", "POST"])
@login_required
def edit_email_template(template_id):

    template = EmailTemplate.query.filter_by(
        id=template_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        if not name or not subject or not body:
            flash("All fields are required.", "danger")
            return redirect(url_for(
                "main.edit_email_template",
                template_id=template.id
            ))

        template.name = name
        template.subject = subject
        template.body = body

        db.session.commit()

        flash("Email template updated successfully!", "success")

        return redirect(url_for("main.email_templates"))

    return render_template(
        "edit_email_template.html",
        template=template
    )


@main.route("/templates/delete/<int:template_id>", methods=["POST"])
@login_required
def delete_email_template(template_id):

    template = EmailTemplate.query.filter_by(
        id=template_id,
        user_id=current_user.id
    ).first_or_404()

    # Prevent deleting templates used by campaigns or sequences
    if Campaign.query.filter_by(template_id=template.id).first() or \
       SequenceEmail.query.filter_by(template_id=template.id).first():

        flash(
            "This template is being used. Remove its campaign or sequence references first.",
            "warning"
        )
        return redirect(url_for("main.email_templates"))

    db.session.delete(template)
    db.session.commit()

    flash("Email template deleted successfully!", "success")

    return redirect(url_for("main.email_templates"))

# ==============================
# CAMPAIGN MANAGEMENT
# ==============================

@main.route("/campaigns")
@login_required
def campaigns():

    campaigns = Campaign.query.filter_by(
        user_id=current_user.id
    ).order_by(Campaign.id.desc()).all()

    campaign_open_counts = {}

    for campaign in campaigns:

        open_count = CampaignOpen.query.filter_by(
            campaign_id=campaign.id
        ).count()

        campaign_open_counts[campaign.id] = open_count

    return render_template(
        "campaigns.html",
        campaigns=campaigns,
        campaign_open_counts=campaign_open_counts
    )

@main.route("/campaigns/add", methods=["GET", "POST"])
@login_required
def add_campaign():

    templates = EmailTemplate.query.filter_by(
        user_id=current_user.id
    ).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        subject = request.form.get("subject", "").strip()
        template_id = request.form.get("template_id")

        if not name or not subject:
            flash("Campaign name and subject are required.", "danger")
            return redirect(url_for("main.add_campaign"))

        selected_template = None

        if template_id:
            selected_template = EmailTemplate.query.filter_by(
                id=template_id,
                user_id=current_user.id
            ).first()

            if not selected_template:
                flash("Invalid email template selected.", "danger")
                return redirect(url_for("main.add_campaign"))

        new_campaign = Campaign(
            user_id=current_user.id,
            name=name,
            subject=subject,
            template_id=selected_template.id if selected_template else None,
            status="draft"
        )

        db.session.add(new_campaign)
        db.session.commit()

        flash("Campaign created successfully!", "success")

        return redirect(url_for("main.campaigns"))

    return render_template(
        "add_campaign.html",
        templates=templates
    )
    
@main.route("/campaigns/edit/<int:campaign_id>", methods=["GET", "POST"])
@login_required
def edit_campaign(campaign_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        user_id=current_user.id
    ).first_or_404()

    templates = EmailTemplate.query.filter_by(
        user_id=current_user.id
    ).all()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        subject = request.form.get("subject", "").strip()
        template_id = request.form.get("template_id")

        if not name or not subject:
            flash("Campaign name and subject are required.", "danger")
            return redirect(url_for(
                "main.edit_campaign",
                campaign_id=campaign.id
            ))

        selected_template = None

        if template_id:
            selected_template = EmailTemplate.query.filter_by(
                id=template_id,
                user_id=current_user.id
            ).first()

            if not selected_template:
                flash("Invalid email template selected.", "danger")
                return redirect(url_for(
                    "main.edit_campaign",
                    campaign_id=campaign.id
                ))

        campaign.name = name
        campaign.subject = subject
        campaign.template_id = (
            selected_template.id if selected_template else None
        )

        db.session.commit()

        flash("Campaign updated successfully!", "success")
        return redirect(url_for("main.campaigns"))

    return render_template(
        "edit_campaign.html",
        campaign=campaign,
        templates=templates
    )

@main.route("/campaigns/delete/<int:campaign_id>", methods=["POST"])
@login_required
def delete_campaign(campaign_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        # Delete campaign tracking records first
        CampaignOpen.query.filter_by(
            campaign_id=campaign.id
        ).delete(synchronize_session=False)

        CampaignClick.query.filter_by(
            campaign_id=campaign.id
        ).delete(synchronize_session=False)

        CampaignConversion.query.filter_by(
            campaign_id=campaign.id
        ).delete(synchronize_session=False)

        CampaignRecipient.query.filter_by(
            campaign_id=campaign.id
        ).delete(synchronize_session=False)

        # Delete campaign
        db.session.delete(campaign)
        db.session.commit()

        flash("Campaign deleted successfully!", "success")

    except Exception as e:
        db.session.rollback()
        print("Campaign Delete Error:", e)
        flash("Unable to delete campaign.", "danger")

    return redirect(url_for("main.campaigns"))    
    
@main.route("/campaigns/recipients/<int:campaign_id>", methods=["GET", "POST"])
@login_required
def manage_campaign_recipients(campaign_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        user_id=current_user.id
    ).first_or_404()

    subscribers = Subscriber.query.filter_by(
        user_id=current_user.id,
        status="active",
        email_consent=True
    ).order_by(Subscriber.id.desc()).all()

    if request.method == "POST":

        selected_ids = request.form.getlist("subscriber_ids")

        CampaignRecipient.query.filter_by(
            campaign_id=campaign.id
        ).delete(synchronize_session=False)

        added = 0

        for subscriber_id in selected_ids:

            subscriber = Subscriber.query.filter_by(
                id=subscriber_id,
                user_id=current_user.id,
                status="active",
                email_consent=True
            ).first()

            if subscriber:
                recipient = CampaignRecipient(
                    campaign_id=campaign.id,
                    subscriber_id=subscriber.id,
                    status="pending"
                )

                db.session.add(recipient)
                added += 1

        db.session.commit()

        flash(
            f"{added} campaign recipients selected successfully!",
            "success"
        )

        return redirect(url_for("main.campaigns"))

    selected_ids = [
        recipient.subscriber_id
        for recipient in CampaignRecipient.query.filter_by(
            campaign_id=campaign.id
        ).all()
    ]

    return render_template(
        "campaign_recipients.html",
        campaign=campaign,
        subscribers=subscribers,
        selected_ids=selected_ids
    )    

# ==============================
# SEND EMAIL CAMPAIGN
# ==============================

class EmailLinkTracker(HTMLParser):

    def __init__(self, campaign_id, subscriber_id):
        super().__init__(convert_charrefs=False)
        self.campaign_id = campaign_id
        self.subscriber_id = subscriber_id
        self.result = ""

    def handle_starttag(self, tag, attrs):

        updated_attrs = []

        for name, value in attrs:

            if tag.lower() == "a" and name.lower() == "href" and value:
                value = url_for(
                    "main.track_email_click",
                    campaign_id=self.campaign_id,
                    subscriber_id=self.subscriber_id,
                    url=value,
                    _external=True
                )

            updated_attrs.append((name, value))

        attrs_text = "".join(
            f' {name}="{escape(value or "", quote=True)}"'
            for name, value in updated_attrs
        )

        self.result += f"<{tag}{attrs_text}>"

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.result = self.result[:-1] + " />"

    def handle_endtag(self, tag):
        self.result += f"</{tag}>"

    def handle_data(self, data):
        self.result += data

    def handle_entityref(self, name):
        self.result += f"&{name};"

    def handle_charref(self, name):
        self.result += f"&#{name};"

    def handle_comment(self, data):
        self.result += f"<!--{data}-->"

@main.route("/test-link-tracking")
@login_required
def test_link_tracking():

    tracker = EmailLinkTracker(5, 12)

    tracker.feed(
        '<a href="https://www.google.com">Visit Google</a>'
    )

    return f"""
    <h3>Tracking Test</h3>
    <p>{tracker.result}</p>
    """

@main.route("/campaigns/send/<int:campaign_id>", methods=["POST"])
@login_required
def send_campaign(campaign_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        user_id=current_user.id
    ).first_or_404()

    if campaign.status == "sent":
        flash("This campaign has already been completed.", "warning")
        return redirect(url_for("main.campaigns"))

    if not campaign.template_id:
        flash("Please select an email template first.", "danger")
        return redirect(url_for("main.campaigns"))

    email_template = EmailTemplate.query.filter_by(
        id=campaign.template_id,
        user_id=current_user.id
    ).first()

    if not email_template:
        flash("Email template not found.", "danger")
        return redirect(url_for("main.campaigns"))

    # Process pending and previously failed recipients only
    recipients = CampaignRecipient.query.filter(
        CampaignRecipient.campaign_id == campaign.id,
        CampaignRecipient.status.in_(["pending", "failed"])
    ).all()

    if not recipients:
        flash("No pending or failed recipients available.", "warning")
        return redirect(url_for("main.campaigns"))

    sent_count = 0
    failed_count = 0
    skipped_count = 0

    for recipient in recipients:

        subscriber = Subscriber.query.filter_by(
            id=recipient.subscriber_id,
            user_id=current_user.id,
            status="active",
            email_consent=True
        ).first()

        if not subscriber:
            recipient.status = "skipped"
            skipped_count += 1
            continue

        unsubscribe_url = url_for(
            "main.unsubscribe",
            token=subscriber.unsubscribe_token,
            _external=True
        )

        tracking_url = url_for(
            "main.track_email_open",
            campaign_id=campaign.id,
            subscriber_id=subscriber.id,
            _external=True
        )

        # Convert template links into click-tracking links
        link_tracker = EmailLinkTracker(
            campaign.id,
            subscriber.id
        )

        link_tracker.feed(email_template.body)
        tracked_template_body = link_tracker.result

        email_body = f"""
<html>
<body>

    {tracked_template_body}

    <hr>

    <p style="font-size:12px;color:gray;">
        You received this email because you agreed to receive
        marketing emails from us.
    </p>

    <p>
        <a href="{unsubscribe_url}">Unsubscribe</a>
    </p>

    <img
        src="{tracking_url}"
        width="1"
        height="1"
        alt=""
        style="display:none;"
    >

</body>
</html>
"""

        try:
            message = Message(
                subject=campaign.subject,
                recipients=[subscriber.email],
                html=email_body
            )

            mail.send(message)

            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            sent_count += 1

        except Exception:

            recipient.status = "failed"
            failed_count += 1

            current_app.logger.exception(
                "Campaign email failed for subscriber %s",
                subscriber.id
            )

    # Count all successful deliveries
    total_sent = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="sent"
    ).count()

    remaining_failed = CampaignRecipient.query.filter_by(
        campaign_id=campaign.id,
        status="failed"
    ).count()

    if remaining_failed > 0:
        campaign.status = (
            "partially_sent" if total_sent > 0 else "failed"
        )
    else:
        campaign.status = "sent"

    if total_sent > 0 and not campaign.sent_at:
        campaign.sent_at = datetime.utcnow()

    db.session.commit()

    flash(
        f"Campaign processing completed! "
        f"Sent: {sent_count}, Failed: {failed_count}, "
        f"Skipped: {skipped_count}",
        "success" if failed_count == 0 else "warning"
    )

    return redirect(url_for("main.campaigns"))

  
  
# ==============================
# SEND TEST CAMPAIGN EMAIL
# ==============================

@main.route("/campaigns/test/<int:campaign_id>", methods=["POST"])
@login_required
def send_test_campaign_email(campaign_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        user_id=current_user.id
    ).first_or_404()

    if not campaign.template_id:
        flash("Please select an email template first.", "danger")
        return redirect(url_for("main.campaigns"))

    email_template = EmailTemplate.query.filter_by(
        id=campaign.template_id,
        user_id=current_user.id
    ).first()

    if not email_template:
        flash("Email template not found.", "danger")
        return redirect(url_for("main.campaigns"))

    test_email = current_app.config.get("MAIL_USERNAME")

    if not test_email:
        flash("Test email address is not configured.", "danger")
        return redirect(url_for("main.campaigns"))

    email_body = f"""
    <html>
    <body>
        <h3>TEST EMAIL</h3>

        <p>This is a test email for your campaign.</p>

        <hr>

        {email_template.body}

        <hr>

        <p style="color:gray;font-size:12px;">
            This is a test message. It was not sent to your subscribers.
        </p>
    </body>
    </html>
    """

    try:
        message = Message(
            subject=f"[TEST] {campaign.subject}",
            recipients=[test_email],
            html=email_body
        )

        mail.send(message)

        flash(
            "Test email sent successfully to your configured Gmail address!",
            "success"
        )

    except Exception:
        current_app.logger.exception("Test campaign email failed")
        flash("Unable to send test email. Check the application logs.", "danger")

    return redirect(url_for("main.campaigns"))

@main.route("/test-email", methods=["GET", "POST"])
@login_required
def test_email():

    if request.method == "POST":

        recipient = request.form.get("email", "").strip()

        if not recipient:
            flash("Please enter an email address.", "danger")

        else:
            try:
                msg = Message(
                    subject="Email Marketing Automation - Test Email",
                    recipients=[recipient],
                    body="Congratulations! Your email configuration is working successfully."
                )

                mail.send(msg)

                flash("Test email sent successfully!", "success")

            except Exception as e:
                import traceback
                traceback.print_exc()
                flash(f"Email sending failed: {str(e)}", "danger")
        
        return redirect(url_for("main.test_email"))

    return render_template("test_email.html")

# ==============================
# EMAIL OPEN TRACKING
# ==============================

@main.route("/track/open/<int:campaign_id>/<int:subscriber_id>")
def track_email_open(campaign_id, subscriber_id):

    campaign = Campaign.query.filter_by(
        id=campaign_id
    ).first()

    subscriber = Subscriber.query.filter_by(
        id=subscriber_id
    ).first()

    if campaign and subscriber:

        existing_open = CampaignOpen.query.filter_by(
            campaign_id=campaign_id,
            subscriber_id=subscriber_id
        ).first()

        if not existing_open:
            new_open = CampaignOpen(
                campaign_id=campaign_id,
                subscriber_id=subscriber_id
            )

            db.session.add(new_open)
            db.session.commit()

    # Return a transparent 1x1 tracking pixel
    from flask import Response

    pixel = (
        b"\x47\x49\x46\x38\x39\x61"
        b"\x01\x00\x01\x00"
        b"\x80\x00\x00"
        b"\x00\x00\x00\xff\xff\xff"
        b"\x21\xf9\x04\x01\x00\x00\x00\x00"
        b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00"
        b"\x00\x02\x02\x44\x01\x00\x3b"
    )

    return Response(
        pixel,
        mimetype="image/gif",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )
    

# ==============================
# EMAIL CLICK TRACKING
# ==============================

@main.route("/track/click/<int:campaign_id>/<int:subscriber_id>")
def track_email_click(campaign_id, subscriber_id):

    from flask import abort
    from urllib.parse import urlparse

    campaign = Campaign.query.filter_by(
        id=campaign_id
    ).first()

    subscriber = Subscriber.query.filter_by(
        id=subscriber_id
    ).first()

    if not campaign or not subscriber:
        abort(404)

    # Verify subscriber belongs to campaign owner
    if campaign.user_id != subscriber.user_id:
        abort(403)

    target_url = request.args.get("url", "").strip()

    parsed_url = urlparse(target_url)

    if (
        parsed_url.scheme not in ("http", "https")
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
    ):
        abort(400)

    new_click = CampaignClick(
        campaign_id=campaign_id,
        subscriber_id=subscriber_id,
        link_url=target_url
    )

    db.session.add(new_click)
    db.session.commit()

    return redirect(target_url)
