from app import app
from models import db, User
from werkzeug.security import generate_password_hash


# =========================================================
# CREATE ADMIN ACCOUNT
# =========================================================

with app.app_context():

    admin_email = "admin@librix.com"
    admin_password = "admin123"

    # Check if admin already exists
    existing_admin = User.query.filter_by(
        email=admin_email
    ).first()

    if existing_admin:

        print("----------------------------------------")
        print("ADMIN ACCOUNT ALREADY EXISTS")
        print(f"Email : {admin_email}")
        print("----------------------------------------")

    else:

        admin = User(

            name="LIBRIX Admin",

            email=admin_email,

            password=generate_password_hash(
                admin_password
            ),

            role="admin"
        )

        db.session.add(admin)
        db.session.commit()

        print("----------------------------------------")
        print("ADMIN ACCOUNT CREATED SUCCESSFULLY")
        print("----------------------------------------")
        print(f"Email    : {admin_email}")
        print(f"Password : {admin_password}")
        print("Role     : admin")
        print("----------------------------------------")