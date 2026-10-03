import json
import re


INPUT_PATH = "datasets/final_findings_with_locations.json"
OUTPUT_PATH = "datasets/final_findings_deduplicated.json"


# =========================================
# LOAD DATA
# =========================================

with open(
    INPUT_PATH,
    "r",
    encoding="utf-8"
) as f:
    data = json.load(f)


findings = data.get("findings", [])


# =========================================
# NORMALIZE TEXT
# =========================================

def normalize_text(text):
    """
    Normalisasi text untuk membantu
    mendeteksi duplicate.
    """

    text = text.lower().strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# =========================================
# DUPLICATE DETECTION
# =========================================

unique_findings = []
duplicates = []

seen = {}


for finding in findings:

    text = normalize_text(
        finding.get(
            "problematic_text",
            ""
        )
    )

    issue_type = normalize_text(
        finding.get(
            "issue_type",
            ""
        )
    )

    location = finding.get(
        "location",
        {}
    )

    location_key = (
        location.get("page"),
        location.get("section"),
        location.get("paragraph")
    )

    # -------------------------------------
    # Duplicate key
    # -------------------------------------

    duplicate_key = (
        text,
        issue_type,
        location_key
    )


    if duplicate_key in seen:

        duplicates.append({
            "duplicate_finding":
                finding.get("finding_id"),

            "original_finding":
                seen[duplicate_key],

            "problematic_text":
                finding.get(
                    "problematic_text"
                ),

            "location":
                location
        })

        continue


    # -------------------------------------
    # Unique finding
    # -------------------------------------

    seen[duplicate_key] = finding.get(
        "finding_id"
    )

    unique_findings.append(
        finding
    )


# =========================================
# REASSIGN FINDING IDs
# =========================================

for index, finding in enumerate(
    unique_findings,
    start=1
):

    finding["finding_id"] = (
        f"PG-{index:03d}"
    )


# =========================================
# OUTPUT
# =========================================

output = {

    "paper_id":
        data.get("paper_id"),

    "title":
        data.get("title"),

    "total_findings":
        len(unique_findings),

    "removed_duplicates":
        len(duplicates),

    "findings":
        unique_findings,

    "duplicates":
        duplicates
}


with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================
# REPORT
# =========================================

print("====================================")
print("PAPERGUARD DEDUPLICATION")
print("====================================")

print(
    "Original findings:",
    len(findings)
)

print(
    "Unique findings:",
    len(unique_findings)
)

print(
    "Removed duplicates:",
    len(duplicates)
)

print()


if duplicates:

    print("DUPLICATES")
    print("------------------------------------")

    for duplicate in duplicates:

        print(
            f"{duplicate['duplicate_finding']} "
            f"→ duplicate of "
            f"{duplicate['original_finding']}"
        )

        print(
            "Text:",
            duplicate["problematic_text"]
        )

        location = duplicate["location"]

        print(
            "Location:",
            f"Page {location.get('page')} | "
            f"{location.get('section')} | "
            f"Paragraph {location.get('paragraph')}"
        )

        print()


print("====================================")
print("Deduplication selesai!")
print(
    "Output:",
    OUTPUT_PATH
)
print("====================================")