
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    asc,
    desc,
)
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String, default="")
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)


class ProductCatalog:
    def __init__(self, database_url: str = "sqlite:///product_catalog.db"):
        self.engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def create_product(self, data: dict) -> dict:
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            return {"error": "Invalid or missing product name"}

        if len(data["name"]) > 100:
            return {"error": "Product name must be at most 100 characters"}

        if not isinstance(data.get("price"), (int, float)) or data["price"] < 0:
            return {"error": "Invalid price"}

        if not isinstance(data.get("stock"), int) or data["stock"] < 0:
            return {"error": "Invalid stock"}

        description = data.get("description", "")
        if not isinstance(description, str):
            return {"error": "Invalid description"}

        product = Product(
            name=data["name"].strip(),
            description=description.strip(),
            price=float(data["price"]),
            stock=int(data["stock"]),
        )

        session: Session = self.Session()
        try:
            session.add(product)
            session.commit()
            return self._product_to_dict(product)
        except IntegrityError:
            session.rollback()
            return {"error": "Integrity error while creating product"}
        finally:
            session.close()

    def get_product(self, product_id: int) -> dict:
        session: Session = self.Session()
        try:
            product = session.get(Product, product_id)
            if product:
                return self._product_to_dict(product)
            return {"error": "Product not found"}
        finally:
            session.close()

    def update_product(self, product_id: int, data: dict) -> dict:
        session: Session = self.Session()
        try:
            product = session.get(Product, product_id)
            if not product:
                return {"error": "Product not found"}

            if "name" in data:
                if not isinstance(data["name"], str) or not data["name"].strip():
                    return {"error": "Invalid product name"}
                if len(data["name"]) > 100:
                    return {"error": "Product name must be at most 100 characters"}
                product.name = data["name"].strip()

            if "price" in data:
                if not isinstance(data["price"], (int, float)) or data["price"] < 0:
                    return {"error": "Invalid price"}
                product.price = float(data["price"])

            if "stock" in data:
                if not isinstance(data["stock"], int) or data["stock"] < 0:
                    return {"error": "Invalid stock"}
                product.stock = int(data["stock"])

            if "description" in data:
                if not isinstance(data["description"], str):
                    return {"error": "Invalid description"}
                product.description = data["description"].strip()

            session.commit()
            return self._product_to_dict(product)
        except IntegrityError:
            session.rollback()
            return {"error": "Integrity error while updating product"}
        finally:
            session.close()

    def delete_product(self, product_id: int) -> dict:
        session: Session = self.Session()
        try:
            product = session.get(Product, product_id)
            if not product:
                return {"error": "Product not found"}

            session.delete(product)
            session.commit()
            return {"message": "Product deleted successfully"}
        except Exception as exc:
            session.rollback()
            return {"error": f"Could not delete product: {str(exc)}"}
        finally:
            session.close()

    def list_products(
        self,
        page: int = 1,
        page_size: int = 10,
        sort_by: str = None,
        ascending: bool = True,
        min_price: float = None,
        max_price: float = None,
        name_contains: str = None,
        min_stock: int = None,
    ) -> dict:
        if page < 1:
            return {"error": "Page number must be >= 1"}
        if page_size < 1 or page_size > 100:
            return {"error": "Page size must be between 1 and 100"}

        session: Session = self.Session()
        try:
            query = session.query(Product)

            # Filters
            if min_price is not None:
                query = query.filter(Product.price >= min_price)
            if max_price is not None:
                query = query.filter(Product.price <= max_price)
            if name_contains:
                query = query.filter(Product.name.ilike(f"%{name_contains}%"))
            if min_stock is not None:
                query = query.filter(Product.stock >= min_stock)

            # Sorting
            valid_sort_fields = {"name", "price", "stock"}
            if sort_by:
                if sort_by not in valid_sort_fields:
                    return {"error": "Invalid sort field"}
                sort_column = getattr(Product, sort_by)
                if ascending:
                    query = query.order_by(asc(sort_column), asc(Product.id))
                else:
                    query = query.order_by(desc(sort_column), asc(Product.id))
            else:
                query = query.order_by(asc(Product.id))

            total_products = query.count()
            total_pages = (total_products + page_size - 1) // page_size

            query = query.offset((page - 1) * page_size).limit(page_size)
            products = query.all()

            return {
                "products": [self._product_to_dict(product) for product in products],
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_products": total_products,
            }
        finally:
            session.close()

    @staticmethod
    def _product_to_dict(product: Product) -> dict:
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
        }
