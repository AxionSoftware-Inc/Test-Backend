# QuestLab Backend

Minimal Django REST Framework backend for the frontend MVP.

## Stack

- Django 5.2
- Django REST Framework
- PostgreSQL
- drf-spectacular for API docs

## Database

Current dev database settings:

- DB: `answer`
- User: `postgres`
- Password: `root`
- Host: `localhost`
- Port: `5432`

## Setup

```powershell
cd backend
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 127.0.0.1:8000
```

## Main Flow

Frontend hierarchy:

```text
subjects -> topics -> levels -> tests -> start session -> answer -> submit
```

API endpoints:

```text
GET  /api/subjects/
GET  /api/subjects/{subjectSlug}/topics/
GET  /api/topics/{topicSlug}/levels/
GET  /api/topics/{topicSlug}/tests/?difficulty=beginner
GET  /api/tests/{testSlug}/
POST /api/tests/{testSlug}/start/
POST /api/sessions/{sessionId}/answer/
POST /api/sessions/{sessionId}/submit/
```

Docs:

```text
GET /api/docs/
GET /api/schema/
```
