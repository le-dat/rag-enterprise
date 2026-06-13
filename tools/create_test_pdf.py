import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_pdf(filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Company X Executive Profile")
    
    c.setFont("Helvetica", 12)
    text = [
        "",
        "This is an executive summary profile of Company X.",
        "Nguyen Van A is a technology entrepreneur. He is the founder of Company X.",
        "Company X was founded in 2020 and specializes in artificial intelligence systems.",
        "Nguyen Van A currently acts as the CEO and majority shareholder of Company X.",
        "The company is headquartered in Hanoi, Vietnam.",
        "Security Group Restriction: This document is classified as finance and management only."
    ]
    
    y = height - 80
    for line in text:
        c.drawString(50, y, line)
        y -= 25
        
    c.save()
    print(f"✅ Đã tạo thành công file PDF mẫu tại: {filename}")

if __name__ == "__main__":
    create_pdf("data/company_x.pdf")
