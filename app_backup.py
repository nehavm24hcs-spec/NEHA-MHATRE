from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash
)

from models import db, User, Book, Issue
from seed_books import books

from datetime import date, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

import qrcode
import os


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "librix-secret-key-2026"


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///library.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ---------------------------------------------------------
# PC IPv4 ADDRESS
# Mobile must be connected to same Wi-Fi
# ---------------------------------------------------------

app.config["SERVER_NAME"] = "192.168.0.100:5000"

db.init_app(app)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_current_user():

    if "user_id" not in session:
        return None

    user = db.session.get(
        User,
        session["user_id"]
    )

    return user


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required():

    if "user_id" not in session:
        return False

    user = get_current_user()

    if not user:
        session.clear()
        return False

    return True


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required():

    if "user_id" not in session:
        return False

    user = get_current_user()

    if not user:
        session.clear()
        return False

    if user.role != "admin":
        return False

    return True


# =========================================================
# PASSWORD CHECK
# =========================================================

def verify_password(stored_password, entered_password):

    # -----------------------------------------------------
    # New users have hashed passwords
    # -----------------------------------------------------

    try:

        if check_password_hash(
            stored_password,
            entered_password
        ):

            return True

    except Exception:
        pass

    # -----------------------------------------------------
    # Compatibility with old plain-text passwords
    # -----------------------------------------------------

    return stored_password == entered_password


# =========================================================
# QR CODE GENERATION
# =========================================================

def generate_book_qr(book_id):

    qr_folder = os.path.join(
        app.static_folder,
        "qr_codes"
    )

    os.makedirs(
        qr_folder,
        exist_ok=True
    )

    book_url = url_for(
        "book_details",
        book_id=book_id,
        _external=True
    )

    print(
        f"QR URL for book {book_id}: {book_url}"
    )

    qr = qrcode.make(
        book_url
    )

    qr_path = os.path.join(
        qr_folder,
        f"book_{book_id}.png"
    )

    qr.save(
        qr_path
    )

    return f"qr_codes/book_{book_id}.png"


# =========================================================
# REGENERATE ALL QR CODES
# =========================================================

def regenerate_all_book_qr_codes():

    all_books = Book.query.all()

    generated_count = 0

    for book in all_books:

        try:

            book.qr_code = generate_book_qr(
                book.id
            )

            generated_count += 1

        except Exception as e:

            print(
                f"Error generating QR for book "
                f"{book.id}: {e}"
            )

    try:

        db.session.commit()

        print("----------------------------------------")
        print("QR CODE REGENERATION COMPLETED")
        print(
            f"QR codes generated : {generated_count}"
        )
        print(
            f"Total books checked : {len(all_books)}"
        )
        print("----------------------------------------")

    except Exception as e:

        db.session.rollback()

        print(
            f"QR code database error: {e}"
        )


# =========================================================
# ADD DEFAULT BOOKS
# =========================================================

def add_default_books():

    existing_books = Book.query.count()

    if existing_books > 0:

        print("----------------------------------------")
        print("BOOK DATABASE ALREADY CONTAINS BOOKS")
        print(
            f"Existing books : {existing_books}"
        )
        print("No duplicate books added.")
        print("----------------------------------------")

        return

    added_count = 0

    for book_data in books:

        try:

            new_book = Book(

                title=book_data["title"],

                author=book_data["author"],

                isbn=book_data["isbn"],

                category=book_data["category"],

                quantity=book_data["quantity"],

                available=book_data["quantity"],

                shelf=book_data["shelf"]
            )

            db.session.add(
                new_book
            )

            db.session.flush()

            new_book.qr_code = generate_book_qr(
                new_book.id
            )

            added_count += 1

        except Exception as e:

            print(
                f"Error adding book: {e}"
            )

    try:

        db.session.commit()

        print("----------------------------------------")
        print("DEFAULT BOOKS ADDED")
        print(
            f"Books added : {added_count}"
        )
        print("----------------------------------------")

    except Exception as e:

        db.session.rollback()

        print(
            f"Database error: {e}"
        )


