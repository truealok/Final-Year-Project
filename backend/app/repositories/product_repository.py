"""Product and category repositories."""

from app.models.category import Category
from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product


class CategoryRepository(BaseRepository[Category]):
    model = Category
