# Email Marketing Automation Platform

A web-based Email Marketing Automation Platform built using Python Flask and MySQL. It helps users manage subscribers, create email templates, send email campaigns, track engagement, and generate campaign performance reports.

## Features

- **User Authentication:** User registration and secure login.
- **Subscriber Management:** Add, edit, delete, and manage subscribers.
- **CSV Import:** Import subscriber details using CSV files.
- **Email Templates:** Create, edit, and delete reusable email templates.
- **Campaign Management:** Create campaigns and select recipients.
- **Email Sending:** Send campaigns using Gmail SMTP.
- **Subscriber Consent:** Send emails only to active subscribers who have given consent.
- **Unsubscribe Management:** Secure unsubscribe links for subscribers.
- **Email Open Tracking:** Track email opens using tracking pixels.
- **Click Tracking:** Track clicks on links inside campaign emails.
- **Analytics Dashboard:** View campaign performance, open rates, and click rates.
- **Reports:** Download campaign performance reports in CSV format.

## Technologies Used

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, Bootstrap, JavaScript |
| Database | MySQL |
| ORM | Flask-SQLAlchemy |
| Authentication | Flask-Login, Flask-Bcrypt |
| Email Service | Gmail SMTP |
| Data Export | CSV |
| Development Tools | VS Code, XAMPP, phpMyAdmin |
| Version Control | Git, GitHub |

## Project Structure

```text
Email-Marketing-Automation/
│
├── app/
│   ├── templates/
│   ├── static/
│   ├── routes.py
│   └── models.py
│
├── run.py
├── config.py
├── requirements.txt
├── .env
└── README.md
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Priyanka-github26/Email-Marketing-Automation.git
```

### 2. Navigate to the project directory

```bash
cd Email-Marketing-Automation
```

### 3. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 4. Configure MySQL

- Start Apache and MySQL using XAMPP.
- Open phpMyAdmin.
- Create a database named `email_marketing_db`.

### 5. Configure environment variables

Create a `.env` file in the project root and configure the required database and Gmail SMTP settings.

Do not upload your `.env` file or Gmail App Password to GitHub.

### 6. Run the application

```bash
py run.py
```

### 7. Open in your browser

```text
http://127.0.0.1:5000
```

## Application Workflow

1. Register and log in.
2. Add subscribers or import them through CSV.
3. Create reusable email templates.
4. Create campaigns and select eligible recipients.
5. Send campaigns through Gmail SMTP.
6. Track email opens and link clicks.
7. Monitor campaign performance through analytics.
8. Export campaign reports as CSV files.

## Future Enhancements

- Scheduled email campaigns.
- Automated follow-up emails.
- Advanced subscriber segmentation.
- A/B testing for email campaigns.
- Improved conversion tracking.

## Author

**Priyanka Patil**

BE Computer Engineering

GitHub: [Priyanka-github26](https://github.com/Priyanka-github26)

---

*This project was developed to demonstrate practical skills in Python web development, database management, email integration, and analytics.*