import pymupdf
import json


INPUT_PATH = "datasets/extracted_paper.json"
OUTPUT_PATH = "datasets/parsed_paper.json"


# Baca metadata hasil extraction
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    paper = json.load(f)


pdf_path = paper["source_file"]

print("Membuka PDF:")
print(pdf_path)


doc = pymupdf.open(pdf_path)

pages = []


for page_number, page in enumerate(doc, start=1):

    blocks = page.get_text("blocks")

    page_blocks = []

    for block_number, block in enumerate(
        blocks,
        start=1
    ):

        x0, y0, x1, y1, text, *_ = block

        text = text.strip()

        if not text:
            continue

        page_blocks.append({
            "block": block_number,
            "text": text,
            "bbox": {
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1
            }
        })

    pages.append({
        "page": page_number,
        "blocks": page_blocks
    })


doc.close()


result = {
    "paper_id": paper["paper_id"],
    "title": paper["title"],
    "source_file": pdf_path,
    "pages": pages
}


with open(OUTPUT_PATH, "w", encoding="utf-8") as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("====================================")
print("PAPERGUARD PDF PARSING")
print("====================================")
print("Paper:", paper["title"])
print("Jumlah halaman:", len(pages))

total_blocks = sum(
    len(page["blocks"])
    for page in pages
)

print("Total text blocks:", total_blocks)
print("Output:", OUTPUT_PATH)
print("====================================")
print("PDF parsing berhasil!")