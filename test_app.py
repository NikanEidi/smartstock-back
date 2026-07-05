import pytest
import json
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from app import app, token_required, JWT_SECRET

# ============================================================================
# FIXTURES AND SETUP
# ============================================================================

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    """Mock MongoDB database fixture."""
    with patch('app.db') as mock:
        yield mock

@pytest.fixture
def valid_token():
    """Generate a valid JWT token for testing."""
    payload = {
        "email": "test@example.com",
        "role": "Admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@pytest.fixture
def expired_token():
    """Generate an expired JWT token for testing."""
    payload = {
        "email": "test@example.com",
        "role": "Admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

@pytest.fixture
def mock_user():
    """Mock user object for testing."""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Test User",
        "email": "test@example.com",
        "password": bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode('utf-8'),
        "role": "Admin",
        "created_at": datetime.now(timezone.utc)
    }

@pytest.fixture
def mock_inventory_item():
    """Mock inventory item object for testing."""
    return {
        "item_id": 1,
        "item_name": "Test Item",
        "quantity": 100,
        "price": 29.99,
        "category": "Electronics"
    }

# ============================================================================
# HEALTH CHECK ENDPOINT TESTS
# ============================================================================

class TestHealthCheck:
    """Test suite for GET / health check endpoint."""

    def test_health_check_success(self, client, mock_db):
        """Test successful health check when database is connected."""
        with patch('app.db', "Connected"):
            response = client.get('/')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert "status" in data
            assert "backend service is operational" in data["status"]
            assert "database" in data

    def test_health_check_db_disconnected(self, client):
        """Test health check when database is disconnected."""
        with patch('app.db', None):
            response = client.get('/')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["database"] == "Disconnected"

# ============================================================================
# AUTHENTICATION ENDPOINTS TESTS
# ============================================================================

class TestUserCreation:
    """Test suite for POST /api/users user creation endpoint."""

    def test_create_user_success(self, client, mock_db):
        """Test successful user account creation."""
        mock_db.users.find_one.return_value = None
        mock_db.users.insert_one.return_value = None

        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "secure_password123",
            "role": "Employee"
        }

        response = client.post('/api/users', 
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert "message" in data
        assert "created successfully" in data["message"]

    def test_create_user_missing_fields(self, client, mock_db):
        """Test user creation with missing required fields."""
        payload = {
            "name": "John Doe",
            "email": "john@example.com"
            # Missing password and role
        }

        response = client.post('/api/users',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing required fields" in data["error"]

    def test_create_user_email_already_exists(self, client, mock_db):
        """Test user creation with email that already exists."""
        existing_user = {"email": "john@example.com"}
        mock_db.users.find_one.return_value = existing_user

        payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "password": "secure_password123",
            "role": "Employee"
        }

        response = client.post('/api/users',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 409
        data = json.loads(response.data)
        assert "already exists" in data["error"]

    def test_create_user_empty_payload(self, client, mock_db):
        """Test user creation with empty payload."""
        response = client.post('/api/users',
                               json={},
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing required fields" in data["error"]

# ============================================================================
# LOGIN ENDPOINT TESTS
# ============================================================================

class TestLogin:
    """Test suite for POST /api/auth/login endpoint."""

    def test_login_success(self, client, mock_db, mock_user):
        """Test successful login with valid credentials."""
        mock_db.users.find_one.return_value = mock_user

        payload = {
            "email": "test@example.com",
            "password": "password123"
        }

        response = client.post('/api/auth/login',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "token" in data
        assert "message" in data
        assert data["role"] == "Admin"
        assert data["name"] == "Test User"

    def test_login_missing_credentials(self, client, mock_db):
        """Test login with missing email or password."""
        payload = {"email": "test@example.com"}
        
        response = client.post('/api/auth/login',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing credentials" in data["error"]

    def test_login_invalid_email(self, client, mock_db):
        """Test login with email that doesn't exist."""
        mock_db.users.find_one.return_value = None

        payload = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }

        response = client.post('/api/auth/login',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "Invalid email or password" in data["error"]

    def test_login_invalid_password(self, client, mock_db, mock_user):
        """Test login with incorrect password."""
        mock_db.users.find_one.return_value = mock_user

        payload = {
            "email": "test@example.com",
            "password": "wrong_password"
        }

        response = client.post('/api/auth/login',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "Invalid email or password" in data["error"]

    def test_login_empty_payload(self, client, mock_db):
        """Test login with empty payload."""
        response = client.post('/api/auth/login',
                               json={},
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing credentials" in data["error"]

    def test_login_no_json_body(self, client, mock_db):
        """Test login with no JSON body."""
        response = client.post('/api/auth/login')
        assert response.status_code == 500

# ============================================================================
# LOGOUT ENDPOINT TESTS
# ============================================================================

class TestLogout:
    """Test suite for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client, mock_db, mock_user, valid_token):
        """Test successful logout with valid token."""
        mock_db.users.find_one.return_value = mock_user

        response = client.post('/api/auth/logout',
                               headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "logged out successfully" in data["message"]

    def test_logout_missing_token(self, client, mock_db):
        """Test logout without authentication token."""
        response = client.post('/api/auth/logout')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "missing" in data["error"].lower()

    def test_logout_invalid_token(self, client, mock_db):
        """Test logout with invalid token."""
        response = client.post('/api/auth/logout',
                               headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "invalid or expired" in data["error"].lower()

    def test_logout_expired_token(self, client, mock_db, expired_token):
        """Test logout with expired token."""
        response = client.post('/api/auth/logout',
                               headers={"Authorization": f"Bearer {expired_token}"})
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "invalid or expired" in data["error"].lower()

    def test_logout_malformed_auth_header(self, client, mock_db):
        """Test logout with malformed authorization header."""
        response = client.post('/api/auth/logout',
                               headers={"Authorization": "InvalidFormat token"})
        assert response.status_code == 401

# ============================================================================
# NLP CHAT ENDPOINT TESTS
# ============================================================================

class TestNLPAssistant:
    """Test suite for POST /api/chat endpoint."""

    def test_chat_unmatched_falls_back(self, client):
        """A message that matches no rule returns the fallback reply."""
        payload = {"message": "tell me a joke"}

        response = client.post('/api/chat',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data
        assert data["source"] == "fallback"

    def test_chat_low_stock_intent(self, client, mock_db):
        """A low-stock question lists items at or below their threshold."""
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Olive Oil", "quantity": 3, "minimum_threshold": 5},
            {"item_name": "Tomatoes", "quantity": 50, "minimum_threshold": 10},
        ]

        response = client.post('/api/chat',
                               json={"message": "what is running low?"},
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["source"] == "rules"
        assert "Olive Oil" in data["response"]
        assert "Tomatoes" not in data["response"]

    def test_chat_item_quantity_intent(self, client, mock_db):
        """An item-quantity question reports that item's current stock."""
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Olive Oil", "quantity": 15},
        ]

        response = client.post('/api/chat',
                               json={"message": "how much olive oil do we have?"},
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["source"] == "rules"
        assert "Olive Oil: 15" in data["response"]

    def test_chat_empty_message(self, client):
        """Test chat endpoint with empty message."""
        payload = {"message": ""}

        response = client.post('/api/chat',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data

    def test_chat_no_message(self, client):
        """Test chat endpoint without message field."""
        response = client.post('/api/chat',
                               json={},
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data

    def test_chat_no_json_body(self, client):
        """Test chat endpoint with no JSON body."""
        response = client.post('/api/chat')
        assert response.status_code == 415

    def _ask(self, client, message):
        """Helper: post a chat message and return the parsed JSON body."""
        response = client.post('/api/chat',
                               json={"message": message},
                               content_type='application/json')
        assert response.status_code == 200
        return json.loads(response.data)

    def test_chat_expiring_soon(self, client, mock_db):
        """Expiring question lists items sorted by expiry date."""
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Fresh Tomatoes",
             "expiry_date": datetime(2026, 5, 25, tzinfo=timezone.utc)},
        ]
        data = self._ask(client, "what is expiring soon?")
        assert data["source"] == "rules"
        assert "Fresh Tomatoes" in data["response"]
        assert "2026-05-25" in data["response"]

    def test_chat_cheapest_supplier(self, client, mock_db):
        """Cheapest question resolves a partial item name and lowest price."""
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Fresh Tomatoes", "item_id": 101},
        ]
        mock_db.supplier_prices.find.return_value = [
            {"supplier_id": 2, "price": 2.10},
            {"supplier_id": 1, "price": 2.45},
        ]
        mock_db.suppliers.find_one.return_value = {"supplier_name": "Fresh Valley"}
        data = self._ask(client, "cheapest supplier for tomatoes")
        assert data["source"] == "rules"
        assert "Fresh Valley" in data["response"]
        assert "2.1" in data["response"]

    def test_chat_supplier_list(self, client, mock_db):
        """Supplier question lists every registered vendor."""
        mock_db.suppliers.find.return_value = [
            {"supplier_name": "Alpha"},
            {"supplier_name": "Beta"},
        ]
        data = self._ask(client, "who are our suppliers?")
        assert data["source"] == "rules"
        assert "Alpha" in data["response"]
        assert "Beta" in data["response"]

    def test_chat_waste_report(self, client, mock_db):
        """Waste question sums quantity_wasted across records."""
        mock_db.historical_data.find.return_value = [
            {"quantity_wasted": 10},
            {"quantity_wasted": 5.5},
        ]
        data = self._ask(client, "total waste this month")
        assert data["source"] == "rules"
        assert "15.5" in data["response"]
        assert "2 record" in data["response"]

    def test_chat_items_by_category(self, client, mock_db):
        """Category question lists the items in a named category."""
        mock_db.inventory_items.distinct.return_value = ["Produce"]
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Fresh Tomatoes"},
        ]
        data = self._ask(client, "what's in produce?")
        assert data["source"] == "rules"
        assert "Produce" in data["response"]
        assert "Fresh Tomatoes" in data["response"]

    def test_chat_list_categories(self, client, mock_db):
        """Categories question lists the distinct categories."""
        mock_db.inventory_items.distinct.return_value = ["Produce", "Groceries"]
        data = self._ask(client, "what categories do we have?")
        assert data["source"] == "rules"
        assert "Produce" in data["response"]
        assert "Groceries" in data["response"]

    def test_chat_count_items(self, client, mock_db):
        """Count question reports the inventory item count."""
        mock_db.inventory_items.count_documents.return_value = 5
        data = self._ask(client, "item count please")
        assert data["source"] == "rules"
        assert "5" in data["response"]

    def test_chat_list_items(self, client, mock_db):
        """List question names every inventory item."""
        mock_db.inventory_items.find.return_value = [
            {"item_name": "Olive Oil"},
            {"item_name": "Fresh Tomatoes"},
        ]
        data = self._ask(client, "list all items")
        assert data["source"] == "rules"
        assert "Olive Oil" in data["response"]
        assert "Fresh Tomatoes" in data["response"]

    def test_chat_greeting(self, client):
        """Greeting returns a friendly welcome without touching the db."""
        data = self._ask(client, "hello")
        assert data["source"] == "rules"
        assert "Hi!" in data["response"]

    def test_chat_help(self, client):
        """Help explains what the assistant can answer."""
        data = self._ask(client, "what can you do?")
        assert data["source"] == "rules"
        assert "low stock" in data["response"]

# ============================================================================
# FORECAST ENDPOINT TESTS
# ============================================================================

def _build_history(item_id=42, points=12):
    """Build a mock historical_data series for the forecast pipeline."""
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    
    quantities = [40, 42, 41, 45, 47, 46, 200, 50, 52, 51, 55, 57]
    return [
        {
            "item_id": item_id,
            "date": base + timedelta(days=7 * i),
            "quantity_sold": quantities[i % len(quantities)],
        }
        for i in range(points)
    ]


class TestDemandForecast:
    """Test suite for POST /api/forecast endpoint (JWT-protected, DB-backed)."""

    def test_forecast_with_item_id(self, client, mock_db, mock_user, valid_token):
        """Test forecast endpoint with a valid token and historical data."""
        mock_db.users.find_one.return_value = mock_user
      
        mock_db.historical_data.find.return_value.sort.return_value = _build_history(42)

        payload = {"item_id": 42}
        response = client.post('/api/forecast',
                               json=payload,
                               headers={"Authorization": f"Bearer {valid_token}"},
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["item_id"] == 42
        assert "predicted_demand" in data
        assert "confidence_level" in data
        assert isinstance(data["predicted_demand"], (int, float))
        assert isinstance(data["confidence_level"], (int, float))
        assert 0.0 <= data["confidence_level"] <= 1.0

    def test_forecast_no_historical_data(self, client, mock_db, mock_user, valid_token):
        """Test forecast returns 404 when the item has no historical data."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.historical_data.find.return_value.sort.return_value = []

        payload = {"item_id": 9999}
        response = client.post('/api/forecast',
                               json=payload,
                               headers={"Authorization": f"Bearer {valid_token}"},
                               content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "No historical data" in data["error"]

    def test_forecast_no_auth(self, client, mock_db):
        """Test forecast endpoint rejects requests without a token."""
        response = client.post('/api/forecast',
                               json={"item_id": 42},
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "missing" in data["error"].lower()

    def test_forecast_invalid_token(self, client, mock_db):
        """Test forecast endpoint rejects an invalid token."""
        response = client.post('/api/forecast',
                               json={"item_id": 42},
                               headers={"Authorization": "Bearer invalid_token"},
                               content_type='application/json')
        assert response.status_code == 401

# ============================================================================
# INVENTORY ENDPOINTS TESTS
# ============================================================================

class TestGetAllInventory:
    """Test suite for GET /api/inventory endpoint."""

    def test_get_all_inventory_success(self, client, mock_db, mock_inventory_item):
        """Test retrieving all inventory items."""
        mock_db.inventory_items.find.return_value = [mock_inventory_item]

        response = client.get('/api/inventory')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["item_id"] == 1

    def test_get_all_inventory_empty(self, client, mock_db):
        """Test retrieving inventory when no items exist."""
        mock_db.inventory_items.find.return_value = []

        response = client.get('/api/inventory')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_all_inventory_multiple_items(self, client, mock_db):
        """Test retrieving multiple inventory items."""
        items = [
            {"item_id": 1, "item_name": "Item 1"},
            {"item_id": 2, "item_name": "Item 2"},
            {"item_id": 3, "item_name": "Item 3"}
        ]
        mock_db.inventory_items.find.return_value = items

        response = client.get('/api/inventory')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data) == 3


class TestGetInventoryItem:
    """Test suite for GET /api/inventory/<int:item_id> endpoint."""

    def test_get_inventory_item_success(self, client, mock_db, mock_inventory_item):
        """Test retrieving a specific inventory item."""
        mock_db.inventory_items.find_one.return_value = mock_inventory_item

        response = client.get('/api/inventory/1')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["item_id"] == 1
        assert data["item_name"] == "Test Item"

    def test_get_inventory_item_not_found(self, client, mock_db):
        """Test retrieving non-existent inventory item."""
        mock_db.inventory_items.find_one.return_value = None

        response = client.get('/api/inventory/999')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_get_inventory_item_various_ids(self, client, mock_db):
        """Test retrieving inventory items with different IDs."""
        test_items = [
            {"item_id": 1, "item_name": "Item 1"},
            {"item_id": 42, "item_name": "Item 42"},
            {"item_id": 9999, "item_name": "Item 9999"}
        ]

        for item in test_items:
            mock_db.inventory_items.find_one.return_value = item
            response = client.get(f'/api/inventory/{item["item_id"]}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["item_id"] == item["item_id"]


class TestAddInventoryItem:
    """Test suite for POST /api/inventory endpoint."""

    def test_add_inventory_item_success(self, client, mock_db, mock_user, valid_token):
        """Test successfully adding an inventory item with authentication."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.find_one.return_value = None
        mock_db.inventory_items.insert_one.return_value = None

        payload = {
            "item_id": 1,
            "item_name": "New Item",
            "quantity": 50,
            "price": 19.99
        }

        response = client.post('/api/inventory',
                               json=payload,
                               headers={"Authorization": f"Bearer {valid_token}"},
                               content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert "created successfully" in data["message"]

    def test_add_inventory_item_missing_fields(self, client, mock_db, mock_user, valid_token):
        """Test adding inventory item with missing required fields."""
        mock_db.users.find_one.return_value = mock_user

        payload = {"item_name": "New Item"}  # Missing item_id

        response = client.post('/api/inventory',
                               json=payload,
                               headers={"Authorization": f"Bearer {valid_token}"},
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing required fields" in data["error"]

    def test_add_inventory_item_duplicate_id(self, client, mock_db, mock_user, valid_token):
        """Test adding inventory item with duplicate ID."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.find_one.return_value = {"item_id": 1}

        payload = {
            "item_id": 1,
            "item_name": "New Item"
        }

        response = client.post('/api/inventory',
                               json=payload,
                               headers={"Authorization": f"Bearer {valid_token}"},
                               content_type='application/json')
        assert response.status_code == 409
        data = json.loads(response.data)
        assert "already exists" in data["error"]

    def test_add_inventory_item_no_auth(self, client, mock_db):
        """Test adding inventory item without authentication."""
        payload = {
            "item_id": 1,
            "item_name": "New Item"
        }

        response = client.post('/api/inventory',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "missing" in data["error"].lower()

    def test_add_inventory_item_invalid_token(self, client, mock_db):
        """Test adding inventory item with invalid token."""
        payload = {
            "item_id": 1,
            "item_name": "New Item"
        }

        response = client.post('/api/inventory',
                               json=payload,
                               headers={"Authorization": "Bearer invalid_token"},
                               content_type='application/json')
        assert response.status_code == 401


class TestUpdateInventoryItem:
    """Test suite for PUT /api/inventory/<int:item_id> endpoint."""

    def test_update_inventory_item_success(self, client, mock_db, mock_user, valid_token):
        """Test successfully updating an inventory item."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.update_one.return_value = Mock(matched_count=1)

        payload = {
            "quantity": 200,
            "price": 24.99
        }

        response = client.put('/api/inventory/1',
                              json=payload,
                              headers={"Authorization": f"Bearer {valid_token}"},
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "updated successfully" in data["message"]

    def test_update_inventory_item_not_found(self, client, mock_db, mock_user, valid_token):
        """Test updating non-existent inventory item."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.update_one.return_value = Mock(matched_count=0)

        payload = {"quantity": 200}

        response = client.put('/api/inventory/999',
                              json=payload,
                              headers={"Authorization": f"Bearer {valid_token}"},
                              content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_update_inventory_item_no_auth(self, client, mock_db):
        """Test updating inventory item without authentication."""
        payload = {"quantity": 200}

        response = client.put('/api/inventory/1',
                              json=payload,
                              content_type='application/json')
        assert response.status_code == 401

    def test_update_inventory_item_invalid_token(self, client, mock_db):
        """Test updating inventory item with invalid token."""
        payload = {"quantity": 200}

        response = client.put('/api/inventory/1',
                              json=payload,
                              headers={"Authorization": "Bearer invalid_token"},
                              content_type='application/json')
        assert response.status_code == 401


class TestDeleteInventoryItem:
    """Test suite for DELETE /api/inventory/<int:item_id> endpoint."""

    def test_delete_inventory_item_admin_success(self, client, mock_db, mock_user, valid_token):
        """Test successfully deleting an inventory item as Admin."""
        mock_user["role"] = "Admin"
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.delete_one.return_value = Mock(deleted_count=1)

        response = client.delete('/api/inventory/1',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "deleted successfully" in data["message"]

    def test_delete_inventory_item_manager_success(self, client, mock_db, mock_user, valid_token):
        """Test successfully deleting an inventory item as Manager."""
        mock_user["role"] = "Manager"
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.delete_one.return_value = Mock(deleted_count=1)

        response = client.delete('/api/inventory/1',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 200

    def test_delete_inventory_item_employee_forbidden(self, client, mock_db, mock_user, valid_token):
        """Test deletion forbidden for Employee role."""
        mock_user["role"] = "Employee"
        mock_db.users.find_one.return_value = mock_user

        response = client.delete('/api/inventory/1',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Insufficient privileges" in data["error"]

    def test_delete_inventory_item_not_found(self, client, mock_db, mock_user, valid_token):
        """Test deleting non-existent inventory item."""
        mock_user["role"] = "Admin"
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.delete_one.return_value = Mock(deleted_count=0)

        response = client.delete('/api/inventory/999',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_delete_inventory_item_no_auth(self, client, mock_db):
        """Test deleting inventory item without authentication."""
        response = client.delete('/api/inventory/1')
        assert response.status_code == 401

    def test_delete_inventory_item_invalid_token(self, client, mock_db):
        """Test deleting inventory item with invalid token."""
        response = client.delete('/api/inventory/1',
                                 headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401

    def test_delete_inventory_item_various_roles(self, client, mock_db, mock_user, valid_token):
        """Test deletion with various user roles."""
        mock_db.inventory_items.delete_one.return_value = Mock(deleted_count=1)

        allowed_roles = ["Admin", "Manager"]
        for role in allowed_roles:
            mock_user["role"] = role
            mock_db.users.find_one.return_value = mock_user
            response = client.delete('/api/inventory/1',
                                     headers={"Authorization": f"Bearer {valid_token}"})
            assert response.status_code == 200


# ============================================================================
# THRESHOLD CONFIGURATION ENDPOINT TESTS
# ============================================================================

class TestConfigureThreshold:
    """Test suite for PUT /api/inventory/<int:item_id>/threshold endpoint."""

    def test_configure_threshold_success(self, client, mock_db, mock_user, valid_token):
        """Test successfully configuring a minimum threshold for an item."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.update_one.return_value = Mock(matched_count=1)

        payload = {"minimum_threshold": 20}

        response = client.put('/api/inventory/1/threshold',
                              json=payload,
                              headers={"Authorization": f"Bearer {valid_token}"},
                              content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "configured successfully" in data["message"]

    def test_configure_threshold_missing_field(self, client, mock_db, mock_user, valid_token):
        """Test configuring threshold without the minimum_threshold field."""
        mock_db.users.find_one.return_value = mock_user

        response = client.put('/api/inventory/1/threshold',
                              json={},
                              headers={"Authorization": f"Bearer {valid_token}"},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Missing required fields" in data["error"]

    def test_configure_threshold_item_not_found(self, client, mock_db, mock_user, valid_token):
        """Test configuring threshold for a non-existent item."""
        mock_db.users.find_one.return_value = mock_user
        mock_db.inventory_items.update_one.return_value = Mock(matched_count=0)

        payload = {"minimum_threshold": 10}

        response = client.put('/api/inventory/9999/threshold',
                              json=payload,
                              headers={"Authorization": f"Bearer {valid_token}"},
                              content_type='application/json')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_configure_threshold_no_auth(self, client, mock_db):
        """Test configuring threshold without authentication."""
        payload = {"minimum_threshold": 20}

        response = client.put('/api/inventory/1/threshold',
                              json=payload,
                              content_type='application/json')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "missing" in data["error"].lower()

    def test_configure_threshold_invalid_token(self, client, mock_db):
        """Test configuring threshold with an invalid token."""
        payload = {"minimum_threshold": 20}

        response = client.put('/api/inventory/1/threshold',
                              json=payload,
                              headers={"Authorization": "Bearer invalid_token"},
                              content_type='application/json')
        assert response.status_code == 401


# ============================================================================
# STOCK ALERT ENDPOINT TESTS
# ============================================================================

class TestStockAlerts:
    """Test suite for GET /api/inventory/alerts endpoint."""

    def test_stock_alerts_below_threshold(self, client, mock_db):
        """Test that an item below its threshold appears in the alerts."""
        items = [
            {"item_id": 102, "item_name": "Olive Oil", "quantity": 15.0, "minimum_threshold": 20}
        ]
        mock_db.inventory_items.find.return_value = items

        response = client.get('/api/inventory/alerts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["alert_count"] == 1
        assert data["items_at_risk"][0]["item_id"] == 102

    def test_stock_alerts_above_threshold(self, client, mock_db):
        """Test that an item above its threshold is not flagged."""
        items = [
            {"item_id": 101, "item_name": "Fresh Tomatoes", "quantity": 120.5, "minimum_threshold": 30}
        ]
        mock_db.inventory_items.find.return_value = items

        response = client.get('/api/inventory/alerts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["alert_count"] == 0
        assert len(data["items_at_risk"]) == 0

    def test_stock_alerts_quantity_equals_threshold(self, client, mock_db):
        """Test that an item sitting exactly on its threshold is flagged."""
        items = [
            {"item_id": 5, "item_name": "Boundary Item", "quantity": 5, "minimum_threshold": 5}
        ]
        mock_db.inventory_items.find.return_value = items

        response = client.get('/api/inventory/alerts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["alert_count"] == 1

    def test_stock_alerts_empty_inventory(self, client, mock_db):
        """Test alerts when no items carry a threshold."""
        mock_db.inventory_items.find.return_value = []

        response = client.get('/api/inventory/alerts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["alert_count"] == 0
        assert data["items_at_risk"] == []

    def test_stock_alerts_mixed_items(self, client, mock_db):
        """Test alerts with a mix of flagged and healthy items."""
        items = [
            {"item_id": 1, "quantity": 3, "minimum_threshold": 10},
            {"item_id": 2, "quantity": 50, "minimum_threshold": 10},
            {"item_id": 3, "quantity": 8, "minimum_threshold": 8}
        ]
        mock_db.inventory_items.find.return_value = items

        response = client.get('/api/inventory/alerts')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["alert_count"] == 2


# ============================================================================
# USER MANAGEMENT ENDPOINTS TESTS (Owner-only)
# ============================================================================

class TestListUsers:
    """Test suite for GET /api/users endpoint (Owner-only)."""

    def test_list_users_owner_success(self, client, mock_db, mock_user, valid_token):
        """Owner can list all accounts; passwords are excluded by the query."""
        mock_user["role"] = "Owner"
        mock_db.users.find_one.return_value = mock_user
        mock_db.users.find.return_value = [
            {"user_id": 1, "name": "Nikan Eidi", "email": "nikan@smartstock.com", "role": "Admin"},
            {"user_id": 2, "name": "Jun Ho Jeon", "email": "junho@smartstock.com", "role": "Manager"},
        ]

        response = client.get('/api/users',
                              headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["email"] == "nikan@smartstock.com"

    def test_list_users_non_owner_forbidden(self, client, mock_db, mock_user, valid_token):
        """Admin (non-Owner) is forbidden from listing accounts."""
        mock_user["role"] = "Admin"
        mock_db.users.find_one.return_value = mock_user

        response = client.get('/api/users',
                              headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Insufficient privileges" in data["error"]

    def test_list_users_no_auth(self, client, mock_db):
        """Listing accounts requires authentication."""
        response = client.get('/api/users')
        assert response.status_code == 401


class TestDeleteUser:
    """Test suite for DELETE /api/users/<email> endpoint (Owner-only)."""

    def test_delete_user_owner_success(self, client, mock_db, mock_user, valid_token):
        """Owner can delete another user's account by email."""
        mock_user["role"] = "Owner"  # owner email is test@example.com
        mock_db.users.find_one.return_value = mock_user
        mock_db.users.delete_one.return_value = Mock(deleted_count=1)

        response = client.delete('/api/users/other@example.com',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "deleted successfully" in data["message"]

    def test_delete_user_self_blocked(self, client, mock_db, mock_user, valid_token):
        """Owner cannot delete their own account."""
        mock_user["role"] = "Owner"  # email test@example.com
        mock_db.users.find_one.return_value = mock_user

        response = client.delete('/api/users/test@example.com',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "your own account" in data["error"]

    def test_delete_user_not_found(self, client, mock_db, mock_user, valid_token):
        """Deleting a non-existent user returns 404."""
        mock_user["role"] = "Owner"
        mock_db.users.find_one.return_value = mock_user
        mock_db.users.delete_one.return_value = Mock(deleted_count=0)

        response = client.delete('/api/users/ghost@example.com',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "not found" in data["error"].lower()

    def test_delete_user_non_owner_forbidden(self, client, mock_db, mock_user, valid_token):
        """Admin (non-Owner) cannot delete accounts."""
        mock_user["role"] = "Admin"
        mock_db.users.find_one.return_value = mock_user

        response = client.delete('/api/users/other@example.com',
                                 headers={"Authorization": f"Bearer {valid_token}"})
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "Insufficient privileges" in data["error"]

    def test_delete_user_no_auth(self, client, mock_db):
        """Deleting a user requires authentication."""
        response = client.delete('/api/users/other@example.com')
        assert response.status_code == 401

# ============================================================================
# SUPPLIER SOURCING & PRICE COMPARISON ENDPOINT TESTS
# ============================================================================

class TestGetSuppliers:
    """Test suite for GET /api/suppliers endpoint."""

    def test_get_all_suppliers_success(self, client, mock_db):
        """Test retrieving the full supplier registry."""
        suppliers = [
            {"supplier_id": 1, "supplier_name": "Ontario Local Foods Inc"},
            {"supplier_id": 2, "supplier_name": "Fresh Valley Distributors"},
        ]
        mock_db.suppliers.find.return_value = suppliers

        response = client.get('/api/suppliers')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["supplier_name"] == "Ontario Local Foods Inc"

    def test_get_all_suppliers_empty(self, client, mock_db):
        """Test retrieving suppliers when the registry is empty."""
        mock_db.suppliers.find.return_value = []

        response = client.get('/api/suppliers')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == []


class TestItemSupplierPrices:
    """Test suite for GET /api/inventory/<int:item_id>/prices endpoint."""

    def test_prices_sorted_and_lowest_flagged(self, client, mock_db):
        """Test that offers come back cheapest-first with the best one flagged."""
        prices = [
            {"supplier_id": 1, "item_id": 101, "price": 2.45, "last_updated": "2026-06-01"},
            {"supplier_id": 2, "item_id": 101, "price": 2.10, "last_updated": "2026-06-01"},
            {"supplier_id": 3, "item_id": 101, "price": 2.80, "last_updated": "2026-06-01"},
        ]
        suppliers = [
            {"supplier_id": 1, "supplier_name": "Ontario Local Foods Inc"},
            {"supplier_id": 2, "supplier_name": "Fresh Valley Distributors"},
            {"supplier_id": 3, "supplier_name": "Metro Wholesale Grocers"},
        ]
        mock_db.supplier_prices.find.return_value = prices
        mock_db.suppliers.find.return_value = suppliers

        response = client.get('/api/inventory/101/prices')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["item_id"] == 101
        assert data["offer_count"] == 3
        assert data["best_price"] == 2.10
        # Offers are ordered from cheapest to most expensive
        assert [o["price"] for o in data["offers"]] == [2.10, 2.45, 2.80]
        # Only the cheapest offer carries the lowest flag
        assert data["offers"][0]["is_lowest"] is True
        assert data["offers"][0]["supplier_name"] == "Fresh Valley Distributors"
        assert all(o["is_lowest"] is False for o in data["offers"][1:])

    def test_prices_no_offers(self, client, mock_db):
        """Test the response shape when no vendor has quoted the item."""
        mock_db.supplier_prices.find.return_value = []

        response = client.get('/api/inventory/999/prices')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["offer_count"] == 0
        assert data["best_price"] is None
        assert data["offers"] == []

    def test_prices_unknown_supplier(self, client, mock_db):
        """Test that a price with no matching supplier falls back gracefully."""
        prices = [
            {"supplier_id": 99, "item_id": 101, "price": 5.00, "last_updated": "2026-06-01"},
        ]
        mock_db.supplier_prices.find.return_value = prices
        mock_db.suppliers.find.return_value = []

        response = client.get('/api/inventory/101/prices')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["offers"][0]["supplier_name"] == "Unknown Supplier"
        assert data["offers"][0]["is_lowest"] is True


# ============================================================================
# ERROR HANDLING AND EDGE CASES
# ============================================================================

class TestErrorHandling:
    """Test suite for general error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test 405 error for wrong HTTP method."""
        response = client.post('/')
        assert response.status_code == 405

    def test_invalid_json(self, client):
        """Test invalid JSON payload."""
        response = client.post('/api/users',
                               data='invalid json',
                               content_type='application/json')
        assert response.status_code == 500


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_user_creation_and_login_flow(self, client, mock_db, mock_user):
        """Test complete flow: create user -> login -> get token."""
        # Create user
        mock_db.users.find_one.return_value = None
        create_response = client.post('/api/users',
                                      json={
                                          "name": "Test User",
                                          "email": "test@example.com",
                                          "password": "password123",
                                          "role": "Admin"
                                      },
                                      content_type='application/json')
        assert create_response.status_code == 201

        # Login
        mock_db.users.find_one.return_value = mock_user
        login_response = client.post('/api/auth/login',
                                     json={
                                         "email": "test@example.com",
                                         "password": "password123"
                                     },
                                     content_type='application/json')
        assert login_response.status_code == 200
        token = json.loads(login_response.data)["token"]
        assert token is not None

    def test_inventory_crud_workflow(self, client, mock_db, mock_user, valid_token):
        """Test complete inventory CRUD workflow."""
        mock_db.users.find_one.return_value = mock_user

        # Create
        mock_db.inventory_items.find_one.return_value = None
        create_response = client.post('/api/inventory',
                                      json={
                                          "item_id": 1,
                                          "item_name": "Test Item"
                                      },
                                      headers={"Authorization": f"Bearer {valid_token}"},
                                      content_type='application/json')
        assert create_response.status_code == 201

        # Read
        item = {"item_id": 1, "item_name": "Test Item"}
        mock_db.inventory_items.find_one.return_value = item
        read_response = client.get('/api/inventory/1')
        assert read_response.status_code == 200

        # Update
        mock_db.inventory_items.update_one.return_value = Mock(matched_count=1)
        update_response = client.put('/api/inventory/1',
                                     json={"item_name": "Updated Item"},
                                     headers={"Authorization": f"Bearer {valid_token}"},
                                     content_type='application/json')
        assert update_response.status_code == 200

        # Delete
        mock_user["role"] = "Admin"
        mock_db.inventory_items.delete_one.return_value = Mock(deleted_count=1)
        delete_response = client.delete('/api/inventory/1',
                                        headers={"Authorization": f"Bearer {valid_token}"})
        assert delete_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])