import pymupdf
import json
import sys
from pathlib import Path


OUTPUT_PATH = "datasets/extracted_paper.json"


# Ambil path PDF dari argument
if len(sys.argv) > 1:
    pdf_path = Path(sys.argv[1])
else:
    # Default: PDF lama untuk testing
    pdf_path = Path(
        r"C:\Users\DAVID\.cache\kagglehub\datasets\dipeshlohchab"
        r"\arxiv-research-papers\versions\1\data\pdfs\arxiv"
        r"\arxiv_adap-org_9712004.pdf"
    )


# Cek apakah file ada
if not pdf_path.exists():
    print("ERROR: PDF tidak ditemukan!")
    print("Path:", pdf_path)
    sys.exit(1)


# Buka PDF
doc = pymupdf.open(pdf_path)

pages = []

for page_number, page in enumerate(doc, start=1):

    text = page.get_text()

    pages.append({
        "page": page_number,
        "text": text
    })

doc.close()


# Ambil nama file sebagai ID
paper_id = pdf_path.stem

# Judul sementara berdasarkan nama file
title = paper_id.replace("_", " ")


output = {
    "paper_id": paper_id,
    "title": title,
    "source_file": str(pdf_path),
    "pages": pages
}


# Pastikan folder datasets ada
Path("datasets").mkdir(exist_ok=True)


# Simpan hasil extraction
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


print("====================================")
print("PAPERGUARD PDF EXTRACTION")
print("====================================")
print("File:", pdf_path)
print("Paper ID:", paper_id)
print("Jumlah halaman:", len(pages))
print("Output:", OUTPUT_PATH)
print("====================================")
print("Berhasil!")