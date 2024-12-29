# **ProMed: Medicine Information Management System**

ProMed is a web application designed to manage and retrieve information about medicines using QR codes and NFC tags. The system allows users to add, view, and track medicine details, including expiry and manufacturing dates.

---

## **Features**
- **Home Screen**:
  - Introduction to the service with options: Medicine Details, Add Medicine, and About Us.
- **Add Medicine**:
  - Add medicine details such as name, factory name, manufacturing date, expiry date, and uses.
  - Generate unique QR codes for each medicine.
- **Medicine Details**:
  - View detailed information about each medicine by scanning a QR code or NFC tag.
- **About Us**:
  - Overview of the application and its features.

---

## **Technologies Used**
- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML, CSS (No React)
- **QR Code Generation**: PyQRCode library
- **NFC Tag Support**: External hardware integration (optional)

---

## **Installation and Setup**
### Prerequisites
- Python 3.8+
- pip (Python package manager)
- SQLite installed

### Steps
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/ProMed.git
   cd ProMed
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up the Database**:
   - Run the following commands in Python to initialize the database:
     ```python
     from app import db
     db.create_all()
     ```

4. **Run the Application**:
   ```bash
   flask run
   ```
   The application will be accessible at `http://127.0.0.1:5000/`.

5. **Access the Application**:
   - Navigate to the home page and start exploring the features.

---

## **Deployment**
### Using Tunneling with Cloudflared
1. Install Cloudflared:
   ```bash
   npm install -g cloudflared
   ```
2. Run the Flask application locally:
   ```bash
   flask run
   ```
3. Start the Cloudflared tunnel:
   ```bash
   cloudflared tunnel --url http://127.0.0.1:5000
   ```
   This will generate a public URL that you can share to access your application.

### Other Deployment Options
The project can also be deployed on cloud platforms such as:
- **Heroku**
- **PythonAnywhere**
- **Google Cloud**

Ensure all dependencies and database configurations are updated in the deployment environment.

---

## **Usage**
1. **Add Medicine**:
   - Navigate to the "Add Medicine" page, fill out the form, and submit the details.
   - A QR code will be generated and stored in the `/static/qrcodes` folder.

2. **View Medicine Details**:
   - Scan the QR code with a compatible scanner or navigate to the "Medicine Details" page to view all medicines.

3. **About Us**:
   - Learn about the application's features and functionalities.

---

## **Project Structure**
```
ProMed/
├── static/
│   ├── css/               # CSS files for styling
│   │   ├── aboutus.css
│   │   ├── addmedicine.css
│   │   ├── home.css
│   │   ├── login.css
│   │   ├── medicinedetails.css
│   │   ├── signup.css
│   │   └── viewmedicine.css
│   ├── qrcodes/           # Folder to store QR codes (PNG format)
├── templates/             # HTML templates
│   ├── aboutus.html
│   ├── addmedicine.html
│   ├── home.html
│   ├── login.html
│   ├── medicinedetails.html
│   ├── signup.html
│   └── viewmedicine.html
├── app.py                 # Main Flask application
├── check_users.py         # Script to check user-related operations
├── models.py              # Database models
├── promed.db              # SQLite database file
├── requirements.txt       # List of dependencies
└── README.md              # Project documentation
```

---

## **Contributing**
We welcome contributions! Follow these steps to contribute:
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-branch
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m "Add new feature"
   ```
4. Push to your branch:
   ```bash
   git push origin feature-branch
   ```
5. Open a pull request.

---

## **License**
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## **Acknowledgments**
- Flask documentation for its excellent guides.
- PyQRCode library for seamless QR code generation.

Feel free to customize the content, especially URLs and project details, as needed!

