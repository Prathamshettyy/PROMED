#!/usr/bin/env python3
"""
Database connection test script for ProMed
Run this to verify your database setup is working correctly

Usage:
    python3 test_db.py              # Test local SQLite database
    python3 test_db.py --production # Test PythonAnywhere MySQL database
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables based on command line arguments"""
    if len(sys.argv) > 1 and sys.argv[1] == '--production':
        # Force production environment detection
        if not os.getenv('PYTHONANYWHERE_USERNAME'):
            print("⚠️  Production mode requested but PYTHONANYWHERE_USERNAME not set in environment")
            username = input("Enter your PythonAnywhere username: ").strip()
            if username:
                os.environ['PYTHONANYWHERE_USERNAME'] = username
                print(f"✅ Set PYTHONANYWHERE_USERNAME={username}")
            else:
                print("❌ Username required for production testing")
                return False
        return True
    else:
        print("🏠 Testing local SQLite database")
        # Ensure we're NOT in production mode
        if 'PYTHONANYWHERE_USERNAME' in os.environ:
            del os.environ['PYTHONANYWHERE_USERNAME']
        return True

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from app import app, db, User, Medicine
        print("✅ Successfully imported Flask app and models")
        return app, db, User, Medicine
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure you're in the correct directory")
        print("   2. Activate your virtual environment: source promed-env/bin/activate")
        print("   3. Install dependencies: pip install -r requirements.txt")
        return None, None, None, None
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        return None, None, None, None

