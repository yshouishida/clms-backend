# Project Structure

```text
clms-backend/
├── README.md
├── run.py
└── backend/
    ├── .env.example
    ├── .gitignore
    ├── __init__.py
    ├── config/
    │   └── settings.py
    ├── controllers/
    │   └── student_control.py
    ├── database/
    │   └── connection.py
    ├── repositories/
    │   ├── instructors_repository.py
    │   ├── students_repository.py
    │   └── users_repository.py
    ├── routes/
    │   ├── instructors_route.py
    │   ├── student_route.py
    │   └── users_route.py
    ├── services/
    │   └── student_service.py
    └── utils/
        ├── api_response.py
        └── jwt.py
```
