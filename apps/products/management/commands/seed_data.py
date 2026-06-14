"""
Management command: seed_data

Generates realistic test data using Faker and bulk_create for performance.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear    # Clear existing data first

Data generated:
    - 10 categories
    - 1000 products (distributed across categories)
    - 20 stores
    - 300+ inventory items per store (bulk-created)

Performance notes:
    - Products, Inventory records use bulk_create() to minimize round-trips.
    - Inventory batch size is 500 to avoid hitting DB parameter limits.
    - The command is idempotent if --clear is used.
"""

import random
import time
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from apps.products.models import Category, Product
from apps.stores.models import Inventory, Store

fake = Faker()

# -----------------------------------------------------------------------
# Configuration constants — tweak as needed
# -----------------------------------------------------------------------
NUM_CATEGORIES = 10
NUM_PRODUCTS = 1000
NUM_STORES = 20
MIN_INVENTORY_PER_STORE = 300
MAX_INVENTORY_PER_STORE = 400
BULK_CREATE_BATCH_SIZE = 500


CATEGORY_NAMES = [
    "Electronics",
    "Clothing",
    "Books",
    "Home & Garden",
    "Sports & Outdoors",
    "Toys & Games",
    "Food & Beverage",
    "Health & Beauty",
    "Automotive",
    "Office Supplies",
]


