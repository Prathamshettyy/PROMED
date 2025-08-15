import os, uuid, re, logging
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import pyqrcode, dotenv
from functools import wraps
from flask_apscheduler import APScheduler
import urllib.parse

# ───── Load environment variables ─────
dotenv.load_dotenv()

# Configure logging for better error tracking
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Config
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key'),
    SQLALCHEMY_DATABASE_URI=os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///promed.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    WTF_CSRF_ENABLED=True,

    # Mail config
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.getenv('MAIL_USERNAME'),

    # Scheduler
    SCHEDULER_API_ENABLED=True
)

# ───── Extensions ─────
db = SQLAlchemy(app)
csrf = CSRFProtect(app)
mail = Mail(app)
scheduler = APScheduler()

# ───── Models ─────
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    medicines = db.relationship('Medicine', backref='owner', lazy=True, cascade='all,delete-orphan')

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    factory_name = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    uses = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(260), nullable=False)
    
    # FIXED: Email alert tracking columns
    expiry_alert_sent_prior = db.Column(db.Boolean, default=False)  # Alert 24h prior
    expiry_alert_sent_expiry_day = db.Column(db.Boolean, default=False)  # Alert on expiry day
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# ───── Helpers ─────
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email) is not None

def validate_mail_config():
    """Validate mail configuration and log warnings."""
    issues = []
    
    if not app.config.get('MAIL_USERNAME'):
        issues.append("MAIL_USERNAME not set in environment variables")
    if not app.config.get('MAIL_PASSWORD'):
        issues.append("MAIL_PASSWORD not set in environment variables")
    if not app.config.get('MAIL_SERVER'):
        issues.append("MAIL_SERVER not configured")
    
    if issues:
        logger.warning("Mail configuration issues found:")
        for issue in issues:
            logger.warning(f"  - {issue}")
        logger.warning("Email functionality will not work until these are resolved.")
        return False
    return True

QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
os.makedirs(QR_FOLDER, exist_ok=True)

