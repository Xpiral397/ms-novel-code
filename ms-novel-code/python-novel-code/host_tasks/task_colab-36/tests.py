# tests

import unittest

from textwrap import dedent

from main import generate_sqlalchemy_model  # Replace with the actual import if needed


class TestGenerateSQLAlchemyModel(unittest.TestCase):

    def test_empty_input(self):
        columns = []
        expected = dedent("""\
            from sqlalchemy import Column
            from sqlalchemy.ext.declarative import declarative_base

            Base = declarative_base()

            class GeneratedModel(Base):
                __tablename__ = 'generated_model'
                pass""")
        self.assertEqual(generate_sqlalchemy_model(columns).strip(), expected.strip())

    def test_basic_integer_column(self):
        columns = [{
            "name": "age",
            "type": "Integer",
            "primary_key": False,
            "nullable": True,
            "server_default": False,
            "default_function": None
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("age = Column(Integer)", output)

    def test_primary_key_uuid_with_func(self):
        columns = [{
            "name": "id",
            "type": "UUID",
            "primary_key": True,
            "nullable": False,
            "server_default": True,
            "default_function": "uuid_generate_v4"
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("UUID", output)
        self.assertIn("server_default=func.uuid_generate_v4()", output)

    def test_string_with_literal_default(self):
        columns = [{
            "name": "status",
            "type": "String",
            "primary_key": False,
            "nullable": False,
            "server_default": True,
            "default_function": "'active'"
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=text('active')", output)

    def test_datetime_with_now_function(self):
        columns = [{
            "name": "created_at",
            "type": "DateTime",
            "primary_key": False,
            "nullable": False,
            "server_default": True,
            "default_function": "now"
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=func.now()", output)

    def test_boolean_true_default(self):
        columns = [{
            "name": "is_active",
            "type": "Boolean",
            "primary_key": False,
            "nullable": True,
            "server_default": True,
            "default_function": True
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=text('TRUE')", output)

    def test_boolean_false_default(self):
        columns = [{
            "name": "is_active",
            "type": "Boolean",
            "primary_key": False,
            "nullable": True,
            "server_default": True,
            "default_function": False
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=text('FALSE')", output)

    def test_integer_literal_default(self):
        columns = [{
            "name": "level",
            "type": "Integer",
            "primary_key": False,
            "nullable": False,
            "server_default": True,
            "default_function": 5
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=text('5')", output)

    def test_float_literal_default(self):
        columns = [{
            "name": "rating",
            "type": "Float",
            "primary_key": False,
            "nullable": False,
            "server_default": True,
            "default_function": 4.5
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("server_default=text('4.5')", output)

    def test_unsupported_type_is_skipped(self):
        columns = [{
            "name": "metadata",
            "type": "JSONB",
            "primary_key": False,
            "nullable": True,
            "server_default": False,
            "default_function": None
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertNotIn("metadata", output)

    def test_missing_type_is_skipped(self):
        columns = [{
            "name": "broken",
            "primary_key": False,
            "nullable": True,
            "server_default": False,
            "default_function": None
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertNotIn("broken", output)

    def test_server_default_flag_true_but_missing_default_function(self):
        columns = [{
            "name": "email_verified",
            "type": "Boolean",
            "primary_key": False,
            "nullable": True,
            "server_default": True
            # default_function is missing
        }]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("email_verified", output)
        self.assertNotIn("server_default=", output)

    def test_all_supported_types(self):
        columns = [
            {"name": "id", "type": "UUID", "primary_key": True, "nullable": False, "server_default": True, "default_function": "uuid_generate_v4"},
            {"name": "name", "type": "String", "primary_key": False, "nullable": False, "server_default": True, "default_function": "'John'"},
            {"name": "age", "type": "Integer", "primary_key": False, "nullable": True, "server_default": True, "default_function": 30},
            {"name": "created_at", "type": "DateTime", "primary_key": False, "nullable": False, "server_default": True, "default_function": "CURRENT_TIMESTAMP"},
            {"name": "is_admin", "type": "Boolean", "primary_key": False, "nullable": False, "server_default": True, "default_function": False},
            {"name": "score", "type": "Float", "primary_key": False, "nullable": True, "server_default": True, "default_function": 98.6},
        ]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("id = Column(UUID", output)
        self.assertIn("name = Column(String", output)
        self.assertIn("age = Column(Integer", output)
        self.assertIn("created_at = Column(DateTime", output)
        self.assertIn("is_admin = Column(Boolean", output)
        self.assertIn("score = Column(Float", output)

    def test_import_lines_are_minimal_and_correct(self):
        columns = [
            {"name": "title", "type": "String", "primary_key": False, "nullable": False, "server_default": True, "default_function": "'draft'"},
        ]
        output = generate_sqlalchemy_model(columns)
        self.assertIn("from sqlalchemy import Column", output)
        self.assertIn("from sqlalchemy import String", output)
        self.assertIn("from sqlalchemy import text", output)
        self.assertNotIn("func.", output)



if __name__ == '__main__':
    unittest.main(argv = [''])
