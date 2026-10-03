import json

with open("datasets/processed_paper.json", "r", encoding="utf-8") as f:
    paper = json.load(f)

for page in paper["pages"][:2]:
    print(f"\n===== PAGE {page['page']} =====")

    for i, paragraph in enumerate(page["paragraphs"], start=1):
        print(f"\nParagraph {i}:")
        print(paragraph[:500])