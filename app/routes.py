
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Subscriber

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

