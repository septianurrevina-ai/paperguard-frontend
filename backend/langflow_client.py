import os
import json
import requests
import pymupdf
import unicodedata

def normalize_pdf_text(text):
    text = unicodedata.normalize("NFKC", text)

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

    return text
from dotenv import load_dotenv

def make_langflow_safe(text):
    """
    Memastikan teks tidak mengandung karakter
    yang gagal diproses oleh encoding Windows.
    """

    return text.encode("cp1252", errors="replace").decode("cp1252")

load_dotenv()

LANGFLOW_API_KEY = os.getenv("LANGFLOW_API_KEY")

FLOW_ID = "dec6471d-021e-41b4-9f74-2d7afcaaa95e"

LANGFLOW_URL = (
    f"http://localhost:7860/api/v1/run/{FLOW_ID}"
)

PDF_PATH = "datasets/current_paper.pdf"


def extract_pdf_text(pdf_path):
    """Mengambil dan menormalisasi seluruh teks dari PDF."""

    doc = pymupdf.open(pdf_path)

    pages = []

    for page_number, page in enumerate(doc, start=1):
        text = page.get_text("text")

        if text.strip():
            text = normalize_pdf_text(text)

            pages.append(
                f"[PAGE {page_number}]\n{text}"
            )

    doc.close()

    return "\n\n".join(pages)


def review_with_langflow(paper_text):
    """Mengirim teks paper ke Langflow."""

    if not LANGFLOW_API_KEY:
        raise RuntimeError(
            "LANGFLOW_API_KEY belum ditemukan di .env"
        )

    safe_text = make_langflow_safe(paper_text)

    payload = {
        "output_type": "chat",
        "input_type": "chat",
        "input_value": safe_text,
    }

    headers = {
        "x-api-key": LANGFLOW_API_KEY,
        "Content-Type": "application/json",
    }

    response = requests.post(
        LANGFLOW_URL,
        json=payload,
        headers=headers,
        timeout=300,
    )

    if response.status_code != 200:
        print("\n=== LANGFLOW ERROR ===")
        print("STATUS:", response.status_code)
        print(response.text)
        return None

    data = response.json()

    return extract_langflow_text(data)


def extract_langflow_text(data):
    """Mengambil teks hasil dari response Langflow."""

    try:
        return data["outputs"][0]["outputs"][0]["results"]["message"]["text"]
    except (KeyError, IndexError, TypeError):
        pass

    try:
        return data["outputs"][0]["outputs"][0]["messages"][0]["message"]
    except (KeyError, IndexError, TypeError):
        pass

    raise RuntimeError(
        "Format response Langflow tidak dikenali:\n"
        + json.dumps(data, indent=2)
    )


if __name__ == "__main__":
    print("=== PAPERGUARD → LANGFLOW ===")
    print(f"PDF: {PDF_PATH}")
    print()

    print("[1/2] Membaca PDF...")
    paper_text = extract_pdf_text(PDF_PATH)
    print(f"Berhasil mengambil {len(paper_text):,} karakter.")
    print()

    print("[2/2] Mengirim paper ke Langflow...")
    print("Mohon tunggu...")
    print()

    result = review_with_langflow(paper_text)

    if result is None:
        print("Langflow gagal mengembalikan hasil.")
        raise SystemExit(1)

    print("=== LANGFLOW RESULT ===")
    print(result)

    # Simpan hasil Langflow ke JSON
    output_path = "datasets/langflow_findings.json"

    try:
        findings = json.loads(result)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(findings, f, ensure_ascii=False, indent=2)

        print()
        print("=== BERHASIL DISIMPAN ===")
        print(f"File: {output_path}")
        print(f"Jumlah findings: {len(findings)}")

    except json.JSONDecodeError as e:
        print()
        print("Hasil Langflow bukan JSON yang valid.")
        print(f"Error: {e}")