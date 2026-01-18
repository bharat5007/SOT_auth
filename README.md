# Auth Microservice - FastAPI Backend

A production-ready JWT authentication microservice built with FastAPI, SQLAlchemy, and PostgreSQL.

## Features

- 🔐 JWT Authentication (Access + Refresh tokens)
- 🔒 Bcrypt password hashing
- 👤 User & Vendor registration
- 🛡️ Role-based access control (User, Vendor, Admin)
- 🔄 Token rotation for security
- 📦 SQLAlchemy ORM with PostgreSQL

## Quick Start

### 1. Clone and Setup

```bash
cd backend-template
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials and secret key
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Access API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login with email/password |
| POST | `/api/v1/auth/signup` | Register new user |
| POST | `/api/v1/auth/vendor/signup` | Register vendor with business |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| GET | `/api/v1/auth/me` | Get current user context |
| POST | `/api/v1/auth/logout` | Logout (revoke tokens) |
| PATCH | `/api/v1/auth/profile` | Update user profile |
| POST | `/api/v1/auth/change-password` | Change password |

## Database Setup

### PostgreSQL

```sql
CREATE DATABASE auth_db;
CREATE USER auth_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE auth_db TO auth_user;
```

### Run Migrations (Optional - using Alembic)

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Railway/Render

1. Connect your GitHub repo
2. Set environment variables
3. Deploy!

## Frontend Integration

Update your frontend config to point to this backend:

```typescript
// src/config/api.ts
export const API_BASE_URL = 'https://your-backend-url.com';
```

## Security Notes

⚠️ **Important for Production:**

1. Change `SECRET_KEY` to a strong random value
2. Use HTTPS in production
3. Set proper `ALLOWED_ORIGINS` for CORS
4. Enable rate limiting
5. Use a proper database (not SQLite)
6. Store secrets in environment variables

## License

MIT
