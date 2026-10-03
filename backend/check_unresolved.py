import json


with open(
    "datasets/structured_paper.json",
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)


targets = [
    "offboth",
    "occuring"
]


for page in data["pages"]:

    for paragraph in page["paragraphs"]:

        text = paragraph.get(
            "text",
            ""
        )

        text_lower = text.lower()

        if any(
            target in text_lower
            for target in targets
        ):

            print("=" * 80)
            print(
                "PAGE:",
                page["page"]
            )
            print(
                "SECTION:",
                paragraph.get(
                    "section",
                    "UNKNOWN"
                )
            )
            print()
            print("TEXT:")
            print(text)
            print()