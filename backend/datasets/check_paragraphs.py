import json

with open("datasets/paragraphs.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for i, paragraph in enumerate(data["pages"][0]["paragraphs"], start=1):
    print(f"\n===== PARAGRAPH {i} =====")
    print(paragraph["text"])