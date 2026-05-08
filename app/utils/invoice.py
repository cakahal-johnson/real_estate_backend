# app/utils/invoice.py
import io
import qrcode
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


LOGO_PATH = "app/static/logo.png"  # put your logo here


def generate_invoice_pdf(order):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    listing = order.listing

    # =========================
    # 🏢 LOGO
    # =========================
    try:
        pdf.drawImage(LOGO_PATH, 40, height - 80, width=80, height=50, mask='auto')
    except:
        pass  # ignore if logo missing

    # =========================
    # 🏷️ BRAND HEADER
    # =========================
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(140, height - 50, "REAL ESTATE HUB INVOICE")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(140, height - 70, "Professional Property Transaction Receipt")

    # =========================
    # 📄 INVOICE META
    # =========================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 120, f"Invoice #: INV-{order.id}-{order.created_at.year}")
    pdf.drawString(40, height - 140, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")

    pdf.drawString(40, height - 160, f"Status: PAID" if order.payment_status == "paid" else "PENDING")

    # =========================
    # 🏡 PROPERTY INFO
    # =========================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 200, "Property Details")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, height - 220, f"Title: {listing.title if listing else 'N/A'}")
    pdf.drawString(40, height - 240, f"Location: {listing.location if listing else 'N/A'}")

    # =========================
    # 💰 PAYMENT INFO
    # =========================
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, height - 280, "Payment Summary")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, height - 300, f"Amount Paid: ₦{order.amount:,.2f}")
    pdf.drawString(40, height - 320, f"Payment Method: {order.payment_method or 'Paystack'}")
    pdf.drawString(40, height - 340, f"Reference: {order.payment_reference or 'N/A'}")

    # =========================
    # 🔳 QR CODE (verification link)
    # =========================
    qr_data = f"https://yourfrontend.com/orders/{order.id}"

    qr = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr.save(qr_buffer)
    qr_buffer.seek(0)

    qr_img = ImageReader(qr_buffer)
    pdf.drawImage(qr_img, 420, height - 220, width=120, height=120)

    pdf.setFont("Helvetica", 8)
    pdf.drawString(420, height - 240, "Scan to verify invoice")

    # =========================
    # 🧾 FOOTER
    # =========================
    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(40, 60, "Thank you for your trust in Real Estate Hub.")

    pdf.setFont("Helvetica", 8)
    pdf.drawString(40, 45, "This is a system-generated invoice and does not require a signature.")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return buffer