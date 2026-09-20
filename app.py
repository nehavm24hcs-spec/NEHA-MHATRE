from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Book, Issue
from seed_books import books
from datetime import date, timedelta
from functools import wraps

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

# PC IPv4 address
# Mobile must be connected to the same Wi-Fi
app.config["SERVER_NAME"] = "192.168.0.100:5000"

db.init_app(app)


# =========================================================
# LOGIN REQUIRED
# =========================================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            # Save the current book URL
            # so user can return to it after login
            next_page = request.url

            return redirect(
                url_for(
                    "login",
                    next=next_page
                )
            )

        user = db.session.get(
            User,
            session["user_id"]
        )

        if not user:

            session.clear()

            flash(
                "Your session has expired. Please login again.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login to continue.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        user = db.session.get(
            User,
            session["user_id"]
        )

        if not user:

            session.clear()

            return redirect(
                url_for("login")
            )

        if user.role != "admin":

            flash(
                "Access denied. Admin privileges are required.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        return f(*args, **kwargs)

    return decorated_function


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
                f"Error generating QR for book {book.id}: {e}"
            )

    try:

        db.session.commit()

        print("----------------------------------------")
        print("QR CODE REGENERATION COMPLETED")
        print(f"QR codes generated : {generated_count}")
        print(f"Total books checked : {len(all_books)}")
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
        print(f"Existing books : {existing_books}")
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
        print(f"Books added : {added_count}")
        print("----------------------------------------")

    except Exception as e:

        db.session.rollback()

        print(
            f"Database error: {e}"
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
                f"Registration failed: {str(e)}",
                "error"
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

    # -----------------------------------------------------
    # Get the page from which login was requested
    # -----------------------------------------------------

    next_page = request.args.get(
        "next"
    )

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        # IMPORTANT:
        # Hidden input from login.html
        # keeps the QR book URL during POST
        form_next = request.form.get(
            "next",
            ""
        ).strip()

        if form_next:
            next_page = form_next

        user = User.query.filter_by(
            email=email
        ).first()

        # -------------------------------------------------
        # CHECK LOGIN
        # -------------------------------------------------

        if (
            user
            and check_password_hash(
                user.password,
                password
            )
        ):

            # Save next page BEFORE clearing session
            saved_page = next_page

            session.clear()

            session["user_id"] = user.id
            session["role"] = user.role

            flash(
                "Login successful!",
                "success"
            )

            # -------------------------------------------------
            # QR CODE BOOK PAGE REDIRECT
            # -------------------------------------------------

            if saved_page:

                return redirect(
                    saved_page
                )

            # -------------------------------------------------
            # NORMAL LOGIN
            # -------------------------------------------------

            if user.role == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )

            return redirect(
                url_for("dashboard")
            )

        # -------------------------------------------------
        # INVALID LOGIN
        # -------------------------------------------------

        flash(
            "Invalid email or password!",
            "error"
        )

        return render_template(
            "auth/login.html",
            next=next_page
        )

    # -----------------------------------------------------
    # LOGIN PAGE
    # -----------------------------------------------------

    return render_template(
        "auth/login.html",
        next=next_page
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # Empty fields
        if (
            not email
            or not new_password
            or not confirm_password
        ):

            flash(
                "Please fill in all fields.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        # Password length
        if len(new_password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        # Password confirmation
        if new_password != confirm_password:

            flash(
                "New password and confirm password do not match.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        # Find user
        user = User.query.filter_by(
            email=email
        ).first()

        if not user:

            flash(
                "Email address not found.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        # Update password
        try:

            user.password = generate_password_hash(
                new_password
            )

            db.session.commit()

            flash(
                "Password updated successfully! Please login.",
                "success"
            )

            return redirect(
                url_for("login")
            )

        except Exception as e:

            db.session.rollback()

            flash(
                f"Unable to update password: {str(e)}",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

    return render_template(
        "auth/forgot_password.html"
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = db.session.get(
        User,
        session["user_id"]
    )

    if user.role == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    total_books = Book.query.count()

    available_books = (
        db.session
        .query(
            db.func.coalesce(
                db.func.sum(Book.available),
                0
            )
        )
        .scalar()
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
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    user = db.session.get(
        User,
        session["user_id"]
    )

    total_books = Book.query.count()

    available_books = (
        db.session
        .query(
            db.func.coalesce(
                db.func.sum(Book.available),
                0
            )
        )
        .scalar()
    )

    total_copies = (
        db.session
        .query(
            db.func.coalesce(
                db.func.sum(Book.quantity),
                0
            )
        )
        .scalar()
    )

    total_students = User.query.filter_by(
        role="student"
    ).count()

    total_users = User.query.count()

    issued_books = Issue.query.filter_by(
        status="Issued"
    ).count()

    returned_books = Issue.query.filter_by(
        status="Returned"
    ).count()

    current_date = date.today()

    active_issues = Issue.query.filter_by(
        status="Issued"
    ).all()

    overdue_books = 0

    for issue in active_issues:

        if (
            issue.due_date
            and current_date > issue.due_date
        ):

            overdue_books += 1

    recent_books = (
        Book.query
        .order_by(
            Book.id.desc()
        )
        .limit(10)
        .all()
    )

    return render_template(

        "admin/dashboard.html",

        user=user,

        total_books=total_books,

        available_books=available_books,

        total_copies=total_copies,

        total_students=total_students,

        total_users=total_users,

        issued_books=issued_books,

        returned_books=returned_books,

        overdue_books=overdue_books,

        books=recent_books
    )


# =========================================================
# ADMIN - VIEW ALL USERS
# =========================================================

@app.route("/admin/users")
@admin_required
def admin_users():

    users = (
        User.query
        .order_by(
            User.id.desc()
        )
        .all()
    )

    return render_template(
        "admin/users.html",
        users=users
    )


# =========================================================
# ADMIN - VIEW ALL ISSUES
# =========================================================

@app.route("/admin/issues")
@admin_required
def admin_issues():

    issues = (
        Issue.query
        .order_by(
            Issue.id.desc()
        )
        .all()
    )

    current_date = date.today()

    for issue in issues:

        issue.is_overdue = False

        if (
            issue.status == "Issued"
            and issue.due_date
            and current_date > issue.due_date
        ):

            issue.is_overdue = True

    return render_template(

        "admin/issues.html",

        issues=issues,

        current_date=current_date
    )


# =========================================================
# BROWSE BOOKS
# =========================================================

@app.route("/books")
@login_required
def books_page():

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

    return render_template(

        "books/books.html",

        books=all_books,

        search=search,

        availability=availability
    )


# =========================================================
# LIVE BOOK SUGGESTIONS
# =========================================================

@app.route("/book-suggestions")
@login_required
def book_suggestions():

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
@login_required
def book_details(book_id):

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

    user = db.session.get(
        User,
        session["user_id"]
    )

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
@login_required
def issue_book(book_id):

    user = db.session.get(
        User,
        session["user_id"]
    )

    if user.role == "admin":

        flash(
            "Admin accounts cannot issue books.",
            "error"
        )

        return redirect(
            url_for(
                "book_details",
                book_id=book_id
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
            f"Unable to issue book: {str(e)}",
            "error"
        )

    return redirect(

        url_for(
            "book_details",
            book_id=book.id
        )
    )


# =========================================================
# MY BOOKS
# =========================================================

@app.route("/my-books")
@login_required
def my_books():

    user = db.session.get(
        User,
        session["user_id"]
    )

    if user.role == "admin":

        return redirect(
            url_for("admin_dashboard")
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
# RETURN BOOK
# =========================================================

@app.route(
    "/return-book/<int:issue_id>",
    methods=["POST"]
)
@login_required
def return_book(issue_id):

    user = db.session.get(
        User,
        session["user_id"]
    )

    if user.role == "admin":

        flash(
            "Admin accounts cannot return student books from this page.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
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

    if issue.user_id != user.id:

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
            f"Unable to return book: {str(e)}",
            "error"
        )

    return redirect(
        url_for("my_books")
    )


# =========================================================
# ADD BOOK - ADMIN ONLY
# =========================================================

@app.route(
    "/add-book",
    methods=["GET", "POST"]
)
@admin_required
def add_book():

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
                f"Unable to add book: {str(e)}",
                "error"
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
@admin_required
def delete_book(book_id):

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

        Issue.query.filter_by(
            book_id=book.id
        ).delete(
            synchronize_session=False
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
            f"Unable to delete book: {str(e)}",
            "error"
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

    # Add default books only if database is empty
    add_default_books()

    # Generate/update QR codes
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
