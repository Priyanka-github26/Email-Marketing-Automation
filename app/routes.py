
from flask import Blueprint, render_template, request, redirect, url_for, flash
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
    return render_template("dashboard.html", user=current_user)

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

        subscriber.name = name or None
        subscriber.email = email

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

    return render_template(
        "campaigns.html",
        campaigns=campaigns
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
        status="active"
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
                status="active"
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
