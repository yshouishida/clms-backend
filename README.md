# CLMS Backend

## Start the server

The project uses Python 3, Flask, and a MySQL database. Run these commands in PowerShell from the `clms-backend` directory.

1. Create a virtual environment and install the packages imported by the project. There is currently no dependency manifest in the repository.

   ```powershell
   python -m venv backend/.venv
   .\backend\.venv\Scripts\python.exe -m pip install Flask python-dotenv PyMySQL PyJWT
   ```

2. Make sure MySQL is running and that `DB_NAME` refers to a database with the application's tables. This repository does not include a table creation or migration script.

3. Create `backend/.env` if it does not already exist:

   ```powershell
   if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
   ```

   Edit `backend/.env` so every name listed in `.env.example` has a value in `KEY=value` format. For example, replace the placeholders below with your database settings and secret:

   ```dotenv
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_NAME=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   JWT_SECRET_KEY=replace-with-a-random-secret
   JWT_TOKEN_EXPIRES=3600
   ```

   `DB_PORT` and `JWT_TOKEN_EXPIRES` must be integers because the code converts both with `int(...)`. The `.env.example` file lists names only, so it must be filled in before use.

4. Start the development server:

   ```powershell
   .\backend\.venv\Scripts\python.exe run.py
   ```

   Flask serves the application at `http://127.0.0.1:5000` by default. Stop it with `Ctrl+C`. `run.py` enables debug mode; the repository does not currently define a production server command.

## Project Structure

```text
clms-backend/
├── README.md                              # Setup instructions and project map
├── run.py                                 # Creates and starts the Flask development app
└── backend/                               # Application package
    ├── .env.example                       # Required environment variable names
    ├── .gitignore                         # Ignores local secrets, caches, and the views script
    ├── __init__.py                        # App factory and registered blueprints
    ├── config/                            # Application settings
    │   └── settings.py                    # Reads JWT settings from the environment
    ├── controllers/                       # HTTP request and response handling
    │   ├── instructors_control.py         # Instructor request handlers
    │   └── students_control.py            # Student request handlers
    ├── database/                          # Database access and SQL scripts
    │   ├── connection.py                  # Creates PyMySQL connections
    │   └── views.sql                      # Local SQL views; ignored by Git
    ├── repositories/                      # Database queries
    │   ├── instructors_repository.py      # Instructor queries
    │   ├── students_repository.py         # Student queries
    │   └── users_repository.py            # User queries
    ├── routes/                            # Flask blueprints and URL routes
    │   ├── auth_route.py                  # Authentication route stub; not registered
    │   ├── instructors_route.py           # Instructor endpoints
    │   ├── students_route.py              # Student endpoints
    │   └── users_route.py                 # Users blueprint; no endpoints defined yet
    ├── services/                          # Business logic between controllers and queries
    │   ├── instructors_service.py         # Instructor operations
    │   └── students_service.py            # Student operations
    └── utils/                             # Shared helpers
        ├── api_response.py                # JSON success and error responses
        └── jwt.py                         # JWT creation and access decorators
```
