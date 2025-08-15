import os
import uuid
import re
import logging
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import pyqrcode
from dotenv import load_dotenv
from functools import wraps
from flask_apscheduler import APScheduler
import urllib.parse
from flask_migrate import Migrate # <--- IMPORT MIGRATE

# ───── Load environment variables ─────
load_dotenv()

# Configure logging for better error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ───── Configuration ─────
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-secure-dev-secret-key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

# --- Database Configuration ---
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///promed.db'

# --- Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# --- Scheduler Configuration ---
app.config['SCHEDULER_API_ENABLED'] = True

# ───── Extensions ─────
db = SQLAlchemy(app)
migrate = Migrate(app, db) # <--- INITIALIZE MIGRATE
csrf = CSRFProtect(app)
mail = Mail(app)
scheduler = APScheduler()


# ───── Models ─────
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    medicines = db.relationship('Medicine', backref='owner', lazy=True, cascade='all, delete-orphan')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    factory_name = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    uses = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(260), nullable=False)
    
    expiry_alert_sent_prior = db.Column(db.Boolean, default=False)
    expiry_alert_sent_expiry_day = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ───── Helpers ─────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
os.makedirs(QR_FOLDER, exist_ok=True)

# ───── Email Alerts Function ─────
def send_expiry_alerts():
    with app.app_context():
        logger.info("Starting expiry alerts check...")
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        warning_meds = Medicine.query.filter(
            Medicine.expiry_date == tomorrow,
            Medicine.expiry_alert_sent_prior == False
        ).all()
        
        expired_meds = Medicine.query.filter(
            Medicine.expiry_date == today,
            Medicine.expiry_alert_sent_expiry_day == False
        ).all()
        
        logger.info(f"Found {len(warning_meds)} medicines expiring tomorrow, {len(expired_meds)} expired today")
        
        for med in warning_meds:
            user = User.query.get(med.user_id)
            if user and user.email:
                try:
                    msg = Message(
                        subject="ProMed – Medicine Will Expire Tomorrow",
                        recipients=[user.email],
                        body=f"Reminder: '{med.name}' from {med.factory_name} will expire on {med.expiry_date.strftime('%d-%m-%Y')}."
                    )
                    mail.send(msg)
                    med.expiry_alert_sent_prior = True
                    db.session.commit()
                    logger.info(f"Sent 24hr warning to {user.email} for {med.name}")
                except Exception as e:
                    logger.error(f"Failed to send 24hr warning to {user.email}: {e}")
                    db.session.rollback()

        for med in expired_meds:
            user = User.query.get(med.user_id)
            if user and user.email:
                try:
                    msg = Message(
                        subject="ProMed – Medicine Has Expired",
                        recipients=[user.email],
                        body=f"Alert: '{med.name}' from {med.factory_name} has expired today ({med.expiry_date.strftime('%d-%m-%Y')})."
                    )
                    mail.send(msg)
                    med.expiry_alert_sent_expiry_day = True
                    db.session.commit()
                    logger.info(f"Sent expired alert to {user.email} for {med.name}")
                except Exception as e:
                    logger.error(f"Failed to send expired alert to {user.email}: {e}")
                    db.session.rollback()

# ───── Routes ─────
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not all([username, email, password]):
            flash('All fields are required.', 'danger')
        elif not is_valid_email(email):
            flash('Invalid email format.', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already registered.', 'danger')
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        
        return render_template('signup.html')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form.get('login_input', '').strip().lower()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username == login_input) | (User.email == login_input)).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash(f"Welcome back, {user.username}!", 'success')
            return redirect(url_for('view_medicines'))
        else:
            flash('Invalid credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/add-medicine', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        factory_name = request.form.get('factory_name', '').strip()
        mfg_date_str = request.form.get('manufacturing_date', '').strip()
        expiry_date_str = request.form.get('expiry_date', '').strip()
        uses = request.form.get('uses', '').strip()

        if not all([name, factory_name, mfg_date_str, expiry_date_str, uses]):
            flash('All fields are required.', 'danger')
        else:
            try:
                mfg_date = datetime.strptime(mfg_date_str, '%Y-%m-%d').date()
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()

                if expiry_date <= mfg_date:
                    flash('Expiry must be after manufacturing date.', 'danger')
                else:
                    filename = f"{uuid.uuid4().hex}.png"
                    file_path = os.path.join(QR_FOLDER, filename)
                    
                    medicine_url = url_for('qr_scan_handler', name=name, factory=factory_name, mfg=mfg_date, exp=expiry_date, uses=uses, _external=True)
                    
                    pyqrcode.create(medicine_url).png(file_path, scale=6)

                    new_medicine = Medicine(
                        name=name,
                        factory_name=factory_name,
                        manufacturing_date=mfg_date,
                        expiry_date=expiry_date,
                        uses=uses,
                        qr_code=os.path.join('static', 'qrcodes', filename),
                        user_id=session['user_id']
                    )
                    db.session.add(new_medicine)
                    db.session.commit()
                    flash('Medicine added successfully.', 'success')
                    return redirect(url_for('view_medicines'))

            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')

    return render_template('add_medicine.html')

@app.route('/medicines')
@login_required
def view_medicines():
    medicines = Medicine.query.filter_by(user_id=session['user_id']).order_by(Medicine.expiry_date).all()
    return render_template('medicine_details.html', medicines=medicines)

@app.route('/medicine/<int:medicine_id>')
@login_required
def view_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    if medicine.user_id != session['user_id']:
        abort(403)
    return render_template('view_medicine.html', medicine=medicine)

@app.route('/medicine/<int:medicine_id>/delete', methods=['POST'])
@login_required
def delete_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    if medicine.user_id != session['user_id']:
        abort(403)
    
    try:
        if os.path.exists(medicine.qr_code):
            os.remove(medicine.qr_code)
        db.session.delete(medicine)
        db.session.commit()
        flash('Medicine deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting medicine: {e}")
        flash('Error deleting medicine.', 'danger')
        
    return redirect(url_for('view_medicines'))

@app.route('/qr-scan')
def qr_scan_handler():
    medicine_data = {
        'name': request.args.get('name', 'N/A'),
        'factory_name': request.args.get('factory', 'N/A'),
        'manufacturing_date': request.args.get('mfg', 'N/A'),
        'expiry_date': request.args.get('exp', 'N/A'),
        'uses': request.args.get('uses', 'N/A')
    }
    return render_template('qr_scan_result.html', medicine=medicine_data)

# ───── Error Handlers ─────
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('500.html'), 500

# ───── CLI Command ─────
@app.cli.command("init-db")
def init_db_command():
    """Drops and creates all database tables."""
    db.drop_all()
    db.create_all()
    print("Database initialized.")

# ───── Main Execution ─────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    scheduler.init_app(app)
    scheduler.add_job(id='send_expiry_alerts_job', func=send_expiry_alerts, trigger='cron', hour=8)
    scheduler.start()
    
    app.run(debug=True)
