import json
import re


# =========================================
# LOAD PAPER
# =========================================

with open(
    "datasets/paragraphs.json",
    "r",
    encoding="utf-8"
) as f:
    paper = json.load(f)


# =========================================
# SECTION DETECTOR
# =========================================

def detect_section(text):

    text = text.strip()

    if not text:
        return None

    lower_text = text.lower()

    # Special sections
    if lower_text == "abstract":
        return "ABSTRACT"

    if lower_text in [
        "references",
        "bibliography"
    ]:
        return "REFERENCES"

    if lower_text in [
        "acknowledgments",
        "acknowledgements"
    ]:
        return "ACKNOWLEDGMENTS"

    # Numbered sections
    match = re.match(
        r"^(\d+(?:\.\d+)*)\.?\s+(.+)$",
        text
    )

    if match:

        title = match.group(2).strip()

        title = re.sub(
            r"[^A-Za-z0-9\s]",
            "",
            title
        )

        return title.upper().strip()

    return None


# =========================================
# ASSIGN SECTIONS
# =========================================

current_section = "UNKNOWN"

references_started = False


for page in paper["pages"]:

    for paragraph in page["paragraphs"]:

        text = paragraph.get(
            "text",
            ""
        ).strip()

        # ---------------------------------
        # Setelah REFERENCES dimulai,
        # semua isi berikutnya tetap REFERENCES
        # ---------------------------------

        if references_started:

            paragraph["section"] = "REFERENCES"

            continue


        # ---------------------------------
        # Heading
        # ---------------------------------

        if paragraph.get("type") == "heading":

            detected = detect_section(text)

            if detected:

                current_section = detected

                if detected == "REFERENCES":

                    references_started = True


        paragraph["section"] = current_section


# =========================================
# SAVE
# =========================================

output_path = (
    "datasets/structured_paper.json"
)


with open(
    output_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        paper,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================
# PRINT RESULT
# =========================================

print("====================================")
print("SECTION DETECTION")
print("====================================")

for page in paper["pages"]:

    for paragraph in page["paragraphs"]:

        section = paragraph.get(
            "section",
            "UNKNOWN"
        )

        if (
            section != "UNKNOWN"
            and paragraph.get("type") == "heading"
        ):

            print(
                f"Page {page['page']} | "
                f"{section} | "
                f"{paragraph['text'][:100]}"
            )


print()
print("Berhasil disimpan ke:")
print(output_path)