# ───── FIXED: Email Alerts Function ─────
def send_expiry_alerts():
    """Send expiry alerts with improved error handling and logging."""
    logger.info("Starting expiry alerts check...")
    
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    # 24hr prior warnings (send if expiry is tomorrow, warning not sent)
    warning_meds = Medicine.query.filter(
        Medicine.expiry_date == tomorrow,
        Medicine.expiry_alert_sent_prior == False
    ).all()
    
    # "Has expired" alerts (send if expiry is today, alert not sent)
    expired_meds = Medicine.query.filter(
        Medicine.expiry_date == today,
        Medicine.expiry_alert_sent_expiry_day == False
    ).all()
    
    logger.info(f"Found {len(warning_meds)} medicines expiring tomorrow, {len(expired_meds)} expired today")
    
    # Send warning emails for tomorrow's expiries
    for med in warning_meds:
        user = User.query.get(med.user_id)
        if not user or not user.email:
            logger.warning(f"No valid user/email for med {med.id}")
            continue
        try:
            # Validate mail configuration before sending
            if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
                logger.error("Mail configuration missing. Check MAIL_USERNAME and MAIL_PASSWORD in .env")
                continue
                
            msg = Message(
                subject="ProMed – Medicine Will Expire Tomorrow",
                recipients=[user.email],
                body=f"Reminder: '{med.name}' from {med.factory_name} will expire on {med.expiry_date.strftime('%d-%m-%Y')}.\n\nPlease check your medicine inventory."
            )
            logger.info(f"Attempting to send 24hr warning to {user.email}")
            mail.send(msg)
            med.expiry_alert_sent_prior = True
            db.session.commit()
            logger.info(f"Sent 24hr warning to {user.email} for {med.name}")
        except Exception as e:
            logger.error(f"Failed to send 24hr warning to {user.email}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if "SMTPAuthenticationError" in str(type(e)):
                logger.error("SMTP Authentication failed - check MAIL_USERNAME and MAIL_PASSWORD")
            elif "SMTPConnectError" in str(type(e)):
                logger.error("Failed to connect to SMTP server - check MAIL_SERVER and MAIL_PORT")
            db.session.rollback()
    
    # Send final "has expired" alert for today's expiries
    for med in expired_meds:
        user = User.query.get(med.user_id)
        if not user or not user.email:
            logger.warning(f"No valid user/email for med {med.id}")
            continue
        try:
            # Validate mail configuration before sending
            if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
                logger.error("Mail configuration missing. Check MAIL_USERNAME and MAIL_PASSWORD in .env")
                continue
                
            msg = Message(
                subject="ProMed – Medicine Has Expired",
                recipients=[user.email],
                body=f"Alert: '{med.name}' from {med.factory_name} has expired today ({med.expiry_date.strftime('%d-%m-%Y')}).\n\nPlease dispose of this medicine safely."
            )
            logger.info(f"Attempting to send expired alert to {user.email}")
            mail.send(msg)
            med.expiry_alert_sent_expiry_day = True
            db.session.commit()
            logger.info(f"Sent expired alert to {user.email} for {med.name}")
        except Exception as e:
            logger.error(f"Failed to send expired alert to {user.email}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if "SMTPAuthenticationError" in str(type(e)):
                logger.error("SMTP Authentication failed - check MAIL_USERNAME and MAIL_PASSWORD")
            elif "SMTPConnectError" in str(type(e)):
                logger.error("Failed to connect to SMTP server - check MAIL_SERVER and MAIL_PORT")
            db.session.rollback()

# ───── Routes ─────
@app.before_first_request
def create_tables():
    db.create_all()
    print("Database tables created on first request")

@app.route('/init-db')
def init_database():
    try:
        db.create_all()
        return "Database tables created successfully!"
    except Exception as e:
        return f"Error creating database: {str(e)}"


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        uname = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        pwd = request.form.get('password', '').strip()

        if not uname or not email or not pwd:
            flash('All fields are required.', 'danger'); return render_template('signup.html')
        if not is_valid_email(email):
            flash('Invalid email format.', 'danger'); return render_template('signup.html')
        if len(pwd) < 6:
            flash('Password must be at least 6 characters.', 'danger'); return render_template('signup.html')
        if User.query.filter((User.username==uname)|(User.email==email)).first():
            flash('Username or email already registered.', 'danger'); return render_template('signup.html')

        u = User(username=uname, email=email, password=generate_password_hash(pwd))
        db.session.add(u); db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        login_in = request.form.get('login_input', '').strip().lower()
        pwd = request.form.get('password', '').strip()

        user = User.query.filter((User.username==login_in)|(User.email==login_in)).first()
        if user and check_password_hash(user.password, pwd):
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash(f"Welcome back, {user.username}!", 'success')
            return redirect(url_for('view_medicines'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/add-medicine', methods=['GET','POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        fac = request.form.get('factory_name', '').strip()
        mfg_s = request.form.get('manufacturing_date', '').strip()
        exp_s = request.form.get('expiry_date', '').strip()
        uses = request.form.get('uses', '').strip()

        if not all([name, fac, mfg_s, exp_s, uses]):
            flash('All fields are required.', 'danger'); return render_template('add_medicine.html')

        try:
            mfg = datetime.strptime(mfg_s, '%Y-%m-%d').date()
            exp = datetime.strptime(exp_s, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger'); return render_template('add_medicine.html')

        if exp <= mfg:
            flash('Expiry must be after manufacturing date.', 'danger'); return render_template('add_medicine.html')

        filename = f"{uuid.uuid4().hex}.png"
        file_path = os.path.join(QR_FOLDER, filename)
        
        # FIXED: Create a URL that points to our QR scan handler instead of raw text
        medicine_url = f"{request.host_url}qr-scan?name={urllib.parse.quote(name)}&factory={urllib.parse.quote(fac)}&mfg={mfg}&exp={exp}&uses={urllib.parse.quote(uses)}"
        
        # Generate QR code with the URL
        pyqrcode.create(medicine_url).png(file_path, scale=6)

        med = Medicine(
            name=name, factory_name=fac,
            manufacturing_date=mfg, expiry_date=exp,
            uses=uses,
            qr_code=f"static/qrcodes/{filename}",
            expiry_alert_sent_prior=False,
            expiry_alert_sent_expiry_day=False,
            user_id=session['user_id']
        )
        db.session.add(med); db.session.commit()
        flash('Medicine added successfully.', 'success')
        return redirect(url_for('view_medicines'))

    return render_template('add_medicine.html')

@app.route('/medicines')
@login_required
def view_medicines():
    meds = Medicine.query.filter_by(user_id=session['user_id']).order_by(Medicine.expiry_date).all()
    return render_template('medicine_details.html', medicines=meds)

@app.route('/medicine/<int:medicine_id>')
@login_required
def view_medicine(medicine_id):
    med = Medicine.query.get_or_404(medicine_id)
    if med.user_id != session['user_id']:
        abort(403)
    return render_template('view_medicine.html', medicine=med)

@app.route('/medicine/<int:medicine_id>/delete', methods=['POST'])
@login_required
def delete_medicine(medicine_id):
    med = Medicine.query.get_or_404(medicine_id)
    if med.user_id != session['user_id']:
        abort(403)
    try:
        if os.path.exists(med.qr_code):
            os.remove(med.qr_code)
        db.session.delete(med); db.session.commit()
        flash('Medicine deleted.', 'success')
    except Exception:
        db.session.rollback()
        flash('Error deleting medicine.', 'danger')
    return redirect(url_for('view_medicines'))

# ───── NEW: QR Code Scan Handler Route ─────
@app.route('/qr-scan')
def qr_scan_handler():
    """Handle QR code scanning with a proper formatted page."""
    # Get medicine details from QR code URL parameters
    name = request.args.get('name', '')
    factory = request.args.get('factory', '')
    mfg = request.args.get('mfg', '')
    exp = request.args.get('exp', '')
    uses = request.args.get('uses', '')
    
    # Create medicine data object for template
    medicine_data = {
        'name': name,
        'factory_name': factory,
        'manufacturing_date': mfg,
        'expiry_date': exp,
        'uses': uses
    }
    
    return render_template('qr_scan_result.html', medicine=medicine_data)

# ───── Test Routes ─────
@app.route('/run-expiry-test')
@login_required
def run_expiry_test():
    """Manually trigger expiry alerts with detailed feedback."""
    try:
        logger.info(f"Manual expiry test triggered by user {session['username']}")
        send_expiry_alerts()
        flash('Manually triggered expiry alerts — check logs for details.', 'info')
    except Exception as e:
        logger.error(f"Error during manual expiry test: {str(e)}")
        flash(f'Error running expiry test: {str(e)}', 'danger')
    return redirect(url_for('view_medicines'))

@app.route('/test-email')
@login_required
def test_email():
    """Test email functionality with comprehensive error reporting."""
    try:
        # Validate configuration
        config_issues = []
        if not app.config.get('MAIL_USERNAME'):
            config_issues.append("MAIL_USERNAME not configured")
        if not app.config.get('MAIL_PASSWORD'):
            config_issues.append("MAIL_PASSWORD not configured")
        if not app.config.get('MAIL_SERVER'):
            config_issues.append("MAIL_SERVER not configured")
        
        if config_issues:
            error_msg = "Mail configuration issues: " + ", ".join(config_issues)
            logger.error(error_msg)
            flash(error_msg, 'danger')
            return redirect(url_for('view_medicines'))
        
        # Get current user's email
        user_email = session.get('email')
        if not user_email:
            flash('No email address found for current user', 'warning')
            return redirect(url_for('view_medicines'))
        
        # Create test message
        msg = Message(
            subject="ProMed Email Test",
            recipients=[user_email],
            body=f"This is a test email from ProMed.\n\nSent at: {datetime.now()}\n\nIf you receive this, email functionality is working correctly!"
        )
        
        logger.info(f"Sending test email to {user_email}")
        logger.info(f"Using SMTP server: {app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}")
        logger.info(f"Using username: {app.config.get('MAIL_USERNAME')}")
        
        mail.send(msg)
        
        success_msg = f"Test email sent successfully to {user_email}. Check your inbox (and spam folder)!"
        logger.info(success_msg)
        flash(success_msg, 'success')
        
    except Exception as e:
        error_msg = f"Failed to send test email: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Error type: {type(e).__name__}")
        
        # Provide specific troubleshooting advice
        if "SMTPAuthenticationError" in str(type(e)):
            flash("SMTP Authentication Error: Check your Gmail app password. Make sure you're using an app password (not your regular password) and that 2FA is enabled.", 'danger')
        elif "SMTPConnectError" in str(type(e)):
            flash("SMTP Connection Error: Cannot connect to Gmail servers. Check your internet connection.", 'danger')
        elif "SMTPRecipientsRefused" in str(type(e)):
            flash("Recipient email refused: Check that the email address is valid.", 'danger')
        else:
            flash(f"Email Error: {error_msg}", 'danger')
    
    return redirect(url_for('view_medicines'))

@app.route('/test-flask-mail-direct')
@login_required
def test_flask_mail_direct():
    try:
        from flask_mail import Message
        msg = Message(
            subject="Direct Flask Test",
            recipients=[session.get('email')],
            body="This is a direct Flask-Mail test"
        )
        mail.send(msg)
        return "✅ Flask-Mail sent successfully!"
    except Exception as e:
        return f"❌ Flask-Mail failed: {str(e)}"

# ───── Error handlers ─────
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

# ───── CLI ─────
@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()
    print("Database initialized.")

# ───── Main ─────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created/verified")
        validate_mail_config()

        scheduler.init_app(app)
        scheduler.start()

        from datetime import datetime

        # 1) Immediate run inside app context
        scheduler.add_job(
            id='expiry_alerts_immediate',
            func=lambda: app.app_context().push() or send_expiry_alerts(),
            trigger='date',
            run_date=datetime.now()
        )

        # 2) Daily run at 8 AM inside app context
        def wrapped_send():
            with app.app_context():
                send_expiry_alerts()

        scheduler.add_job(
            id='expiry_alerts_daily',
            func=wrapped_send,
            trigger='cron',
            hour=7,
            minute=0
        )

    app.run(debug=True)
