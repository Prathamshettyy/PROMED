from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define Medicine model
class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    factory_name = db.Column(db.String(100), nullable=False)
    manufacturing_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    uses = db.Column(db.Text, nullable=False)
    qr_code = db.Column(db.String(200), nullable=False)
    
    # Email alert tracking - FIXED: These should be inside the Medicine class
    expiry_alert_sent_prior = db.Column(db.Boolean, default=False)  # Alert 24h prior
    expiry_alert_sent_expiry_day = db.Column(db.Boolean, default=False)  # Alert on expiry day
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Define User model for login/signup
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Increased size for hashed password
    email = db.Column(db.String(120), unique=True, nullable=False)  # Added email field
    medicines = db.relationship('Medicine', backref='owner', lazy=True, cascade='all,delete-orphan')