# =========================================================
# CREATE DEFAULT ADMIN
# =========================================================

def create_default_admin():

    admin_email = "admin@librix.com"

    existing_admin = User.query.filter_by(
        email=admin_email
    ).first()

    if existing_admin:

        # -------------------------------------------------
        # Make sure existing account is admin
        # -------------------------------------------------

        if existing_admin.role != "admin":

            existing_admin.role = "admin"

            db.session.commit()

        return

    admin = User(

        name="LIBRIX Administrator",

        email=admin_email,

        password=generate_password_hash(
            "admin123"
        ),

        role="admin"
    )

    try:

        db.session.add(
            admin
        )

        db.session.commit()

        print("----------------------------------------")
        print("DEFAULT ADMIN CREATED")
        print("Email    : admin@librix.com")
        print("Password : admin123")
        print("----------------------------------------")

    except Exception as e:

        db.session.rollback()

        print(
            f"Unable to create admin: {e}"
        )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if (
            not name
            or not email
            or not password
        ):

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:

            flash(
                "Email already registered!",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # -------------------------------------------------
        # PUBLIC REGISTRATION ALWAYS CREATES STUDENT
        # -------------------------------------------------

        new_user = User(

            name=name,

            email=email,

            password=generate_password_hash(
                password
            ),

            role="student"
        )

        try:

            db.session.add(
                new_user
            )

            db.session.commit()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            db.session.rollback()

            flash(
                "Registration failed. Please try again.",
                "error"
            )

            print(
                f"Registration error: {e}"
            )

            return redirect(
                url_for("register")
            )

    return render_template(
        "auth/register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        user = User.query.filter_by(
            email=email
        ).first()

        if user and verify_password(
            user.password,
            password
        ):

            # -------------------------------------------------
            # Upgrade old plain-text password to hash
            # -------------------------------------------------

            if not user.password.startswith(
                ("pbkdf2:", "scrypt:")
            ):

                user.password = generate_password_hash(
                    password
                )

                try:

                    db.session.commit()

                except Exception:

                    db.session.rollback()

            session.clear()

            session["user_id"] = user.id

            # -------------------------------------------------
            # ROLE BASED LOGIN
            # -------------------------------------------------

            if user.role == "admin":

                flash(
                    "Welcome Admin!",
                    "success"
                )

                return redirect(
                    url_for("admin_dashboard")
                )

            flash(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password!",
            "error"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "auth/login.html"
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not login_required():

        return redirect(
            url_for("login")
        )

    user = get_current_user()

    # -----------------------------------------------------
    # ADMIN SHOULD GO TO ADMIN DASHBOARD
    # -----------------------------------------------------

    if user.role == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    total_books = Book.query.count()

    available_books = (
        db.session
        .query(
            db.func.sum(Book.available)
        )
        .scalar()
        or 0
    )

    borrowed_books = Issue.query.filter_by(
        user_id=user.id,
        status="Issued"
    ).count()

    all_activities = (
        Issue.query
        .filter_by(
            user_id=user.id
        )
        .order_by(
            Issue.id.desc()
        )
        .all()
    )

    recent_activities = []

    current_date = date.today()

    for activity in all_activities:

        book = db.session.get(
            Book,
            activity.book_id
        )

        if not book:
            continue

        activity.activity_type = "Issued"

        activity.activity_date = (
            activity.issue_date
            if activity.issue_date
            else date.min
        )

        activity.is_overdue = False

        activity.days_left = None

        activity.activity_book = book

        if (
            activity.status == "Returned"
            and activity.return_date
        ):

            activity.activity_type = "Returned"

            activity.activity_date = (
                activity.return_date
            )

        elif activity.status == "Issued":

            if activity.due_date:

                if current_date > activity.due_date:

                    activity.is_overdue = True

                    activity.days_left = (
                        current_date
                        - activity.due_date
                    ).days

                else:

                    activity.days_left = (
                        activity.due_date
                        - current_date
                    ).days

        recent_activities.append(
            activity
        )

    recent_activities.sort(
        key=lambda activity: (
            activity.activity_date
            if activity.activity_date
            else date.min
        ),
        reverse=True
    )

    recent_activities = recent_activities[:10]

    activity_count = len(
        recent_activities
    )

    return render_template(

        "auth/dashboard.html",

        user=user,

        total_books=total_books,

        available_books=available_books,

        borrowed_books=borrowed_books,

        recent_activities=recent_activities,

        activity_count=activity_count,

        current_date=current_date
    )


# =========================================================
# BROWSE BOOKS
# =========================================================

@app.route("/books")
def books_page():

    if not login_required():

        return redirect(
            url_for("login")
        )

    search = request.args.get(
        "search",
        ""
    ).strip()

    availability = request.args.get(
        "availability",
        ""
    ).strip().lower()

    query = Book.query

    if search:

        search_pattern = f"%{search}%"

        query = query.filter(

            db.or_(

                Book.title.ilike(
                    search_pattern
                ),

                Book.author.ilike(
                    search_pattern
                ),

                Book.category.ilike(
                    search_pattern
                ),

                Book.isbn.ilike(
                    search_pattern
                )
            )
        )

    if availability == "available":

        query = query.filter(
            Book.available > 0
        )

    all_books = (
        query
        .order_by(
            Book.title.asc()
        )
        .all()
    )

    user = get_current_user()

    return render_template(

        "books/books.html",

        books=all_books,

        search=search,

        availability=availability,

        user=user
    )


# =========================================================
# LIVE BOOK SUGGESTIONS
# =========================================================

@app.route("/book-suggestions")
def book_suggestions():

    if not login_required():

        return {
            "suggestions": []
        }

    search = request.args.get(
        "q",
        ""
    ).strip()

    if not search:

        return {
            "suggestions": []
        }

    search_pattern = f"{search}%"

    suggestion_books = (
        Book.query
        .filter(
            Book.title.ilike(
                search_pattern
            )
        )
        .order_by(
            Book.title.asc()
        )
        .limit(8)
        .all()
    )

    suggestions = []

    for book in suggestion_books:

        suggestions.append({

            "id": book.id,

            "title": book.title,

            "author": book.author
        })

    return {
        "suggestions": suggestions
    }


# =========================================================
# BOOK DETAILS
# =========================================================

@app.route(
    "/book/<int:book_id>"
)
def book_details(book_id):

    if not login_required():

        return redirect(
            url_for("login")
        )

    book = db.session.get(
        Book,
        book_id
    )

    if not book:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("books_page")
        )

    user = get_current_user()

    current_issue = Issue.query.filter_by(

        user_id=user.id,

        book_id=book.id,

        status="Issued"

    ).first()

    return render_template(

        "books/book_details.html",

        book=book,

        user=user,

        current_issue=current_issue
    )


# =========================================================
# ISSUE / BORROW BOOK
# =========================================================

@app.route(
    "/issue-book/<int:book_id>",
    methods=["POST"]
)
def issue_book(book_id):

    if not login_required():

        return redirect(
            url_for("login")
        )

    user = get_current_user()

    # -----------------------------------------------------
    # ADMIN CANNOT ISSUE BOOKS
    # -----------------------------------------------------

    if user.role == "admin":

        flash(
            "Admin accounts cannot issue books.",
            "error"
        )

        return redirect(
            url_for(
                "admin_dashboard"
            )
        )

    book = db.session.get(
        Book,
        book_id
    )

    if not book:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("books_page")
        )

    if book.available <= 0:

        flash(
            "This book is currently not available.",
            "error"
        )

        return redirect(
            url_for(
                "book_details",
                book_id=book.id
            )
        )

    existing_issue = Issue.query.filter_by(

        user_id=user.id,

        book_id=book.id,

        status="Issued"

    ).first()

    if existing_issue:

        flash(
            "You have already issued this book.",
            "error"
        )

        return redirect(
            url_for(
                "book_details",
                book_id=book.id
            )
        )

    issue_date = date.today()

    due_date = (
        issue_date
        + timedelta(days=14)
    )

    new_issue = Issue(

        user_id=user.id,

        book_id=book.id,

        issue_date=issue_date,

        due_date=due_date,

        return_date=None,

        status="Issued"
    )

    book.available -= 1

    try:

        db.session.add(
            new_issue
        )

        db.session.commit()

        flash(

            f"'{book.title}' issued successfully! "
            f"Expected return date: "
            f"{due_date.strftime('%d-%m-%Y')}",

            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to issue book. Please try again.",
            "error"
        )

        print(
            f"Issue error: {e}"
        )

    return redirect(

        url_for(
            "book_details",
            book_id=book.id
        )
    )


