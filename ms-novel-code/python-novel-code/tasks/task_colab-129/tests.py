# tests


import unittest
from unittest.mock import patch
import io, sys
from sqlalchemy import create_engine
from main import LibraryManager, Base

class TestLibraryManagerCLI(unittest.TestCase):
    def setUp(self):
        self._stdout = sys.stdout
        self.buf = io.StringIO()
        sys.stdout = self.buf

        # Patch create_engine to use in-memory SQLite
        patcher = patch('main.create_engine')
        self.addCleanup(patcher.stop)
        mock_create = patcher.start()
        self.engine = create_engine('sqlite:///:memory:')
        mock_create.return_value = self.engine

        # Initialize in-memory DB
        Base.metadata.create_all(self.engine)

        # Instantiate manager (uses patched engine)
        self.lm = LibraryManager()

    def tearDown(self):
        sys.stdout = self._stdout

    def test_add_book_success(self):
        self.lm.add_book("1984", "George Orwell", 1949)
        out = self.buf.getvalue()
        self.assertIn("Book added: 1984 by George Orwell (1949)", out)

    def test_view_books_empty(self):
        self.lm.view_books()
        out = self.buf.getvalue()
        self.assertIn("Library Collection:", out)
        self.assertIn("ID", out)
        # No book rows
        rows = [line for line in out.splitlines() if line.startswith("|")]
        self.assertEqual(rows, [])

    def test_view_books_with_entries(self):
        self.lm.add_book("Dune", "Frank Herbert", 1965)
        self.buf.truncate(0); self.buf.seek(0)
        self.lm.view_books()
        out = self.buf.getvalue()
        self.assertIn("Dune", out)
        self.assertIn("Frank Herbert", out)
        self.assertIn("1965", out)

    def test_update_book_success(self):
        self.lm.add_book("Old Title", "Author", 2000)
        self.buf.truncate(0); self.buf.seek(0)
        self.lm.update_book(1, title="New Title")
        out = self.buf.getvalue()
        self.assertIn("Book updated: 1", out)

    def test_update_book_nonexistent(self):
        self.lm.update_book(99, author="X")
        out = self.buf.getvalue()
        self.assertIn("No book found with ID 99", out)

    def test_delete_book_success(self):
        self.lm.add_book("Temp", "Writer", 2021)
        self.buf.truncate(0); self.buf.seek(0)
        self.lm.delete_book(1)
        out = self.buf.getvalue()
        self.assertIn("Book with ID 1 deleted", out)

    def test_delete_book_twice(self):
        self.lm.add_book("Temp", "Writer", 2021)
        self.lm.delete_book(1)
        self.buf.truncate(0); self.buf.seek(0)
        self.lm.delete_book(1)
        out = self.buf.getvalue()
        self.assertIn("No book found with ID 1", out)

    def test_add_book_invalid_year(self):
        self.lm.add_book("Title", "Author", -5)
        out = self.buf.getvalue()
        self.assertIn("Invalid year", out)

    def test_add_book_empty_title(self):
        self.lm.add_book("", "Author", 2020)
        out = self.buf.getvalue()
        self.assertIn("Title cannot be empty", out)

    def test_update_book_invalid_year(self):
        self.lm.add_book("Valid", "Author", 2020)
        self.buf.truncate(0); self.buf.seek(0)
        self.lm.update_book(1, year=-1)
        out = self.buf.getvalue()
        self.assertIn("Invalid year", out)

    def test_close_session(self):
        try:
            self.lm.close_session()
        except Exception as e:
            self.fail(f"close_session raised {e}")

if __name__ == '__main__':
    unittest.main()
