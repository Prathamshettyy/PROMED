import os
import sys # Import the sys module
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import pyqrcode
import bcrypt
import dotenv
from datetime import datetime

# 1. Load environment variables
dotenv.load_dotenv()

app = Flask(__name__)

# 2. Configure app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'a-fallback-secret-key-for-development')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'SQLALCHEMY_DATABASE_URI',
    'sqlite:///promed.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 3. Mail settings
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# 4. Initialize extensions
db   = SQLAlchemy(app)
mail = Mail(app)

# 5. Models (These are correct, no changes needed)
class Medicine(db.Model):
    id                 = db.Column(db.Integer, primary_key=True)
    name               = db.Column(db.String(100), nullable=False)
    factory_name       = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date        = db.Column(db.Date, nullable=False)
    uses               = db.Column(db.Text, nullable=False)
    qr_code            = db.Column(db.String(200), nullable=False)
    user_id            = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class User(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    username  = db.Column(db.String(100), unique=True, nullable=False)
    password  = db.Column(db.String(200), nullable=False)
    medicines = db.relationship('Medicine', backref='owner', lazy=True)

# 6. Routes (These are correct, no changes needed)
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
            return redirect(url_for('view_medicines'))
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
            h = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
            db.session.add(User(username=u, password=h))
            db.session.commit()
            flash("User created! Please log in.", "success")
            return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('home'))

@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'user_id' not in session:
        flash('Please log in to add a medicine.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        fac  = request.form['factory_name']
        mfg  = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d')
        exp  = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')
        uses = request.form['uses']
        os.makedirs('static/qrcodes', exist_ok=True)
        qr   = pyqrcode.create(f"{name} - {fac}")
        fn   = f"static/qrcodes/{name}_{fac}.png"
        qr.png(fn, scale=6)

        m = Medicine(
            name=name, factory_name=fac,
            manufacturing_date=mfg,
            expiry_date=exp, uses=uses,
            qr_code=fn,
            user_id=session['user_id']
        )
        db.session.add(m)
        db.session.commit()
        flash("Medicine added successfully!", "success")
        return redirect(url_for('view_medicines'))
    return render_template('add_medicine.html')

@app.route('/medicines')
def view_medicines():
    if 'user_id' not in session:
        flash('Please log in to view your medicines.', 'warning')
        return redirect(url_for('login'))

    meds = Medicine.query.filter_by(user_id=session['user_id']).all()
    return render_template('medicine_details.html', medicines=meds)

@app.route('/view_medicine/<int:medicine_id>')
def view_medicine(medicine_id):
    if 'user_id' not in session:
        flash('Please log in to view this page.', 'warning')
        return redirect(url_for('login'))

    med = Medicine.query.get_or_404(medicine_id)

    if med.owner.id != session['user_id']:
        flash('You do not have permission to view this medicine.', 'danger')
        return redirect(url_for('view_medicines'))

    return render_template('view_medicine.html', medicine=med)
    
@app.route('/delete_medicine/<int:medicine_id>', methods=['POST'])
def delete_medicine(medicine_id):
    if 'user_id' not in session:
        flash('Please log in to perform this action.', 'warning')
        return redirect(url_for('login'))
        
    med = Medicine.query.get_or_404(medicine_id)

    if med.owner.id != session['user_id']:
        flash('You do not have permission to delete this medicine.', 'danger')
        return redirect(url_for('view_medicines'))

    try:
        if os.path.exists(med.qr_code):
            os.remove(med.qr_code)
            
        db.session.delete(med)
        db.session.commit()
        flash('Medicine deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting medicine: {e}', 'danger')

    return redirect(url_for('view_medicines'))

@app.route('/about_us')
def about_us():
    return render_template('about_us.html')

# --- THE GUARANTEED FIX ---
# This block will run the correct database setup command.
if __name__ == '__main__':
    # Check if a command-line argument 'init-db' was passed
    if len(sys.argv) > 1 and sys.argv[1] == 'init-db':
        with app.app_context():
            print("Dropping all tables...")
            db.drop_all() # Deletes all existing tables
            print("Creating all tables...")
            db.create_all() # Creates new tables with the correct schema
            print("Database has been reset and initialized.")
    else:
        # If no argument, run the app as usual
        app.run(debug=True)