from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# =========================================================
# USER MODEL
# =========================================================

class User(db.Model):

    __tablename__ = "user"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    # -----------------------------------------------------
    # Password is stored as HASH, not plain text
    # -----------------------------------------------------

    password = db.Column(
        db.String(255),
        nullable=False
    )

    # -----------------------------------------------------
    # Allowed roles:
    # student
    # admin
    # -----------------------------------------------------

    role = db.Column(
        db.String(20),
        nullable=False,
        default="student"
    )

    # -----------------------------------------------------
    # Relationship with Issue
    # -----------------------------------------------------

    issues = db.relationship(
        "Issue",
        back_populates="user",
        cascade="all, delete-orphan"
    )


# =========================================================
# BOOK MODEL
# =========================================================

class Book(db.Model):

    __tablename__ = "book"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    title = db.Column(
        db.String(200),
        nullable=False
    )

    author = db.Column(
        db.String(150),
        nullable=False
    )

    isbn = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    category = db.Column(
        db.String(100),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    available = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    shelf = db.Column(
        db.String(50),
        nullable=False
    )

    qr_code = db.Column(
        db.String(200)
    )

    # -----------------------------------------------------
    # Relationship with Issue
    # -----------------------------------------------------

    issues = db.relationship(
        "Issue",
        back_populates="book"
    )


# =========================================================
# ISSUE MODEL
# =========================================================

class Issue(db.Model):

    __tablename__ = "issue"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    book_id = db.Column(
        db.Integer,
        db.ForeignKey("book.id"),
        nullable=False
    )

    issue_date = db.Column(
        db.Date,
        nullable=False
    )

    due_date = db.Column(
        db.Date,
        nullable=False
    )

    return_date = db.Column(
        db.Date,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="Issued"
    )

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    user = db.relationship(
        "User",
        back_populates="issues"
    )

    book = db.relationship(
        "Book",
        back_populates="issues"
    )