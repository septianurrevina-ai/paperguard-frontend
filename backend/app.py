import json
import os
import shutil
import subprocess
import sys

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASETS_DIR = os.path.join(
    BASE_DIR,
    "datasets"
)

CURRENT_PAPER_PATH = os.path.join(
    DATASETS_DIR,
    "current_paper.pdf"
)

OUTPUT_FILE = os.path.join(
    DATASETS_DIR,
    "paper_findings_with_highlights.json"
)


# ============================================================
# INTERMEDIATE FILES
# ============================================================

PIPELINE_FILES = [
    "extracted_text.json",
    "parsed_paper.json",
    "structured_paper.json",
    "langflow_findings.json",
    "paper_findings.json",
    "paper_findings_with_locations.json",
    "paper_findings_with_highlights.json",
]


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="PaperGuard API",
    description="AI-powered academic paper review API",
    version="0.2.1"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "app": "PaperGuard",
        "status": "running",
        "version": "0.2.1",
        "engine": "Langflow + Gemini"
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": "PaperGuard"
    }


# ============================================================
# GET REVIEW RESULT
# ============================================================

@app.get("/review")
def get_review():

    if not os.path.exists(OUTPUT_FILE):
        raise HTTPException(
            status_code=404,
            detail="Hasil review belum tersedia."
        )

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


# ============================================================
# CURRENT PAPER
# ============================================================

@app.get("/current-paper")
def get_current_paper():

    if not os.path.exists(CURRENT_PAPER_PATH):
        raise HTTPException(
            status_code=404,
            detail="Current paper belum tersedia."
        )

    return FileResponse(
        CURRENT_PAPER_PATH,
        media_type="application/pdf",
        filename="current_paper.pdf"
    )


# ============================================================
# FINDINGS
# ============================================================

@app.get("/findings")
def get_findings():

    if not os.path.exists(OUTPUT_FILE):
        raise HTTPException(
            status_code=404,
            detail="Belum ada hasil review."
        )

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


# ============================================================
# CLEAN OLD PIPELINE OUTPUTS
# ============================================================

def clean_pipeline_outputs():

    print()
    print("Membersihkan hasil review sebelumnya...")

    for filename in PIPELINE_FILES:

        path = os.path.join(
            DATASETS_DIR,
            filename
        )

        if os.path.exists(path):

            try:
                os.remove(path)

                print(
                    f"  Removed: {filename}"
                )

            except Exception as e:

                print(
                    f"  Tidak bisa menghapus "
                    f"{filename}: {e}"
                )

    print()


# ============================================================
# RUN PYTHON SCRIPT
# ============================================================

def run_script(
    script_relative_path,
    *arguments
):

    script_path = os.path.join(
        BASE_DIR,
        script_relative_path
    )

    if not os.path.exists(script_path):
        raise RuntimeError(
            f"Script tidak ditemukan: "
            f"{script_relative_path}"
        )

    command = [
        sys.executable,
        "-X",
        "utf8",
        script_path,
        *arguments
    ]

    print()
    print("------------------------------------")
    print(
        f"RUNNING: {script_relative_path}"
    )
    print("------------------------------------")

    # --------------------------------------------------------
    # FORCE UTF-8 FOR WINDOWS SUBPROCESS
    # --------------------------------------------------------

    environment = os.environ.copy()

    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"

    process = subprocess.run(
        command,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment
    )

    if process.stdout:
        print(process.stdout)

    if process.stderr:
        print(process.stderr)

    if process.returncode != 0:

        raise RuntimeError(
            f"Pipeline gagal pada "
            f"{script_relative_path}\n\n"
            f"STDOUT:\n"
            f"{process.stdout}\n\n"
            f"STDERR:\n"
            f"{process.stderr}"
        )

    return {
        "script": script_relative_path,
        "return_code": process.returncode,
        "stdout": process.stdout[-3000:],
        "stderr": process.stderr[-3000:]
    }


# ============================================================
# VALIDATE PDF
# ============================================================

def validate_pdf(filename):

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension != ".pdf":

        raise HTTPException(
            status_code=400,
            detail=(
                "Untuk sementara PaperGuard "
                "hanya menerima file PDF."
            )
        )


# ============================================================
# RUN COMPLETE PAPERGUARD PIPELINE
# ============================================================

