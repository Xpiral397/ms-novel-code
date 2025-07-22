
from typing import List, Optional, Union
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

class Book(Base):
    """
    ORM model for the 'books' table.
    Each row represents a single book with title, author, and year of publication.
    """
    __tablename__ = "books"
    __table_args__ = {"sqlite_autoincrement": True}

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    title: str = Column(String, nullable=False)
    author: str = Column(String, nullable=False)
    year_published: int = Column(Integer, nullable=False)

class LibraryManager:
    """
    Handles all operations related to managing the digital library.
    Supports adding, viewing, updating, and deleting books using SQLAlchemy ORM.
    """

    def __init__(self, db_ref: Union[str, Engine] = "sqlite:///library.db"):
        """
        Initializes the LibraryManager with a SQLite database.
        Automatically creates the 'books' table if it doesn't exist.
        """
        try:
            self.engine: Engine = (
                create_engine(db_ref, echo=False) if isinstance(db_ref, str) else db_ref
            )
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            self.session: Session = self.Session()
        except SQLAlchemyError as exc:
            raise RuntimeError(f"Database setup failed: {exc}") from exc

    def _int_or_error(self, value: Union[int, str]) -> int:
        """
        Tries to convert the given value into an integer.
        Raises ValueError if the conversion fails.
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError("Year must be an integer.")

    def add_book(self, title: str, author: str, year: Union[int, str]) -> None:
        """
        Adds a new book to the database after validating inputs.
        Rejects empty title/author and negative or invalid years.
        """
        if not title.strip():
            print("Title cannot be empty")
            return
        if not author.strip():
            print("Author cannot be empty")
            return

        try:
            year_int = self._int_or_error(year)
        except ValueError:
            print("Invalid year")
            return

        if year_int < 0:
            print("Invalid year")
            return

        book = Book(title=title.strip(), author=author.strip(), year_published=year_int)
        self.session.add(book)
        self.session.commit()
        print(f"Book added: {book.title} by {book.author} ({book.year_published})")

    def view_books(self) -> None:
        """
        Displays all books currently stored in the library in a formatted table.
        Sorted by ID in ascending order.
        """
        books: List[Book] = self.session.query(Book).order_by(Book.id).all()

        print("\nLibrary Collection:")
        print(f" {'ID':<3} | {'Title':<20} | {'Author':<20} | Year")
        print(f"-{'-'*3}-+-{'-'*20}-+-{'-'*20}-+------")

        for b in books:
            print(f" {b.id:<3} | {b.title:<20} | {b.author:<20} | {b.year_published}")
        print()

    def update_book(
        self,
        book_id: int,
        title: Optional[str] = None,
        author: Optional[str] = None,
        year: Optional[Union[int, str]] = None,
    ) -> None:
        """
        Updates the title, author, or year of a specific book.
        Only the fields provided will be updated. Skips others.
        Prints a message if the book doesn't exist or inputs are invalid.
        """
        book = self.session.query(Book).filter_by(id=book_id).first()
        if not book:
            print(f"No book found with ID {book_id}")
            return

        if title is not None:
            if not title.strip():
                print("Title cannot be empty")
                return
            book.title = title.strip()

        if author is not None:
            if not author.strip():
                print("Author cannot be empty")
                return
            book.author = author.strip()

        if year is not None:
            try:
                year_int = self._int_or_error(year)
            except ValueError:
                print("Invalid year")
                return

            if year_int < 0:
                print("Invalid year")
                return
            book.year_published = year_int

        self.session.commit()
        print(f"Book updated: {book_id}")

    def delete_book(self, book_id: int) -> None:
        """
        Deletes a book by its ID from the database.
        If the ID does not exist, a message is shown.
        """
        book = self.session.query(Book).filter_by(id=book_id).first()
        if not book:
            print(f"No book found with ID {book_id}")
            return
        self.session.delete(book)
        self.session.commit()
        print(f"Book with ID {book_id} deleted.")

    def close_session(self) -> None:
        """
        Safely closes the current database session.
        Should be called before exiting the application.
        """
        self.session.close()
