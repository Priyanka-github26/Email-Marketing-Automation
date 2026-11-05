
from flask import Blueprint, render_template, request, redirect, url_for, flash
import csv
import io
from flask_login import login_required, current_user
from app import db
from app.models import Subscriber, EmailTemplate, Campaign, SequenceEmail

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
            status="active"
        )

        db.session.add(new_subscriber)
        db.session.commit()

        flash("Subscriber added successfully!", "success")
        return redirect(url_for("main.subscribers"))

    return render_template("add_subscriber.html")


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

    return render_template("edit_subscriber.html", subscriber=subscriber)


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
                    status="active"
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
            flash("Import failed. Please check your CSV file and try again.", "danger")
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
