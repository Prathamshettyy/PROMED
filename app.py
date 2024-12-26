from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import pyqrcode
import os
from datetime import datetime
from flask_mail import Mail, Message
import dotenv
import bcrypt

# Load environment variables
dotenv.load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Set the URI for the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///promed.db'  # Adjust the path if needed
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # To avoid warnings
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Ensure this is set in your .env file

# Initialize Mail and DB
mail = Mail(app)
db = SQLAlchemy(app)

# Models
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    factory_name = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    uses = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(200), nullable=False)

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
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        # bcrypt.checkpw expects the stored password to be bytes
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password):
            session['user_id'] = user.id
            flash("Login successful!", "success")
            return redirect(url_for('add_medicine'))
        else:
            flash("Invalid credentials!", "danger")
    
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "danger")
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            new_user = User(username=username, password=hashed_password.decode('utf-8'))
            db.session.add(new_user)
            db.session.commit()
            flash("User created successfully! Please log in.", "success")
            return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/add_medicine', methods=['GET', 'POST'])
def add_medicine():
    if request.method == 'POST':
        name = request.form['name']
        factory_name = request.form['factory_name']
        manufacturing_date = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d')
        expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d')
        uses = request.form['uses']

        if not os.path.exists('static/qrcodes'):
            os.makedirs('static/qrcodes')

        qr_code = pyqrcode.create(f"{name} - {factory_name}")
        qr_code_filename = f"static/qrcodes/{name}_{factory_name}.png"
        qr_code.png(qr_code_filename, scale=6)

        new_medicine = Medicine(
            name=name,
            factory_name=factory_name,
            manufacturing_date=manufacturing_date,
            expiry_date=expiry_date,
            uses=uses,
            qr_code=qr_code_filename
        )
        db.session.add(new_medicine)
        db.session.commit()
        flash("Medicine added successfully!", "success")
        return redirect(url_for('medicine_details'))  # Redirect to medicine details page

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

# Database initialization function
def create_db():
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist

if __name__ == '__main__':
    create_db()  # Ensure the database is created before running the app
    app.run(debug=True)
