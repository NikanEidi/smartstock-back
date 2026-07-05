# Smart Stock — Backend API

### Accessible Supply Chain Intelligence for Small-Scale Restaurants.

**Smart Stock** is a lightweight, cloud-native web application that replaces manual inventory guesswork with AI driven precision. This repository contains the Python backend REST API, responsible for secure data persistence, authentication, and serving as the foundation for our AI predictive models. The application is deployed on Render and connected to a MongoDB Atlas cluster.

---

## About the Backend

While the frontend delivers a seamless BYOD (Bring Your Own Device) experience, the backend acts as the secure engine driving the enterprise-grade analytics. It provides a robust, scalable RESTful architecture designed to handle inventory mutations, enforce strict Role-Based Access Control (RBAC), and process complex queries required by small-scale restaurants operating on thin margins.

## Key Features

* **Robust REST API:** Full CRUD operations for inventory items, categories, and stock thresholds.
* **Stateless Authentication:** Secure JWT-based (JSON Web Token) authentication paired with `bcrypt` password hashing to protect sensitive business data.
* **Role-Based Access Control (RBAC):** Middleware-enforced authorization separating Admin, Manager, and Employee privileges (e.g., only Admins and Managers can delete critical stock records).
* **Low-Stock Threshold Alerts:** Per-item minimum thresholds with an evaluation endpoint that surfaces every item at or below its safety floor, ready to drive stockout alert UIs.
* **Cloud-Native Database:** Fully integrated with MongoDB Atlas for high availability, utilizing PyMongo with custom SSL/TLS bypass configurations for seamless Render deployments.
* **AI-Ready Architecture:** Pre-scaffolded webhooks and payload receipt pipelines designed for the upcoming integration of NLP (Gemma) and Demand Forecasting (Scikit-Learn) models.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Language** | Python 3.10+ |
| **Framework** | Flask 3.0 |
| **Database** | MongoDB Atlas (NoSQL) |
| **Driver / ORM** | PyMongo |
| **Security** | PyJWT, bcrypt, Flask-CORS |
| **Testing** | pytest, pytest-mock |
| **Hosting** | Render (Gunicorn WSGI) |

---

## Project Structure

```
smartstock-back/
├── app.py              # Flask app: routes, db connection, auth middleware
├── chatbot.py          # /api/chat level-1 rule-based intent layer
├── forecast.py         # /api/forecast RandomForest demand pipeline
├── seed.py             # Seed collections, indexes, and mock data
├── prepare_ai_data.py  # Build historical_data from the Kaggle dataset
├── test_app.py         # pytest suite (mocks the database)
├── requirements.txt
└── .github/workflows/  # CI: run the pytest suite on push and PRs
```

Route handlers stay thin in `app.py` and delegate heavier logic to dedicated
modules (e.g. `chatbot.py`), which take the `db` handle as an argument so they
stay independent of the Flask app and easy to test.

---

## Getting Started

### Prerequisites

* Python 3.10 or higher
* pip (Python package manager)
* A MongoDB Atlas cluster URI

### Installation

1. Clone the repository and navigate to the project folder:

```bash
git clone https://github.com/NikanEidi/smartstock-back.git
cd smartstock-back

```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

```

3. Install the required dependencies:

```bash
pip install -r requirements.txt

```

### Environment Variables

Create a `.env` file in the root directory and configure the following variables:

```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0...
PORT=8000
JWT_SECRET=your_super_secure_random_string_here

```

*Note: The `.env` file holds sensitive credentials and must never be committed. Make sure it is listed in `.gitignore`.*

### Database Seeding (First-time setup)

Initialize the MongoDB collections, enforce unique indexes, and generate mock data (including hashed admin credentials):

```bash
python seed.py

```

*Note: The default seed script generates two users: `nikan@smartstock.com` (Admin) and `junho@smartstock.com` (Manager) with pre-configured passwords.*

### Local Development

Run the Flask development server:

```bash
python app.py

```

The API will be available at `http://localhost:8000`.

### Testing

The backend ships with a full `pytest` suite covering authentication, inventory CRUD, RBAC, threshold configuration, and stock alerts. Run it from the project root:

```bash
python -m pytest test_app.py -v

```

*Note: Use `python -m pytest` (rather than a bare `pytest`) to ensure the suite runs inside the active virtual environment. The token fixtures read `JWT_SECRET` directly from the app, so tests pass regardless of the secret configured in your environment.*

---

## Core API Endpoints

### Authentication

* `POST /api/users` - Register a new account.
* `POST /api/auth/login` - Authenticate and receive a JWT.
* `POST /api/auth/logout` - Invalidate client session.

### Inventory

* `GET /api/inventory` - Retrieve all stock items.
* `GET /api/inventory/<item_id>` - Retrieve a specific item.
* `POST /api/inventory` - Create a new item (Requires Auth).
* `PUT /api/inventory/<item_id>` - Modify an item (Requires Auth).
* `DELETE /api/inventory/<item_id>` - Discard an item (Admin / Manager only).

### Thresholds & Stock Alerts

* `PUT /api/inventory/<item_id>/threshold` - Set or revise an item's `minimum_threshold` (Requires Auth).
* `GET /api/inventory/alerts` - Retrieve every item sitting at or below its configured threshold.

The alerts endpoint responds with a count and the list of flagged items, ready for a stockout alert UI:

```json
{
  "alert_count": 1,
  "items_at_risk": [
    {
      "item_id": 102,
      "item_name": "Olive Oil",
      "category": "Groceries",
      "quantity": 15.0,
      "minimum_threshold": 20,
      "expiry_date": null
    }
  ]
}
```

### AI Modules

* `POST /api/chat` - Natural language operational assistant. Level 1 rule-based intent matching over live data, covering low stock, item quantity, item count, listing items/categories, items by category, suppliers, cheapest price, expiring items, sales trends, waste totals, plus greeting/help. A model layer will sit behind the rules next.
* `POST /api/forecast` - Demand forecasting endpoint. Target for the scikit-learn time-series engine (currently returns a mocked prediction schema).

---

## Deployment

The backend is currently deployed as a Web Service on **Render**. Pushes to the `main` branch trigger automatic deployments using Gunicorn as the production WSGI HTTP server.

```bash
# Production execution command
gunicorn app:app

```