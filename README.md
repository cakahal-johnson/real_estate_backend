```
real_estate_backend/
│
├── app/
│   ├── main.py                # Entry point for FastAPI
│   ├── models.py              # SQLAlchemy ORM models
│   ├── schemas.py             # Pydantic models (request/response)
│   ├── database.py            # DB connection + session logic
│   │
│   ├── core/
│   │   ├── config.py          # Environment variables, settings
│   │   └── security.py        # JWT, password hashing utils
│   │
│   ├── routers/               # Modular routes (APIs)
│   │   ├── listings.py
│   │   ├── users.py
│   │   └── auth.py
│   │
│   ├── utils/                 # (optional) helpers like email, file uploads
│   ├── tests/                 # pytest unit/integration tests
│   └── __init__.py
│
├── alembic/                   # (created later for migrations)
│
├── .env                       # Environment variables
├── requirements.txt            # Python dependencies
├── .gitignore
└── README.md
```

# Create venv (Windows)
python -m venv venv

# or (Mac/Linux)
python3 -m venv venv

---

# Windows (PowerShell)
venv\Scripts\Activate

# Mac/Linux
source venv/bin/activate

---
pip install -r requirements.txt
---
Confirm install success with:

pip list
---
# From here, you’ll run the server with:
uvicorn app.main:app --reload
---