class Command(BaseCommand):
    help = "Seed the database with realistic test data using Faker."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before seeding.",
        )

    def handle(self, *args, **options) -> None:
        start = time.monotonic()

        if options["clear"]:
            self._clear_data()

        self.stdout.write("Seeding database...")

        categories = self._seed_categories()
        products = self._seed_products(categories)
        stores = self._seed_stores()
        self._seed_inventory(stores, products)

        elapsed = time.monotonic() - start
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete in {elapsed:.2f}s:\n"
                f"  {len(categories)} categories\n"
                f"  {len(products)} products\n"
                f"  {len(stores)} stores\n"
                f"  ~{MIN_INVENTORY_PER_STORE}–{MAX_INVENTORY_PER_STORE} inventory items per store"
            )
        )

    def _clear_data(self) -> None:
        """Remove all seeded data in dependency order."""
        self.stdout.write("  Clearing existing data...")
        Inventory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Store.objects.all().delete()
        self.stdout.write(self.style.WARNING("  Existing data cleared."))

    def _seed_categories(self) -> list[Category]:
        """Create categories using get_or_create to support re-runs."""
        self.stdout.write("  Creating categories...")
        categories = []
        for name in CATEGORY_NAMES[:NUM_CATEGORIES]:
            category, _ = Category.objects.get_or_create(name=name)
            categories.append(category)
        self.stdout.write(f"    {len(categories)} categories ready.")
        return categories

    def _seed_products(self, categories: list[Category]) -> list[Product]:
        """
        Bulk-create 1000 products spread across categories.

        Uses bulk_create with ignore_conflicts=True for idempotency,
        but since titles are not unique we use a simple check on count.
        """
        self.stdout.write("  Creating products...")

        existing_count = Product.objects.count()
        if existing_count >= NUM_PRODUCTS:
            self.stdout.write(f"    {existing_count} products already exist, skipping.")
            return list(Product.objects.select_related("category").all()[:NUM_PRODUCTS])

        products_to_create = []
        for i in range(NUM_PRODUCTS - existing_count):
            category = random.choice(categories)
            products_to_create.append(
                Product(
                    title=self._generate_product_title(category.name),
                    description=fake.paragraph(nb_sentences=3),
                    price=Decimal(str(round(random.uniform(1.99, 999.99), 2))),
                    category=category,
                )
            )

        created = Product.objects.bulk_create(
            products_to_create,
            batch_size=BULK_CREATE_BATCH_SIZE,
        )
        self.stdout.write(f"    {len(created)} products created.")
        return list(Product.objects.select_related("category").all())

    def _seed_stores(self) -> list[Store]:
        """Create stores using get_or_create to support re-runs."""
        self.stdout.write("  Creating stores...")
        stores = []
        existing_names = set(Store.objects.values_list("name", flat=True))

        for _ in range(NUM_STORES):
            name = f"{fake.company()} Store"
            # Ensure unique name
            while name in existing_names:
                name = f"{fake.company()} Store"
            existing_names.add(name)

            store = Store.objects.create(
                name=name,
                location=f"{fake.city()}, {fake.state_abbr()}",
            )
            stores.append(store)

        self.stdout.write(f"    {len(stores)} stores created.")
        return stores

    def _seed_inventory(
        self, stores: list[Store], products: list[Product]
    ) -> None:
        """
        Bulk-create inventory records for each store.

        Each store gets a random subset of products (MIN to MAX items),
        with random quantities between 0 and 500.

        Uses bulk_create with ignore_conflicts=True for idempotency.
        """
        self.stdout.write("  Creating inventory records...")

        total_created = 0
        for store in stores:
            # Random subset of products for this store
            num_items = random.randint(MIN_INVENTORY_PER_STORE, MAX_INVENTORY_PER_STORE)
            store_products = random.sample(products, min(num_items, len(products)))

            inventory_records = [
                Inventory(
                    store=store,
                    product=product,
                    quantity=random.randint(0, 500),
                )
                for product in store_products
            ]

            created = Inventory.objects.bulk_create(
                inventory_records,
                batch_size=BULK_CREATE_BATCH_SIZE,
                ignore_conflicts=True,  # Safe to re-run
            )
            total_created += len(created)

        self.stdout.write(f"    {total_created} inventory records created.")

    @staticmethod
    def _generate_product_title(category_name: str) -> str:
        """Generate a realistic product title based on its category."""
        adjectives = ["Premium", "Deluxe", "Classic", "Ultra", "Pro", "Smart", "Eco", "Compact"]
        
        category_items = {
            "Electronics": ["Laptop", "Smartphone", "Tablet", "Headphones", "Speaker", "Camera", "Monitor", "Keyboard"],
            "Clothing": ["T-Shirt", "Jacket", "Jeans", "Dress", "Sneakers", "Hat", "Scarf", "Hoodie"],
            "Books": ["Novel", "Textbook", "Guide", "Manual", "Workbook", "Journal", "Atlas", "Encyclopedia"],
            "Home & Garden": ["Chair", "Table", "Lamp", "Rug", "Vase", "Shelf", "Curtain", "Planter"],
            "Sports & Outdoors": ["Bicycle", "Tent", "Kayak", "Yoga Mat", "Dumbbells", "Treadmill", "Backpack", "Sleeping Bag"],
            "Toys & Games": ["Board Game", "Action Figure", "Puzzle", "LEGO Set", "Doll", "RC Car", "Card Game", "Plush Toy"],
            "Food & Beverage": ["Coffee Blend", "Tea Set", "Hot Sauce", "Olive Oil", "Protein Bar", "Spice Mix", "Jam", "Cereal"],
            "Health & Beauty": ["Moisturizer", "Shampoo", "Vitamin C", "Face Mask", "Perfume", "Sunscreen", "Lip Balm", "Serum"],
            "Automotive": ["Car Wax", "Floor Mats", "USB Charger", "Dash Cam", "Air Freshener", "Seat Cover", "Jump Starter", "Tire Gauge"],
            "Office Supplies": ["Notebook", "Pen Set", "Stapler", "Desk Organizer", "Sticky Notes", "Binder", "Calculator", "Whiteboard"],
        }

        items = category_items.get(category_name, ["Item", "Product", "Thing"])
        adjective = random.choice(adjectives)
        item = random.choice(items)
        brand = fake.company().split()[0]  # Use first word of company name as brand
        return f"{brand} {adjective} {item}"