# =========================================================
# MY BOOKS - STUDENT ONLY
# =========================================================

@app.route("/my-books")
def my_books():

    if not login_required():

        return redirect(
            url_for("login")
        )

    user = get_current_user()

    if user.role == "admin":

        return redirect(
            url_for("admin_issues")
        )

    issued_books = (
        Issue.query
        .filter_by(
            user_id=user.id
        )
        .order_by(
            Issue.issue_date.desc()
        )
        .all()
    )

    current_date = date.today()

    return render_template(

        "books/my_books.html",

        user=user,

        issued_books=issued_books,

        current_date=current_date
    )


# =========================================================
# RETURN BOOK - STUDENT
# =========================================================

@app.route(
    "/return-book/<int:issue_id>",
    methods=["POST"]
)
def return_book(issue_id):

    if not login_required():

        return redirect(
            url_for("login")
        )

    issue = db.session.get(
        Issue,
        issue_id
    )

    if not issue:

        flash(
            "Issue record not found.",
            "error"
        )

        return redirect(
            url_for("my_books")
        )

    # -----------------------------------------------------
    # USER CAN RETURN ONLY THEIR OWN BOOK
    # -----------------------------------------------------

    if issue.user_id != session["user_id"]:

        flash(
            "You cannot return this book.",
            "error"
        )

        return redirect(
            url_for("my_books")
        )

    if issue.status != "Issued":

        flash(
            "This book has already been returned.",
            "error"
        )

        return redirect(
            url_for("my_books")
        )

    book = db.session.get(
        Book,
        issue.book_id
    )

    try:

        issue.return_date = date.today()

        issue.status = "Returned"

        if book:

            book.available += 1

            if book.available > book.quantity:

                book.available = book.quantity

        db.session.commit()

        flash(

            (
                f"'{book.title}' returned successfully!"
                if book
                else "Book returned successfully!"
            ),

            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to return book. Please try again.",
            "error"
        )

        print(
            f"Return error: {e}"
        )

    return redirect(
        url_for("my_books")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    total_books = Book.query.count()

    total_copies = (
        db.session
        .query(
            db.func.sum(Book.quantity)
        )
        .scalar()
        or 0
    )

    available_copies = (
        db.session
        .query(
            db.func.sum(Book.available)
        )
        .scalar()
        or 0
    )

    total_students = User.query.filter_by(
        role="student"
    ).count()

    total_admins = User.query.filter_by(
        role="admin"
    ).count()

    active_issues = Issue.query.filter_by(
        status="Issued"
    ).count()

    returned_books = Issue.query.filter_by(
        status="Returned"
    ).count()

    overdue_books = 0

    current_date = date.today()

    active_issue_list = Issue.query.filter_by(
        status="Issued"
    ).all()

    for issue in active_issue_list:

        if issue.due_date and current_date > issue.due_date:

            overdue_books += 1

    recent_issues = (
        Issue.query
        .order_by(
            Issue.id.desc()
        )
        .limit(10)
        .all()
    )

    return render_template(

        "admin/dashboard.html",

        user=get_current_user(),

        total_books=total_books,

        total_copies=total_copies,

        available_copies=available_copies,

        total_students=total_students,

        total_admins=total_admins,

        active_issues=active_issues,

        returned_books=returned_books,

        overdue_books=overdue_books,

        recent_issues=recent_issues,

        current_date=current_date
    )


# =========================================================
# ADMIN - USERS
# =========================================================

@app.route("/admin/users")
def admin_users():

    if not admin_required():

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    users = (
        User.query
        .order_by(
            User.id.desc()
        )
        .all()
    )

    return render_template(

        "admin/users.html",

        user=get_current_user(),

        users=users
    )


# =========================================================
# ADMIN - CHANGE USER ROLE
# =========================================================

@app.route(
    "/admin/change-role/<int:user_id>",
    methods=["POST"]
)
def change_user_role(user_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        flash(
            "User not found.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    # -----------------------------------------------------
    # ADMIN CANNOT CHANGE OWN ROLE
    # -----------------------------------------------------

    if user.id == session["user_id"]:

        flash(
            "You cannot change your own role.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    new_role = request.form.get(
        "role",
        ""
    ).strip().lower()

    if new_role not in [
        "student",
        "admin"
    ]:

        flash(
            "Invalid role.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    try:

        user.role = new_role

        db.session.commit()

        flash(
            f"{user.name}'s role changed to {new_role}.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to change user role.",
            "error"
        )

        print(
            f"Role change error: {e}"
        )

    return redirect(
        url_for("admin_users")
    )


# =========================================================
# ADMIN - DELETE USER
# =========================================================

@app.route(
    "/admin/delete-user/<int:user_id>",
    methods=["POST"]
)
def admin_delete_user(user_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    user = db.session.get(
        User,
        user_id
    )

    if not user:

        flash(
            "User not found.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    # -----------------------------------------------------
    # ADMIN CANNOT DELETE SELF
    # -----------------------------------------------------

    if user.id == session["user_id"]:

        flash(
            "You cannot delete your own account.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    # -----------------------------------------------------
    # DO NOT DELETE USER WITH ACTIVE ISSUE
    # -----------------------------------------------------

    active_issue = Issue.query.filter_by(

        user_id=user.id,

        status="Issued"

    ).first()

    if active_issue:

        flash(
            "Cannot delete this user because they have an issued book.",
            "error"
        )

        return redirect(
            url_for("admin_users")
        )

    try:

        db.session.delete(
            user
        )

        db.session.commit()

        flash(
            "User deleted successfully.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to delete user.",
            "error"
        )

        print(
            f"Delete user error: {e}"
        )

    return redirect(
        url_for("admin_users")
    )


# =========================================================
# ADMIN - ALL ISSUES
# =========================================================

@app.route("/admin/issues")
def admin_issues():

    if not admin_required():

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    issues = (
        Issue.query
        .order_by(
            Issue.id.desc()
        )
        .all()
    )

    current_date = date.today()

    return render_template(

        "admin/issues.html",

        user=get_current_user(),

        issues=issues,

        current_date=current_date
    )


# =========================================================
# ADMIN - RETURN ANY BOOK
# =========================================================

@app.route(
    "/admin/return-book/<int:issue_id>",
    methods=["POST"]
)
def admin_return_book(issue_id):

    if not admin_required():

        flash(
            "Admin access required.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    issue = db.session.get(
        Issue,
        issue_id
    )

    if not issue:

        flash(
            "Issue record not found.",
            "error"
        )

        return redirect(
            url_for("admin_issues")
        )

    if issue.status != "Issued":

        flash(
            "This book has already been returned.",
            "error"
        )

        return redirect(
            url_for("admin_issues")
        )

    book = db.session.get(
        Book,
        issue.book_id
    )

    try:

        issue.status = "Returned"

        issue.return_date = date.today()

        if book:

            book.available += 1

            if book.available > book.quantity:

                book.available = book.quantity

        db.session.commit()

        flash(
            "Book returned successfully.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to return book.",
            "error"
        )

        print(
            f"Admin return error: {e}"
        )

    return redirect(
        url_for("admin_issues")
    )


# =========================================================
# ADD BOOK - ADMIN ONLY
# =========================================================

@app.route(
    "/add-book",
    methods=["GET", "POST"]
)
def add_book():

    if not admin_required():

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        flash(
            "Only admin can add books.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        author = request.form.get(
            "author",
            ""
        ).strip()

        isbn = request.form.get(
            "isbn",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        shelf = request.form.get(
            "shelf",
            ""
        ).strip()

        if (
            not title
            or not author
            or not isbn
            or not category
            or not shelf
        ):

            flash(
                "Please fill in all book details.",
                "error"
            )

            return redirect(
                url_for("add_book")
            )

        try:

            quantity = int(
                request.form.get(
                    "quantity",
                    0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            flash(
                "Quantity must be a number.",
                "error"
            )

            return redirect(
                url_for("add_book")
            )

        if quantity <= 0:

            flash(
                "Quantity must be greater than 0.",
                "error"
            )

            return redirect(
                url_for("add_book")
            )

        existing_book = Book.query.filter_by(
            isbn=isbn
        ).first()

        if existing_book:

            flash(
                "A book with this ISBN already exists!",
                "error"
            )

            return redirect(
                url_for("add_book")
            )

        new_book = Book(

            title=title,

            author=author,

            isbn=isbn,

            category=category,

            quantity=quantity,

            available=quantity,

            shelf=shelf
        )

        try:

            db.session.add(
                new_book
            )

            db.session.flush()

            new_book.qr_code = generate_book_qr(
                new_book.id
            )

            db.session.commit()

            flash(
                "Book added successfully!",
                "success"
            )

        except Exception as e:

            db.session.rollback()

            flash(
                "Unable to add book.",
                "error"
            )

            print(
                f"Add book error: {e}"
            )

        return redirect(
            url_for("books_page")
        )

    return render_template(
        "books/add_book.html"
    )


# =========================================================
# DELETE BOOK - ADMIN ONLY
# =========================================================

@app.route(
    "/delete-book/<int:book_id>",
    methods=["POST"]
)
def delete_book(book_id):

    if not admin_required():

        if "user_id" not in session:

            return redirect(
                url_for("login")
            )

        flash(
            "Only admin can delete books.",
            "error"
        )

        return redirect(
            url_for("dashboard")
        )

    book = db.session.get(
        Book,
        book_id
    )

    if not book:

        flash(
            "Book not found.",
            "error"
        )

        return redirect(
            url_for("books_page")
        )

    try:

        active_issue = Issue.query.filter_by(

            book_id=book.id,

            status="Issued"

        ).first()

        if active_issue:

            flash(

                "This book cannot be deleted "
                "because it is currently issued.",

                "error"
            )

            return redirect(
                url_for("books_page")
            )

        qr_path = os.path.join(

            app.static_folder,

            "qr_codes",

            f"book_{book_id}.png"
        )

        # -------------------------------------------------
        # Delete old issue history for this book
        # -------------------------------------------------

        old_issues = Issue.query.filter_by(
            book_id=book.id
        ).all()

        for old_issue in old_issues:

            db.session.delete(
                old_issue
            )

        db.session.delete(
            book
        )

        db.session.commit()

        if os.path.exists(qr_path):

            os.remove(
                qr_path
            )

        flash(
            "Book deleted successfully!",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            "Unable to delete book.",
            "error"
        )

        print(
            f"Delete book error: {e}"
        )

    return redirect(
        url_for("books_page")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

with app.app_context():

    db.create_all()

    # -----------------------------------------------------
    # Create default admin
    # -----------------------------------------------------

    create_default_admin()

    # -----------------------------------------------------
    # Add default books
    # -----------------------------------------------------

    add_default_books()

    # -----------------------------------------------------
    # Regenerate QR codes
    # -----------------------------------------------------

    regenerate_all_book_qr_codes()


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )