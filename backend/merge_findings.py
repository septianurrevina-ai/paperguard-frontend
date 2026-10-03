import json


# =========================================
# CONFIG
# =========================================

LOCAL_FINDINGS_PATH = (
    "datasets/validated_findings.json"
)

CROSS_SECTION_FINDINGS_PATH = (
    "datasets/validated_cross_section_findings.json"
)

OUTPUT_PATH = (
    "datasets/final_findings.json"
)


# =========================================
# LOAD LOCAL FINDINGS
# =========================================

with open(
    LOCAL_FINDINGS_PATH,
    "r",
    encoding="utf-8"
) as f:
    local_data = json.load(f)


# =========================================
# LOAD CROSS-SECTION FINDINGS
# =========================================

with open(
    CROSS_SECTION_FINDINGS_PATH,
    "r",
    encoding="utf-8"
) as f:
    cross_section_data = json.load(f)


local_findings = local_data.get(
    "findings",
    []
)

cross_section_findings = (
    cross_section_data.get(
        "findings",
        []
    )
)


# =========================================
# MERGE
# =========================================

final_findings = []


# -----------------------------------------
# LOCAL FINDINGS
# -----------------------------------------

for finding in local_findings:

    new_finding = finding.copy()

    # Pastikan category tersedia
    if not new_finding.get("category"):
        new_finding["category"] = "GENERAL"

    # Local finding sebelumnya belum
    # memiliki related_locations
    if "related_locations" not in new_finding:
        new_finding["related_locations"] = []

    final_findings.append(
        new_finding
    )


# -----------------------------------------
# CROSS-SECTION FINDINGS
# -----------------------------------------

for finding in cross_section_findings:

    new_finding = finding.copy()

    final_findings.append(
        new_finding
    )


# =========================================
# REASSIGN FINDING IDs
# =========================================
#
# Semua findings sekarang menggunakan
# satu sistem ID.
#
# PG-001
# PG-002
# ...
# =========================================

for index, finding in enumerate(
    final_findings,
    start=1
):

    finding["finding_id"] = (
        f"PG-{index:03d}"
    )


# =========================================
# SORT FINDINGS
# =========================================
#
# Urutkan berdasarkan:
# 1. page
# 2. section
# 3. finding_id
#
# Supaya frontend lebih mudah menampilkan
# finding berdasarkan posisi di paper.
# =========================================

def get_sort_key(finding):

    location = finding.get(
        "location",
        {}
    )

    page = location.get(
        "page",
        999999
    )

    section = location.get(
        "section",
        ""
    )

    finding_id = finding.get(
        "finding_id",
        ""
    )

    return (
        page,
        section,
        finding_id
    )


final_findings.sort(
    key=get_sort_key
)


# =========================================
# FINAL OUTPUT
# =========================================

output = {

    "paper_id":
        local_data.get(
            "paper_id",
            cross_section_data.get(
                "paper_id"
            )
        ),

    "title":
        local_data.get(
            "title",
            cross_section_data.get(
                "title"
            )
        ),

    "total_findings":
        len(final_findings),

    "local_findings":
        len(local_findings),

    "cross_section_findings":
        len(cross_section_findings),

    "findings":
        final_findings
}


# =========================================
# SAVE
# =========================================

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
# PRINT SUMMARY
# =========================================

print("====================================")
print("PAPERGUARD FINDING MERGER")
print("====================================")

print(
    "Paper:",
    output["title"]
)

print()

print(
    "Local findings:",
    output["local_findings"]
)

print(
    "Cross-section findings:",
    output["cross_section_findings"]
)

print(
    "Total final findings:",
    output["total_findings"]
)

print()

print("Findings:")

for finding in final_findings:

    location = finding.get(
        "location",
        {}
    )

    print(
        f"{finding['finding_id']} | "
        f"{finding.get('category', 'UNKNOWN')} | "
        f"{finding.get('issue_type', 'UNKNOWN')} | "
        f"{finding.get('severity', 'UNKNOWN')}"
    )

    if location:

        print(
            f"   Page {location.get('page')} | "
            f"{location.get('section')}"
        )

    print(
        f"   Text: "
        f"{finding.get('problematic_text', '')[:100]}"
    )


print()
print("====================================")
print("Merge selesai!")
print(
    "Output:",
    OUTPUT_PATH
)
print("====================================")