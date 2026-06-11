import os
import certifi
import jwt
import bcrypt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

# Initialize configurations from environment variables
load_dotenv()

app = Flask(__name__)
# Restrict or allow Cross Origin Resource Sharing for the Next.js ecosystem
CORS(app)

# Database Connection Architecture
MONGO_URI = os.getenv("MONGO_URI")
JWT_SECRET = os.getenv("JWT_SECRET", "fallback_secret_key_if_not_found")
db = None

try:
    # Use certifi and allow invalid certificates to bypass Render's strict SSL/TLS handshake
    client = MongoClient(
        MONGO_URI, 
        tlsCAFile=certifi.where(), 
        tlsAllowInvalidCertificates=True
    )
    # Bind to the central repository database
    db = client.get_database("smartstock")
    
    # Ping the database to force a real connection check immediately
    client.admin.command('ping')
    print("Connection established and verified with MongoDB Atlas cluster.")
except Exception as e:
    print(f"Critical Error: Failed to bind to remote MongoDB cluster: {e}")

# Core Security Middleware

def token_required(f):
    """
    Middleware decorator to protect routes. 
    Intercepts incoming requests to validate JWT payload against the secret key.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Extract Bearer token from headers
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        
        if not token:
            return jsonify({"error": "Authentication token is missing"}), 401
            
        try:
            # Decode token and attach user identity payload
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = db.users.find_one({"email": data["email"]})
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return jsonify({"error": "Authentication token is invalid or expired"}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/', methods=['GET'])
def health_check():
    """
    Monitors backend connectivity state and verifies database readiness.
    """
    database_status = "Connected" if db is not None else "Disconnected"
    return jsonify({
        "status": "Smart Stock API backend service is operational",
        "database": database_status
    }), 200

# Core Authentication & User Management Endpoints

@app.route('/api/users', methods=['POST'])
def create_account():
    """
    Registers a new administrative or employee account.
    Expects JSON payload with name, email, password, and role.
    """
    try:
        data = request.json
        if not all(k in data for k in ("name", "email", "password", "role")):
            return jsonify({"error": "Missing required fields"}), 400
            
        if db.users.find_one({"email": data["email"]}):
            return jsonify({"error": "User with this email already exists"}), 409

        # Generate cryptographic salt and hash the plaintext password
        hashed_password = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())
        
        new_user = {
            "name": data["name"],
            "email": data["email"],
            "password": hashed_password.decode('utf-8'),
            "role": data["role"],
            "created_at": datetime.now(timezone.utc)
        }
        
        db.users.insert_one(new_user)
        return jsonify({"message": "User account created successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create account: {str(e)}"}), 500

@app.route('/api/users', methods=['GET'])
@token_required
def list_users(current_user):
    """
    Returns every registered account for the account-management view.
    Restricted to the Owner role; password hashes are never exposed.
    """
    try:
        # Only the Owner may oversee user accounts
        if current_user.get("role") != "Owner":
            return jsonify({"error": "Insufficient privileges to manage accounts"}), 403

        users = list(db.users.find({}, {"_id": 0, "password": 0}))
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve users: {str(e)}"}), 500

@app.route('/api/users/<email>', methods=['DELETE'])
@token_required
def delete_user(current_user, email):
    """
    Removes a user account by email. Restricted to the Owner role.
    Owners cannot delete their own account to avoid lockout.
    """
    try:
        if current_user.get("role") != "Owner":
            return jsonify({"error": "Insufficient privileges to manage accounts"}), 403

        # Guard against an Owner accidentally deleting themselves
        if current_user.get("email") == email:
            return jsonify({"error": "You cannot delete your own account"}), 400

        result = db.users.delete_one({"email": email})
        if result.deleted_count == 0:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"message": "User account deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete user: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authenticates user credentials and generates a JWT session token.
    """
    try:
        data = request.json
        if not data or "email" not in data or "password" not in data:
            return jsonify({"error": "Missing credentials"}), 400

        user = db.users.find_one({"email": data["email"]})
        
        # Verify user existence and compare hashed password blocks
        if user and bcrypt.checkpw(data["password"].encode('utf-8'), user["password"].encode('utf-8')):
            token_expiration = datetime.now(timezone.utc) + timedelta(hours=24)
            token = jwt.encode({
                "email": user["email"],
                "role": user["role"],
                "exp": token_expiration
            }, JWT_SECRET, algorithm="HS256")
            
            return jsonify({
                "message": "Authentication successful",
                "token": token,
                "role": user["role"],
                "name": user["name"]
            }), 200
            
        return jsonify({"error": "Invalid email or password"}), 401
    except Exception as e:
        return jsonify({"error": f"Login process failed: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    Terminates the active session. 
    Client-side applications must destroy the JWT upon receiving the 200 OK.
    """
    return jsonify({"message": f"User {current_user['email']} logged out successfully"}), 200

# Core AI Module Webhooks and Endpoints

@app.route('/api/chat', methods=['POST'])
def nlp_assistant():
    """
    Processes incoming natural language operational inquiries.
    Target for the upcoming integration of the lightweight local Gemma model.
    """
    payload = request.json or {}
    user_query = payload.get("message", "")
    
    # Mocking Gemma framework generation pipeline for prototype phase validation
    return jsonify({
        "response": f"Gemma Local Model Payload Receipt Verification. Received: '{user_query}'. Parsing operations manual context...",
        "source": "Operations NLP Architecture"
    }), 200

@app.route('/api/forecast', methods=['POST'])
@token_required
def demand_forecast(current_user):
    """
    Generates quantitative asset optimization metrics.
    Target for the scikit-learn time-series mathematical execution.
    """
    payload = request.json or {}
    target_item_id = payload.get("item_id")
    
    historical_data = list(db.historical_data.find({"item_id": target_item_id}).sort("date", 1))
    
    if not historical_data:
        return jsonify({"error": "No historical data found for this item"}), 404
        
    first_date = historical_data[0]["date"]
    X_raw = []
    y_raw = []
    for record in historical_data:
        days_since = (record["date"] - first_date).days
        X_raw.append(days_since)
        y_raw.append(record["quantity_sold"])
        
    # 1. Convert X and y into a pandas DataFrame
    df = pd.DataFrame({"days_since": X_raw, "quantity_sold": y_raw})
    
    # 2. Remove Outliers using IQR method
    Q1 = df['quantity_sold'].quantile(0.25)
    Q3 = df['quantity_sold'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    df = df[(df['quantity_sold'] >= lower_bound) & (df['quantity_sold'] <= upper_bound)]
    
    # 3. Data Smoothing: Simple Moving Average (window=3)
    df['quantity_sold'] = df['quantity_sold'].rolling(window=3).mean()
    
    # 4. Drop any NaN values generated by the rolling window
    df.dropna(inplace=True)
    
    # 5. Extract the cleaned and smoothed values back into X (2D) and y (1D)
    X = df[['days_since']].values
    y = df['quantity_sold'].values
    
    # 6. Fit the RandomForestRegressor model on cleaned data
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    y_pred = model.predict(X)
    mape = np.mean(np.abs((y - y_pred) / y))
    confidence_level = max(0.0, min(1.0, 1 - mape))
    
    # 7. Predict the target value for last_days_since + 7
    last_days_since = (historical_data[-1]["date"] - first_date).days
    target_days = np.array([[last_days_since + 7]])
    predicted_demand = model.predict(target_days)[0]
    
    # Mocking statistical engine return schema with required predictive attributes
    return jsonify({
        "item_id": target_item_id,
        "predicted_demand": round(float(predicted_demand), 2),
        "confidence_level": float(confidence_level),
        "message": "Demand forecast generated successfully"
    }), 200

# Core Inventory CRUD API Endpoints

@app.route('/api/inventory', methods=['GET'])
def get_all_inventory():
    """
    Retrieves all inventory items from the database.
    """
    try:
        # Fetch all items, excluding the internal MongoDB object ID field for cleaner JSON output
        items = list(db.inventory_items.find({}, {"_id": 0}))
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve inventory: {str(e)}"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['GET'])
def get_inventory_item(item_id):
    """
    Retrieves a specific inventory item by its unique item identifier.
    """
    try:
        item = db.inventory_items.find_one({"item_id": item_id}, {"_id": 0})
        if item:
            return jsonify(item), 200
        return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve item: {str(e)}"}), 500

@app.route('/api/inventory', methods=['POST'])
@token_required
def add_inventory_item(current_user):
    """
    Creates a new inventory item.
    Expects JSON payload with item details. Protected route requiring JWT validation.
    """
    try:
        data = request.json
        if not data or "item_id" not in data or "item_name" not in data:
            return jsonify({"error": "Missing required fields (item_id, item_name)"}), 400
            
        # Check if item identifier already exists to prevent duplicates
        if db.inventory_items.find_one({"item_id": data["item_id"]}):
            return jsonify({"error": "Item with this ID already exists"}), 409

        db.inventory_items.insert_one(data)
        return jsonify({"message": "Inventory item created successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create item: {str(e)}"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
@token_required
def update_inventory_item(current_user, item_id):
    """
    Updates an existing inventory item. Protected route requiring JWT validation.
    """
    try:
        data = request.json
        result = db.inventory_items.update_one(
            {"item_id": item_id},
            {"$set": data}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Item not found"}), 404
            
        return jsonify({"message": "Inventory item updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update item: {str(e)}"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
@token_required
def delete_inventory_item(current_user, item_id):
    """
    Deletes an inventory item from the database. Protected route requiring JWT validation.
    """
    try:
        # Enforce role-based access control (RBAC) - Only Admins and Managers can delete
        if current_user["role"] not in ["Admin", "Manager"]:
            return jsonify({"error": "Insufficient privileges to delete items"}), 403

        result = db.inventory_items.delete_one({"item_id": item_id})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
            
        return jsonify({"message": "Inventory item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete item: {str(e)}"}), 500

# Core Threshold Configuration & Stock Alert Endpoints

@app.route('/api/inventory/<int:item_id>/threshold', methods=['PUT'])
@token_required
def configure_threshold(current_user, item_id):
    """
    Assigns or revises the minimum safety threshold for a single inventory item.
    Protected route requiring JWT validation.
    """
    try:
        data = request.json
        if not data or "minimum_threshold" not in data:
            return jsonify({"error": "Missing required fields (minimum_threshold)"}), 400

        result = db.inventory_items.update_one(
            {"item_id": item_id},
            {"$set": {"minimum_threshold": data["minimum_threshold"]}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Item not found"}), 404

        return jsonify({"message": "Threshold configured successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to configure threshold: {str(e)}"}), 500

@app.route('/api/inventory/alerts', methods=['GET'])
def get_stock_alerts():
    """
    Scans the full inventory register and surfaces every item whose quantity
    has fallen at or below its configured minimum threshold.
    """
    try:
        # Gather all items carrying a defined safety threshold for evaluation
        items = list(db.inventory_items.find(
            {"minimum_threshold": {"$ne": None}}, {"_id": 0}
        ))

        # Isolate the items sitting at or beneath their safety floor
        low_stock = [
            item for item in items
            if item.get("quantity") is not None
            and item["quantity"] <= item["minimum_threshold"]
        ]

        return jsonify({
            "alert_count": len(low_stock),
            "items_at_risk": low_stock
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to evaluate stock alerts: {str(e)}"}), 500

if __name__ == '__main__':
    runtime_port = int(os.getenv("PORT", 8000))
    # Execute runtime microserver on development configuration flags
    app.run(host='0.0.0.0', port=runtime_port, debug=True)