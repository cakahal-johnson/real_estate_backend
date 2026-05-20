"""
Seed script to populate demo users, listings, orders,
escrow, fraud alerts, support tickets, and audit logs
with images + videos for enterprise admin dashboard.
"""

from app.database import SessionLocal, engine, Base
from app import models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)

db = SessionLocal()


# =========================
# PASSWORD HASH
# =========================
def hash_password(password: str):
    return pwd_context.hash(password)


# =========================
# CLEAR DATABASE
# =========================
def clear_data():
    print("🧹 Clearing existing data...")

    # IMPORTANT: delete child tables first (avoid FK issues)

    db.query(models.Favorite).delete()
    db.query(models.CartItem).delete()
    db.query(models.ChatMessage).delete()
    db.query(models.ChatRoom).delete()
    db.query(models.DocumentSubmission).delete()
    db.query(models.SupportTicket).delete()
    db.query(models.AdminAuditLog).delete()
    db.query(models.FraudAlert).delete()
    db.query(models.EscrowAccount).delete()
    db.query(models.Dispute).delete()
    db.query(models.Order).delete()
    db.query(models.RecentView).delete()
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
# SAFE VIDEOS
# =========================
SAFE_VIDEOS = [
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://www.w3schools.com/html/movie.mp4",
    "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    "https://media.w3.org/2010/05/sintel/trailer.mp4",
]


# =========================
# LISTINGS (MODERATION READY)
# =========================
def seed_listings(users):
    print("🏠 Seeding listings...")

    agents = [u for u in users if u.role == "agent"]

    listings = [
        models.Listing(
            title="Modern 3-Bed Apartment in Lekki",
            description="Beautiful apartment with ocean view.",
            price=350000.0,
            location="Lekki, Lagos",
            review_status="approved",
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
            review_status="pending",
            main_image="https://images.unsplash.com/photo-1560185127-6ed189bf02f4?w=1200",
            images=[
                "https://images.unsplash.com/photo-1560184897-90aeb13f09ec?w=1200",
            ],
            videos=[SAFE_VIDEOS[1]],
            owner_id=agents[0].id,
        ),
        models.Listing(
            title="Luxury Duplex in Victoria Island",
            description="High-end luxury duplex.",
            price=780000.0,
            location="Victoria Island, Lagos",
            review_status="flagged",
            main_image="https://images.unsplash.com/photo-1600585154154-8abdb92f1d33?w=1200",
            images=[
                "https://images.unsplash.com/photo-1600585153931-6a319a9c3a61?w=1200",
            ],
            videos=[SAFE_VIDEOS[2]],
            owner_id=agents[0].id,
        ),
    ]

    db.add_all(listings)
    db.commit()
    return listings


# =========================
# ORDERS
# =========================
def seed_orders(users, listings):
    print("🧾 Seeding orders...")

    buyers = [u for u in users if u.role == "buyer"]

    orders = [
        models.Order(
            buyer_id=buyers[0].id,
            listing_id=listings[0].id,
            status="pending",
            amount=350000.0,
        ),
        models.Order(
            buyer_id=buyers[0].id,
            listing_id=listings[1].id,
            status="completed",
            amount=200000.0,
        ),
    ]

    db.add_all(orders)
    db.commit()
    return orders


# =========================
# ESCROW
# =========================
def seed_escrow(orders):
    print("💰 Seeding escrow accounts...")

    escrow_entries = [
        models.EscrowAccount(
            order_id=o.id,
            amount=o.amount,
            status="held",
        )
        for o in orders
    ]

    db.add_all(escrow_entries)
    db.commit()


# =========================
# FRAUD ALERTS
# =========================
def seed_fraud_alerts(users):
    print("🚨 Seeding fraud alerts...")

    alerts = [
        models.FraudAlert(
            user_id=users[2].id,
            type="suspicious",
            description="Suspicious login pattern detected",
            severity="high",
            is_resolved=0,
        ),
        models.FraudAlert(
            user_id=users[1].id,
            type="keyword_violation",
            description="Multiple listing edits detected",
            severity="medium",
            is_resolved=0,
        ),
    ]

    db.add_all(alerts)
    db.commit()


# =========================
# SUPPORT TICKETS
# =========================
def seed_support_tickets(users):
    print("🎫 Seeding support tickets...")

    tickets = [
        models.SupportTicket(
            user_id=users[2].id,
            message="Payment not reflecting",
            status="open",
        ),
        models.SupportTicket(
            user_id=users[1].id,
            message="Listing approval delay",
            status="open",
        ),
    ]

    db.add_all(tickets)
    db.commit()


# =========================
# AUDIT LOGS (LIVE FEED)
# =========================
def seed_audit_logs(users):
    print("📜 Seeding audit logs...")

    logs = [
        models.AdminAuditLog(
            admin_id=users[0].id,
            action="approve_listing",
            target_type="listing",
            target_id=1,
            description="Approved demo listing",
        ),
        models.AdminAuditLog(
            admin_id=users[0].id,
            action="release_escrow",
            target_type="order",
            target_id=1,
            description="Escrow released successfully",
        ),
    ]

    db.add_all(logs)
    db.commit()


# =========================
# MAIN
# =========================
def main():
    clear_data()

    users = seed_users()
    listings = seed_listings(users)
    orders = seed_orders(users, listings)

    seed_escrow(orders)
    seed_fraud_alerts(users)
    seed_support_tickets(users)
    seed_audit_logs(users)

    print("\n✅ DONE: Enterprise demo data created successfully!")

    print("\n🔑 LOGIN CREDENTIALS")
    print("Admin: admin@example.com / admin123")
    print("Agent: alice.agent@example.com / password123")
    print("Buyer: bob.buyer@example.com / password123")


if __name__ == "__main__":
    main()