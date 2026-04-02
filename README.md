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
````
real_estate_backend/
│
├── app/
│   ├── __init__.py         ✅ must exist
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── core/
│   │   ├── __init__.py     ✅ must exist
│   │   └── config.py
│   └── routers/
│       ├── __init__.py     ✅ must exist
│       └── listings.py
│
├── venv/
└── requirements.txt

````
pip install pydantic[email]

{
  "full_name": "string",
  "email": "user@example.com",
  "password": "string",
  "role": "buyer"
}

Quick Example Route Summary
Route	Description	Auth Required	Role
GET /listings	Public — All listings	❌	Any
GET /listings/{id}	Public — Single listing	❌	Any
POST /listings	Create a listing	✅	Agent only
PUT /listings/{id}	Update own listing	✅	Agent only
DELETE /listings/{id}	Delete own listing	✅	Agent only
GET /listings/me	View own listings	✅	Agent only

{
  "full_name": "Bob Buyer",
  "email": "bob@example.com",
  "password": "strongpassword",
  "role": "buyer"
}

##  Post a Listing (Agent Only)

{
  "full_name": "Alice Agent",
  "email": "alice@example.com",
  "password": "strongpassword",
  "role": "agent"
}

username: alice@example.com
password: strongpassword

POST → http://127.0.0.1:8000/listings/

{
  "title": "Luxury Apartment in Ikoyi",
  "description": "Spacious 3-bedroom apartment with a waterfront view.",
  "price": 500000.0,
  "location": "Lagos, Nigeria",
  "image_url": "https://example.com/ikoyi-apartment.jpg"
}

pip install alembic

/real_estate_backend
│
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│
└── alembic.ini

## Future Use

Each time you change a model (e.g., add a column):

alembic revision --autogenerate -m "add new field"
alembic upgrade head

## Week 3 

extension (filters, pagination, and search for /listings)?



| Feature         | Example                                      |
| --------------- | -------------------------------------------- |
| Search          | `/listings?search=apartment`                 |
| Location filter | `/listings?location=lagos`                   |
| Price range     | `/listings?min_price=50000&max_price=200000` |
| Pagination      | `/listings?skip=10&limit=5`                  |


✅ Example tests (Swagger or Postman)

1️⃣ Get listings by keyword

GET /listings?search=sea


2️⃣ Filter by location and price

GET /listings?location=lagos&min_price=80000&max_price=200000


3️⃣ Paginate results

GET /listings?skip=10&limit=5


4️⃣ Combine all

GET /listings?search=apartment&location=ikoyi&min_price=100000&max_price=500000&skip=0&l

## Next
sorting options (sort_by=price or sort_by=created_at) and a total count for pagination response (like { "total": 120, "items": [...] }) to make it more API-friendly for frontend apps?

Week 3+ enhancements 🎯
Let’s now add sorting (sort_by, sort_order) and a paginated JSON response that includes both the total count and the paginated items.

2️⃣ /listings endpoint — Feature Verification

Let's review what the Week 3+ enhancement required and whether your implementation meets it:

Feature	Requirement	Status
🔎 Search	Filter by title or description	✅ Implemented (ilike)

📍 Location filter	Filter by city/region	✅ Implemented

💰 Price range	min_price, max_price	✅ Implemented

📄 Pagination	skip and limit	✅ Implemented

📊 Total count	Return { "total": X, "items": [...] }	✅ Implemented

↕️ Sorting	sort_by (price, created_at, title) and sort_order (asc, desc)	✅ Implemented

⚙️ Frontend API-ready JSON	Return consistent object for frontend	✅ Implemented

🧠 Search term normalization	Lowercased search for ilike	✅ Implemented

✅ Everything matches perfectly for a production-grade listings endpoint.

✅ 3️⃣ Example API Response (Realistic Output)

When calling:

GET /listings?search=apartment&sort_by=price&sort_order=asc&skip=0&limit=5

## Week 4
Week 4 next — e.g. Favorites, Agent profile listings, and Buyer saved searches (with a new /favorites table and endpoint)

alembic revision --autogenerate -m "Add favorites table"
alembic upgrade head

// React / Vue example
const toggleFavorite = async (listingId, token) => {
  const res = await fetch(`/favorites/toggle/${listingId}`, {
    method: "POST",
    headers: { "Authorization": `Bearer ${token}` }
  });
  const data = await res.json();
  console.log(data.is_favorited ? "❤️ Favorited" : "💔 Unfavorited");
};


---
extend your FavoriteResponse schema to include a nested ListingResponse (so /favorites returns full listing data inside each favorite)?
That’s very useful for building a “My Favorites” page without extra API calls.
---

