# Smart Stock — Backend API

### Accessible Supply Chain Intelligence for Small-Scale Restaurants.

**Smart Stock** is a lightweight, cloud-native web application that replaces manual inventory guesswork with AI driven precision. This repository contains the Python backend REST API, responsible for secure data persistence, authentication, and serving as the foundation for our AI predictive models. The application is deployed on Render and connected to a MongoDB Atlas cluster.

---

## About the Backend

While the frontend delivers a seamless BYOD (Bring Your Own Device) experience, the backend acts as the secure engine driving the enterprise-grade analytics. It provides a robust, scalable RESTful architecture designed to handle inventory mutations, enforce strict Role-Based Access Control (RBAC), and process complex queries required by small-scale restaurants operating on thin margins.

## Key Features

* **Robust REST API:** Full CRUD operations for inventory items, categories, and stock thresholds.
* **Stateless Authentication:** Secure JWT-based (JSON Web Token) authentication paired with `bcrypt` password hashing to protect sensitive business data.
* **Role-Based Access Control (RBAC):** Middleware-enforced authorization separating Admin, Manager, and Employee privileges (e.g., only Admins can delete critical stock records).
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
| **Hosting** | Render (Gunicorn WSGI) |

---

## Getting Started

### Prerequisites

* Python 3.10 or higher
* pip (Python package manager)
* A MongoDB Atlas cluster URI

### Installation

1. Clone the repository and navigate to the project folder:

```bash
git clone <your-repo-url>
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

---

## Core API Endpoints

### Authentication

* `POST /api/users` - Register a new account.
* `POST /api/auth/login` - Authenticate and receive a JWT.
* `POST /api/auth/logout` - Invalidate client session.

### Inventory (Protected Routes)

* `GET /api/inventory` - Retrieve all stock items.
* `GET /api/inventory/<item_id>` - Retrieve a specific item.
* `POST /api/inventory` - Create a new item (Requires Auth).
* `PUT /api/inventory/<item_id>` - Update an item (Requires Auth).
* `DELETE /api/inventory/<item_id>` - Remove an item (Admin only).

---

## Deployment

The backend is currently deployed as a Web Service on **Render**. Pushes to the `main` branch trigger automatic deployments using Gunicorn as the production WSGI HTTP server.

```bash
# Production execution command
gunicorn app:app

```

