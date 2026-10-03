import json
import re

input_file = "datasets/extracted_paper.json"
output_file = "datasets/processed_paper.json"

with open(input_file, "r", encoding="utf-8") as f:
    paper = json.load(f)

processed_pages = []

for page in paper["pages"]:
    text = page["text"]

    # Bersihkan spasi berlebihan
    text = re.sub(r"\s+", " ", text).strip()

    # Pisahkan menjadi paragraf sederhana
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    processed_pages.append({
        "page": page["page"],
        "paragraphs": paragraphs
    })

result = {
    "paper_id": paper["paper_id"],
    "title": paper["title"],
    "pages": processed_pages
}

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("Preprocessing berhasil!")
print("Output:", output_file)