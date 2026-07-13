import os
import bcrypt
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

# Load connection configurations from the environment file
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def seed_database():
    """
    Initializes the MongoDB Atlas database by dropping existing collections,
    defining schemas through mock data injection, and establishing required indexes.
    """
    try:
        # Establish connection to the cloud MongoDB Atlas instance
        client = MongoClient(MONGO_URI)
        db = client.get_database("smartstock")
        print("Initializing database collections and seeding sample data...")

        # Generate live cryptographic hashes for testing login endpoints
        admin_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        manager_hash = bcrypt.hashpw("manager123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 1. Users Collection: Stores credentials and access levels (SRS Section 5.2.1)
        db.users.drop()
        sample_users = [
            {
                "user_id": 1,
                "name": "Nikan Eidi",
                "email": "nikan@smartstock.com",
                "password": admin_hash,
                "role": "Admin"
            },
            {
                "user_id": 2,
                "name": "Jun Ho Jeon",
                "email": "junho@smartstock.com",
                "password": manager_hash,
                "role": "Manager"
            }
        ]
        db.users.insert_many(sample_users)
        db.users.create_index([("email", ASCENDING)], unique=True)
        print("Users collection seeded with unique index constraint and live hashes.")

        # 2. Inventory Items Collection: Tracks physical stock parameters (SRS Section 5.2.2)
        db.inventory_items.drop()
        sample_items = [
            {
                "item_id": 101,
                "item_name": "Fresh Tomatoes",
                "category": "Produce",
                "quantity": 120.50,
                "minimum_threshold": 30.00,
                "expiry_date": datetime(2026, 5, 25, tzinfo=timezone.utc)
            },
            {
                "item_id": 102,
                "item_name": "Olive Oil",
                "category": "Groceries",
                "quantity": 15.00,
                "minimum_threshold": 5.00,
                "expiry_date": None
            },
            # Inject diverse stock levels to test threshold logic and alert generation
            {
                "item_id": 103,
                "item_name": "Cheddar Cheese",
                "category": "Dairy",
                "quantity": 8.00,
                "minimum_threshold": 15.00,
                "expiry_date": datetime(2026, 8, 10, tzinfo=timezone.utc)
            },
            {
                "item_id": 104,
                "item_name": "Chicken Breast",
                "category": "Meat",
                "quantity": 45.00,
                "minimum_threshold": 20.00,
                "expiry_date": datetime(2026, 7, 20, tzinfo=timezone.utc)
            },
            {
                "item_id": 105,
                "item_name": "Red Onions",
                "category": "Produce",
                "quantity": 20.00,
                "minimum_threshold": 20.00,
                "expiry_date": datetime(2026, 9, 1, tzinfo=timezone.utc)
            },
            {
                "item_id": 106,
                "item_name": "Atlantic Salmon",
                "category": "Seafood",
                "quantity": 12.50,
                "minimum_threshold": 15.00,
                "expiry_date": datetime(2026, 7, 18, tzinfo=timezone.utc)
            },
            {
                "item_id": 107,
                "item_name": "Basmati Rice",
                "category": "Groceries",
                "quantity": 250.00,
                "minimum_threshold": 50.00,
                "expiry_date": None
            },
            {
                "item_id": 108,
                "item_name": "Whole Milk",
                "category": "Dairy",
                "quantity": 22.00,
                "minimum_threshold": 20.00,
                "expiry_date": datetime(2026, 7, 25, tzinfo=timezone.utc)
            },
            {
                "item_id": 109,
                "item_name": "Garlic",
                "category": "Produce",
                "quantity": 40.00,
                "minimum_threshold": 10.00,
                "expiry_date": datetime(2026, 9, 15, tzinfo=timezone.utc)
            },
            {
                "item_id": 110,
                "item_name": "Unsalted Butter",
                "category": "Dairy",
                "quantity": 8.50,
                "minimum_threshold": 10.00,
                "expiry_date": datetime(2026, 8, 5, tzinfo=timezone.utc)
            },
            {
                "item_id": 111,
                "item_name": "Beef Ribeye",
                "category": "Meat",
                "quantity": 30.00,
                "minimum_threshold": 25.00,
                "expiry_date": datetime(2026, 7, 22, tzinfo=timezone.utc)
            },
            {
                "item_id": 112,
                "item_name": "Pasta (Penne)",
                "category": "Groceries",
                "quantity": 180.00,
                "minimum_threshold": 40.00,
                "expiry_date": None
            },
            {
                "item_id": 113,
                "item_name": "Romaine Lettuce",
                "category": "Produce",
                "quantity": 18.00,
                "minimum_threshold": 20.00,
                "expiry_date": datetime(2026, 7, 16, tzinfo=timezone.utc)
            },
            {
                "item_id": 114,
                "item_name": "White Sugar",
                "category": "Groceries",
                "quantity": 85.00,
                "minimum_threshold": 20.00,
                "expiry_date": None
            },
            {
                "item_id": 115,
                "item_name": "Eggs (Dozen)",
                "category": "Dairy",
                "quantity": 25.00,
                "minimum_threshold": 15.00,
                "expiry_date": datetime(2026, 8, 1, tzinfo=timezone.utc)
            }
        ]
        db.inventory_items.insert_many(sample_items)
        db.inventory_items.create_index([("item_id", ASCENDING)], unique=True)
        print("Inventory Items collection fully initialized.")

        # 3. Inventory Transactions Collection: Logs all stock mutations (SRS Section 5.2.2)
        db.inventory_transactions.drop()
        sample_transactions = [
            {
                "transaction_id": 5001,
                "item_id": 101,
                "user_id": 1,
                "quantity_change": -5.50,
                "transaction_type": "Waste",
                "timestamp": datetime.now(timezone.utc)
            }
        ]
        db.inventory_transactions.insert_many(sample_transactions)
        print("Inventory Transactions audit log seeded.")

        # 4. Suppliers Collection: Stores vendor identification metadata (SRS Section 5.2.5)
        db.suppliers.drop()
        sample_suppliers = [
            {
                "supplier_id": 1,
                "supplier_name": "Ontario Local Foods Inc",
                "contact_info": "orders@ontariolocal.ca",
                "location": "Newmarket, ON"
            },
            {
                "supplier_id": 2,
                "supplier_name": "Fresh Valley Distributors",
                "contact_info": "sales@freshvalley.ca",
                "location": "Vaughan, ON"
            },
            {
                "supplier_id": 3,
                "supplier_name": "Metro Wholesale Grocers",
                "contact_info": "wholesale@metrogrocers.ca",
                "location": "Mississauga, ON"
            }
        ]
        db.suppliers.insert_many(sample_suppliers)
        print("Suppliers registry initialized.")

        # 5. Supplier Prices Collection: Holds metrics for real-time cost comparison (SRS Section 5.2.4)
        db.supplier_prices.drop()
        sample_prices = [
            # Competing vendor offers for Fresh Tomatoes (item_id 101)
            {
                "price_id": 901,
                "supplier_id": 1,
                "item_id": 101,
                "price": 2.45,
                "last_updated": datetime.now(timezone.utc)
            },
            {
                "price_id": 902,
                "supplier_id": 2,
                "item_id": 101,
                "price": 2.10,
                "last_updated": datetime.now(timezone.utc)
            },
            {
                "price_id": 903,
                "supplier_id": 3,
                "item_id": 101,
                "price": 2.80,
                "last_updated": datetime.now(timezone.utc)
            },
            # Competing vendor offers for Olive Oil (item_id 102)
            {
                "price_id": 904,
                "supplier_id": 1,
                "item_id": 102,
                "price": 8.50,
                "last_updated": datetime.now(timezone.utc)
            },
            {
                "price_id": 905,
                "supplier_id": 2,
                "item_id": 102,
                "price": 9.00,
                "last_updated": datetime.now(timezone.utc)
            },
            {
                "price_id": 906,
                "supplier_id": 3,
                "item_id": 102,
                "price": 7.95,
                "last_updated": datetime.now(timezone.utc)
            }
        ]
        db.supplier_prices.insert_many(sample_prices)
        # Index the item linkage so per-item price lookups stay fast
        db.supplier_prices.create_index([("item_id", ASCENDING)])
        print("Supplier Prices evaluation metrics seeded.")

        # 6. Demand Forecasts Collection: Destination for AI forecasting analytics (SRS Section 5.2.3)
        db.demand_forecasts.drop()
        sample_forecasts = [
            {
                "forecast_id": 301,
                "item_id": 101,
                "predicted_demand": 145.00,
                "confidence_level": 0.88,
                "forecast_date": datetime(2026, 5, 20, tzinfo=timezone.utc)
            }
        ]
        db.demand_forecasts.insert_many(sample_forecasts)
        print("Demand Forecasts AI analytical collection seeded.")

        # 7. Waste Log Collection: Records discarded stock for analytics (SRS Section 5.2.6)
        db.waste_log.drop()
        sample_waste = [
            {
                "log_id": 1,
                "item_id": 101,
                "item_name": "Fresh Tomatoes",
                "quantity": 5.50,
                "reason": "spoilage",
                "logged_by": "nikan@smartstock.com",
                "timestamp": datetime.now(timezone.utc)
            }
        ]
        db.waste_log.insert_many(sample_waste)
        print("Waste Log collection seeded.")

        print("\nDatabase architecture setup and mocking completed successfully.")

    except Exception as e:
        print(f"Database initialization failure: {e}")

if __name__ == "__main__":
    seed_database()