def run_paperguard_pipeline():

    results = []

    # ========================================================
    # 0. CLEAN OLD RESULTS
    # ========================================================

    clean_pipeline_outputs()

    # ========================================================
    # 1. EXTRACT PDF
    # ========================================================

    results.append(
        run_script(
            "datasets/extract_pdf.py",
            CURRENT_PAPER_PATH
        )
    )

    # ========================================================
    # 2. PARSE PDF
    # ========================================================

    results.append(
        run_script(
            "datasets/parse_pdf.py"
        )
    )

    # ========================================================
    # 3. BUILD PARAGRAPHS
    # ========================================================

    results.append(
        run_script(
            "datasets/build_paragraphs.py"
        )
    )

    # ========================================================
    # 4. DETECT SECTIONS
    # ========================================================

    results.append(
        run_script(
            "backend/section_detector.py"
        )
    )

    # ========================================================
    # 5. LANGFLOW + GEMINI
    # ========================================================

    print()
    print("------------------------------------")
    print("AI REVIEW ENGINE")
    print("------------------------------------")
    print("Engine: Langflow + Gemini")
    print()

    results.append(
        run_script(
            "backend/langflow_client.py"
        )
    )

    # ========================================================
    # 6. LANGFLOW ADAPTER
    # ========================================================

    results.append(
        run_script(
            "backend/langflow_adapter.py"
        )
    )

    # ========================================================
    # 7. LOCATION RESOLVER
    # ========================================================

    results.append(
        run_script(
            "backend/location_resolver.py"
        )
    )

    # ========================================================
    # 8. HIGHLIGHT LOCATOR
    # ========================================================

    results.append(
        run_script(
            "backend/highlight_locator.py"
        )
    )

    # ========================================================
    # VERIFY FINAL OUTPUT
    # ========================================================

    if not os.path.exists(OUTPUT_FILE):

        raise RuntimeError(
            "Output review tidak ditemukan:\n"
            f"{OUTPUT_FILE}"
        )

    with open(
        OUTPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        review_result = json.load(f)

    findings = review_result.get(
        "findings",
        []
    )

    total_findings = review_result.get(
        "total_findings",
        len(findings)
    )

    highlights_found = review_result.get(
        "highligdkskhts_found",
        0
    )

    highlights_not_found = review_result.get(
        "highlights_not_found",
        0
    )

    return {
        "status": "success",
        "total_findings": total_findings,
        "highlights_found": highlights_found,
        "highlights_not_found": highlights_not_found,
        "findings": findings,
        "pipeline": {
            "engine": "Langflow + Gemini",
            "steps_completed": [
                "PDF extraction",
                "PDF parsing",
                "Paragraph building",
                "Section detection",
                "AI review with Langflow + Gemini",
                "Finding normalization",
                "Location resolving",
                "Highlight locating"
            ]
        }
    }


# ============================================================
# POST /review
# ============================================================

@app.post("/review")
async def review_paper(
    file: UploadFile = File(...)
):

    filename = file.filename or ""

    validate_pdf(filename)

    try:

        # ----------------------------------------------------
        # SAVE PDF
        # ----------------------------------------------------

        os.makedirs(
            DATASETS_DIR,
            exist_ok=True
        )

        with open(
            CURRENT_PAPER_PATH,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        print()
        print("====================================")
        print("PAPERGUARD REVIEW")
        print("====================================")
        print(
            f"File: {filename}"
        )
        print(
            f"Saved: {CURRENT_PAPER_PATH}"
        )
        print("====================================")

        # ----------------------------------------------------
        # RUN PIPELINE
        # ----------------------------------------------------

        result = run_paperguard_pipeline()

        # ----------------------------------------------------
        # ADD FILE INFO
        # ----------------------------------------------------

        result["filename"] = filename

        print()
        print("====================================")
        print("PAPERGUARD REVIEW SELESAI")
        print("====================================")
        print(
            f"Total findings: "
            f"{result['total_findings']}"
        )
        print(
            f"Highlights found: "
            f"{result['highlights_found']}"
        )
        print(
            f"Highlights not found: "
            f"{result['highlights_not_found']}"
        )
        print("====================================")
        print()

        return result

    except HTTPException:
        raise

    except Exception as e:

        print()
        print("====================================")
        print("PAPERGUARD ERROR")
        print("====================================")
        print(str(e))
        print("====================================")
        print()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

@app.post("/upload")
async def upload_paper(
    file: UploadFile = File(...)
):

    return await review_paper(file)


# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "backend.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )