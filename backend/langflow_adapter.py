import json
import os


INPUT_PATH = "datasets/langflow_findings.json"
OUTPUT_PATH = "datasets/paper_findings.json"


def load_findings():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"File tidak ditemukan: {INPUT_PATH}"
        )

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_findings(findings):
    normalized = []

    for index, finding in enumerate(findings, start=1):
        item = {
            "finding_id": f"PG-{index:03d}",
            "category": finding.get("category", "UNKNOWN"),
            "issue_type": finding.get("issue_type", "UNKNOWN"),
            "severity": finding.get("severity", "MINOR"),
            "status": "CONFIRMED",

            "problematic_text": finding.get(
                "problematic_text", ""
            ),

            "reason": finding.get(
                "reason", ""
            ),

            "recommendation": finding.get(
                "recommendation", ""
            ),

            "confidence": finding.get(
                "confidence", 0
            ),

            "location": None,
            "related_locations": [],
            "evidence": ""
        }

        normalized.append(item)

    return normalized


def save_findings(findings):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            findings,
            f,
            ensure_ascii=False,
            indent=2
        )


if __name__ == "__main__":
    print("=== LANGFLOW ADAPTER ===")
    print()

    print("[1/3] Membaca hasil Langflow...")
    findings = load_findings()
    print(f"Ditemukan {len(findings)} findings.")

    print()
    print("[2/3] Menyesuaikan format...")
    normalized = normalize_findings(findings)

    print()
    print("[3/3] Menyimpan hasil...")
    save_findings(normalized)

    print()
    print("=== BERHASIL ===")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Jumlah findings: {len(normalized)}")