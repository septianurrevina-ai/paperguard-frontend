import os
import json

from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv


# =========================================
# SETUP
# =========================================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =========================================
# OUTPUT SCHEMA
# =========================================

class RelatedLocation(BaseModel):
    page: int
    section: str
    paragraph: int


class ConsistencyFinding(BaseModel):
    problematic_text: str
    category: str
    issue_type: str
    severity: str
    status: str
    reason: str
    recommendation: str
    confidence: float
    related_locations: list[RelatedLocation]


class ConsistencyResult(BaseModel):
    findings: list[ConsistencyFinding]


# =========================================
# LOAD PAPER
# =========================================

with open(
    "datasets/structured_paper.json",
    "r",
    encoding="utf-8"
) as f:
    paper = json.load(f)


# =========================================
# COLLECT ALL DETECTED SECTIONS
# =========================================
#
# Jangan mengasumsikan paper harus memiliki
# Introduction, Methodology, Results, dll.
#
# PaperGuard harus mengikuti struktur paper
# yang sebenarnya.
# =========================================

section_data = {}


for page in paper["pages"]:

    for paragraph_number, paragraph in enumerate(
        page["paragraphs"],
        start=1
    ):

        section = paragraph.get(
            "section",
            "UNKNOWN"
        )

        # Abaikan bagian yang belum diketahui
        if section == "UNKNOWN":
            continue
        
        
        # Abaikan REFERENCES karena akan dianalisis
        # oleh citation analyzer, bukan cross-section analyzer
        if section == "REFERENCES":
            continue

        # Heading bukan isi yang dianalisis
        if paragraph.get("type") == "heading":
            continue

        text = paragraph.get(
            "text",
            ""
        ).strip()

        if not text:
            continue

        if section not in section_data:
            section_data[section] = []

        section_data[section].append({
            "page": page["page"],
            "paragraph": paragraph_number,
            "section": section,
            "text": text
        })


# =========================================
# BUILD PAPER CONTEXT
# =========================================

context_parts = []


for section, paragraphs in section_data.items():

    if not paragraphs:
        continue

    context_parts.append(
        f"\n===== {section} =====\n"
    )

    for item in paragraphs:

        context_parts.append(
            f"""
[PAGE {item['page']}]
[PARAGRAPH {item['paragraph']}]

{item['text']}
"""
        )


paper_context = "\n".join(
    context_parts
)


# =========================================
# PRINT INFO
# =========================================

print("====================================")
print("PAPERGUARD CROSS-SECTION ANALYZER")
print("====================================")

print(
    "Paper:",
    paper["title"]
)

print()

print("Sections found:")

for section, paragraphs in section_data.items():

    print(
        f"- {section}: "
        f"{len(paragraphs)} paragraphs"
    )

print()


# =========================================
# PROMPT
# =========================================

prompt = f"""
You are PaperGuard, an AI academic paper consistency reviewer.

Your task is to analyze the relationships between different sections
of an academic paper.

The goal is NOT ordinary grammar checking.

Look specifically for contradictions, mismatches, unsupported
connections, and inconsistencies between ANY sections of the paper.

IMPORTANT:

Do NOT assume that the paper follows the standard structure:

Introduction → Methodology → Results → Discussion → Conclusion

The paper may use a completely different organizational structure.

Analyze the actual sections provided below.

Do NOT treat the absence of a conventional section as an error.

For example, if the paper does not contain a section called
"METHODOLOGY", do NOT report "missing methodology" because this
analyzer is specifically for CROSS-SECTION CONSISTENCY.

Focus on relationships between sections that actually exist.


==================================================
WHAT TO CHECK
==================================================

Look for meaningful inconsistencies such as:

1. ABSTRACT ↔ MAIN PAPER

- Abstract claims something that is not supported elsewhere
- Abstract describes a result differently from the main paper
- Abstract mentions a concept that conflicts with the main paper

2. EARLIER SECTIONS ↔ LATER SECTIONS

- A concept is defined differently later
- A claim changes meaning
- An argument contradicts an earlier explanation

3. OBJECTIVES ↔ OTHER SECTIONS

- Research objective is stated but later discussion addresses
  something substantially different
- A stated research question is not addressed by later content

4. METHODS / TECHNICAL DESCRIPTION ↔ RESULTS

- Different experiment or system is described
- Dataset or sample description changes
- Variables or parameters change
- Metrics change
- Experimental conditions conflict

5. RESULTS ↔ DISCUSSION

- Discussion interprets results differently from what the results say
- Discussion makes claims that go beyond the reported results
- Quantitative findings are described inconsistently

6. RESULTS ↔ CONCLUSION

- Conclusion claims a result that is not demonstrated
- Conclusion changes the meaning of the reported results
- Quantitative values conflict

7. TERMINOLOGY

- Same concept is given different meanings
- Important technical terminology changes meaning between sections

8. NUMBERS AND DATA

- Sample size changes
- Dataset size changes
- Percentages conflict
- Metrics conflict
- Parameter values conflict
- Experimental results conflict

9. REFERENCES TO OTHER SECTIONS

- A statement claims something was demonstrated earlier,
  but the referenced content does not support it

10. CLAIMS VS EVIDENCE

- A later section makes a strong claim that is not supported
  by evidence presented elsewhere in the paper


==================================================
IMPORTANT REASONING RULES
==================================================

Do NOT invent information.

Only use information explicitly present in the paper.

Do NOT report a problem merely because two sections use
different wording if they clearly mean the same thing.

Do NOT report stylistic differences as inconsistencies.

Do NOT report ordinary grammar or spelling issues.

Only report meaningful cross-section inconsistencies that could
reasonably require revision.

If there are no meaningful cross-section inconsistencies,
return an empty findings list.


==================================================
PROBLEMATIC TEXT
==================================================

"problematic_text" MUST be copied EXACTLY from the paper.

It MUST be an exact substring of one of the provided paragraphs.

Do NOT paraphrase it.

Do NOT rewrite it.

Do NOT create text that does not exist.

Choose the smallest meaningful phrase or clause that represents
the problematic claim.

The problematic_text should normally come from the section where
the inconsistency becomes visible.


==================================================
LOCATION RULES
==================================================

For every finding:

The main problematic_text must come from one of the provided
paragraphs.

Use the exact PAGE and PARAGRAPH numbers provided in the paper.

Do NOT invent page numbers.

Do NOT invent paragraph numbers.

For related_locations:

Include the locations of the other sections that provide
evidence for the inconsistency.

Only use locations that actually exist in the provided paper.

The related location should help explain WHY the problematic text
is inconsistent.


==================================================
CATEGORY
==================================================

category MUST be:

CONSISTENCY


==================================================
ISSUE TYPES
==================================================

Use a specific issue_type.

Allowed examples include:

OBJECTIVE_METHOD_MISMATCH
OBJECTIVE_RESULT_MISMATCH
METHOD_RESULT_MISMATCH
RESULT_CONCLUSION_MISMATCH
ABSTRACT_RESULT_MISMATCH
NUMBER_INCONSISTENCY
METRIC_INCONSISTENCY
VARIABLE_INCONSISTENCY
DATASET_INCONSISTENCY
TERMINOLOGY_INCONSISTENCY
UNSUPPORTED_CONCLUSION
UNANSWERED_RESEARCH_QUESTION


==================================================
SEVERITY
==================================================

severity MUST be one of:

CRITICAL
MAJOR
MINOR
SUGGESTION


Use:

CRITICAL
for a serious contradiction that substantially affects
the validity or interpretation of the paper.

MAJOR
for an important inconsistency that should reasonably be revised.

MINOR
for a smaller inconsistency with limited impact.

SUGGESTION
for something that may improve consistency but is not clearly
an actual error.


==================================================
STATUS
==================================================

status MUST be one of:

CONFIRMED
LIKELY
POSSIBLE
SUGGESTION


Use:

CONFIRMED
only when the inconsistency is directly supported by explicit
information in the paper.

LIKELY
when there is strong evidence but some interpretation is required.

POSSIBLE
when there is a reasonable indication but the evidence is
not conclusive.

SUGGESTION
when the finding is primarily an improvement suggestion.


==================================================
CONFIDENCE
==================================================

confidence MUST be a number from 0 to 1.

Use higher confidence only when the evidence is explicit.

Do not use 1.0 unless the contradiction is extremely clear
and directly demonstrated by the paper.


==================================================
FINAL CHECK BEFORE RETURNING A FINDING
==================================================

Before returning each finding, verify:

1. Does problematic_text exist EXACTLY in the provided paper?

2. Does the related location actually exist?

3. Is there an actual relationship between the two locations?

4. Is this a cross-section issue rather than a grammar issue?

5. Is the problem explicitly supported by the paper?

6. Would the author reasonably need to review or revise it?

If the answer to these checks is NO, do not return the finding.


==================================================
PAPER
==================================================

{paper_context}
"""


# =========================================
# CALL GEMINI
# =========================================

print("Analyzing cross-section consistency...")
print()


response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": ConsistencyResult,
    },
)


# =========================================
# PARSE RESULT
# =========================================

result = ConsistencyResult.model_validate_json(
    response.text
)


# =========================================
# SAVE RESULT
# =========================================

output = {
    "paper_id":
        paper["paper_id"],

    "title":
        paper["title"],

    "total_findings":
        len(result.findings),

    "findings":
        [
            finding.model_dump()
            for finding in result.findings
        ]
}


output_path = (
    "datasets/cross_section_findings.json"
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
# PRINT RESULT
# =========================================

print("====================================")
print("CROSS-SECTION FINDINGS")
print("====================================")


if not result.findings:

    print(
        "Tidak ditemukan cross-section "
        "inconsistency."
    )

else:

    for index, finding in enumerate(
        result.findings,
        start=1
    ):

        print()

        print(
            f"--- CONSISTENCY FINDING {index} ---"
        )

        print(
            "Text:",
            finding.problematic_text
        )

        print(
            "Issue:",
            finding.issue_type
        )

        print(
            "Severity:",
            finding.severity
        )

        print(
            "Status:",
            finding.status
        )

        print(
            "Reason:",
            finding.reason
        )

        print(
            "Recommendation:",
            finding.recommendation
        )

        print(
            "Confidence:",
            finding.confidence
        )

        print(
            "Related locations:"
        )

        for location in finding.related_locations:

            print(
                f"  Page {location.page} | "
                f"{location.section} | "
                f"Paragraph {location.paragraph}"
            )


print()

print("====================================")
print("Cross-section analysis selesai!")
print(
    "Total findings:",
    len(result.findings)
)

print(
    "Output:",
    output_path
)

print("====================================")