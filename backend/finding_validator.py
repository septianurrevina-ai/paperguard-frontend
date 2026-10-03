import json
import re


# =========================================
# LOAD DATA
# =========================================

with open(
    "datasets/structured_paper.json",
    "r",
    encoding="utf-8"
) as f:
    paper = json.load(f)


with open(
    "datasets/paper_review_result.json",
    "r",
    encoding="utf-8"
) as f:
    review = json.load(f)


# =========================================
# VALID VALUES
# =========================================

VALID_CATEGORIES = {
    "LANGUAGE",
    "STRUCTURE",
    "CONSISTENCY",
    "METHODOLOGY",
    "RESULTS",
    "DISCUSSION",
    "CITATIONS",
    "FIGURES_TABLES",
    "COMPLETENESS"
}

VALID_SEVERITIES = {
    "CRITICAL",
    "MAJOR",
    "MINOR",
    "SUGGESTION"
}

VALID_STATUSES = {
    "CONFIRMED",
    "LIKELY",
    "POSSIBLE",
    "SUGGESTION"
}


# =========================================
# BUILD PAPER INDEX
# =========================================

paper_locations = []

for page in paper["pages"]:

    for paragraph_number, paragraph in enumerate(
        page["paragraphs"],
        start=1
    ):

        paper_locations.append({
            "page": page["page"],
            "paragraph": paragraph_number,
            "section": paragraph.get(
                "section",
                "UNKNOWN"
            ),
            "type": paragraph.get(
                "type",
                "paragraph"
            ),
            "text": paragraph["text"]
        })


# =========================================
# HELPER:
# FIND EXACT TEXT
# =========================================

def find_text(problematic_text):

    matches = []

    for location in paper_locations:

        text = location["text"]

        start = text.find(problematic_text)

        if start != -1:

            end = start + len(problematic_text)

            matches.append({
                "page": location["page"],
                "paragraph": location["paragraph"],
                "section": location["section"],
                "start": start,
                "end": end,
                "problematic_text": problematic_text
            })

    return matches


# =========================================
# HELPER:
# CHECK EXTRACTION ARTIFACT
# =========================================

def looks_like_extraction_artifact(text):

    # Banyak simbol matematika yang muncul
    math_symbols = len(
        re.findall(
            r"[∑∫√∞≈≠≤≥αβγθλμσπ∂]",
            text
        )
    )

    # Banyak tanda kurung / pipe yang tidak natural
    strange_symbols = len(
        re.findall(
            r"[|]",
            text
        )
    )

    # Pola karakter yang sangat tidak natural
    repeated_single_chars = bool(
        re.search(
            r"\b[a-zA-Z]\s+[a-zA-Z]\s+[a-zA-Z]\s+[a-zA-Z]",
            text
        )
    )

    # Equation-like text
    equation_like = (
        "=" in text
        and (
            math_symbols >= 2
            or strange_symbols >= 2
            or repeated_single_chars
        )
    )

    return equation_like


# =========================================
# VALIDATE FINDINGS
# =========================================

validated_findings = []

seen = set()

print("====================================")
print("PAPERGUARD FINDING VALIDATOR")
print("====================================")
print()


