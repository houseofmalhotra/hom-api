from fpdf import FPDF
from datetime import datetime
import os

class PanamaLetterhead(FPDF):
    def header(self):
        # --- Corporate Colors ---
        BLUE = (39, 103, 177)
        ORANGE = (244, 115, 33)
        BLACK = (0, 0, 0)
        WHITE = (255, 255, 255)

        # --- 1. Draw Outer Blue Frame ---
        self.set_fill_color(*BLUE)
        self.rect(5, 5, 200, 287, 'F')

        # --- 2. Draw Inner White Canvas ---
        self.set_fill_color(*WHITE)
        self.rect(12, 12, 186, 273, 'F')

        # --- 3. Draw Stylized Inner Border ---
        self.set_draw_color(*BLACK)
        self.set_line_width(1.5)
        self.rect(18, 18, 174, 261, 'D')

        # Add black corner notches to mimic the step-design
        self.set_fill_color(*BLACK)
        self.rect(17, 17, 6, 6, 'F')
        self.rect(187, 17, 6, 6, 'F')
        self.rect(17, 273, 6, 6, 'F')
        self.rect(187, 273, 6, 6, 'F')

        # Add Orange Segment Accents
        self.set_fill_color(*ORANGE)
        # Top & Bottom blocks
        self.rect(45, 17, 18, 3, 'F')
        self.rect(147, 17, 18, 3, 'F')
        self.rect(45, 277, 18, 3, 'F')
        self.rect(147, 277, 18, 3, 'F')
        # Left & Right blocks
        self.rect(17, 80, 3, 18, 'F')
        self.rect(17, 160, 3, 18, 'F')
        self.rect(17, 230, 3, 18, 'F')
        self.rect(190, 80, 3, 18, 'F')
        self.rect(190, 160, 3, 18, 'F')
        self.rect(190, 230, 3, 18, 'F')

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        logo_path = os.path.join(BASE_DIR, "assets", "logo.png")

        self.image(logo_path, x=35, y=22, w=140)

        # ✅ FIX 1: Pushed the Y-coordinate down from 55 to 75 to clear the logo image
        self.set_y(75)

        # Separator Line
        self.set_line_width(0.3)
        self.set_draw_color(*BLACK)
        self.line(40, self.get_y(), 170, self.get_y())

        self.ln(2)
        self.set_font("helvetica", "B", 8)
        self.set_text_color(*BLACK)
        self.cell(0, 5, "-  House of Malhotra  -", align="C", new_x="LMARGIN", new_y="NEXT")

        # Reset colors for document body
        self.set_text_color(0, 0, 0)

    def footer(self):
        # --- 5. Draw Footer Address ---
        self.set_y(-25)
        self.set_font("helvetica", "B", 8)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, "-  17 Horniman Circle, Kala Ghoda, Fort, Mumbai- 400001.  -", align="C")


def generate_invoice_pdf(invoice_number: str, order_items: list, total_amount: float) -> bytes:
    """Generates a premium PDF invoice using the customized PANAMA letterhead template."""
    pdf = PanamaLetterhead()
    pdf.add_page()

    # ✅ FIX 2: Pushed the top margin down to 95 so the invoice content doesn't overlap the header
    # Left: 25, Top: 95, Right: 25
    pdf.set_margins(25, 95, 25)
    pdf.set_y(95)

    LIGHT_GRAY = (240, 240, 240)
    DARK_GRAY = (80, 80, 80)
    BLACK = (0, 0, 0)
    BLUE = (39, 103, 177)

    # --- INVOICE TITLE ---
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "INVOICE", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- METADATA & BILL TO SECTION ---
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(90, 6, "Billed To:", new_x="RIGHT")
    pdf.cell(70, 6, "Invoice Details:", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(*DARK_GRAY)

    pdf.cell(90, 5, "Supply Chain Partner / Distributor", new_x="RIGHT")
    pdf.cell(70, 5, f"Invoice No: {invoice_number}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.cell(90, 5, "Approved Network Entity", new_x="RIGHT")
    pdf.cell(70, 5, f"Date Issued: {datetime.now().strftime('%d %b %Y')}", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)

    # --- INVOICE TABLE ---
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(*BLUE)
    pdf.set_text_color(255, 255, 255)

    # Usable width is 160 (210 - 25 - 25). Dividing columns appropriately.
    pdf.cell(75, 10, "  Item Description", border=0, align="L", fill=True)
    pdf.cell(20, 10, "Qty", border=0, align="C", fill=True)
    pdf.cell(30, 10, "Unit Price", border=0, align="R", fill=True)
    pdf.cell(35, 10, "Line Total  ", border=0, align="R", new_x="LMARGIN", new_y="NEXT", fill=True)

    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(*BLACK)

    fill = False
    pdf.set_fill_color(*LIGHT_GRAY)

    for item in order_items:
        qty_str = str(item['quantity'])
        price_str = f"INR {item['price']:,.2f}"
        total_str = f"INR {(item['quantity'] * item['price']):,.2f}"

        pdf.cell(75, 10, f"  {item['name']}", border=0, align="L", fill=fill)
        pdf.cell(20, 10, qty_str, border=0, align="C", fill=fill)
        pdf.cell(30, 10, price_str, border=0, align="R", fill=fill)
        pdf.cell(35, 10, f"{total_str}  ", border=0, align="R", new_x="LMARGIN", new_y="NEXT", fill=fill)
        fill = not fill

    pdf.ln(5)

    # --- TOTALS ---
    pdf.set_draw_color(*BLUE)
    pdf.line(pdf.get_x() + 95, pdf.get_y(), pdf.get_x() + 160, pdf.get_y())
    pdf.ln(2)

    pdf.set_font("helvetica", "B", 12)
    pdf.cell(125, 10, "Grand Total:", align="R", new_x="RIGHT")
    pdf.cell(35, 10, f"INR {total_amount:,.2f}  ", align="R", new_x="LMARGIN", new_y="NEXT")

    # --- DISCLAIMER ---
    pdf.set_y(-40)
    pdf.set_text_color(*DARK_GRAY)
    pdf.set_font("helvetica", "I", 9)
    pdf.cell(0, 5, "This is a computer-generated document. No signature is required.", align="C", new_x="LMARGIN",
             new_y="NEXT")

    return bytes(pdf.output())