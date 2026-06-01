import pytest
import json
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from app import app, token_required

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
    return jwt.encode(payload, "fallback_secret_key_if_not_found", algorithm="HS256")

@pytest.fixture
def expired_token():
    """Generate an expired JWT token for testing."""
    payload = {
        "email": "test@example.com",
        "role": "Admin",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }
    return jwt.encode(payload, "fallback_secret_key_if_not_found", algorithm="HS256")

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

    def test_chat_with_message(self, client):
        """Test chat endpoint with a message."""
        payload = {"message": "What is the current inventory?"}

        response = client.post('/api/chat',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "response" in data
        assert "source" in data
        assert "Operations NLP Architecture" in data["source"]
        assert "What is the current inventory?" in data["response"]

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

# ============================================================================
# FORECAST ENDPOINT TESTS
# ============================================================================

class TestDemandForecast:
    """Test suite for POST /api/forecast endpoint."""

    def test_forecast_with_item_id(self, client):
        """Test forecast endpoint with valid item ID."""
        payload = {"item_id": 42}

        response = client.post('/api/forecast',
                               json=payload,
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "item_id" in data
        assert data["item_id"] == 42
        assert "predicted_demand" in data
        assert "confidence_level" in data
        assert isinstance(data["predicted_demand"], (int, float))
        assert isinstance(data["confidence_level"], (int, float))

    def test_forecast_without_item_id(self, client):
        """Test forecast endpoint without item ID."""
        response = client.post('/api/forecast',
                               json={},
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["item_id"] is None
        assert "predicted_demand" in data

    def test_forecast_no_json_body(self, client):
        """Test forecast endpoint with no JSON body."""
        response = client.post('/api/forecast')
        assert response.status_code == 415

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
