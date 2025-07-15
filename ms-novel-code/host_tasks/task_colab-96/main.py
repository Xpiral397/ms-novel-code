
"""This module uses SQLAlchemy to store data in normalized tables."""
import re
import bcrypt
import sqlalchemy
from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey, text, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session

Base = declarative_base()


class User(Base):
    """A base user class for user table."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    phone = Column(String(15), unique=True, nullable=False)

    credential = relationship(
        "Credential", uselist=False,
        back_populates="user", cascade="all, delete-orphan")


class Credential(Base):
    """a base credential class to credential table."""

    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey(
            "users.id", ondelete="CASCADE"), unique=True, nullable=False)
    password_hash = Column(LargeBinary, nullable=False)

    user = relationship("User", back_populates="credential")


def init_db() -> sqlalchemy.engine.Engine:
    """Return the Engine after Initiating the database."""
    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
    Base.metadata.create_all(engine)
    return engine


def register_user(payload: dict, session: Session) -> dict | int:
    """
    Register a new user after validating inputs and enforcing constraints.

    Returns {"user_id": int} on success or -1 on failure.
    """
    try:
        username = payload["username"]
        password = payload["password"]
        email = payload["email"]
        phone = payload["phone"]
    except KeyError:
        return -1

    # Validation
    if not (isinstance(
        username, str)
         and 3 <= len(username) <= 32 and username.isascii()):
        return -1
    if not (isinstance(password, str) and len(password) >= 8):
        return -1
    if not (isinstance(
        email, str)
         and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
        return -1
    if not (isinstance(phone, str) and re.fullmatch(r"^\+\d{11,15}$", phone)):
        return -1

    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

        user = User(username=username, email=email, phone=phone)
        user.credential = Credential(password_hash=hashed)

        session.add(user)
        session.commit()
        return {"user_id": user.id}
    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        return -1


def login(payload: dict, session: Session) -> bool:
    """
    Authenticate user by validating (username, password).

    Returns True if match is successful, otherwise raises Exception.
    """
    try:
        username = payload["username"]
        password = payload["password"]
    except KeyError:
        raise Exception("Invalid username or password")

    user = session.query(User).filter_by(username=username).first()
    if not user or not user.credential:
        raise Exception("Invalid username or password")

    if bcrypt.checkpw(password.encode(), user.credential.password_hash):
        return True
    else:
        raise Exception("Invalid username or password")

