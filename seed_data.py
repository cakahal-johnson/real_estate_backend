"""Seed script to populate demo users, listings, and orders with images + videos."""

from app.database import SessionLocal, engine, Base
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)

db = SessionLocal()


# =========================
# PASSWORD
# =========================
def hash_password(password: str):
    return pwd_context.hash(password)


# =========================
# CLEAR DB
# =========================
def clear_data():
    print("🧹 Clearing existing data...")

    db.query(models.Favorite).delete()
    db.query(models.Order).delete()
    db.query(models.Listing).delete()
    db.query(models.User).delete()

    db.commit()


# =========================
# USERS
# =========================
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


# =========================
# SAFE VIDEO LIST
# =========================
SAFE_VIDEOS = [
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://www.w3schools.com/html/movie.mp4",
    "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    "https://media.w3.org/2010/05/sintel/trailer.mp4",
]


# =========================
# LISTINGS
# =========================
def seed_listings(users):
    print("🏠 Seeding listings...")

    agents = [u for u in users if u.role == "agent"]

    if not agents:
        print("⚠️ No agents found.")
        return []

    listings = [
        models.Listing(
            title="Modern 3-Bed Apartment in Lekki",
            description="Beautiful apartment with ocean view.",
            price=350000.0,
            location="Lekki, Lagos",

            main_image="https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=1200",

            images=[
                "https://images.unsplash.com/photo-1600607687690-9fdedddca8c1?w=1200",
                "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=1200",
            ],

            videos=[SAFE_VIDEOS[0]],

            owner_id=agents[0].id,
        ),

        models.Listing(
            title="Cozy 2-Bed Bungalow in Abuja",
            description="Family-friendly bungalow.",
            price=200000.0,
            location="Gwarinpa, Abuja",

            main_image="https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=1200",

            images=[
                "https://images.unsplash.com/photo-1560184897-90aeb13f09ec?w=1200",
                "https://images.unsplash.com/photo-1570129477492-45c003edd2be?w=1200",
            ],

            videos=[SAFE_VIDEOS[1]],

            owner_id=agents[0].id,
        ),

        models.Listing(
            title="Luxury Duplex in Victoria Island",
            description="High-end luxury duplex.",
            price=780000.0,
            location="Victoria Island, Lagos",

            main_image="https://images.unsplash.com/photo-1600585154154-8abdb92f1d33?w=1200",

            images=[
                "https://images.unsplash.com/photo-1600585153931-6a319a9c3a61?w=1200",
                "https://images.unsplash.com/photo-1600585153901-028b9b63f759?w=1200",
            ],

            videos=[SAFE_VIDEOS[2]],

            owner_id=agents[0].id,
        ),

        models.Listing(
            title="Smart Studio Apartment in Yaba",
            description="Modern smart apartment.",
            price=150000.0,
            location="Yaba, Lagos",

            main_image="https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=1200",

            images=[
                "https://images.unsplash.com/photo-1494526585095-c41746248156?w=1200",
            ],

            videos=[SAFE_VIDEOS[3]],

            owner_id=agents[0].id,
        ),
    ]

    db.add_all(listings)
    db.commit()

    print(f"🏘️ Created {len(listings)} listings.")
    return listings


# =========================
# ORDERS
# =========================
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


# =========================
# MAIN
# =========================
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