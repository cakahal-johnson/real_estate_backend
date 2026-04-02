"""Seed script to populate demo users, listings, and orders with updated image fields."""
from app.database import SessionLocal, engine, Base
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base.metadata.create_all(bind=engine)
db = SessionLocal()


def hash_password(password: str):
    return pwd_context.hash(password)


def clear_data():
    print("🧹 Clearing existing data...")
    db.query(models.Favorite).delete()
    db.query(models.Order).delete()
    db.query(models.Listing).delete()
    db.query(models.User).delete()
    db.commit()


def seed_users():
    print("👥 Seeding users...")
    users = [
        models.User(
            full_name="Admin User",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            role="admin",
            phone="+2348000000001",
            photo="https://randomuser.me/api/portraits/men/75.jpg",
        ),
        models.User(
            full_name="Alice Agent",
            email="alice.agent@example.com",
            password_hash=hash_password("password123"),
            role="agent",
            phone="+2348101234567",
            photo="https://randomuser.me/api/portraits/women/65.jpg",
        ),
        models.User(
            full_name="Bob Buyer",
            email="bob.buyer@example.com",
            password_hash=hash_password("password123"),
            role="buyer",
            phone="+2348129876543",
            photo="https://randomuser.me/api/portraits/men/60.jpg",
        ),
    ]
    db.add_all(users)
    db.commit()
    return users


def seed_listings(users):
    print("🏠 Seeding listings...")
    agents = [u for u in users if u.role == "agent"]

    if not agents:
        print("⚠️ No agents found — skipping listings.")
        return []

    listings = [
        models.Listing(
            title="Modern 3-Bed Apartment in Lekki",
            description="Beautiful 3-bedroom apartment with ocean view, modern kitchen, and smart home system.",
            price=350000.0,
            location="Lekki, Lagos",
            main_image="https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800",
            images=[
                "https://images.unsplash.com/photo-1600607687690-9fdedddca8c1?w=800",
                "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800",
                "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800"
            ],
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Cozy 2-Bed Bungalow in Abuja",
            description="Perfect family-friendly bungalow located in a serene neighborhood.",
            price=200000.0,
            location="Gwarinpa, Abuja",
            main_image="https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=800",
            images=[
                "https://images.unsplash.com/photo-1560184897-90aeb13f09ec?w=800",
                "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=800",
                "https://images.unsplash.com/photo-1560185008-b033106af9e2?w=800"
            ],
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Luxury Duplex in Victoria Island",
            description="High-end duplex with 4 bedrooms, private pool, and security surveillance.",
            price=780000.0,
            location="Victoria Island, Lagos",
            main_image="https://plus.unsplash.com/premium_photo-1755612015739-942bd6de858c?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&q=80&w=687?w800",
            images=[
                "https://images.unsplash.com/photo-1600585154154-8abdb92f1d33?w=800",
                "https://images.unsplash.com/photo-1600585153931-6a319a9c3a61?w=800",
                "https://images.unsplash.com/photo-1600585153901-028b9b63f759?w=800"
            ],
            owner_id=agents[0].id,
        ),
    ]
    db.add_all(listings)
    db.commit()
    print(f"🏘️ Created {len(listings)} listings.")
    return listings


def seed_orders(users, listings):
    print("🧾 Seeding orders...")
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
    clear_data()
    users = seed_users()
    listings = seed_listings(users)
    seed_orders(users, listings)
    print("✅ Done! Demo data is ready.")
    print("🔑 Logins:")
    print(" - Admin: admin@example.com / admin123")
    print(" - Agent: alice.agent@example.com / password123")
    print(" - Buyer: bob.buyer@example.com / password123")


if __name__ == "__main__":
    main()
