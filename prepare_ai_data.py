import os
import certifi
import random
import pandas as pd
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

def prepare_data():
    load_dotenv()
    MONGO_URI = os.getenv("MONGO_URI")
    
    print("Reading data/train.csv...")
    df = pd.read_csv("data/train.csv")
    
    # Filter the DataFrame for center_id == 55 and selected meal_ids mapped to inventory items
    # Filter for the last 30 weeks of data (week > 115)
    df = df[(df["center_id"] == 55) & (df["meal_id"].isin([1885, 1993, 2539, 1248, 1062, 2631, 1778, 2707, 1207, 1230, 2322, 2290, 1727, 1109, 2577])) & (df["week"] > 115)].copy()
    
    # Map meal_id to item_id
    item_map = {
        1885: 101, 1993: 102, 2539: 103, 1248: 104, 1062: 105,
        2631: 106, 1778: 107, 2707: 108, 1207: 109, 1230: 110,
        2322: 111, 2290: 112, 1727: 113, 1109: 114, 2577: 115
    }
    df["item_id"] = df["meal_id"].map(item_map)
    
    # Map the Kaggle week integer to a real datetime object (relative to today, timezone.utc)
    max_week = df["week"].max()
    now = datetime.now(timezone.utc)
    # Remove microseconds to have cleaner dates
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    df["date"] = df["week"].apply(lambda w: now - timedelta(weeks=int(max_week - w)))
    
    # Rename num_orders to quantity_sold
    df.rename(columns={"num_orders": "quantity_sold"}, inplace=True)
    
    # Generate synthetic quantity_wasted
    def generate_wasted(sold):
        percent = random.uniform(0.02, 0.12)
        return round(float(sold * percent), 2)
        
    df["quantity_wasted"] = df["quantity_sold"].apply(generate_wasted)
    
    # Select only required columns
    df = df[["item_id", "date", "quantity_sold", "quantity_wasted", "base_price"]]
    
    # Convert to records
    records = df.to_dict("records")
    
    if not records:
        print("No records found to insert.")
        return
        
    # Connect to MongoDB
    print("Connecting to MongoDB Atlas...")
    client = MongoClient(
        MONGO_URI, 
        tlsCAFile=certifi.where(), 
        tlsAllowInvalidCertificates=True
    )
    db = client.get_database("smartstock")
    
    # Drop and insert
    print("Dropping existing historical_data collection...")
    db.historical_data.drop()
    
    print(f"Inserting {len(records)} new records...")
    db.historical_data.insert_many(records)
    print("Data preparation complete.")

if __name__ == "__main__":
    prepare_data()