## 🧩 WEEK 5 — Advanced Features & Production Enhancements

Here’s the recommended scope and structure:

✅ 1. Search + Filter + Pagination for Listings

Make your /listings endpoint frontend-ready with:

Query params:

?q= → search title/description

?min_price=&max_price=

?location=

?page=&limit=

Use SQLAlchemy filters and offset/limit for pagination.

Return a PaginatedListingsResponse with total + items.

File: routers/listings.py
Goal: user-friendly browsing, and efficient API calls for your frontend grid.

✅ 2. Image Uploads / Media Handling

Add support for uploading listing images:

Use FastAPI UploadFile + File dependency.

Store locally in /uploads or connect to a cloud bucket (S3, Cloudinary later).

Return the stored image URL in the response.

File: routers/uploads.py
Goal: Agents can upload property photos when creating or updating listings.

✅ 3. Enhanced Security & User Management

Add /users/me endpoint to fetch profile details.

Add /users/update-profile (PATCH) for name/password change.

Password update with verify_password check.

Optional: Add email uniqueness validator and proper 409 Conflict errors.

✅ 4. Logging, Error Handling, and CORS

Add centralized error handling for 404, 422, etc.

Enable CORS for frontend devs (React/Vue).

Integrate Python logging for DB actions and errors.

✅ 5. Optional: Admin Dashboard Endpoints

/admin/users → list all users (admin-only)

/admin/listings → moderation view (admin-only)

Add @require_admin dependency filter in security.py

✅ 6. Frontend Integration Prep (if full-stack)

Return consistent JSON format (success, message, data).

Add status codes + pagination metadata.

Make endpoints predictable for frontend (React / Next / Vue).

````
app/
 ┣ routers/
 ┃ ┣ listings.py        (add filters & pagination)
 ┃ ┣ uploads.py         (new)
 ┃ ┣ users.py           (profile endpoints)
 ┃ ┗ admin.py           (optional)
 ┣ core/
 ┃ ┣ cors.py            (CORS setup)
 ┃ ┗ logging.py         (custom logging)
 ┗ utils/
    ┗ file_handler.py   (save uploads safely)
````

## 🚀 Stretch Goals (for bonus marks / portfolio polish)

Email notifications (when new listing added, etc.)

Background tasks with FastAPI.BackgroundTasks

Rate limiting / throttling middleware

Dockerfile + environment variables

Full test suite (pytest)


Test Flow in FastAPI Docs

Register /users/register

{
  "full_name": "Agent One",
  "email": "agent@example.com",
  "password": "strongpass",
  "role": "agent"
}


Login /auth/login

username: agent@example.com

password: strongpass

Copy token.

Upload Image /uploads/image

Choose file (JPG/PNG)

Paste token → “Authorize”.

Create Listing /listings

{
  "title": "Modern Apartment",
  "description": "Spacious 2-bedroom near the city center.",
  "price": 120000.0,
  "location": "Downtown",
  "image_url": "/uploads/<your_uploaded_filename>"
}


Search / Filter
/listings?q=apartment&min_price=100000&max_price=150000&page=1&limit=5

## ✅ 7. Next Week (Week 6 Preview)



Email verification / password reset (FastAPI Mail)

Agent–Buyer chat (WebSocket)

Favorites dashboard

Email notifications (when new listing added, etc.)

Background tasks with FastAPI.BackgroundTasks

Rate limiting / throttling middleware

Docker deployment & CI/CD (not yet)

NEXT — Week 6: Notifications, Chat & Background Tasks

Here’s your recommended Week 6 roadmap, building upon your solid Week 5 backend:

📨 1. Email Verification & Password Reset

Goal: Add transactional emails for signup verification and forgotten passwords.

Stack:

fastapi-mail or emails package

.env with MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER

Token-based verification (like JWT or URL-safe signed token)

Files:

core/email.py         # setup FastAPI-Mail
routers/auth.py       # extend with /verify-email and /reset-password routes
templates/verify.html # optional email template

💬 2. Real-Time Agent–Buyer Chat (WebSockets)

Goal: Let users chat directly about listings.

Stack:

FastAPI WebSocket

Optional table ChatMessage with fields:

id, sender_id, receiver_id, listing_id, content, timestamp


Endpoint /ws/chat/{listing_id}

Use JWT token to authenticate socket connections.

❤️ 3. Favorites Dashboard

Goal: Buyers can save favorite listings.

Already partly there! Just extend:

POST /favorites/{listing_id}

DELETE /favorites/{listing_id}

GET /favorites → returns buyer’s saved listings.

🔔 4. Notifications (Background Tasks)

Goal: Notify buyers when a new listing is added in their preferred location.

Stack:

BackgroundTasks from FastAPI

