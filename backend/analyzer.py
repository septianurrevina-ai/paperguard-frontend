import os
import json

from google import genai
from pydantic import BaseModel
from dotenv import load_dotenv

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

with open("datasets/paragraphs.json", "r", encoding="utf-8") as f:
    paper = json.load(f)


# Untuk sementara kita tes 1 paragraf
paragraph = paper["pages"][0]["paragraphs"][2]["text"]


print("===== PARAGRAF YANG DIANALISIS =====")
print(paragraph)
print()


# =========================
# PROMPT
# =========================

prompt = f"""
You are PaperGuard, an AI academic paper reviewer.

Your task is to identify meaningful problems in the paragraph below.

Review the paragraph from multiple perspectives:

1. LANGUAGE
- Grammar
- Spelling
- Academic wording
- Clarity

2. LOGIC
- Logical clarity
- Contradictions
- Unsupported reasoning

3. ACADEMIC WRITING
- Unclear statements
- Redundancy
- Informal or inappropriate academic language

IMPORTANT RULES:

- Do NOT invent problems.
- Do NOT criticize a sentence simply because it could be written differently.
- Only report meaningful issues that could reasonably require revision.
- If there are multiple meaningful issues, report all of them.
- If there are no meaningful issues, return an empty findings list.

VERY IMPORTANT:

"problematic_text" MUST be copied EXACTLY from the paragraph.
The problematic_text should contain ONLY the smallest meaningful
phrase, clause, or sentence fragment that directly contains the issue.

Do NOT return the entire paragraph.
Do NOT return an entire sentence if only a small phrase is problematic.

For example:
If the problem is a missing comma after "In general",
problematic_text should be:
"In general"

If the problem is an unsupported claim about artificial consciousness,
problematic_text should focus on the claim itself, such as:
"it may be possible to build sensor networks that exhibit a form of artificial consciousness"

Do NOT paraphrase it.
Do NOT rewrite it.
Do NOT generate text that does not exist in the paragraph.

The problematic_text must be an exact substring of the original paragraph.

For each finding:

category:
One of:
LANGUAGE
STRUCTURE
CONSISTENCY
METHODOLOGY
RESULTS
DISCUSSION
CITATIONS
FIGURES_TABLES
COMPLETENESS

issue_type:
Use a specific description such as:
GRAMMAR_ERROR
SPELLING_ERROR
UNCLEAR_STATEMENT
ACADEMIC_WORDING
REDUNDANCY
LOGICAL_PROBLEM
UNSUPPORTED_CLAIM
etc.

severity:
One of:
CRITICAL
MAJOR
MINOR
SUGGESTION

status:
One of:
CONFIRMED
LIKELY
POSSIBLE
SUGGESTION

confidence:
A number between 0 and 1.

Paragraph:
{paragraph}
"""


# =========================
# CALL GEMINI
# =========================

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=prompt,
    config={
        "response_mime_type": "application/json",
        "response_schema": ReviewResult,
    },
)


# =========================
# VALIDATE RESULT
# =========================

result = ReviewResult.model_validate_json(response.text)
# =========================
# SAVE REVIEW RESULT
# =========================

output_path = "datasets/review_result.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(
        result.model_dump(),
        f,
        ensure_ascii=False,
        indent=2
    )

print(f"\nReview berhasil disimpan ke: {output_path}")


# =========================
# VERIFY EXACT TEXT
# =========================

print("===== PAPERGUARD RESULT =====")

for i, finding in enumerate(result.findings, start=1):

    print(f"\n--- FINDING {i} ---")

    print("Problematic text:")
    print(finding.problematic_text)

    print("Category:")
    print(finding.category)

    print("Issue type:")
    print(finding.issue_type)

    print("Severity:")
    print(finding.severity)

    print("Status:")
    print(finding.status)

    print("Reason:")
    print(finding.reason)

    print("Recommendation:")
    print(finding.recommendation)

    print("Confidence:")
    print(finding.confidence)

    # Cek apakah teks benar-benar ada
    if finding.problematic_text in paragraph:
        print("Exact text check: ✅ VALID")
    else:
        print("Exact text check: ❌ INVALID")