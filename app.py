import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

# Initialize configurations from environment variables
load_dotenv()

app = Flask(__name__)
# Restrict or allow Cross-Origin Resource Sharing for the Next.js ecosystem
CORS(app)

# Database Connection Architecture
MONGO_URI = os.getenv("MONGO_URI")
db = None

try:
    client = MongoClient(MONGO_URI)
    # Bind to the central repository database
    db = client.get_database("smartstock")
    print("Connection established with MongoDB Atlas cluster.")
except Exception as e:
    print(f"Critical Error: Failed to bind to remote MongoDB cluster: {e}")

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
def demand_forecast():
    """
    Generates quantitative asset optimization metrics.
    Target for the scikit-learn time-series mathematical execution.
    """
    payload = request.json or {}
    target_item_id = payload.get("item_id")
    
    # Mocking statistical engine return schema with required predictive attributes
    return jsonify({
        "item_id": target_item_id,
        "predicted_demand": 45.50,
        "confidence_level": 0.85
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
def add_inventory_item():
    """
    Creates a new inventory item.
    Expects JSON payload with item details.
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
def update_inventory_item(item_id):
    """
    Updates an existing inventory item.
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
def delete_inventory_item(item_id):
    """
    Deletes an inventory item from the database.
    """
    try:
        result = db.inventory_items.delete_one({"item_id": item_id})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Item not found"}), 404
            
        return jsonify({"message": "Inventory item deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete item: {str(e)}"}), 500

if __name__ == '__main__':
    runtime_port = int(os.getenv("PORT", 8000))
    # Execute runtime microserver on development configuration flags
    app.run(host='0.0.0.0', port=runtime_port, debug=True)