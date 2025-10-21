"""Seed script to populate demo users, listings, and orders."""
from app.database import SessionLocal, engine, Base
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base.metadata.create_all(bind=engine)
db = SessionLocal()


def hash_password(password: str):
    return pwd_context.hash(password)


def clear_data():
    db.query(models.Favorite).delete()
    db.query(models.Order).delete()
    db.query(models.Listing).delete()
    db.query(models.User).delete()
    db.commit()


def seed_users():
    users = [
        models.User(
            full_name="Admin User",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",   # 🔹 new
        ),
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
    ]
    db.add_all(users)
    db.commit()
    return users


def seed_listings(users):
    agents = [u for u in users if u.role == "agent"]

    listings = [
        models.Listing(
            title="Modern 3-Bed Apartment",
            description="Spacious 3-bedroom apartment downtown.",
            price=350000.0,
            location="Lagos",
            image_url="https://via.placeholder.com/400x300.png?text=Apartment",
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Cozy 2-Bed Bungalow",
            description="Perfect for small families or couples.",
            price=200000.0,
            location="Abuja",
            image_url="https://via.placeholder.com/400x300.png?text=Bungalow",
            owner_id=agents[0].id,
        ),
    ]
    db.add_all(listings)
    db.commit()
    return listings


def seed_orders(users, listings):
    buyers = [u for u in users if u.role == "buyer"]
    if buyers and listings:
        orders = [
            models.Order(
                buyer_id=buyers[0].id,
                listing_id=listings[0].id,
                status="pending",
            ),
            models.Order(
                buyer_id=buyers[0].id,
                listing_id=listings[1].id,
                status="approved",
            ),
        ]
        db.add_all(orders)
        db.commit()
        print(f"📦 Created {len(orders)} demo orders.")


def main():
    print("🧹 Clearing existing data...")
    clear_data()

    print("👥 Seeding users...")
    users = seed_users()

    print("🏠 Seeding listings...")
    listings = seed_listings(users)

    print("🧾 Seeding orders...")
    seed_orders(users, listings)

    print("✅ Done! You can now log in with:")
    print(" - Admin: admin@example.com / admin123")
    print(" - Agent: alice.agent@example.com / password123")
    print(" - Buyer: bob.buyer@example.com / password123")


if __name__ == "__main__":
    main()