for index, finding in enumerate(
    review["findings"],
    start=1
):

    problematic_text = (
        finding["problematic_text"]
    )

    print(
        f"Validating finding "
        f"{index}/{len(review['findings'])}..."
    )

    matches = find_text(
        problematic_text
    )

    # -------------------------------------
    # EXACT TEXT CHECK
    # -------------------------------------

    exact_text_found = len(matches) > 0

    # -------------------------------------
    # DUPLICATE CHECK
    # -------------------------------------

    duplicate = False

    for match in matches:

        location_key = (
            match["page"],
            match["paragraph"],
            match["start"],
            match["end"]
        )

        if location_key in seen:
            duplicate = True

        seen.add(location_key)

    # -------------------------------------
    # ENUM VALIDATION
    # -------------------------------------

    category_valid = (
        finding["category"]
        in VALID_CATEGORIES
    )

    severity_valid = (
        finding["severity"]
        in VALID_SEVERITIES
    )

    status_valid = (
        finding["status"]
        in VALID_STATUSES
    )

    confidence_valid = (
        isinstance(
            finding["confidence"],
            (int, float)
        )
        and 0 <= finding["confidence"] <= 1
    )

    # -------------------------------------
    # EXTRACTION ARTIFACT
    # -------------------------------------

    extraction_artifact = (
        looks_like_extraction_artifact(
            problematic_text
        )
    )

    # -------------------------------------
    # VALIDATION STATUS
    # -------------------------------------

    if not exact_text_found:

        validation_status = "INVALID"

    elif extraction_artifact:

        validation_status = (
            "NEEDS_EXTRACTION_CHECK"
        )

    elif duplicate:

        validation_status = "DUPLICATE"

    elif not (
        category_valid
        and severity_valid
        and status_valid
        and confidence_valid
    ):

        validation_status = "INVALID_METADATA"

    else:

        validation_status = "VALID"

    # -------------------------------------
    # CREATE LOCATION DATA
    # -------------------------------------

    locations = []

    for match in matches:

        locations.append({
            "page": match["page"],
            "paragraph": match["paragraph"],
            "section": match["section"],
            "start": match["start"],
            "end": match["end"]
        })

    # -------------------------------------
    # CREATE FINAL FINDING
    # -------------------------------------

    validated_finding = {
        "finding_id": f"PG-{index:03d}",

        "problematic_text":
            problematic_text,

        "category":
            finding["category"],

        "issue_type":
            finding["issue_type"],

        "severity":
            finding["severity"],

        "status":
            finding["status"],

        "reason":
            finding["reason"],

        "recommendation":
            finding["recommendation"],

        "confidence":
            finding["confidence"],

        "validation": {
            "status":
                validation_status,

            "exact_text_found":
                exact_text_found,

            "duplicate":
                duplicate,

            "extraction_artifact":
                extraction_artifact,

            "category_valid":
                category_valid,

            "severity_valid":
                severity_valid,

            "status_valid":
                status_valid,

            "confidence_valid":
                confidence_valid
        },

        "locations":
            locations
    }

    validated_findings.append(
        validated_finding
    )


# =========================================
# SUMMARY
# =========================================

valid_count = 0
invalid_count = 0
duplicate_count = 0
artifact_count = 0


for finding in validated_findings:

    status = finding["validation"]["status"]

    if status == "VALID":
        valid_count += 1

    elif status == "INVALID":
        invalid_count += 1

    elif status == "DUPLICATE":
        duplicate_count += 1

    elif status == "NEEDS_EXTRACTION_CHECK":
        artifact_count += 1


# =========================================
# FINAL OUTPUT
# =========================================

output = {
    "paper_id":
        paper["paper_id"],

    "title":
        paper["title"],

    "summary": {
        "total_findings":
            len(validated_findings),

        "valid":
            valid_count,

        "invalid":
            invalid_count,

        "duplicates":
            duplicate_count,

        "needs_extraction_check":
            artifact_count
    },

    "findings":
        validated_findings
}


output_path = (
    "datasets/validated_findings.json"
)


with open(
    output_path,
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
# PRINT SUMMARY
# =========================================

print()
print("====================================")
print("VALIDATION COMPLETE")
print("====================================")

print(
    "Total findings:",
    len(validated_findings)
)

print(
    "Valid:",
    valid_count
)

print(
    "Invalid:",
    invalid_count
)

print(
    "Duplicates:",
    duplicate_count
)

print(
    "Needs extraction check:",
    artifact_count
)

print()
print(
    "Output:",
    output_path
)

print()
print("===== FINDING STATUS =====")

for finding in validated_findings:

    validation = finding["validation"]

    print(
        f"{finding['finding_id']} | "
        f"{validation['status']} | "
        f"{finding['category']} | "
        f"{finding['problematic_text'][:70]}"
    )