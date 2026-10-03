import json
import os
import re
import unicodedata


STRUCTURED_PAPER_PATH = "datasets/structured_paper.json"
FINDINGS_PATH = "datasets/paper_findings.json"
OUTPUT_PATH = "datasets/paper_findings_with_locations.json"


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalisasi teks agar perbedaan karakter PDF seperti
    ligature (ﬁ, ﬃ, ﬀ, dll.) tidak menghambat pencarian.
    """

    if not text:
        return ""

    text = str(text)

    # Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # Explicit PDF ligature mapping
    ligatures = {
        "\ufb00": "ff",   # ﬀ
        "\ufb01": "fi",   # ﬁ
        "\ufb02": "fl",   # ﬂ
        "\ufb03": "ffi",  # ﬃ
        "\ufb04": "ffl",  # ﬄ
        "\ufb05": "st",   # ﬅ
        "\ufb06": "st",   # ﬆ
    }

    for old, new in ligatures.items():
        text = text.replace(old, new)

    # Common PDF characters
    replacements = {
        "\u2217": "*",
        "\u2212": "-",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def compact_text(text):
    """
    Menghapus whitespace agar kasus seperti:

    off both
    offboth
    oﬀboth

    tetap bisa dibandingkan.
    """

    normalized = normalize_text(text)

    return re.sub(r"\s+", "", normalized)


# ============================================================
# FIND TEXT
# ============================================================

def find_text_in_paragraph(
    problematic_text,
    paragraph_text
):
    """
    Mencari problematic_text di dalam paragraph_text.

    Urutan:
    1. Exact normalized match
    2. Compact match
    """

    target = normalize_text(problematic_text)
    source = normalize_text(paragraph_text)

    if not target or not source:
        return False, None

    # --------------------------------------------------------
    # 1. Exact normalized match
    # --------------------------------------------------------

    if target.lower() in source.lower():
        return True, "normalized_exact"

    # --------------------------------------------------------
    # 2. Compact match
    # --------------------------------------------------------

    target_compact = compact_text(problematic_text)
    source_compact = compact_text(paragraph_text)

    if target_compact and target_compact.lower() in source_compact.lower():
        return True, "compact"

    return False, None


# ============================================================
# LOAD DATA
# ============================================================

def load_json(path):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"File tidak ditemukan: {path}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


# ============================================================
# RESOLVE LOCATION
# ============================================================

def resolve_finding(
    finding,
    pages
):
    problematic_text = finding.get(
        "problematic_text",
        ""
    )

    if not problematic_text:
        return None, None

    for page in pages:

        page_number = page.get(
            "page"
        )

        section_default = page.get(
            "section",
            "UNKNOWN"
        )

        paragraphs = page.get(
            "paragraphs",
            []
        )

        for paragraph_index, paragraph in enumerate(
            paragraphs,
            start=1
        ):

            paragraph_text = paragraph.get(
                "text",
                ""
            )

            matched, match_method = find_text_in_paragraph(
                problematic_text,
                paragraph_text
            )

            if matched:

                section = paragraph.get(
                    "section",
                    section_default
                )

                location = {
                    "page": page_number,
                    "section": section,
                    "paragraph": paragraph_index
                }

                return location, match_method

    return None, None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 36)
    print("PAPERGUARD LOCATION RESOLVER")
    print("=" * 36)

    print()

    structured_data = load_json(
        STRUCTURED_PAPER_PATH
    )

    findings_data = load_json(
        FINDINGS_PATH
    )

    pages = structured_data.get(
        "pages",
        []
    )

    print(
        f"Paper: Current Paper"
    )

    print()

    print(
        f"Total findings: {len(findings_data)}"
    )

    print()

    resolved_findings = []
    unresolved_findings = []

    for finding in findings_data:

        finding_copy = dict(finding)

        location, match_method = resolve_finding(
            finding,
            pages
        )

        if location:

            finding_copy["location"] = location
            finding_copy["match_method"] = match_method

            resolved_findings.append(
                finding_copy
            )

        else:

            finding_copy["location"] = None
            finding_copy["match_method"] = None
            finding_copy["status"] = "UNRESOLVED"

            unresolved_findings.append(
                finding_copy
            )

    # ========================================================
    # SAVE
    # ========================================================

    output = {
        "paper_id": "current_paper",
        "title": "Current Paper",
        "total_findings": len(findings_data),
        "resolved": len(resolved_findings),
        "unresolved": len(unresolved_findings),
        "findings": resolved_findings + unresolved_findings
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

    # ========================================================
    # RESULT
    # ========================================================

    print(
        f"Resolved: {len(resolved_findings)}"
    )

    print(
        f"Unresolved: {len(unresolved_findings)}"
    )

    print()

    if resolved_findings:

        print(
            "RESOLVED LOCATIONS"
        )

        print(
            "-" * 36
        )

        for finding in resolved_findings:

            location = finding["location"]

            print()

            print(
                finding["finding_id"]
            )

            print(
                f"Text: {finding['problematic_text']}"
            )

            print(
                f"Location: "
                f"Page {location['page']} | "
                f"{location['section']} | "
                f"Paragraph {location['paragraph']}"
            )

            print(
                f"Match: {finding['match_method']}"
            )

    print()

    if unresolved_findings:

        print(
            "UNRESOLVED FINDINGS"
        )

        print(
            "-" * 36
        )

        for finding in unresolved_findings:

            print()

            print(
                finding["finding_id"]
            )

            print(
                f"Text: {finding['problematic_text']}"
            )

            print(
                "Reason: problematic_text "
                "tidak ditemukan di structured_paper.json"
            )

    print()

    print("=" * 36)
    print("Location resolving selesai!")
    print(
        f"Output: {OUTPUT_PATH}"
    )
    print("=" * 36)


if __name__ == "__main__":
    main()