Async email sending after create_listing

Optional: Celery + Redis if scaling.

🐳 5. Docker + Deployment Prep

Goal: Prepare for production.

Files:

Dockerfile
docker-compose.yml
.env


Include:

FastAPI + Uvicorn

SQLite or PostgreSQL

Alembic migration commands on container start.

⚙️ 6. (Stretch) Rate Limiting / Throttling

Use slowapi or custom middleware to limit API abuse:

@limiter.limit("10/minute")

````
📂 Suggested Week 6 Folder Additions
app/
 ┣ core/
 ┃ ┣ email.py
 ┃ ┗ websocket_manager.py
 ┣ routers/
 ┃ ┣ chat.py
 ┃ ┣ favorites.py
 ┃ ┗ notifications.py
 ┣ utils/
 ┃ ┗ background_tasks.py
 ┣ templates/
 ┃ ┗ verify.html
 ┗ Dockerfile
````

| Area                            | Description                                                 | Files                                         |
| ------------------------------- | ----------------------------------------------------------- | --------------------------------------------- |
| **Database + ORM**              | SQLAlchemy models for `User`, `Listing`, `Favorite`         | `models.py`                                   |
| **Pydantic Schemas**            | Input/output validation                                     | `schemas.py`                                  |
| **JWT Auth System**             | Registration, login, secure routes                          | `auth.py`, `security.py`                      |
| **CRUD Listings**               | Agents can create/edit/delete; buyers can browse            | `routers/listings.py`                         |
| **Alembic Migrations**          | Versioned database migrations                               | `/alembic`                                    |
| **Seeder Script**               | Demo users + listings for testing                           | `seed_data.py`                                |
| **Search, Filters, Pagination** | `/listings?q=&location=&min_price=&max_price=&page=&limit=` | `routers/listings.py`                         |
| **Uploads**                     | Local file uploads for property images                      | `routers/uploads.py`, `utils/file_handler.py` |
| **User Profile Management**     | `/users/me`, `/users/update-profile`                        | `routers/users.py`                            |
| **CORS + Logging**              | Ready for frontend integration                              | `core/cors.py`, `core/logging.py`             |
| **Optional Admin APIs**         | `/admin/users`, `/admin/listings`                           | `routers/admin.py`                            |
---
## 🧩 Step 5 — Optional Enhancements


You can later extend Order to track buyer interest, payments, or delivery; and ChatMessage can tie to WebSocket-based live messaging in Week 6.

If you run alembic revision --autogenerate -m "Add orders and chat_messages" && alembic upgrade head,

| Feature                    | Endpoint              | Role  |
| -------------------------- | --------------------- | ----- |
| List all users             | `/admin/users`        | Admin |
| Delete user                | `/admin/users/{id}`   | Admin |
| Approve or delete listings | `/admin/listings/...` | Admin |
| View/manage orders         | `/admin/orders`       | Admin |
| Moderate chats             | `/admin/chats`        | Admin |

✅ Done! You can now log in with:
 - Admin: admin@example.com / admin123
 - Agent: alice.agent@example.com / password123
 - Buyer: bob.buyer@example.com / password123


generate a routers/orders.py next, so that buyers can place and view their orders (with proper role-based JWT protection)

✅ Test via /docs

Login as Buyer → copy your JWT access token.

Authorize in Swagger UI (Authorize → Bearer token).

Use:

POST /orders?listing_id=1 → place order.

GET /orders/my → view buyer’s own orders.

GET /orders/sales → if agent/admin → see orders for listings you own.

---
| Feature              | Route                              | Role        | Description                 |
| -------------------- | ---------------------------------- | ----------- | --------------------------- |
| 💳 Simulated Payment | `POST /orders/{order_id}/pay`      | Buyer       | Mock payment + generate ref |
| ✅ Complete Order     | `POST /orders/{order_id}/complete` | Agent/Admin | Marks as completed          |
| 📊 Sales Summary     | `GET /orders/sales/summary`        | Agent/Admin | Shows total revenue & sales |
| 💼 Revenue Dashboard | `GET /admin/revenue-summary`       | Admin       | Platform-wide stats         |

pip install fastapi-mail
pip install email-validator

include the frontend API integration endpoints list (for React/Vue/Next.js) next — e.g., how to call these new payment and completion routes from the buyer and agent dashboards

🔥 Next Enhancements (choose what’s next)

A) ✅ Buyer — Order View modal (show full listing + payment details)
B) ✅ Agent — Orders page /dashboard/agent/orders
C) ✅ Success screen after payment (with receipt)
D) ✅ Order Status Badge styles (warning, approved, completed)
E) ✅ Add timestamps with “x days ago”

python seed_data.py    