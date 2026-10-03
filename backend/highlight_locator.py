import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

import fitz


PDF_PATH = "datasets/current_paper.pdf"
FINDINGS_PATH = "datasets/paper_findings_with_locations.json"
OUTPUT_PATH = "datasets/paper_findings_with_highlights.json"


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text)

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    ligatures = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\ufb05": "st",
        "\ufb06": "st",
    }

    for old, new in ligatures.items():
        text = text.replace(
            old,
            new
        )

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
        text = text.replace(
            old,
            new
        )

    # Gabungkan whitespace
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_word(text):
    """
    Normalisasi khusus untuk satu token.
    """
    return normalize_text(
        text
    ).lower()


# ============================================================
# LOAD JSON
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
# TOKENIZATION
# ============================================================

def tokenize(text):
    normalized = normalize_text(
        text
    )

    if not normalized:
        return []

    return normalized.split()


# ============================================================
# BUILD PAGE WORD STRUCTURE
# ============================================================

def get_page_blocks(page):
    """
    Mengambil words dari PDF dan mengelompokkannya berdasarkan
    block_no.

    Struktur word PyMuPDF:

    x0, y0, x1, y1, text,
    block_no, line_no, word_no

    Pengelompokan berdasarkan block penting supaya pencarian
    tidak lompat ke kolom/paragraf lain.
    """

    words = page.get_text(
        "words"
    )

    if not words:
        return []

    blocks = {}

    for word in words:

        if len(word) < 8:
            continue

        x0, y0, x1, y1 = (
            word[0],
            word[1],
            word[2],
            word[3],
        )

        text = word[4]
        block_no = word[5]
        line_no = word[6]
        word_no = word[7]

        normalized = normalize_word(
            text
        )

        if not normalized:
            continue

        block = blocks.setdefault(
            block_no,
            {
                "block_no": block_no,
                "words": [],
            }
        )

        block["words"].append(
            {
                "original": text,
                "normalized": normalized,
                "bbox": [
                    x0,
                    y0,
                    x1,
                    y1,
                ],
                "line_no": line_no,
                "word_no": word_no,
            }
        )

    result = []

    for block in blocks.values():

        block["words"].sort(
            key=lambda item: (
                item["line_no"],
                item["word_no"],
            )
        )

        result.append(
            block
        )

    result.sort(
        key=lambda block: (
            min(
                word["bbox"][1]
                for word in block["words"]
            ),
            min(
                word["bbox"][0]
                for word in block["words"]
            ),
        )
    )

    return result


# ============================================================
# CREATE BLOCK TEXT
# ============================================================

def block_text(block):
    return " ".join(
        word["normalized"]
        for word in block["words"]
    )


# ============================================================
# EXACT TOKEN MATCH
# ============================================================

def find_exact_sequences(
    block,
    target_tokens
):
    """
    Mencari sequence token secara berurutan
    hanya di dalam satu block.
    """

    words = block["words"]

    if not words:
        return []

    target_count = len(
        target_tokens
    )

    if target_count == 0:
        return []

    candidates = []

    for start in range(
        len(words)
    ):

        end = (
            start +
            target_count
        )

        if end > len(words):
            break

        sequence = words[
            start:end
        ]

        sequence_tokens = [
            word["normalized"]
            for word in sequence
        ]

        if (
            sequence_tokens ==
            target_tokens
        ):
            candidates.append(
                sequence
            )

    return candidates


# ============================================================
# FUZZY SEQUENCE MATCH
# ============================================================

def find_fuzzy_sequences(
    block,
    target_tokens
):
    """
    Fallback ketika PDF memecah teks sedikit berbeda.

    Contoh:

    target:
        "switch them off both"

    PDF:
        "switch them offboth"

    Kita tetap mencari kandidat yang paling mirip,
    tetapi tetap berada di dalam block yang sama.
    """

    words = block["words"]

    if not words:
        return []

    target_text = " ".join(
        target_tokens
    )

    target_count = len(
        target_tokens
    )

    # Berikan window sedikit lebih lebar
    min_window = max(
        1,
        target_count - 2
    )

    max_window = min(
        len(words),
        target_count + 3
    )

    candidates = []

    for window_size in range(
        min_window,
        max_window + 1
    ):

        for start in range(
            0,
            len(words) - window_size + 1
        ):

            sequence = words[
                start:start + window_size
            ]

            candidate_text = " ".join(
                word["normalized"]
                for word in sequence
            )

            ratio = SequenceMatcher(
                None,
                target_text,
                candidate_text,
            ).ratio()

            if ratio >= 0.72:
                candidates.append(
                    {
                        "words": sequence,
                        "score": ratio,
                    }
                )

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates


# ============================================================
# FIND BEST TEXT ON PAGE
# ============================================================

