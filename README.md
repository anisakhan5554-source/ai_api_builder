# AI API Builder

A production-ready REST API built with FastAPI and Python.

## Features
- JWT Authentication
- User CRUD with Role-Based Access Control
- Password Hashing (bcrypt)
- Rate Limiting
- Input Validation
- Global Exception Handling
- Database Migrations (Alembic)
- Automated Tests (pytest)
- Logging System

## Tech Stack
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- JWT
- Alembic

## Installation
pip install -r requirements.txt
uvicorn main:app --reload

## API Endpoints
- POST /api/login
- GET/POST /api/users
- GET/PUT/DELETE /api/users/{id}
- GET /api/profile
- GET /api/me

## LIVE API
https://aiapibuilder-production.up.railway.app/docs