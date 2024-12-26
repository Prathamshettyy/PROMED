from app import app, db, User  # Import app, db, and User model

# Start the application context
with app.app_context():
    users = User.query.all()  # Query all users
    for user in users:
        print(user.username, user.email)  # Print each user's username and email
