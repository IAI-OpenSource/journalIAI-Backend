from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import cm
from io import BytesIO
from app.globals.messages import Messages as msg

from app.schemas.registration_schemas import ReadRegistration

class PDFExportUtils:
    @classmethod
    def generate_jetons_pdf(cls, students_data: list[ReadRegistration], classe_nom: str) -> BytesIO:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        logo_path_iai = "app/static/logo_iai.jpeg"
        logo_path_comite = "app/static/logo_comite.jpg"
        
        try:
            c.drawImage(logo_path_iai, 2*cm, height - 5.9*cm, width=2.5*cm, preserveAspectRatio=True, mask='auto')
            c.drawImage(logo_path_comite, 16.6*cm, height - 7.9*cm, width=3*cm, preserveAspectRatio=True, mask='auto')
        except OSError:
            raise OSError("Image introuvable")
        
        # --- En-tête ---
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, height - 2*cm, "LISTE DES JETONS D'INSCRIPTION")

        c.setFont("Helvetica", 11) 
        c.drawCentredString(width/2, height - 2.8*cm, f"Contact : {msg.COMITE_ETUDIANT_EMAIL}")

        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width/2, height - 3.4*cm, f"Classe : {classe_nom}")

        # --- Tableau (En-tête) ---
        y = height - 4.8*cm
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2*cm, y, "NOM")
        c.drawString(7*cm, y, "PRÉNOM")
        c.drawString(11*cm, y, "CODE JETON")
        c.drawString(16.8*cm, y, "SIGNATURE")
        
        c.line(2*cm, y - 0.2*cm, width - 2*cm, y - 0.2*cm)
        y -= 0.8*cm

        # --- Données ---
        c.setFont("Helvetica", 10)
        for student in students_data:
            if y < 2*cm: # Gestion du saut de page
                c.showPage()
                y = height - 2*cm
                c.setFont("Helvetica", 10)

            c.drawString(2*cm, y, student.last_name.upper())
            c.drawString(7*cm, y, student.first_name.title())
            
            # Mise en évidence du jeton
            c.setFont("Courier-Bold", 11)
            c.drawString(11*cm, y, f"{student.jeton[:7]}*****")
            c.setFont("Helvetica", 10)
            
            y -= 0.6*cm
            c.setStrokeColor(colors.lightgrey)
            c.line(2*cm, y + 0.2*cm, width - 2*cm, y + 0.2*cm)
            y -= 0.2*cm

        c.save()
        buffer.seek(0)
        return buffer