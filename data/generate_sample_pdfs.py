"""
Generates demo PDFs so the project works end-to-end without requiring you
to source real documents first. Drop your own PDFs into data/pdfs/ at any
time instead — the ingestion pipeline doesn't care where they came from.
"""
from pathlib import Path
from fpdf import FPDF

OUT_DIR = Path("data/pdfs")

DOCS = {
    "general_info.pdf": [
        ("About Our Parking Service",
         "SmartPark offers advance parking reservations across three partner "
         "locations in the city: Downtown Garage, Airport Parking, and Mall "
         "Parking. A reservation guarantees you a spot upon arrival, which "
         "removes the stress of searching for parking during peak hours. "
         "The service is aimed at commuters, travelers, and shoppers who "
         "want certainty about where they will park before they leave home."),
        ("How Payment Works",
         "Payment for a reservation is collected on-site at the time of "
         "arrival, not at the time of booking. We accept credit cards, "
         "debit cards, and major mobile payment wallets at every location. "
         "No cash payments are accepted at Airport Parking due to contactless "
         "entry requirements, but Downtown Garage and Mall Parking still "
         "accept cash at the staffed booth during business hours."),
        ("Entering and Exiting the Lot",
         "Upon arrival, drivers present their car's license plate number at "
         "the entrance gate or self-service kiosk. The system automatically "
         "recognizes the active reservation tied to that plate and opens the "
         "barrier without requiring a printed ticket. The same automatic "
         "recognition applies on exit, so there is no need to stop and pay "
         "again if the reservation already covers the parked duration."),
    ],
    "locations_and_hours.pdf": [
        ("Downtown Garage",
         "Downtown Garage sits at 123 Main St, two blocks from the central "
         "train station, making it convenient for commuters arriving by "
         "rail. The garage is open from 06:00 to 23:00 every day, including "
         "weekends and public holidays. Its central location means it fills "
         "up quickly on weekday mornings, so early reservations are "
         "recommended for anyone working downtown."),
        ("Airport Parking",
         "Airport Parking is located on Airport Rd, directly across from the "
         "Terminal 2 departures hall, within easy walking distance for "
         "travelers with light luggage. Unlike the other locations, Airport "
         "Parking operates 24 hours a day, every day of the year, since "
         "flights arrive and depart around the clock. A free shuttle runs "
         "every fifteen minutes between the lot and the terminal for "
         "travelers with heavier luggage."),
        ("Mall Parking",
         "Mall Parking is situated at 456 Market Ave, next to the north "
         "entrance of the shopping mall, close to the main food court. It "
         "is open from 08:00 to 22:00 daily, matching the mall's own opening "
         "hours. Because the lot closes overnight, any vehicle still parked "
         "after 22:00 will be flagged for staff follow-up the next morning."),
    ],
    "pricing_and_policies.pdf": [
        ("Hourly Rates",
         "Pricing differs by location to reflect demand and convenience. "
         "Downtown Garage charges $3.50 per hour, Airport Parking charges "
         "$5.00 per hour due to its 24/7 operation and shuttle service, and "
         "Mall Parking charges the lowest rate at $2.00 per hour. Discounted "
         "daily and weekly rates are available on request for long-stay "
         "customers, particularly frequent travelers at Airport Parking."),
        ("Cancellation Policy",
         "Reservations can be cancelled free of charge up to two hours "
         "before the scheduled start time, with the full amount refunded "
         "automatically. Cancellations made within the two-hour window "
         "before the start time may incur a one-hour cancellation fee, "
         "since the slot can no longer be reliably resold to another "
         "driver on short notice."),
        ("Getting Help",
         "If something goes wrong with a reservation -- for example, a "
         "slot that was supposed to be available is occupied -- drivers can "
         "contact on-site staff directly at the location, or use the chatbot "
         "to escalate the issue to an administrator. Escalated issues are "
         "typically resolved within fifteen minutes during staffed hours."),
    ],
}


def _write_pdf(filename, sections):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for heading, body in sections:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 10, heading)
        pdf.ln(4)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, body)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_DIR / filename))
    print(f"[generate_sample_pdfs] wrote {OUT_DIR / filename}")


if __name__ == "__main__":
    for filename, sections in DOCS.items():
        _write_pdf(filename, sections)