"""Generate the demo sample PDFs (all data is fake).

Run from the repo root:
    python demo/samples/make_samples.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent


def write(path, pages):
    c = canvas.Canvas(str(path), pagesize=A4)
    w, h = A4
    for title, lines in pages:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2 * cm, h - 2.5 * cm, title)
        c.setFont("Helvetica", 11)
        y = h - 3.6 * cm
        for line in lines:
            c.drawString(2 * cm, y, line)
            y -= 0.62 * cm
        c.showPage()
    c.save()


write(OUT / "bank_statement.pdf", [
    ("Horizon Bank - Account Statement (October 2026)", [
        "Account holder: Priya Sharma",
        "Registered email: priya.sharma@example.com",
        "Registered mobile: +91 98765 43210",
        "PAN on file: ABCDE1234F",
        "",
        "Card used for online payments: 4532 0151 1283 0366",
        "Statement period: 01 Oct 2026 to 31 Oct 2026",
        "Opening balance: Rs 1,24,500.00",
        "",
        "02 Oct  Amazon order #4021-7781        Rs 2,499.00 debit",
        "05 Oct  Salary credit, Acme Corp       Rs 85,000.00 credit",
        "11 Oct  UPI to Rahul Verma             Rs 1,200.00 debit",
        "19 Oct  Electricity bill               Rs 3,140.00 debit",
        "",
        "Closing balance: Rs 2,02,661.00",
    ]),
    ("Security notice", [
        "On 21 Oct 2026 a login was attempted from IP 203.0.113.42.",
        "Your one-time password for that login was 482913. Never share it.",
        "If this wasn't you, reset your password at https://horizonbank.example.com/secure/reset",
        "or call our helpline. Relationship manager: Ananya Iyer (ananya.iyer@horizonbank.example.com).",
        "",
        "Interest rate on savings: 3.5% per annum, credited quarterly.",
        "Minimum average balance: Rs 10,000.",
    ]),
])

write(OUT / "kyc_form.pdf", [
    ("KYC Update Form - Customer Copy", [
        "Full name: Arjun Mehta",
        "Date of birth: 14/03/1994",
        "PAN: FGHIJ5678K",
        "Mobile: 9123456789",
        "Alternate contact: +44 20 7946 0958",
        "Email: arjun.mehta@mail.co.in",
        "",
        "Address: 12 Lake View Road, Pune 411001",
        "Occupation: Software engineer",
        "Annual income bracket: 10-25 lakh",
        "",
        "Nominee: Kavya Nair (sister)",
        "Declaration: I confirm the details above are correct.",
        "Submitted from device IP 198.51.100.7 via https://kyc.example.org/form/8841",
    ]),
])
print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
