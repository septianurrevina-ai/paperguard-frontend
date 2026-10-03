import os
import json

from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv


# =========================
# SETUP
# =========================

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# =========================
# OUTPUT SCHEMA
# =========================

class Finding(BaseModel):
    problematic_text: str
    category: str
    issue_type: str
    severity: str
    status: str
    reason: str
    recommendation: str
    confidence: float


class ReviewResult(BaseModel):
    findings: list[Finding]


# =========================
# LOAD PAPER
# =========================

with open(
    "datasets/structured_paper.json",
    "r",
    encoding="utf-8"
) as f:
    paper = json.load(f)


# =========================
# COLLECT PARAGRAPHS
# =========================

paragraphs = []

for page in paper["pages"]:

    for paragraph_number, paragraph in enumerate(
        page["paragraphs"],
        start=1
    ):

        text = paragraph["text"].strip()

        if not text:
            continue

        # Jangan analisis heading sebagai isi
        if paragraph.get("type") == "heading":
            continue

        # Jangan analisis references dulu
        if paragraph.get("section") == "REFERENCES":
            continue

        paragraphs.append({
            "page": page["page"],
            "paragraph": paragraph_number,
            "section": paragraph.get(
                "section",
                "UNKNOWN"
            ),
            "text": text
        })


print("====================================")
print("PAPERGUARD WHOLE PAPER REVIEW")
print("====================================")

print("Paper :", paper["title"])
print("Pages :", len(paper["pages"]))
print("Paragraphs :", len(paragraphs))
print()


# =========================
# CHUNKING
# =========================

CHUNK_SIZE = 5

chunks = [
    paragraphs[i:i + CHUNK_SIZE]
    for i in range(
        0,
        len(paragraphs),
        CHUNK_SIZE
    )
]

print("Total chunks:", len(chunks))
print()


# =========================
# REVIEW FUNCTION
# =========================

def review_chunk(chunk, chunk_number):

    context = "\n\n".join(
        [
            f"""
[PAGE {item['page']}]
[SECTION: {item['section']}]
[PARAGRAPH: {item['paragraph']}]

{item['text']}
"""
            for item in chunk
        ]
    )

    prompt = f"""
You are PaperGuard, an AI academic paper reviewer.

You are reviewing a real academic paper.

Analyze the following group of paragraphs.

Your job is to identify meaningful issues that may require revision.

Review these categories:

1. LANGUAGE
- Grammar
- Spelling
- Academic wording
- Clarity

2. STRUCTURE
- Poor paragraph organization
- Missing structural information
- Poor section organization

3. CONSISTENCY
- Contradictory terminology
- Contradictory numbers
- Contradictory objectives
- Contradictory variables
- Contradictory claims

4. METHODOLOGY
- Missing methodological information
- Unclear dataset/sample
- Unclear experimental setup
- Reproducibility problems

5. RESULTS
- Claims not supported by results
- Numerical inconsistencies
- Result interpretation problems

6. DISCUSSION
- Unsupported interpretation
- Conclusions that go beyond evidence
- Logical problems

7. CITATIONS
- Claims that appear to require citations
- Citation-related problems

8. FIGURES_TABLES
- References to figures/tables that appear inconsistent
- Missing figure/table references

9. COMPLETENESS
- Important information appears to be missing
- Unsupported claims

IMPORTANT:

Do NOT invent problems.

Do NOT criticize text simply because you would personally write it differently.

Only report meaningful issues that could reasonably require revision.

If there are no meaningful issues, return an empty findings list.

VERY IMPORTANT:

"problematic_text" MUST be copied EXACTLY from the provided paragraphs.

It must be an exact substring of one of the paragraphs.

Do NOT paraphrase.

Do NOT rewrite.

Do NOT generate text that does not exist.

Choose the SMALLEST meaningful phrase or clause containing the problem.

Do NOT return the entire paragraph unless the entire paragraph is genuinely problematic.

Each finding must have:

category:
LANGUAGE
STRUCTURE
CONSISTENCY
METHODOLOGY
RESULTS
DISCUSSION
CITATIONS
FIGURES_TABLES
COMPLETENESS

severity:
CRITICAL
MAJOR
MINOR
SUGGESTION

status:
CONFIRMED
LIKELY
POSSIBLE
SUGGESTION

confidence:
number from 0 to 1

Do not make claims about information that is not present in the provided text.

This is chunk {chunk_number}.

PAPER CONTENT:

{context}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": ReviewResult,
        },
    )

    return ReviewResult.model_validate_json(
        response.text
    )


# =========================
# RUN REVIEW
# =========================

all_findings = []

for index, chunk in enumerate(
    chunks,
    start=1
):

    print(
        f"Analyzing chunk "
        f"{index}/{len(chunks)}..."
    )

    result = review_chunk(
        chunk,
        index
    )

    print(
        f"  Findings: "
        f"{len(result.findings)}"
    )

    for finding in result.findings:

        all_findings.append(
            finding.model_dump()
        )


# =========================
# SAVE RESULT
# =========================

output = {
    "paper_id": paper["paper_id"],
    "title": paper["title"],
    "total_findings": len(all_findings),
    "findings": all_findings
}


output_path = (
    "datasets/paper_review_result.json"
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


# =========================
# PRINT FINDINGS
# =========================

print()
print("====================================")
print("PAPERGUARD FINDINGS")
print("====================================")

for index, finding in enumerate(
    all_findings,
    start=1
):

    print()
    print(f"--- FINDING {index} ---")

    print(
        "Text:",
        finding["problematic_text"]
    )

    print(
        "Category:",
        finding["category"]
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
        "Reason:",
        finding["reason"]
    )

    print(
        "Recommendation:",
        finding["recommendation"]
    )

    print(
        "Confidence:",
        finding["confidence"]
    )


print()
print("====================================")
print("Review selesai!")
print("Total findings:", len(all_findings))
print("Output:", output_path)
print("====================================")