def find_text_on_page(
    page,
    problematic_text
):
    """
    Mencari lokasi problematic_text pada page.

    Strategi:

    1. Ambil semua text block.
    2. Cari exact token sequence dalam block yang sama.
    3. Jika tidak ditemukan, gunakan fuzzy matching.
    4. Pilih kandidat dengan skor terbaik.
    5. Jangan pernah mencocokkan sequence lintas block.
    """

    target_tokens = tokenize(
        problematic_text
    )

    if not target_tokens:
        return []

    blocks = get_page_blocks(
        page
    )

    if not blocks:
        return []

    # --------------------------------------------------------
    # PASS 1
    # EXACT MATCH
    # --------------------------------------------------------

    exact_candidates = []

    for block_index, block in enumerate(
        blocks
    ):

        matches = find_exact_sequences(
            block,
            target_tokens
        )

        for matched_words in matches:

            # Kandidat exact selalu sangat kuat.
            exact_candidates.append(
                {
                    "words": matched_words,
                    "score": 1.0,
                    "block_index": block_index,
                    "method": "exact_block",
                }
            )

    if exact_candidates:

        # Jika lebih dari satu exact match,
        # pilih kandidat dengan posisi paling masuk akal.
        #
        # Untuk paper akademik, kita prioritaskan
        # sequence yang lebih panjang dan berada
        # dalam satu block.
        exact_candidates.sort(
            key=lambda item: (
                len(item["words"]),
                -item["block_index"],
            ),
            reverse=True
        )

        return exact_candidates[0]["words"]

    # --------------------------------------------------------
    # PASS 2
    # FUZZY MATCH
    # --------------------------------------------------------

    fuzzy_candidates = []

    for block_index, block in enumerate(
        blocks
    ):

        matches = find_fuzzy_sequences(
            block,
            target_tokens
        )

        for match in matches:

            fuzzy_candidates.append(
                {
                    "words": match["words"],
                    "score": match["score"],
                    "block_index": block_index,
                    "method": "fuzzy_block",
                }
            )

    if not fuzzy_candidates:
        return []

    fuzzy_candidates.sort(
        key=lambda item: (
            item["score"],
            len(item["words"]),
        ),
        reverse=True
    )

    best = fuzzy_candidates[0]

    # Jangan mengambil fuzzy match yang terlalu lemah.
    if best["score"] < 0.78:
        return []

    return best["words"]


# ============================================================
# CREATE RECT
# ============================================================

def create_rect(words):
    if not words:
        return None

    x0 = min(
        word["bbox"][0]
        for word in words
    )

    y0 = min(
        word["bbox"][1]
        for word in words
    )

    x1 = max(
        word["bbox"][2]
        for word in words
    )

    y1 = max(
        word["bbox"][3]
        for word in words
    )

    return {
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
    }


# ============================================================
# PROCESS FINDING
# ============================================================

def process_finding(
    finding,
    document
):
    location = finding.get(
        "location"
    )

    problematic_text = finding.get(
        "problematic_text",
        ""
    )

    if not location:
        finding["highlight"] = None
        finding["highlight_status"] = (
            "NO_LOCATION"
        )
        return finding

    page_number = location.get(
        "page"
    )

    if not page_number:
        finding["highlight"] = None
        finding["highlight_status"] = (
            "NO_PAGE"
        )
        return finding

    page_index = (
        page_number - 1
    )

    if (
        page_index < 0
        or page_index >= len(document)
    ):
        finding["highlight"] = None
        finding["highlight_status"] = (
            "INVALID_PAGE"
        )
        return finding

    page = document[
        page_index
    ]

    matched_words = find_text_on_page(
        page,
        problematic_text
    )

    if not matched_words:

        finding["highlight"] = None

        finding["highlight_status"] = (
            "NOT_FOUND"
        )

        return finding

    rect = create_rect(
        matched_words
    )

    if not rect:

        finding["highlight"] = None

        finding["highlight_status"] = (
            "NOT_FOUND"
        )

        return finding

    finding["highlight"] = {
        "page": page_number,
        "rect": rect,
        "words": [
            {
                "text": word["original"],
                "bbox": word["bbox"],
            }
            for word in matched_words
        ],
    }

    finding["highlight_status"] = (
        "FOUND"
    )

    return finding


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 40)
    print("PAPERGUARD HIGHLIGHT LOCATOR")
    print("=" * 40)

    print()

    print(
        f"PDF: {PDF_PATH}"
    )

    print(
        f"Findings: {FINDINGS_PATH}"
    )

    print()

    findings_data = load_json(
        FINDINGS_PATH
    )

    if isinstance(
        findings_data,
        dict
    ):
        findings = findings_data.get(
            "findings",
            []
        )
    else:
        findings = findings_data

    print(
        f"Total findings: {len(findings)}"
    )

    print()

    # --------------------------------------------------------
    # OPEN PDF
    # --------------------------------------------------------

    if not os.path.exists(
        PDF_PATH
    ):
        raise FileNotFoundError(
            f"PDF tidak ditemukan: {PDF_PATH}"
        )

    document = fitz.open(
        PDF_PATH
    )

    print(
        f"Total halaman: {len(document)}"
    )

    print()

    # --------------------------------------------------------
    # PROCESS
    # --------------------------------------------------------

    processed = []

    found_count = 0
    not_found_count = 0

    for finding in findings:

        finding_copy = dict(
            finding
        )

        finding_copy = process_finding(
            finding_copy,
            document
        )

        processed.append(
            finding_copy
        )

        status = finding_copy.get(
            "highlight_status"
        )

        print(
            finding_copy.get(
                "finding_id",
                "UNKNOWN"
            )
        )

        print(
            "Text:",
            finding_copy.get(
                "problematic_text",
                ""
            )
        )

        if status == "FOUND":

            found_count += 1

            highlight = finding_copy[
                "highlight"
            ]

            print(
                "Highlight: FOUND"
            )

            print(
                "Method: block-based matching"
            )

            print(
                "Page:",
                highlight["page"]
            )

            print(
                "Rect:",
                highlight["rect"]
            )

        else:

            not_found_count += 1

            print(
                "Highlight:",
                status
            )

        print()

    document.close()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "paper_id": "current_paper",
        "title": "Current Paper",
        "total_findings": len(
            processed
        ),
        "highlights_found": found_count,
        "highlights_not_found": not_found_count,
        "findings": processed,
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

    print("=" * 40)
    print("SELESAI")
    print("=" * 40)

    print(
        f"Highlights ditemukan: {found_count}"
    )

    print(
        f"Highlights tidak ditemukan: {not_found_count}"
    )

    print()

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print("=" * 40)


if __name__ == "__main__":
    main()