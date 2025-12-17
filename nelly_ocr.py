import pytesseract
import fitz  # PyMuPDF
from pathlib import Path
from PIL import Image
import io

# --- CONFIGURATION ---
# Windows (si nécessaire) :
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def pdf_to_html_ocr(pdf_path, html_path, dpi=300, lang="eng+fra"):
    pdf_path = Path(pdf_path)
    html_path = Path(html_path)

    print("Ouverture du PDF...")
    doc = fitz.open(str(pdf_path))

    html_parts = [
        "<html><body style='font-family: sans-serif; line-height: 1.6; padding: 20px;'>"
    ]

    # Conversion DPI -> matrice de zoom (PyMuPDF travaille en 72 DPI par défaut)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    total = doc.page_count
    for i in range(total):
        print(f"Traitement de la page {i+1}/{total}...")

        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Pixmap -> PIL Image (sans fichiers temporaires)
        img_bytes = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_bytes))

        text = pytesseract.image_to_string(image, lang=lang)

        clean_text = (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
        )

        html_parts.append(
            "<div style='margin-bottom: 40px; border-bottom: 1px solid #ccc;'>"
            f"<h2 style='color: #2c3e50;'>Page {i+1}</h2>"
            f"<p>{clean_text}</p>"
            "</div>"
        )

    html_parts.append("</body></html>")

    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text("\n".join(html_parts), encoding="utf-8")
    print(f"Terminé ! Fichier enregistré sous : {html_path}")

if __name__ == "__main__":
    pdf_file = "source/nelly1.pdf"
    html_file = "data/nelly_ocr.html"
    pdf_to_html_ocr(pdf_file, html_file, dpi=300, lang="eng+fra")
