import os
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import pyqrcode, bcrypt, dotenv
from datetime import datetime

# 1. Load environment variables from your .env
dotenv.load_dotenv()

app = Flask(__name__)

# 2. Configure app entirely from .env
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'SQLALCHEMY_DATABASE_URI',
    'sqlite:///promed.db'       # fallback if not set
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Mail settings from .env
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# 4. Initialize extensions
db   = SQLAlchemy(app)
mail = Mail(app)

# 5. Models
class Medicine(db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(100), nullable=False)
    factory_name       = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date,    nullable=False)
    expiry_date        = db.Column(db.Date,    nullable=False)
    uses               = db.Column(db.Text,    nullable=False)
    qr_code            = db.Column(db.String(200), nullable=False)

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200),               nullable=False)

# 6. Routes (unchanged logic)
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and bcrypt.checkpw(p.encode(), user.password.encode()):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('add_medicine'))
        flash("Invalid credentials!", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        u = request.form['username']
        p = request.form['password']
        if User.query.filter_by(username=u).first():
            flash("Username already exists!", "danger")
        else:
            h = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            db.session.add(User(username=u, password=h))
            db.session.commit()
            flash("User created! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/add_medicine', methods=['GET','POST'])
def add_medicine():
    if request.method=='POST':
        name = request.form['name']
        fac  = request.form['factory_name']
        mfg  = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d')
        exp  = datetime.strptime(request.form['expiry_date'],      '%Y-%m-%d')
        uses = request.form['uses']
        os.makedirs('static/qrcodes', exist_ok=True)
        qr  = pyqrcode.create(f"{name} - {fac}")
        fn  = f"static/qrcodes/{name}_{fac}.png"
        qr.png(fn, scale=6)
        m = Medicine(
            name=name, factory_name=fac,
            manufacturing_date=mfg,
            expiry_date=exp, uses=uses,
            qr_code=fn
        )
        db.session.add(m)
        db.session.commit()
        flash("Medicine added successfully!", "success")
        return redirect(url_for('medicine_details'))
    return render_template('add_medicine.html')

@app.route('/medicine_details')
def medicine_details():
    meds = Medicine.query.all()
    return render_template('medicine_details.html', medicines=meds)

@app.route('/view_medicine/<int:medicine_id>')
def view_medicine(medicine_id):
    med = Medicine.query.get_or_404(medicine_id)
    return render_template('view_medicine.html', medicine=med)

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

# 7. DB init
def create_db():
    with app.app_context():
        db.create_all()

if __name__=='__main__':
    create_db()
    app.run(debug=True)
