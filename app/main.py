# app/main.py
from fastapi import FastAPI
from app.database import Base, engine
from app.routers import listings
from fastapi.middleware.cors import CORSMiddleware

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="RealEstateHub API")

# Allow frontend & mobile access (update origins later)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(listings.router)


@app.get("/")
def root():
    return {"message": "Welcome to RealEstateHub API"}
