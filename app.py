import os, uuid, re
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import pyqrcode, dotenv
from functools import wraps
from flask_apscheduler import APScheduler

# ───── Load environment variables ─────
dotenv.load_dotenv()
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
    expiry_alert_sent = db.Column(db.Boolean, default=False, nullable=False)
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

QR_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
os.makedirs(QR_FOLDER, exist_ok=True)

# ───── Scheduled Job ─────
def send_expiry_alerts():
    tomorrow = date.today() + timedelta(days=1)
    expiring_meds = Medicine.query.filter(
        Medicine.expiry_date == tomorrow,
        Medicine.expiry_alert_sent == False
    ).all()

    user_meds = {}
    for med in expiring_meds:
        user_meds.setdefault(med.user_id, []).append(med)

    for user_id, meds in user_meds.items():
        user = User.query.get(user_id)
        if not user or not user.email:
            continue

        details = []
        for m in meds:
            details.append(
                f"Name: {m.name}\n"
                f"Factory: {m.factory_name}\n"
                f"Manufactured: {m.manufacturing_date.strftime('%d-%m-%Y')}\n"
                f"Expires: {m.expiry_date.strftime('%d-%m-%Y')}\n"
                f"Uses: {m.uses}\n"
            )

        body = "The following medicine(s) will expire tomorrow:\n\n" + "\n".join(details)

        try:
            mail.send(Message(
                subject="ProMed Medicine Expiry Alert",
                recipients=[user.email],
                body=body
            ))
            for m in meds:
                m.expiry_alert_sent = True
            db.session.commit()
            print(f"Sent expiry alert email to {user.email}")
        except Exception as e:
            print(f"Failed to send email to {user.email}: {e}")
            db.session.rollback()

# ───── Routes ─────
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
        qr_payload = f"Name: {name}\\nFactory: {fac}\\nMfg: {mfg}\\nExp: {exp}\\nUses: {uses}"
        pyqrcode.create(qr_payload).png(file_path, scale=6)

        med = Medicine(
            name=name, factory_name=fac,
            manufacturing_date=mfg, expiry_date=exp,
            uses=uses,
            qr_code=f"static/qrcodes/{filename}",
            expiry_alert_sent=False,
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

# ───── Test Route: Manually Trigger Alert ─────
@app.route('/run-expiry-test')
@login_required
def run_expiry_test():
    send_expiry_alerts()
    flash('Manually triggered expiry alerts — check your email.', 'info')
    return redirect(url_for('view_medicines'))

# Error handlers
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

# CLI
@app.cli.command('init-db')
def init_db():
    db.drop_all()
    db.create_all()
    print("Database initialized.")

# ───── Main ─────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # makes sure expiry_alert_sent exists
    scheduler.init_app(app)
    scheduler.start()
    scheduler.add_job(id='expiry_alerts', func=send_expiry_alerts, trigger='cron', hour=8)
    app.run(debug=True)
