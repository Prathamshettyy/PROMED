# ProMed: Medicine Information Management System

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)  [![Flask](https://img.shields.io/badge/flask-3.1.1-green.svg)](https://flask.palletsprojects.com/)  [![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)  [![Deployment](https://img.shields.io/badge/deployment-PythonAnywhere-brightgreen.svg)](https://www.pythonanywhere.com/)

ProMed is a web application that enables healthcare providers and individuals to record, retrieve and monitor medicine information using QR codes. The platform supports multi-user accounts, automated e-mail alerts for expiring medicines and a production-ready deployment configuration for PythonAnywhere.

---
<p align="center">
  <img src="\static\images\project-banner.png" width="70%" />
</p>

---
## LIVE DEMO

🔗 https://promed.pythonanywhere.com/

---

## Table of Contents
1. [Key Features](#key-features)
2. [Technology Stack](#technology-stack)
3. [Installation](#installation)
4. [PythonAnywhere Deployment](#pythonanywhere-deployment)
5. [Configuration](#configuration)
6. [Usage Guide](#usage-guide)
7. [API End-Points](#api-end-points)
8. [Project Structure](#project-structure)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)
12. [Roadmap / Future Enhancements](#roadmap--future-enhancements)

---

## Key Features

| Category | Description |
|----------|-------------|
| Medicine Management | Add, view and delete medicines with full validation and UUID-based QR code generation |
| QR Code Support | Automatic PNG QR code created for every medicine; scanning opens a public detail page |
| Expiry Monitoring | Visual traffic-light indicators (valid / expiring soon / expired) and daily e-mail notifications |
| Secure Authentication | Password hashing, CSRF protection, session management and custom error pages |
| Multi-User Isolation | Each user maintains a private medicine inventory |
| Production Deployment | Configuration scripts and instructions tailored for PythonAnywhere (MySQL database) |
| Automated Tasks | APScheduler triggers e-mail alerts once per day via a PythonAnywhere scheduled job |

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend Framework | Flask 3.1.1 |
| ORM / Database | SQLAlchemy 3.1.1 · Flask-SQLAlchemy · SQLite (development) · MySQL (production) |
| Migrations | Flask-Migrate 4.1.0 |
| Templating | Jinja2 with Bootstrap-based layout |
| Static Assets | Custom CSS (only **main.css**) · JavaScript (home.js) |
| QR Code Generation | PyQRCode + Pillow |
| Mail Service | Flask-Mail with Gmail SMTP |
| Task Scheduling | APScheduler |

---

## Installation

### Prerequisites
* Python 3.8 or higher
* pip (Python package manager)
* Git (optional but recommended)

### Local Setup
```bash
# Clone repository
$ git clone https://github.com/yourusername/ProMed.git
$ cd ProMed

# Create virtual environment
$ python -m venv venv
$ source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
(venv) $ pip install -r requirements.txt

# Create an environment file (.env) – see Configuration section

# Initialise database (SQLite by default)
(venv) $ flask db init
(venv) $ flask db migrate -m "Initial schema"
(venv) $ flask db upgrade

# Run application
(venv) $ python app.py
```
Application is reachable at `http://127.0.0.1:5000/`.

---

## PythonAnywhere Deployment
This project is optimised for PythonAnywhere. The steps below assume a paid “Hacker” plan (required for MySQL and scheduled tasks).

1. **Clone and prepare the project** on the PythonAnywhere Bash console:
   ```bash
   $ git clone https://github.com/yourusername/ProMed.git ~/ProMed
   $ cd ~/ProMed
   $ python -m venv promed-env
   $ source promed-env/bin/activate
   (promed-env) $ pip install -r requirements.txt
   ```
2. **Create MySQL database** via the PythonAnywhere *Databases* tab. Use name `yourusername$promed`.
3. **Generate the `.env` file**:
   ```bash
   (promed-env) $ python setup_env.py   # Follow interactive prompts
   (promed-env) $ flask db upgrade
   ```
4. **Configure the web application** (Web tab):
   * Working directory: `/home/yourusername/ProMed`
   * WSGI file:
     ```python
     import sys, os
     path = '/home/yourusername/ProMed'
     if path not in sys.path:
         sys.path.append(path)
     from app import app as application
     os.environ['PYTHONANYWHERE_USERNAME'] = 'yourusername'
     ```
   * Virtualenv: `/home/yourusername/.virtualenvs/promed-env`
   * Static files: URL `/static/` → `/home/yourusername/ProMed/static/`
5. **Set up daily e-mail alert task** (Tasks tab):
   ```bash
   /home/yourusername/.virtualenvs/promed-env/bin/python /home/yourusername/ProMed/check_users.py
   ```
6. **Reload** the web app from the dashboard.

---

## Configuration
Create a `.env` file in the project root. Example:
```ini
# Security
SECRET_KEY=s3cure-r@ndom-key

# MySQL (PythonAnywhere)
MYSQL_USERNAME=yourusername
MYSQL_PASSWORD=your-mysql-password
MYSQL_HOST=yourusername.mysql.pythonanywhere-services.com
MYSQL_DBNAME=yourusername$promed
PYTHONANYWHERE_USERNAME=yourusername
PYTHONANYWHERE_DOMAIN=pythonanywhere.com

# Gmail SMTP (expiry alerts)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
```
Ensure `.env` is **never committed** (it is listed in `.gitignore`).

---

## Usage Guide
1. **Register** a new account via *Sign Up*.
2. **Log In** and navigate to *Add Medicine*.
3. Fill in medicine details – a QR code is generated automatically.
4. Use *View Medicines* to monitor inventory and status colour codes.
5. The scheduler dispatches e-mails 24 hours before expiry and on the expiry day.

---

## API End-Points
| Method | URL | Description | Auth |
|--------|-----|-------------|------|
| GET | `/` | Home page | – |
| GET | `/about_us` | About page | – |
| GET / POST | `/signup` | Register user | – |
| GET / POST | `/login` | User login | – |
| GET | `/logout` | Log out | ✓ |
| GET | `/medicines` | User inventory | ✓ |
| GET / POST | `/add-medicine` | Add medicine | ✓ |
| GET | `/medicine/<id>` | Detail view | ✓ |
| POST | `/medicine/<id>/delete` | Delete medicine | ✓ |
| GET | `/qr-scan` | Display data from scanned QR code | – |

---

## Project Structure
```
PROMED/
├── app.py               # Main Flask application
├── check_users.py       # Daily expiry alert script
├── setup_env.py         # Interactive .env generator for PythonAnywhere
├── test_db.py           # Database diagnostics script
├── migrations/          # Alembic migration history
├── static/
│   ├── css/main.css     # Sole active style sheet
│   ├── js/home.js       # Front-page JavaScript
│   ├── images/          # Static images
│   └── qrcodes/         # Generated QR PNG files
├── templates/           # Jinja2 templates
│   └── ...              # base.html, home.html, etc.
├── requirements.txt     # Python dependencies
├── .gitignore           # Version-control exclusions
└── README.md            # Project documentation
```

---

## Troubleshooting
* **Database connection** – run `python test_db.py --production` on PythonAnywhere.
* **E-mail failures** – verify Gmail app password and 2-FA settings.
* **Static files** – ensure `/static/` mapping in Web tab matches filesystem path.
* **Scheduler issues** – check task logs on PythonAnywhere if e-mails are not sent.

---

## Contributing
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`.
3. Follow PEP 8 and add unit tests where appropriate.
4. Commit with conventional messages and open a pull request.

---

## License
This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Roadmap / Future Enhancements
* **Web NFC Support** – planned addition of optional NFC tag reading/writing using the Web NFC API for supported Android devices. QR codes will remain fully supported as a fallback.
* **Role-based Access Control** – introduce admin and pharmacist roles for broader workflows.
* **REST API** – expose JSON endpoints for integration with external systems.
* **Search and Filtering** – advanced filtering by medicine name, factory and expiry range.
