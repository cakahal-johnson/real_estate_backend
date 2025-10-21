# app/main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.routers import listings, users, auth, favorites
from fastapi.middleware.cors import CORSMiddleware
from app.core.cors import setup_cors


# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RealEstateHub API")


setup_cors(app)

# origins = ["*"]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# Include Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(listings.router)
app.include_router(favorites.router)


@app.get("/")
def root():
    return {"message": "Welcome to RealEstateHub API"}
