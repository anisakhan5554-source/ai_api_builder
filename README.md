# # AI API Builder

A production-ready AI-powered REST API built with FastAPI and Python.
Generate, save, version, and export FastAPI code using AI — all through a single API.

## Live API
https://aiapibuilder-production.up.railway.app/docs

## Features
- JWT Authentication
- User CRUD with Role-Based Access Control (RBAC)
- Password Hashing (bcrypt)
- Rate Limiting (slowapi)
- Input Validation
- Global Exception Handling
- Database Migrations (Alembic)
- Automated Tests (pytest)
- Logging System
- AI Code Generation (Groq/Llama)
- AI OpenAPI Schema Generation
- Save & Version Generated APIs
- Export Generated Code as .py file
- Generation History with Pagination & Search
- Dashboard Stats
- Prompt Templates
- Redis Caching (Upstash)
- Background Tasks
- Soft Delete
- Docker Support

## Tech Stack
- FastAPI
- SQLAlchemy
- PostgreSQL
- Pydantic
- JWT
- Alembic
- Docker
- Railway (deployment)
- Groq AI (Llama 3.3)
- Upstash Redis

## Installation
pip install -r requirements.txt
uvicorn main:app --reload

## API Endpoints

### Auth
- POST /api/v1/login

### Users
- POST /api/v1/generate-api (create user)
- GET /api/v1/users
- GET /api/v1/users/{id}
- PUT /api/v1/users/{id}
- DELETE /api/v1/users/{id}

### AI
- POST /api/v1/ai/generate
- POST /api/v1/ai/schema
- GET /api/v1/ai/history
- GET /api/v1/ai/export/{id}
- GET /api/v1/ai/stats
- GET /api/v1/ai/templates
- GET /api/v1/ai/versions/{id}
- DELETE /api/v1/ai/history/{id}

## Environment Variables
DATABASE_URL=
SECRET_KEY=
GROQ_API_KEY=
GEMINI_API_KEY=
AI_PROVIDER=groq
REDIS_URL=
REDIS_TOKEN=

