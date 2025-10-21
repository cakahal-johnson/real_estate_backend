"""
Seed script to populate demo users and listings.
Run once after alembic upgrade head:
    python seed_data.py
"""

from app.database import SessionLocal, engine, Base
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create tables if not already created (safe guard)
Base.metadata.create_all(bind=engine)

db = SessionLocal()


# --- Helper to hash passwords ---
def hash_password(password: str):
    return pwd_context.hash(password)


# --- Clear existing data (for clean reseed) ---
def clear_data():
    db.query(models.Favorite).delete()
    db.query(models.Listing).delete()
    db.query(models.User).delete()
    db.commit()


# --- Seed users (agents + buyers) ---
def seed_users():
    users = [
        models.User(
            full_name="Alice Agent",
            email="alice.agent@example.com",
            password_hash=hash_password("password123"),
            role="agent",
        ),
        models.User(
            full_name="Bob Buyer",
            email="bob.buyer@example.com",
            password_hash=hash_password("password123"),
            role="buyer",
        ),
        models.User(
            full_name="Charlie Agent",
            email="charlie.agent@example.com",
            password_hash=hash_password("password123"),
            role="agent",
        ),
    ]
    db.add_all(users)
    db.commit()
    return users


# --- Seed listings (owned by agents) ---
def seed_listings(users):
    agents = [u for u in users if u.role == "agent"]

    listings = [
        models.Listing(
            title="Modern 3-Bed Apartment",
            description="Spacious 3-bedroom apartment in downtown area with great amenities.",
            price=350000.0,
            location="Lagos",
            image_url="https://via.placeholder.com/400x300.png?text=Apartment",
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Cozy 2-Bed Bungalow",
            description="Perfect for small families or couples, with a beautiful garden.",
            price=200000.0,
            location="Abuja",
            image_url="https://via.placeholder.com/400x300.png?text=Bungalow",
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Luxury Villa with Pool",
            description="Premium villa featuring 5 bedrooms, a pool, and ocean view.",
            price=850000.0,
            location="Lekki",
            image_url="https://via.placeholder.com/400x300.png?text=Villa",
            owner_id=agents[1].id,
        ),
    ]
    db.add_all(listings)
    db.commit()
    return listings


def main():
    print("🧹 Clearing existing data...")
    clear_data()

    print("👥 Seeding demo users...")
    users = seed_users()

    print("🏠 Seeding demo listings...")
    listings = seed_listings(users)

    print(f"✅ Done! Seeded {len(users)} users and {len(listings)} listings.")
    print("You can now log in using:")
    print(" - Agent: alice.agent@example.com / password123")
    print(" - Buyer: bob.buyer@example.com / password123")
    print(" - Agent 2: charlie.agent@example.com / password123")


if __name__ == "__main__":
    main()

# python seed_data.py
