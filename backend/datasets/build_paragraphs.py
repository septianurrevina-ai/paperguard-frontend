import json
import re

with open("datasets/parsed_paper.json", "r", encoding="utf-8") as f:
    paper = json.load(f)

result_pages = []

for page in paper["pages"]:
    paragraphs = []
    current_text = []
    current_bbox = None

    for block in page["blocks"]:
        text = block["text"].strip()

        # Buang metadata arXiv
        if "adap-org/" in text.lower():
            continue

        # Pecah berdasarkan baris
        lines = [x.strip() for x in text.split("\n") if x.strip()]

        for line in lines:

            # Heading
            is_heading = (
                line.lower() in ["abstract", "references", "acknowledgments"]
                or re.match(r"^\d+(\.\d+)*\.?\s+[A-Z]", line)
            )

            if is_heading:

                # Simpan paragraf sebelumnya
                if current_text:
                    paragraphs.append({
                        "type": "paragraph",
                        "text": " ".join(current_text),
                        "bbox": current_bbox
                    })
                    current_text = []
                    current_bbox = None

                # Simpan heading
                paragraphs.append({
                    "type": "heading",
                    "text": line,
                    "bbox": block["bbox"]
                })

            else:
                if current_bbox is None:
                    current_bbox = block["bbox"]

                current_text.append(line)

    # Simpan paragraf terakhir
    if current_text:
        paragraphs.append({
            "type": "paragraph",
            "text": " ".join(current_text),
            "bbox": current_bbox
        })

    result_pages.append({
        "page": page["page"],
        "paragraphs": paragraphs
    })

result = {
    "paper_id": paper["paper_id"],
    "title": paper["title"],
    "pages": result_pages
}

with open("datasets/paragraphs.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Paragraph building berhasil!")