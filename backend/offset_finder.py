import json


# =========================
# LOAD PAPER
# =========================

with open("datasets/paragraphs.json", "r", encoding="utf-8") as f:
    paper = json.load(f)


# =========================
# LOAD AI REVIEW
# =========================

with open("datasets/review_result.json", "r", encoding="utf-8") as f:
    review = json.load(f)


# =========================
# FIND EACH PROBLEM
# =========================

results = []

for finding in review["findings"]:

    problematic_text = finding["problematic_text"]

    found = False

    for page in paper["pages"]:

        for paragraph_number, paragraph in enumerate(
            page["paragraphs"],
            start=1
        ):

            text = paragraph["text"]

            start = text.find(problematic_text)

            if start != -1:

                end = start + len(problematic_text)

                result = {
                    "page": page["page"],
                    "paragraph": paragraph_number,
                    "start": start,
                    "end": end,
                    "problematic_text": problematic_text,
                    "category": finding["category"],
                    "issue_type": finding["issue_type"],
                    "severity": finding["severity"],
                    "status": finding["status"],
                    "reason": finding["reason"],
                    "recommendation": finding["recommendation"],
                    "confidence": finding["confidence"]
                }

                results.append(result)

                found = True
                break

        if found:
            break

    if not found:

        print("❌ Text tidak ditemukan:")
        print(problematic_text)


# =========================
# SAVE RESULT
# =========================

output_path = "datasets/review_with_offsets.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(
        {
            "findings": results
        },
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================
# DISPLAY
# =========================

print("===== OFFSET RESULT =====")

for i, result in enumerate(results, start=1):

    print(f"\n--- FINDING {i} ---")

    print("Page:", result["page"])
    print("Paragraph:", result["paragraph"])
    print("Start:", result["start"])
    print("End:", result["end"])
    print("Issue:", result["issue_type"])
    print("Text:", result["problematic_text"])

print(f"\nBerhasil disimpan ke: {output_path}")