
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField
from wtforms.validators import DataRequired, Length, ValidationError
import json
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
app.config["SECRET_KEY"] = "secret"
app.config["WTF_CSRF_ENABLED"] = False
db = SQLAlchemy(app)

MESSAGES = {
    "en_US": {
        "success": "Product saved successfully",
        "validation_failed": "Validation failed",
        "cert_required": "Certification required",
    },
    "de_DE": {
        "success": "Produkt erfolgreich gespeichert",
        "validation_failed": "Validierung fehlgeschlagen",
        "cert_required": "Zertifizierung ist erforderlich",
    },
}


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    launch_date = db.Column(db.Date, nullable=False)
    certification = db.Column(db.String(100))
    locale = db.Column(db.String(5), nullable=False)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    locale = db.Column(db.String(5), nullable=False)


with app.app_context():
    db.create_all()
    db.session.add_all(
        [
            Category(name="Electronics", locale="en_US"),
            Category(name="Books", locale="en_US"),
            Category(name="Clothing", locale="en_US"),
            Category(name="Elektronik", locale="de_DE"),
            Category(name="Bücher", locale="de_DE"),
            Category(name="Kleidung", locale="de_DE"),
        ]
    )
    db.session.commit()


def validate_certification(cert_code: str) -> bool:
    return cert_code.startswith("CE")


def create_price_validator(min_val: float, max_val: float, message: str):
    def price_validator(form, field):
        try:
            value = float(field.data)
            if not (min_val <= value <= max_val):
                raise ValidationError(message)
        except (ValueError, TypeError):
            raise ValidationError(message)

    return price_validator


def create_category_validator(locale: str, message: str):
    def category_validator(form, field):
        with app.app_context():
            valid_categories = [
                cat.name
                for cat in Category.query.filter_by(locale=locale).all()
            ]
            if field.data not in valid_categories:
                raise ValidationError(message)

    return category_validator


def create_date_validator(date_format: str, message: str):
    def date_validator(form, field):
        try:
            datetime.strptime(field.data, date_format)
        except ValueError:
            raise ValidationError(message)

    return date_validator


class ProductFormUS(FlaskForm):
    name = StringField(
        "Name", validators=[DataRequired(), Length(min=1, max=100)]
    )
    price = DecimalField("Price", validators=[DataRequired()])
    category = StringField("Category", validators=[DataRequired()])
    launch_date = StringField("Launch Date", validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price.validators.append(
            create_price_validator(
                10.00, 5000.00, "Price must be between 10.00 and 5,000.00"
            )
        )
        self.category.validators.append(
            create_category_validator(
                "en_US",
                "Category must be one of: Electronics, Books, Clothing",
            )
        )
        self.launch_date.validators.append(
            create_date_validator("%m/%d/%Y", "Date format must be MM/DD/YYYY")
        )


class ProductFormDE(FlaskForm):
    name = StringField(
        "Name", validators=[DataRequired(), Length(min=1, max=100)]
    )
    price = DecimalField("Price", validators=[DataRequired()])
    category = StringField("Category", validators=[DataRequired()])
    launch_date = StringField("Launch Date", validators=[DataRequired()])
    certification = StringField(
        "Certification",
        validators=[DataRequired(message="Zertifizierung ist erforderlich")],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.price.validators.append(
            create_price_validator(
                5.00, 4000.00, "Preis muss zwischen 5.00 und 4.000,00 liegen"
            )
        )
        self.category.validators.append(
            create_category_validator(
                "de_DE",
                "Kategorie muss eine der folgenden sein: Elektronik, "
                "Bücher, Kleidung",
            )
        )
        self.launch_date.validators.append(
            create_date_validator(
                "%d.%m.%Y", "Datumsformat muss DD.MM.YYYY sein"
            )
        )

    def validate_certification(self, field):
        if not validate_certification(field.data):
            raise ValidationError(MESSAGES["de_DE"]["cert_required"])


def validate_and_store_product(product_json: str, locale: str) -> dict:
    try:
        product_data = json.loads(product_json)
    except (json.JSONDecodeError, TypeError):
        return {
            "status": "storage_error",
            "product_id": None,
            "errors": {},
            "message": "Database operation failed",
        }

    if locale not in ["en_US", "de_DE"]:
        return {
            "status": "storage_error",
            "product_id": None,
            "errors": {},
            "message": "Database operation failed",
        }

    with app.app_context():
        if locale == "en_US":
            form = ProductFormUS(data=product_data)
        else:
            form = ProductFormDE(data=product_data)

        if form.validate():
            if locale == "en_US":
                launch_date = datetime.strptime(
                    product_data["launch_date"], "%m/%d/%Y"
                ).date()
            else:
                launch_date = datetime.strptime(
                    product_data["launch_date"], "%d.%m.%Y"
                ).date()

            product = Product(
                name=form.name.data,
                price=float(form.price.data),
                category=form.category.data,
                launch_date=launch_date,
                certification=product_data.get("certification"),
                locale=locale,
            )

            try:
                db.session.add(product)
                db.session.commit()
                return {
                    "status": "success",
                    "product_id": product.id,
                    "errors": {},
                    "message": MESSAGES[locale]["success"],
                }
            except Exception:
                db.session.rollback()
                return {
                    "status": "storage_error",
                    "product_id": None,
                    "errors": {},
                    "message": "Database operation failed",
                }
        else:
            errors = {}
            for field_name, field_errors in form.errors.items():
                if isinstance(field_errors, list):
                    errors[field_name] = field_errors
                else:
                    errors[field_name] = [field_errors]

            return {
                "status": "validation_error",
                "product_id": None,
                "errors": errors,
                "message": MESSAGES[locale]["validation_failed"],
            }

