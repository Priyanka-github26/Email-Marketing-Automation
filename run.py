from app import create_app, db
from flask import jsonify
from sqlalchemy import text

app = create_app()


@app.route("/")
def home():
    return "Email Marketing Automation Platform is running!"


@app.route("/db-check")
def db_check():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"database": "Connected successfully!"})
    except Exception as e:
        return jsonify({"database": "Connection failed", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)