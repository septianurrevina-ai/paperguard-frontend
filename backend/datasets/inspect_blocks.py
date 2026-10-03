import json

with open("datasets/parsed_paper.json", "r", encoding="utf-8") as f:
    paper = json.load(f)

page = paper["pages"][0]

for block in page["blocks"]:
    print(f"\nBLOCK {block['block']}")
    print("TEXT:", block["text"].replace("\n", " | "))
    print("BBOX:", block["bbox"])