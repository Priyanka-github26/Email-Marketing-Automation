
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
