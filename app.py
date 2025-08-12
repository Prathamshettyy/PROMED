import os
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
import pyqrcode
import bcrypt
import dotenv

# Load env vars
dotenv.load_dotenv()

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'SQLALCHEMY_DATABASE_URI', 'sqlite:///promed_v2.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# Init extensions
db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)  # Migration support

# Models
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    factory_name = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    uses = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(200), nullable=False)
    tablets = db.relationship('Tablet', back_populates='medicine', cascade='all, delete-orphan')

class Tablet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicine.id'), nullable=False)
    batch_code = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    used = db.Column(db.Boolean, default=False)
    medicine = db.relationship('Medicine', back_populates='tablets')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and bcrypt.checkpw(p.encode(), user.password.encode()):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('add_medicine'))
        flash("Invalid credentials!", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if User.query.filter_by(username=u).first():
            flash("Username already exists!", "danger")
        else:
            hashed = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            db.session.add(User(username=u, password=hashed))
            db.session.commit()
            flash("User created! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        factory = request.form['factory_name']
        mfg = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d')
        uses = request.form['uses']

        os.makedirs('static/qrcodes', exist_ok=True)
        qr = pyqrcode.create(f"{name}|{factory}")
        qr_filename = f"static/qrcodes/{name}_{factory}.png"
        qr.png(qr_filename, scale=6)

        med = Medicine(
            name=name,
            factory_name=factory,
            manufacturing_date=mfg,
            uses=uses,
            qr_code=qr_filename
        )
        db.session.add(med)
        db.session.commit()

        # Handle tablets
        batch_codes = request.form.getlist('batch_code')
        expiries = request.form.getlist('expiry_date')
        for bc, exp in zip(batch_codes, expiries):
            tab = Tablet(
                medicine_id=med.id,
                batch_code=bc,
                expiry_date=datetime.strptime(exp, '%Y-%m-%d')
            )
            db.session.add(tab)
        db.session.commit()

        flash('Medicine and tablets added!', 'success')
        return redirect(url_for('medicine_details'))
    return render_template('add_medicine.html')

@app.route('/medicine_details')
def medicine_details():
    medicines = Medicine.query.all()
    return render_template('medicine_details.html', medicines=medicines)

@app.route('/view_medicine/<int:medicine_id>')
def view_medicine(medicine_id):
    medicine = Medicine.query.get_or_404(medicine_id)
    return render_template('view_medicine.html', medicine=medicine)

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

if __name__ == '__main__':
    app.run(debug=True)
