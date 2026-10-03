import json
import re

with open("datasets/parsed_paper.json", "r", encoding="utf-8") as f:
    paper = json.load(f)

cleaned_pages = []

for page in paper["pages"]:

    cleaned_blocks = []

    for block in page["blocks"]:
        text = block["text"].strip()

        # Buang metadata arXiv di sisi kiri halaman
        if "arxiv" in text.lower() or "adap-org/" in text.lower():
            continue

        # Pecah berdasarkan baris
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:

            # Deteksi heading seperti:
            # 1. Introduction
            # 2. Method
            # 3. Results
            if re.match(r"^\d+(\.\d+)*\.?\s+[A-Z]", line):
                block_type = "heading"

            elif line.lower() in ["abstract", "references", "acknowledgments"]:
                block_type = "heading"

            else:
                block_type = "text"

            cleaned_blocks.append({
                "type": block_type,
                "text": line,
                "bbox": block["bbox"]
            })

    cleaned_pages.append({
        "page": page["page"],
        "blocks": cleaned_blocks
    })

result = {
    "paper_id": paper["paper_id"],
    "title": paper["title"],
    "pages": cleaned_pages
}

with open("datasets/cleaned_paper.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Cleaning berhasil!")

for page in cleaned_pages[:1]:
    for block in page["blocks"]:
        print(f"[{block['type']}] {block['text'][:100]}")