def test_database_connection(app, db):
    """Test basic database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        with app.app_context():
            # Test basic database connection
            db.engine.execute('SELECT 1')
            print("✅ Database connection successful!")
            
            # Get database info
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')
            if 'mysql' in db_url:
                db_type = "MySQL (Production)"
            elif 'sqlite' in db_url:
                db_type = "SQLite (Development)"
            else:
                db_type = "Unknown"
            
            print(f"📊 Database type: {db_type}")
            return True
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   1. Check your .env file has correct database credentials")
        print("   2. Ensure MySQL database exists in PythonAnywhere (for production)")
        print("   3. Verify database permissions")
        return False

def test_table_structure(app, db):
    """Test database table structure"""
    print("\n🔍 Testing table structure...")
    
    try:
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"📋 Found {len(tables)} tables: {tables}")
            
            required_tables = ['user', 'medicine']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing required tables: {missing_tables}")
                print("🔧 Attempting to create missing tables...")
                
                try:
                    db.create_all()
                    # Check again
                    new_tables = inspect(db.engine).get_table_names()
                    print(f"✅ Tables created successfully! Now have: {new_tables}")
                except Exception as create_error:
                    print(f"❌ Error creating tables: {create_error}")
                    return False
            else:
                print("✅ All required tables exist!")
            
            # Test table structure details
            for table_name in ['user', 'medicine']:
                if table_name in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns(table_name)]
                    print(f"   📄 {table_name} columns: {columns}")
            
            return True
            
    except Exception as e:
        print(f"❌ Table structure test failed: {e}")
        return False

def test_crud_operations(app, db, User, Medicine):
    """Test basic CRUD operations"""
    print("\n🔍 Testing CRUD operations...")
    
    try:
        with app.app_context():
            from werkzeug.security import generate_password_hash
            from datetime import date, timedelta
            
            # Test user creation (if not exists)
            test_username = 'test_user_db_check'
            existing_user = User.query.filter_by(username=test_username).first()
            
            if existing_user:
                print(f"✅ Test user '{test_username}' already exists")
                test_user = existing_user
            else:
                print(f"🔧 Creating test user '{test_username}'...")
                test_user = User(
                    username=test_username,
                    email='test@promed-test.com',
                    password=generate_password_hash('test123')
                )
                db.session.add(test_user)
                db.session.commit()
                print(f"✅ Test user created with ID: {test_user.id}")
            
            # Test medicine creation
            test_medicine_name = 'Test Medicine DB Check'
            existing_medicine = Medicine.query.filter_by(name=test_medicine_name).first()
            
            if not existing_medicine:
                print(f"🔧 Creating test medicine...")
                test_medicine = Medicine(
                    name=test_medicine_name,
                    factory_name='Test Factory',
                    manufacturing_date=date.today(),
                    expiry_date=date.today() + timedelta(days=365),
                    uses='Testing database connection',
                    qr_code='test-qr-code.png',
                    user_id=test_user.id
                )
                db.session.add(test_medicine)
                db.session.commit()
                print(f"✅ Test medicine created with ID: {test_medicine.id}")
            else:
                print(f"✅ Test medicine already exists")
            
            # Test queries
            user_count = User.query.count()
            medicine_count = Medicine.query.count()
            
            print(f"📊 Database statistics:")
            print(f"   👥 Total users: {user_count}")
            print(f"   💊 Total medicines: {medicine_count}")
            
            # Test relationship
            user_medicines = Medicine.query.filter_by(user_id=test_user.id).count()
            print(f"   🔗 Medicines for test user: {user_medicines}")
            
            print("✅ All CRUD operations successful!")
            return True
            
    except Exception as e:
        print(f"❌ CRUD operations failed: {e}")
        db.session.rollback()
        print("\n💡 This might indicate:")
        print("   1. Database permissions issues")
        print("   2. Table structure problems")
        print("   3. Foreign key constraint issues")
        return False

def test_environment_config(app):
    """Test environment configuration"""
    print("\n🔍 Testing environment configuration...")
    
    try:
        config_items = [
            ('SECRET_KEY', app.config.get('SECRET_KEY')),
            ('SQLALCHEMY_DATABASE_URI', app.config.get('SQLALCHEMY_DATABASE_URI')),
            ('SQLALCHEMY_TRACK_MODIFICATIONS', app.config.get('SQLALCHEMY_TRACK_MODIFICATIONS')),
            ('MAIL_SERVER', app.config.get('MAIL_SERVER')),
            ('MAIL_USERNAME', app.config.get('MAIL_USERNAME')),
        ]
        
        print("⚙️  Configuration check:")
        for key, value in config_items:
            if key == 'SECRET_KEY':
                status = "✅ Set" if value and value != 'a-secure-dev-secret-key-change-this' else "⚠️  Default/Missing"
            elif key == 'SQLALCHEMY_DATABASE_URI':
                status = f"✅ {value[:20]}..." if value else "❌ Missing"
            elif key == 'MAIL_USERNAME':
                status = "✅ Set" if value else "⚠️  Not configured (emails disabled)"
            else:
                status = f"✅ {value}" if value is not None else "❌ Missing"
            
            print(f"   {key}: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment configuration test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 ProMed Database Test Suite")
    print("=" * 40)
    
    # Step 1: Setup environment
    if not setup_environment():
        return 1
    
    # Step 2: Test imports
    app, db, User, Medicine = test_imports()
    if not all([app, db, User, Medicine]):
        return 1
    
    # Step 3: Test database connection
    if not test_database_connection(app, db):
        return 1
    
    # Step 4: Test table structure
    if not test_table_structure(app, db):
        return 1
    
    # Step 5: Test CRUD operations
    if not test_crud_operations(app, db, User, Medicine):
        return 1
    
    # Step 6: Test environment configuration
    if not test_environment_config(app):
        print("⚠️  Some configuration issues found, but database is working")
    
    print("\n🎉 All database tests passed!")
    print("\n✅ Your ProMed database is ready for deployment!")
    
    # Final recommendations
    print("\n📝 Recommendations:")
    if 'mysql' in app.config.get('SQLALCHEMY_DATABASE_URI', '').lower():
        print("   • MySQL database is working correctly")
        print("   • Make sure to configure your web app settings in PythonAnywhere")
    else:
        print("   • SQLite database is working correctly")
        print("   • For production deployment, ensure MySQL is configured")
    
    if not app.config.get('MAIL_USERNAME'):
        print("   • Configure email settings for expiry alerts")
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)