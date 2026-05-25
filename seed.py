import os
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

        # 1. Users Collection: Stores credentials and access levels (SRS Section 5.2.1)
        db.users.drop()
        sample_users = [
            {
                "user_id": 1,
                "name": "Nikan Eidi",
                "email": "nikan@smartstock.com",
                "password": "hashed_password_123",
                "role": "Admin"
            },
            {
                "user_id": 2,
                "name": "Jun Ho Jeon",
                "email": "junho@smartstock.com",
                "password": "hashed_password_456",
                "role": "Manager"
            }
        ]
        db.users.insert_many(sample_users)
        db.users.create_index([("email", ASCENDING)], unique=True)
        print("Users collection seeded with unique index constraint.")

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
            }
        ]
        db.suppliers.insert_many(sample_suppliers)
        print("Suppliers registry initialized.")

        # 5. Supplier Prices Collection: Holds metrics for real-time cost comparison (SRS Section 5.2.4)
        db.supplier_prices.drop()
        sample_prices = [
            {
                "price_id": 901,
                "supplier_id": 1,
                "price": 2.45,
                "last_updated": datetime.now(timezone.utc)
            }
        ]
        db.supplier_prices.insert_many(sample_prices)
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

        print("\nDatabase architecture setup and mocking completed successfully.")

    except Exception as e:
        print(f"Database initialization failure: {e}")

if __name__ == "__main__":
    seed_database()