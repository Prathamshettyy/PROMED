# check_users.py
from app import app, send_expiry_alerts

if __name__ == '__main__':
    # The app_context is needed so the script can access the database
    # and other parts of your Flask application.
    with app.app_context():
        send_expiry_alerts()