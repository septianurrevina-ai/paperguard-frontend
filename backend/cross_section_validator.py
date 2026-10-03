import json
import re


# =========================================
# CONFIG
# =========================================

PAPER_PATH = "datasets/structured_paper.json"
FINDINGS_PATH = "datasets/cross_section_findings.json"
OUTPUT_PATH = "datasets/validated_cross_section_findings.json"


# =========================================
# LOAD FILES
# =========================================

with open(
    PAPER_PATH,
    "r",
    encoding="utf-8"
) as f:
    paper = json.load(f)


with open(
    FINDINGS_PATH,
    "r",
    encoding="utf-8"
) as f:
    review = json.load(f)


# =========================================
# VALID VALUES
# =========================================

VALID_CATEGORIES = {
    "CONSISTENCY"
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
#
# Kita membuat index berdasarkan:
# page + paragraph + section
#
# Tujuannya agar lokasi dari Gemini
# bisa diverifikasi secara deterministic.
# =========================================

paper_locations = {}

all_paragraphs = []


for page in paper["pages"]:

    for paragraph_number, paragraph in enumerate(
        page["paragraphs"],
        start=1
    ):

        section = paragraph.get(
            "section",
            "UNKNOWN"
        )

        text = paragraph.get(
            "text",
            ""
        ).strip()

        location = {
            "page": page["page"],
            "section": section,
            "paragraph": paragraph_number,
            "text": text
        }

        key = (
            page["page"],
            section,
            paragraph_number
        )

        paper_locations[key] = location

        if text:
            all_paragraphs.append(location)


# =========================================
# EXACT TEXT SEARCH
# =========================================

def find_exact_text(problematic_text):

    matches = []

    if not problematic_text:
        return matches

    for item in all_paragraphs:

        if problematic_text in item["text"]:

            matches.append({
                "page": item["page"],
                "section": item["section"],
                "paragraph": item["paragraph"]
            })

    return matches


# =========================================
# LOCATION VALIDATION
# =========================================

def validate_location(location):

    if not isinstance(location, dict):
        return False, "Location bukan object."

    page = location.get("page")
    section = location.get("section")
    paragraph = location.get("paragraph")

    if not isinstance(page, int):
        return False, "Page bukan integer."

    if not isinstance(section, str):
        return False, "Section bukan string."

    if not isinstance(paragraph, int):
        return False, "Paragraph bukan integer."

    key = (
        page,
        section,
        paragraph
    )

    if key not in paper_locations:

        return (
            False,
            "Location tidak ditemukan di paper."
        )

    return True, ""


# =========================================
# VALIDATE FINDING
# =========================================

validated_findings = []

invalid_findings = []


for index, finding in enumerate(
    review.get("findings", []),
    start=1
):

    errors = []

    problematic_text = finding.get(
        "problematic_text",
        ""
    )

    category = finding.get(
        "category"
    )

    severity = finding.get(
        "severity"
    )

    status = finding.get(
        "status"
    )

    confidence = finding.get(
        "confidence"
    )

    related_locations = finding.get(
        "related_locations",
        []
    )


    # -------------------------------------
    # 1. Validate problematic text
    # -------------------------------------

    text_matches = find_exact_text(
        problematic_text
    )

    if not text_matches:

        errors.append(
            "problematic_text tidak ditemukan "
            "secara exact di paper."
        )


    # -------------------------------------
    # 2. Validate category
    # -------------------------------------

    if category not in VALID_CATEGORIES:

        errors.append(
            f"Category tidak valid: {category}"
        )


    # -------------------------------------
    # 3. Validate severity
    # -------------------------------------

    if severity not in VALID_SEVERITIES:

        errors.append(
            f"Severity tidak valid: {severity}"
        )


    # -------------------------------------
    # 4. Validate status
    # -------------------------------------

    if status not in VALID_STATUSES:

        errors.append(
            f"Status tidak valid: {status}"
        )


    # -------------------------------------
    # 5. Validate confidence
    # -------------------------------------

    if not isinstance(
        confidence,
        (int, float)
    ):

        errors.append(
            "Confidence bukan angka."
        )

    else:

        if confidence < 0 or confidence > 1:

            errors.append(
                "Confidence harus berada "
                "di antara 0 dan 1."
            )


    # -------------------------------------
    # 6. Validate related locations
    # -------------------------------------

    valid_related_locations = []


    for location in related_locations:

        valid, error = validate_location(
            location
        )

        if not valid:

            errors.append(
                f"Related location invalid: {error}"
            )

        else:

            valid_related_locations.append(
                location
            )


    # -------------------------------------
    # 7. Check that related locations
    #    are actually different evidence
    # -------------------------------------

    if (
        problematic_text
        and valid_related_locations
        and text_matches
    ):

        main_locations = {
            (
                match["page"],
                match["section"],
                match["paragraph"]
            )
            for match in text_matches
        }

        cleaned_related = []

        for location in valid_related_locations:

            related_key = (
                location["page"],
                location["section"],
                location["paragraph"]
            )

            if related_key not in main_locations:

                cleaned_related.append(
                    location
                )

        valid_related_locations = cleaned_related


    # -------------------------------------
    # 8. Deduplication
    # -------------------------------------
    #
    # Dua finding dianggap duplicate jika:
    # - problematic_text sama
    # - issue_type sama
    # - lokasi utama sama
    #
    # Ini lebih aman daripada hanya
    # membandingkan problematic_text.
    # -------------------------------------

    issue_type = finding.get(
        "issue_type",
        ""
    )

    duplicate = False

    current_location_keys = {
        (
            match["page"],
            match["section"],
            match["paragraph"]
        )
        for match in text_matches
    }


    for existing in validated_findings:

        existing_location_keys = {
            (
                match["page"],
                match["section"],
                match["paragraph"]
            )
            for match in find_exact_text(
                existing["problematic_text"]
            )
        }

        if (
            existing["problematic_text"]
            == problematic_text
            and existing["issue_type"]
            == issue_type
            and (
                current_location_keys
                & existing_location_keys
            )
        ):

            duplicate = True
            break


    if duplicate:

        errors.append(
            "Finding duplicate."
        )


    # -------------------------------------
    # 9. RESULT
    # -------------------------------------

    if errors:

        invalid_findings.append({
            "original_index": index,
            "finding": finding,
            "errors": errors
        })

    else:

        validated_findings.append({

            "finding_id":
                f"PG-CS-{len(validated_findings) + 1:03d}",

            "problematic_text":
                problematic_text,

            "category":
                category,

            "issue_type":
                issue_type,

            "severity":
                severity,

            "status":
                status,

            "reason":
                finding.get(
                    "reason",
                    ""
                ),

            "recommendation":
                finding.get(
                    "recommendation",
                    ""
                ),

            "confidence":
                confidence,

            "related_locations":
                valid_related_locations
        })


# =========================================
# SAVE OUTPUT
# =========================================

output = {

    "paper_id":
        paper["paper_id"],

    "title":
        paper["title"],

    "total_findings":
        len(validated_findings),

    "valid_findings":
        len(validated_findings),

    "invalid_findings":
        len(invalid_findings),

    "findings":
        validated_findings,

    "invalid":
        invalid_findings
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
# PRINT RESULT
# =========================================

print("====================================")
print("CROSS-SECTION FINDING VALIDATOR")
print("====================================")

print(
    "Paper:",
    paper["title"]
)

print()

print(
    "Total AI findings:",
    len(review.get("findings", []))
)

print(
    "Valid:",
    len(validated_findings)
)

print(
    "Invalid:",
    len(invalid_findings)
)

print()


# =========================================
# VALID FINDINGS
# =========================================

if validated_findings:

    print("VALID FINDINGS")
    print("------------------------------------")

    for finding in validated_findings:

        print()

        print(
            finding["finding_id"]
        )

        print(
            "Text:",
            finding["problematic_text"]
        )

        print(
            "Issue:",
            finding["issue_type"]
        )

        print(
            "Severity:",
            finding["severity"]
        )

        print(
            "Status:",
            finding["status"]
        )

        print(
            "Confidence:",
            finding["confidence"]
        )

        print(
            "Related locations:"
        )

        for location in finding[
            "related_locations"
        ]:

            print(
                f"  Page {location['page']} | "
                f"{location['section']} | "
                f"Paragraph {location['paragraph']}"
            )


# =========================================
# INVALID FINDINGS
# =========================================

if invalid_findings:

    print()
    print("INVALID FINDINGS")
    print("------------------------------------")

    for item in invalid_findings:

        print()

        print(
            f"AI Finding #{item['original_index']}"
        )

        print(
            "Text:",
            item["finding"].get(
                "problematic_text",
                ""
            )
        )

        for error in item["errors"]:

            print(
                "ERROR:",
                error
            )


# =========================================
# FINISH
# =========================================

print()
print("====================================")
print("Validation selesai!")
print(
    "Output:",
    OUTPUT_PATH
)
print("====================================")