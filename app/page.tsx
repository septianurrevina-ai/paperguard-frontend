"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

// ============================================================
// REACT-PDF
// ============================================================

const Document = dynamic(
  () => import("react-pdf").then((mod) => mod.Document),
  {
    ssr: false,
  }
);

const Page = dynamic(
  () => import("react-pdf").then((mod) => mod.Page),
  {
    ssr: false,
  }
);

import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

// ============================================================
// API
// ============================================================

const API_URL = "http://127.0.0.1:8000";

// ============================================================
// TYPES
// ============================================================

type HighlightRect = {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
};

type HighlightWord = {
  text: string;
  bbox: number[];
};

type Highlight = {
  page: number;
  rect: HighlightRect;
  words?: HighlightWord[];
};

type Location = {
  page: number;
  section: string;
  paragraph: number;
};

type Finding = {
  finding_id: string;
  category: string;
  issue_type: string;
  severity: string;
  status: string;
  problematic_text: string;
  reason: string;
  recommendation: string;
  confidence: number;
  location: Location | null;
  highlight: Highlight | null;
  highlight_status: string;
};

type ReviewData = {
  paper_id: string;
  title: string;
  total_findings: number;
  highlights_found: number;
  highlights_not_found: number;
  findings: Finding[];
};

// ============================================================
// SEVERITY
// ============================================================

const severityConfig: Record<
  string,
  {
    label: string;
    color: string;
    background: string;
    border: string;
  }
> = {
  CRITICAL: {
    label: "Perlu segera diperiksa",
    color: "#b42318",
    background: "#fff1f0",
    border: "#f4b8b3",
  },

  MAJOR: {
    label: "Perlu diperhatikan",
    color: "#b54708",
    background: "#fff7ed",
    border: "#fed7aa",
  },

  MINOR: {
    label: "Perbaikan kecil",
    color: "#9a6700",
    background: "#fffbea",
    border: "#f4d58d",
  },

  SUGGESTION: {
    label: "Saran",
    color: "#175cd3",
    background: "#eff8ff",
    border: "#b2ddff",
  },
};

function getSeverityStyle(severity: string) {
  return (
    severityConfig[severity] ||
    severityConfig.MINOR
  );
}

// ============================================================
// CATEGORY
// ============================================================

function getCategoryLabel(category: string) {
  const labels: Record<string, string> = {
    LANGUAGE: "Bahasa",
    STRUCTURE: "Struktur",
    CONSISTENCY: "Konsistensi",
    METHODOLOGY: "Metodologi",
    RESULTS: "Hasil",
    DISCUSSION: "Pembahasan",
    CITATIONS: "Sitasi",
    FIGURES_TABLES: "Tabel & Gambar",
    COMPLETENESS: "Kelengkapan",
  };

  return labels[category] || category;
}

// ============================================================
// ISSUE TYPE
// ============================================================

function getIssueLabel(issueType: string) {
  const labels: Record<string, string> = {
    GRAMMAR: "Tata bahasa",
    TYPO: "Typo",
    SPELLING: "Ejaan",
    CLARITY: "Kejelasan",
    STRUCTURE: "Struktur",
    CONSISTENCY: "Konsistensi",
    UNSUPPORTED_CLAIM: "Klaim tanpa dukungan",
    MISSING_INFORMATION: "Informasi belum lengkap",
  };

  return labels[issueType] || issueType;
}

// ============================================================
// MAIN
// ============================================================

export default function Home() {
  const [data, setData] =
    useState<ReviewData | null>(null);

  const [selectedFinding, setSelectedFinding] =
    useState<Finding | null>(null);

  const [numPages, setNumPages] =
    useState<number>(0);

  const [currentPage, setCurrentPage] =
    useState<number>(1);

  const [pageSize, setPageSize] =
    useState<{
      width: number;
      height: number;
      scale: number;
    } | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [filter, setFilter] =
    useState("ALL");

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [isDragging, setIsDragging] =
    useState(false);

  const [reviewStarted, setReviewStarted] =
    useState(false);

  const [reviewStatus, setReviewStatus] =
    useState(
      "Mempersiapkan paper..."
    );

  const [pdfReady, setPdfReady] =
    useState(false);

  /*
   * Digunakan untuk memaksa browser
   * mengambil PDF terbaru setelah upload.
   */
  const [pdfVersion, setPdfVersion] =
    useState<number>(0);

  const fileInputRef =
    useRef<HTMLInputElement | null>(null);

  // ==========================================================
  // PDF.JS WORKER
  // ==========================================================

  useEffect(() => {
    let mounted = true;

    async function setupPdfWorker() {
      try {
        const { pdfjs } =
          await import("react-pdf");

        if (!mounted) {
          return;
        }

        pdfjs.GlobalWorkerOptions.workerSrc =
          `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

        setPdfReady(true);
      } catch (err) {
        console.error(
          "Gagal menyiapkan PDF.js:",
          err
        );

        setError(
          "PDF viewer gagal disiapkan."
        );
      }
    }

    setupPdfWorker();

    return () => {
      mounted = false;
    };
  }, []);

  // ==========================================================
  // FILE
  // ==========================================================

  function handleFileSelect(
    file: File | null
  ) {
    if (!file) {
      return;
    }

    setError("");

    const isPdf =
      file.type === "application/pdf" ||
      file.name
        .toLowerCase()
        .endsWith(".pdf");

    if (!isPdf) {
      setError(
        "Untuk saat ini PaperGuard hanya menerima file PDF."
      );
      return;
    }

    setSelectedFile(file);
  }

  function handleFileInput(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const file =
      event.target.files?.[0] || null;

    handleFileSelect(file);
  }

  function handleDrop(
    event: React.DragEvent<HTMLDivElement>
  ) {
    event.preventDefault();

    setIsDragging(false);

    const file =
      event.dataTransfer.files?.[0] ||
      null;

    handleFileSelect(file);
  }

  // ==========================================================
  // START REVIEW
  // ==========================================================

  async function startReview() {
    if (!selectedFile) {
      setError(
        "Silakan pilih file paper terlebih dahulu."
      );
      return;
    }

    try {
      setLoading(true);
      setReviewStarted(true);
      setError("");

      setData(null);
      setSelectedFinding(null);
      setCurrentPage(1);
      setNumPages(0);
      setPageSize(null);

      setReviewStatus(
        "Mengunggah paper..."
      );

      const formData =
        new FormData();

      formData.append(
        "file",
        selectedFile
      );

      setReviewStatus(
        "Membaca isi paper..."
      );

      const response =
        await fetch(
          `${API_URL}/upload`,
          {
            method: "POST",
            body: formData,
          }
        );

      if (!response.ok) {
        const text =
          await response.text();

        throw new Error(
          text ||
            `HTTP ${response.status}`
        );
      }

      setReviewStatus(
        "AI sedang melakukan screening..."
      );

      const result =
        await response.json();

      console.log(
        "PAPERGUARD RESULT:",
        result
      );

      if (
        !result ||
        !Array.isArray(
          result.findings
        )
      ) {
        throw new Error(
          "Response backend tidak memiliki findings yang valid."
        );
      }

      setReviewStatus(
        "Menentukan lokasi temuan..."
      );

      setData(result);

      /*
       * Pastikan PDF yang ditampilkan
       * adalah PDF hasil upload terbaru.
       */
      setPdfVersion(
        Date.now()
      );

      if (
        result.findings.length > 0
      ) {
        const firstFinding =
          result.findings[0];

        setSelectedFinding(
          firstFinding
        );

        if (
          firstFinding.location?.page
        ) {
          setCurrentPage(
            firstFinding.location.page
          );
        }
      }

      setReviewStatus(
        "Screening selesai."
      );
    } catch (err) {
      console.error(
        "PaperGuard error:",
        err
      );

      setError(
        "Paper gagal diproses. Pastikan backend PaperGuard dan Langflow sedang berjalan."
      );

      setReviewStarted(false);
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // RESET
  // ==========================================================

  function resetToLanding() {
    setData(null);
    setSelectedFinding(null);
    setSelectedFile(null);

    setReviewStarted(false);

    setError("");

    setCurrentPage(1);
    setNumPages(0);
    setPageSize(null);

    setPdfVersion(
      Date.now()
    );

    if (
      fileInputRef.current
    ) {
      fileInputRef.current.value =
        "";
    }
  }

  // ==========================================================
  // PDF DOCUMENT LOAD
  // ==========================================================

  function handleDocumentLoadSuccess({
    numPages,
  }: {
    numPages: number;
  }) {
    console.log(
      "PDF loaded:",
      numPages,
      "pages"
    );

    setNumPages(numPages);

    /*
     * Kalau halaman yang dipilih melebihi
     * jumlah halaman PDF terbaru,
     * kembalikan ke halaman 1.
     */
    setCurrentPage(
      (page) =>
        page > numPages
          ? 1
          : page
    );
  }

  // ==========================================================
  // PDF PAGE LOAD
  // ==========================================================

  function handlePageLoad(
    page: any
  ) {
    const viewport =
      page.getViewport({
        scale: 1,
      });

    const PDF_WIDTH =
      800;

    const scale =
      PDF_WIDTH /
      viewport.width;

    setPageSize({
      width:
        viewport.width,
      height:
        viewport.height,
      scale,
    });
  }

  // ==========================================================
  // FINDING
  // ==========================================================

  function selectFinding(
    finding: Finding
  ) {
    setSelectedFinding(
      finding
    );

    if (
      finding.location?.page
    ) {
      setCurrentPage(
        finding.location.page
      );
    }
  }

  // ==========================================================
  // FILTER
  // ==========================================================

  const filteredFindings =
    data?.findings.filter(
      (finding) => {
        if (
          filter === "ALL"
        ) {
          return true;
        }

        return (
          finding.severity ===
          filter
        );
      }
    ) || [];

  // ==========================================================
  // COUNTS
  // ==========================================================

  const minorCount =
    data?.findings.filter(
      (item) =>
        item.severity ===
        "MINOR"
    ).length || 0;

  const majorCount =
    data?.findings.filter(
      (item) =>
        item.severity ===
        "MAJOR"
    ).length || 0;

  // ==========================================================
  // HIGHLIGHT
  //
  // PENTING:
  // Jangan lagi menggunakan satu rect besar
  // kalau backend menyediakan words.
  //
  // Kita gambar highlight per kata berdasarkan
  // bbox asli dari PyMuPDF.
  // ==========================================================

  function renderHighlight() {
    if (
      !selectedFinding?.highlight ||
      !pageSize
    ) {
      return null;
    }

    const highlight =
      selectedFinding.highlight;

    if (
      highlight.page !==
      currentPage
    ) {
      return null;
    }

    /*
     * Prioritas utama:
     * highlight.words
     */
    const words =
      highlight.words || [];

    if (
      words.length > 0
    ) {
      return (
        <>
          {words.map(
            (word, index) => {
              const bbox =
                word.bbox;

              if (
                !bbox ||
                bbox.length < 4
              ) {
                return null;
              }

              const x0 =
                Number(bbox[0]);

              const y0 =
                Number(bbox[1]);

              const x1 =
                Number(bbox[2]);

              const y1 =
                Number(bbox[3]);

              const left =
                x0 *
                pageSize.scale;

              const top =
                y0 *
                pageSize.scale;

              const width =
                (x1 - x0) *
                pageSize.scale;

              const height =
                (y1 - y0) *
                pageSize.scale;

              if (
                width <= 0 ||
                height <= 0
              ) {
                return null;
              }

              return (
                <div
                  key={`${selectedFinding.finding_id}-word-${index}`}
                  style={{
                    position:
                      "absolute",

                    left,

                    top,

                    width,

                    height,

                    background:
                      "rgba(239, 68, 68, 0.22)",

                    border:
                      "1px solid rgba(220, 38, 38, 0.75)",

                    borderRadius: 2,

                    pointerEvents:
                      "none",

                    zIndex: 20,

                    boxSizing:
                      "border-box",
                  }}
                />
              );
            }
          )}
        </>
      );
    }

    /*
     * Fallback:
     * kalau backend belum memberikan words,
     * gunakan rect keseluruhan.
     */
    const rect =
      highlight.rect;

    if (!rect) {
      return null;
    }

    const left =
      rect.x0 *
      pageSize.scale;

    const top =
      rect.y0 *
      pageSize.scale;

    const width =
      (rect.x1 -
        rect.x0) *
      pageSize.scale;

    const height =
      (rect.y1 -
        rect.y0) *
      pageSize.scale;

    if (
      width <= 0 ||
      height <= 0
    ) {
      return null;
    }

    return (
      <div
        style={{
          position:
            "absolute",

          left,

          top,

          width,

          height,

          background:
            "rgba(239, 68, 68, 0.22)",

          border:
            "2px solid rgba(220, 38, 38, 0.85)",

          borderRadius: 4,

          pointerEvents:
            "none",

          zIndex: 20,

          boxSizing:
            "border-box",
        }}
      />
    );
  }

  // ==========================================================
  // LANDING PAGE
  // ==========================================================

  if (
    !data &&
    !reviewStarted
  ) {
    return (
      <main
        style={{
          minHeight:
            "100vh",

          background:
            "linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #ffffff 100%)",

          color:
            "#101828",

          fontFamily:
            "Inter, Arial, Helvetica, sans-serif",
        }}
      >
        {/* NAVBAR */}

        <header
          style={{
            padding:
              "22px 32px",

            borderBottom:
              "1px solid rgba(234,236,240,0.8)",

            background:
              "rgba(255,255,255,0.75)",

            backdropFilter:
              "blur(12px)",
          }}
        >
          <div
            style={{
              maxWidth:
                1180,

              margin:
                "0 auto",

              display:
                "flex",

              alignItems:
                "center",

              justifyContent:
                "space-between",
            }}
          >
            <div
              style={{
                display:
                  "flex",

                alignItems:
                  "center",

                gap: 11,
              }}
            >
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 13,
                  background:
                    "#111827",
                  color:
                    "white",
                  display:
                    "flex",
                  alignItems:
                    "center",
                  justifyContent:
                    "center",
                  fontWeight: 800,
                  fontSize: 20,
                }}
              >
                P
              </div>

              <div>
                <div
                  style={{
                    fontWeight: 800,
                    fontSize: 18,
                  }}
                >
                  PaperGuard
                </div>

                <div
                  style={{
                    fontSize: 11,
                    color:
                      "#667085",
                  }}
                >
                  Academic Paper Screening
                </div>
              </div>
            </div>

            <div
              style={{
                fontSize: 13,
                color:
                  "#667085",
              }}
            >
              AI-assisted paper review
            </div>
          </div>
        </header>

        {/* HERO */}

        <section
          style={{
            maxWidth:
              1180,

            margin:
              "0 auto",

            padding:
              "80px 32px 70px",
          }}
        >
          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "1.05fr 0.95fr",

              gap: 60,

              alignItems:
                "center",
            }}
          >
            {/* LEFT */}

            <div>
              <div
                style={{
                  display:
                    "inline-flex",

                  alignItems:
                    "center",

                  gap: 7,

                  padding:
                    "7px 11px",

                  borderRadius:
                    30,

                  background:
                    "#ffffff",

                  border:
                    "1px solid #e4e7ec",

                  fontSize: 11,

                  fontWeight: 700,

                  color:
                    "#475467",

                  marginBottom:
                    22,
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius:
                      "50%",
                    background:
                      "#12b76a",
                  }}
                />

                AI-Powered Academic Review
              </div>

              <h1
                style={{
                  fontSize:
                    "clamp(42px, 5vw, 68px)",

                  lineHeight:
                    1.02,

                  letterSpacing:
                    "-3px",

                  margin: 0,

                  maxWidth:
                    680,
                }}
              >
                Temukan masalah
                <br />

                <span
                  style={{
                    color:
                      "#dc2626",
                  }}
                >
                  sebelum reviewer
                </span>{" "}
                menemukannya.
              </h1>

              <p
                style={{
                  fontSize: 17,

                  lineHeight:
                    1.7,

                  color:
                    "#667085",

                  maxWidth:
                    590,

                  margin:
                    "24px 0 30px",
                }}
              >
                PaperGuard membantu memeriksa
                paper akademik dari sisi bahasa,
                konsistensi, struktur,
                metodologi, hasil, dan bagian
                lain yang perlu diperhatikan.
              </p>

              <div
                style={{
                  display:
                    "flex",

                  gap: 10,

                  flexWrap:
                    "wrap",
                }}
              >
                {[
                  "✓ Bahasa",
                  "✓ Konsistensi",
                  "✓ Metodologi",
                ].map(
                  (item) => (
                    <span
                      key={item}
                      style={{
                        padding:
                          "8px 12px",

                        borderRadius:
                          8,

                        background:
                          "rgba(255,255,255,0.8)",

                        border:
                          "1px solid #e4e7ec",

                        fontSize: 12,

                        color:
                          "#475467",
                      }}
                    >
                      {item}
                    </span>
                  )
                )}
              </div>
            </div>

            {/* UPLOAD CARD */}

            <div
              style={{
                background:
                  "rgba(255,255,255,0.92)",

                border:
                  "1px solid #e4e7ec",

                borderRadius:
                  24,

                padding:
                  28,

                boxShadow:
                  "0 25px 70px rgba(16,24,40,0.10)",
              }}
            >
              <div
                style={{
                  marginBottom:
                    18,
                }}
              >
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 750,
                  }}
                >
                  Mulai screening paper
                </div>

                <div
                  style={{
                    fontSize: 12,
                    color:
                      "#667085",
                    marginTop: 5,
                  }}
                >
                  Upload paper kamu dalam format PDF.
                </div>
              </div>

              {/* DROPZONE */}

              <div
                onDragOver={(
                  event
                ) => {
                  event.preventDefault();
                  setIsDragging(
                    true
                  );
                }}
                onDragLeave={() =>
                  setIsDragging(
                    false
                  )
                }
                onDrop={
                  handleDrop
                }
                onClick={() =>
                  fileInputRef.current?.click()
                }
                style={{
                  border:
                    isDragging
                      ? "2px dashed #dc2626"
                      : "2px dashed #d0d5dd",

                  background:
                    isDragging
                      ? "#fff5f5"
                      : "#f9fafb",

                  borderRadius:
                    17,

                  padding:
                    "35px 22px",

                  textAlign:
                    "center",

                  cursor:
                    "pointer",

                  transition:
                    "all 0.2s ease",
                }}
              >
                <input
                  ref={
                    fileInputRef
                  }
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={
                    handleFileInput
                  }
                  style={{
                    display:
                      "none",
                  }}
                />

                <div
                  style={{
                    width: 54,
                    height: 54,
                    borderRadius: 16,
                    margin:
                      "0 auto 14px",
                    display:
                      "flex",
                    alignItems:
                      "center",
                    justifyContent:
                      "center",
                    background:
                      "#fee2e2",
                    fontSize: 25,
                  }}
                >
                  📄
                </div>

                {selectedFile ? (
                  <>
                    <div
                      style={{
                        fontWeight:
                          700,
                        fontSize: 14,
                        color:
                          "#101828",
                        wordBreak:
                          "break-word",
                      }}
                    >
                      {
                        selectedFile.name
                      }
                    </div>

                    <div
                      style={{
                        marginTop:
                          5,
                        fontSize:
                          11,
                        color:
                          "#667085",
                      }}
                    >
                      {(
                        selectedFile.size /
                        1024 /
                        1024
                      ).toFixed(
                        2
                      )}{" "}
                      MB
                    </div>
                  </>
                ) : (
                  <>
                    <div
                      style={{
                        fontWeight:
                          700,
                        fontSize:
                          14,
                      }}
                    >
                      Pilih paper kamu
                    </div>

                    <div
                      style={{
                        marginTop:
                          5,
                        fontSize:
                          12,
                        color:
                          "#667085",
                      }}
                    >
                      Klik di sini atau drag & drop file PDF
                    </div>
                  </>
                )}
              </div>

              {error && (
                <div
                  style={{
                    marginTop:
                      12,

                    padding:
                      11,

                    borderRadius:
                      10,

                    background:
                      "#fff1f0",

                    border:
                      "1px solid #f4b8b3",

                    color:
                      "#b42318",

                    fontSize:
                      12,
                  }}
                >
                  {error}
                </div>
              )}

              <button
                onClick={
                  startReview
                }
                disabled={
                  !selectedFile ||
                  loading
                }
                style={{
                  width:
                    "100%",

                  marginTop:
                    16,

                  border:
                    "none",

                  borderRadius:
                    12,

                  padding:
                    "13px 18px",

                  background:
                    selectedFile &&
                    !loading
                      ? "#111827"
                      : "#d0d5dd",

                  color:
                    "white",

                  fontSize:
                    13,

                  fontWeight:
                    700,

                  cursor:
                    selectedFile &&
                    !loading
                      ? "pointer"
                      : "default",
                }}
              >
                {loading
                  ? "Sedang memproses..."
                  : "Mulai Screening Paper →"}
              </button>

              <div
                style={{
                  marginTop:
                    13,

                  textAlign:
                    "center",

                  fontSize:
                    10,

                  color:
                    "#98a2b3",
                }}
              >
                Format yang didukung: PDF
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}

        <section
          style={{
            maxWidth:
              1180,

            margin:
              "0 auto",

            padding:
              "20px 32px 80px",
          }}
        >
          <div
            style={{
              textAlign:
                "center",

              marginBottom:
                30,
            }}
          >
            <div
              style={{
                fontSize:
                  11,

                fontWeight:
                  800,

                color:
                  "#98a2b3",

                letterSpacing:
                  "1px",
              }}
            >
              HOW PAPERGUARD WORKS
            </div>

            <h2
              style={{
                margin:
                  "8px 0 0",

                fontSize:
                  28,

                letterSpacing:
                  "-0.8px",
              }}
            >
              Dari paper menjadi insight
            </h2>
          </div>

          <div
            style={{
              display:
                "grid",

              gridTemplateColumns:
                "repeat(3, 1fr)",

              gap:
                16,
            }}
          >
            <FeatureCard
              number="01"
              icon="📄"
              title="Upload paper"
              description="Masukkan paper akademik yang ingin kamu periksa."
            />

            <FeatureCard
              number="02"
              icon="🔎"
              title="AI screening"
              description="PaperGuard menganalisis berbagai bagian paper untuk menemukan masalah."
            />

            <FeatureCard
              number="03"
              icon="🔴"
              title="Review findings"
              description="Temuan ditandai langsung pada dokumen dan dilengkapi alasan serta saran."
            />
          </div>
        </section>

        <footer
          style={{
            borderTop:
              "1px solid #eaecf0",

            padding:
              "22px 32px",

            textAlign:
              "center",

            color:
              "#98a2b3",

            fontSize:
              11,
          }}
        >
          PaperGuard · Academic Paper Screening Assistant
        </footer>
      </main>
    );
  }

  // ==========================================================
  // REVIEW PROCESS
  // ==========================================================

  if (
    reviewStarted &&
    !data
  ) {
    return (
      <main
        style={{
          minHeight:
            "100vh",

          background:
            "linear-gradient(135deg, #f8fafc, #eef2ff)",

          display:
            "flex",

          alignItems:
            "center",

          justifyContent:
            "center",

          fontFamily:
            "Inter, Arial, Helvetica, sans-serif",

          color:
            "#101828",

          padding:
            30,
        }}
      >
        <div
          style={{
            width:
              "min(520px, 100%)",

            background:
              "white",

            border:
              "1px solid #eaecf0",

            borderRadius:
              24,

            padding:
              36,

            textAlign:
              "center",

            boxShadow:
              "0 25px 70px rgba(16,24,40,0.10)",
          }}
        >
          <div
            style={{
              width:
                70,

              height:
                70,

              borderRadius:
                22,

              background:
                "#fee2e2",

              display:
                "flex",

              alignItems:
                "center",

              justifyContent:
                "center",

              fontSize:
                30,

              margin:
                "0 auto 20px",
            }}
          >
            🔎
          </div>

          <h1
            style={{
              margin:
                0,

              fontSize:
                24,
            }}
          >
            PaperGuard sedang bekerja
          </h1>

          <p
            style={{
              margin:
                "10px 0 25px",

              color:
                "#667085",

              fontSize:
                13,
            }}
          >
            Paper kamu sedang dianalisis.
            Jangan tutup halaman ini.
          </p>

          <div
            style={{
              height:
                8,

              background:
                "#f2f4f7",

              borderRadius:
                20,

              overflow:
                "hidden",
            }}
          >
            <div
              style={{
                height:
                  "100%",

                width:
                  "70%",

                background:
                  "#dc2626",

                borderRadius:
                  20,

                animation:
                  "paperGuardProgress 1.5s ease-in-out infinite alternate",
              }}
            />
          </div>

          <div
            style={{
              marginTop:
                18,

              fontSize:
                13,

              fontWeight:
                600,

              color:
                "#344054",
            }}
          >
            {reviewStatus}
          </div>

          <style jsx>{`
            @keyframes paperGuardProgress {
              from {
                transform: translateX(-35%);
              }

              to {
                transform: translateX(45%);
              }
            }
          `}</style>
        </div>
      </main>
    );
  }

  // ==========================================================
  // MAIN REVIEW
  // ==========================================================

  if (!data) {
    return null;
  }

  const pdfUrl =
    `${API_URL}/current-paper?v=${pdfVersion}`;

  return (
    <main
      style={{
        minHeight:
          "100vh",

        background:
          "#f7f8fa",

        color:
          "#101828",

        fontFamily:
          "Inter, Arial, Helvetica, sans-serif",
      }}
    >
      {/* TOP BAR */}

      <header
        style={{
          background:
            "white",

          borderBottom:
            "1px solid #eaecf0",

          padding:
            "14px 32px",

          position:
            "sticky",

          top:
            0,

          zIndex:
            100,
        }}
      >
        <div
          style={{
            maxWidth:
              1500,

            margin:
              "0 auto",

            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "space-between",

            gap:
              20,
          }}
        >
          <div
            style={{
              display:
                "flex",

              alignItems:
                "center",

              gap:
                11,
            }}
          >
            <div
              style={{
                width:
                  38,

                height:
                  38,

                borderRadius:
                  11,

                background:
                  "#111827",

                color:
                  "white",

                display:
                  "flex",

                alignItems:
                  "center",

                justifyContent:
                  "center",

                fontWeight:
                  800,
              }}
            >
              P
            </div>

            <div>
              <div
                style={{
                  fontWeight:
                    750,

                  fontSize:
                    17,
                }}
              >
                PaperGuard
              </div>

              <div
                style={{
                  fontSize:
                    10,

                  color:
                    "#98a2b3",
                }}
              >
                Academic Paper Screening
              </div>
            </div>
          </div>

          <button
            onClick={
              resetToLanding
            }
            style={{
              border:
                "1px solid #d0d5dd",

              background:
                "white",

              borderRadius:
                9,

              padding:
                "8px 12px",

              fontSize:
                12,

              fontWeight:
                600,

              color:
                "#344054",

              cursor:
                "pointer",
            }}
          >
            ← Screening paper lain
          </button>
        </div>
      </header>

      <div
        style={{
          maxWidth:
            1500,

          margin:
            "0 auto",

          padding:
            "24px 32px 40px",
        }}
      >
        {/* TITLE */}

        <div
          style={{
            marginBottom:
              20,
          }}
        >
          <div
            style={{
              fontSize:
                11,

              fontWeight:
                700,

              color:
                "#98a2b3",

              letterSpacing:
                "0.7px",
            }}
          >
            HASIL SCREENING
          </div>

          <h1
            style={{
              margin:
                "5px 0 0",

              fontSize:
                26,

              letterSpacing:
                "-0.7px",
            }}
          >
            Temukan bagian paper yang perlu diperbaiki
          </h1>

          <p
            style={{
              margin:
                "6px 0 0",

              color:
                "#667085",

              fontSize:
                13,
            }}
          >
            PaperGuard menemukan{" "}
            <strong>
              {data.total_findings}
            </strong>{" "}
            bagian yang perlu kamu periksa.
          </p>
        </div>

        {/* SUMMARY */}

        <div
          style={{
            display:
              "grid",

            gridTemplateColumns:
              "repeat(3, minmax(0, 1fr))",

            gap:
              12,

            marginBottom:
              18,
          }}
        >
          <SummaryCard
            value={
              data.total_findings
            }
            label="Bagian ditemukan"
            description="Temuan dari AI"
            color="#111827"
          />

          <SummaryCard
            value={
              minorCount
            }
            label="Perbaikan kecil"
            description="Typo & tata bahasa"
            color="#9a6700"
          />

          <SummaryCard
            value={
              majorCount
            }
            label="Perlu perhatian"
            description="Masalah lebih penting"
            color="#b54708"
          />
        </div>

        {/* MAIN GRID */}

        <div
          style={{
            display:
              "grid",

            gridTemplateColumns:
              "300px minmax(500px, 1fr) 330px",

            gap:
              15,

            alignItems:
              "start",
          }}
        >
          {/* FINDINGS */}

          <aside
            style={{
              background:
                "white",

              border:
                "1px solid #eaecf0",

              borderRadius:
                15,

              overflow:
                "hidden",

              position:
                "sticky",

              top:
                75,
            }}
          >
            <div
              style={{
                padding:
                  "16px 16px 12px",

                borderBottom:
                  "1px solid #eaecf0",
              }}
            >
              <strong
                style={{
                  fontSize:
                    14,
                }}
              >
                Yang perlu diperiksa
              </strong>

              <div
                style={{
                  fontSize:
                    11,

                  color:
                    "#98a2b3",

                  marginTop:
                    3,
                }}
              >
                {
                  filteredFindings.length
                }{" "}
                bagian
              </div>

              <div
                style={{
                  display:
                    "flex",

                  gap:
                    5,

                  marginTop:
                    12,

                  flexWrap:
                    "wrap",
                }}
              >
                {[
                  ["ALL", "Semua"],
                  ["MINOR", "Kecil"],
                  ["MAJOR", "Perhatian"],
                  ["CRITICAL", "Penting"],
                ].map(
                  ([
                    value,
                    label,
                  ]) => (
                    <button
                      key={
                        value
                      }
                      onClick={() =>
                        setFilter(
                          value
                        )
                      }
                      style={{
                        border:
                          filter ===
                          value
                            ? "1px solid #111827"
                            : "1px solid #eaecf0",

                        background:
                          filter ===
                          value
                            ? "#111827"
                            : "white",

                        color:
                          filter ===
                          value
                            ? "white"
                            : "#667085",

                        borderRadius:
                          20,

                        padding:
                          "5px 9px",

                        fontSize:
                          10,

                        cursor:
                          "pointer",
                      }}
                    >
                      {
                        label
                      }
                    </button>
                  )
                )}
              </div>
            </div>

            <div
              style={{
                maxHeight:
                  "calc(100vh - 250px)",

                overflowY:
                  "auto",
              }}
            >
              {filteredFindings.map(
                (
                  finding
                ) => {
                  const active =
                    selectedFinding?.finding_id ===
                    finding.finding_id;

                  const severity =
                    getSeverityStyle(
                      finding.severity
                    );

                  return (
                    <button
                      key={
                        finding.finding_id
                      }
                      onClick={() =>
                        selectFinding(
                          finding
                        )
                      }
                      style={{
                        width:
                          "100%",

                        border:
                          "none",

                        borderBottom:
                          "1px solid #f2f4f7",

                        textAlign:
                          "left",

                        padding:
                          13,

                        background:
                          active
                            ? "#f9fafb"
                            : "white",

                        cursor:
                          "pointer",

                        position:
                          "relative",
                      }}
                    >
                      {active && (
                        <div
                          style={{
                            position:
                              "absolute",

                            left:
                              0,

                            top:
                              0,

                            bottom:
                              0,

                            width:
                              3,

                            background:
                              severity.color,
                          }}
                        />
                      )}

                      <div
                        style={{
                          display:
                            "flex",

                          justifyContent:
                            "space-between",

                          gap:
                            8,
                        }}
                      >
                        <span
                          style={{
                            fontSize:
                              10,

                            fontWeight:
                              700,

                            color:
                              "#98a2b3",
                          }}
                        >
                          {
                            finding.finding_id
                          }
                        </span>

                        <span
                          style={{
                            fontSize:
                              9,

                            fontWeight:
                              700,

                            color:
                              severity.color,

                            background:
                              severity.background,

                            border:
                              `1px solid ${severity.border}`,

                            borderRadius:
                              20,

                            padding:
                              "3px 6px",
                          }}
                        >
                          {
                            severity.label
                          }
                        </span>
                      </div>

                      <div
                        style={{
                          marginTop:
                            6,

                          fontSize:
                            11,

                          color:
                            "#667085",
                        }}
                      >
                        {
                          getCategoryLabel(
                            finding.category
                          )
                        }{" "}
                        ·{" "}
                        {
                          getIssueLabel(
                            finding.issue_type
                          )
                        }
                      </div>

                      <div
                        style={{
                          marginTop:
                            6,

                          fontSize:
                            12,

                          lineHeight:
                            1.45,

                          color:
                            "#344054",
                        }}
                      >
                        {
                          finding.problematic_text
                        }
                      </div>

                      {finding.location && (
                        <div
                          style={{
                            marginTop:
                              6,

                            fontSize:
                              10,

                            color:
                              "#98a2b3",
                          }}
                        >
                          Halaman{" "}
                          {
                            finding
                              .location
                              .page
                          }
                        </div>
                      )}
                    </button>
                  );
                }
              )}
            </div>
          </aside>

          {/* PDF */}

          <section
            style={{
              background:
                "#e9eaec",

              border:
                "1px solid #eaecf0",

              borderRadius:
                15,

              overflow:
                "hidden",

              minWidth:
                0,
            }}
          >
            <div
              style={{
                height:
                  58,

                background:
                  "white",

                borderBottom:
                  "1px solid #eaecf0",

                display:
                  "flex",

                alignItems:
                  "center",

                justifyContent:
                  "center",

                gap:
                  10,
              }}
            >
              <button
                onClick={() =>
                  setCurrentPage(
                    (page) =>
                      Math.max(
                        1,
                        page - 1
                      )
                  )
                }
                disabled={
                  currentPage <=
                  1
                }
                style={{
                  width:
                    33,

                  height:
                    33,

                  border:
                    "1px solid #eaecf0",

                  background:
                    "white",

                  borderRadius:
                    8,

                  cursor:
                    currentPage <=
                    1
                      ? "default"
                      : "pointer",
                }}
              >
                ←
              </button>

              <div
                style={{
                  padding:
                    "7px 13px",

                  background:
                    "#f9fafb",

                  border:
                    "1px solid #eaecf0",

                  borderRadius:
                    8,

                  fontSize:
                    11,

                  fontWeight:
                    600,

                  color:
                    "#475467",
                }}
              >
                Halaman{" "}
                {currentPage}{" "}
                /{" "}
                {numPages}
              </div>

              <button
                onClick={() =>
                  setCurrentPage(
                    (page) =>
                      Math.min(
                        numPages,
                        page + 1
                      )
                  )
                }
                disabled={
                  currentPage >=
                  numPages
                }
                style={{
                  width:
                    33,

                  height:
                    33,

                  border:
                    "1px solid #eaecf0",

                  background:
                    "white",

                  borderRadius:
                    8,

                  cursor:
                    currentPage >=
                    numPages
                      ? "default"
                      : "pointer",
                }}
              >
                →
              </button>
            </div>

            <div
              style={{
                padding:
                  "24px 18px 30px",

                overflow:
                  "auto",
              }}
            >
              <div
                style={{
                  display:
                    "flex",

                  justifyContent:
                    "center",
                }}
              >
                <div
                  style={{
                    position:
                      "relative",

                    width:
                      pageSize
                        ? pageSize.width *
                          pageSize.scale
                        : 800,

                    minHeight:
                      pageSize
                        ? pageSize.height *
                          pageSize.scale
                        : 1000,

                    background:
                      "white",

                    boxShadow:
                      "0 8px 30px rgba(16,24,40,0.12)",
                  }}
                >
                  {pdfReady ? (
                    <Document
                      file={
                        pdfUrl
                      }
                      onLoadSuccess={
                        handleDocumentLoadSuccess
                      }
                      onLoadError={(
                        error
                      ) => {
                        console.error(
                          "PDF load error:",
                          error
                        );

                        setError(
                          "PDF gagal ditampilkan."
                        );
                      }}
                      loading={
                        <div
                          style={{
                            background:
                              "white",

                            padding:
                              60,

                            textAlign:
                              "center",

                            color:
                              "#667085",
                          }}
                        >
                          Membuka dokumen...
                        </div>
                      }
                    >
                      <Page
                        pageNumber={
                          currentPage
                        }
                        width={
                          800
                        }
                        onLoadSuccess={
                          handlePageLoad
                        }
                        renderTextLayer={
                          true
                        }
                        renderAnnotationLayer={
                          true
                        }
                      />
                    </Document>
                  ) : (
                    <div
                      style={{
                        background:
                          "white",

                        padding:
                          60,

                        textAlign:
                          "center",

                        color:
                          "#667085",
                      }}
                    >
                      Menyiapkan PDF viewer...
                    </div>
                  )}

                  {/* HIGHLIGHT */}

                  {renderHighlight()}
                </div>
              </div>
            </div>
          </section>

          {/* DETAIL */}

          <aside
            style={{
              background:
                "white",

              border:
                "1px solid #eaecf0",

              borderRadius:
                15,

              padding:
                19,

              position:
                "sticky",

              top:
                75,
            }}
          >
            {selectedFinding ? (
              <>
                {(() => {
                  const severity =
                    getSeverityStyle(
                      selectedFinding.severity
                    );

                  return (
                    <>
                      <div
                        style={{
                          display:
                            "flex",

                          justifyContent:
                            "space-between",

                          alignItems:
                            "center",

                          gap:
                            8,
                        }}
                      >
                        <span
                          style={{
                            fontSize:
                              10,

                            color:
                              "#98a2b3",

                            fontWeight:
                              700,
                          }}
                        >
                          {
                            selectedFinding.finding_id
                          }
                        </span>

                        <span
                          style={{
                            color:
                              severity.color,

                            background:
                              severity.background,

                            border:
                              `1px solid ${severity.border}`,

                            borderRadius:
                              20,

                            padding:
                              "4px 8px",

                            fontSize:
                              9,

                            fontWeight:
                              700,
                          }}
                        >
                          {
                            severity.label
                          }
                        </span>
                      </div>

                      <h2
                        style={{
                          margin:
                            "9px 0 4px",

                          fontSize:
                            18,

                          letterSpacing:
                            "-0.3px",
                        }}
                      >
                        {
                          getIssueLabel(
                            selectedFinding.issue_type
                          )
                        }
                      </h2>

                      <div
                        style={{
                          fontSize:
                            11,

                          color:
                            "#667085",
                        }}
                      >
                        {
                          getCategoryLabel(
                            selectedFinding.category
                          )
                        }
                      </div>

                      <DetailSection
                        title="Bagian yang perlu diperiksa"
                      >
                        <div
                          style={{
                            background:
                              "rgba(239, 68, 68, 0.08)",

                            border:
                              "1px solid rgba(220,38,38,0.22)",

                            borderLeft:
                              "4px solid #dc2626",

                            borderRadius:
                              10,

                            padding:
                              12,

                            color:
                              "#344054",

                            fontSize:
                              12,

                            lineHeight:
                              1.55,

                            wordBreak:
                              "break-word",
                          }}
                        >
                          “
                          {
                            selectedFinding.problematic_text
                          }
                          ”
                        </div>
                      </DetailSection>

                      <DetailSection
                        title="Kenapa?"
                      >
                        <p
                          style={{
                            margin:
                              0,

                            fontSize:
                              12,

                            lineHeight:
                              1.6,

                            color:
                              "#475467",
                          }}
                        >
                          {
                            selectedFinding.reason
                          }
                        </p>
                      </DetailSection>

                      <DetailSection
                        title="Saran perbaikan"
                      >
                        <div
                          style={{
                            display:
                              "flex",

                            gap:
                              9,

                            background:
                              "#f0fdf4",

                            border:
                              "1px solid #bbf7d0",

                            borderRadius:
                              10,

                            padding:
                              12,
                          }}
                        >
                          <span>
                            ✓
                          </span>

                          <p
                            style={{
                              margin:
                                0,

                              fontSize:
                                12,

                              lineHeight:
                                1.6,

                              color:
                                "#344054",
                            }}
                          >
                            {
                              selectedFinding.recommendation
                            }
                          </p>
                        </div>
                      </DetailSection>

                      {selectedFinding.location && (
                        <div
                          style={{
                            marginTop:
                              18,

                            paddingTop:
                              15,

                            borderTop:
                              "1px solid #eaecf0",
                          }}
                        >
                          <div
                            style={{
                              fontSize:
                                10,

                              color:
                                "#98a2b3",

                              marginBottom:
                                5,
                            }}
                          >
                            LOKASI
                          </div>

                          <div
                            style={{
                              fontSize:
                                12,

                              color:
                                "#344054",

                              lineHeight:
                                1.6,
                            }}
                          >
                            <strong>
                              Halaman{" "}
                              {
                                selectedFinding
                                  .location
                                  .page
                              }
                            </strong>

                            <br />

                            {
                              selectedFinding
                                .location
                                .section
                            }
                          </div>
                        </div>
                      )}

                      <div
                        style={{
                          marginTop:
                            16,

                          padding:
                            10,

                          background:
                            "#f9fafb",

                          borderRadius:
                            9,

                          fontSize:
                            10,

                          color:
                            "#667085",
                        }}
                      >
                        AI yakin sekitar{" "}
                        <strong>
                          {Math.round(
                            selectedFinding.confidence *
                              100
                          )}
                          %
                        </strong>{" "}
                        bahwa bagian ini perlu diperiksa.
                      </div>
                    </>
                  );
                })()}
              </>
            ) : (
              <div
                style={{
                  textAlign:
                    "center",

                  padding:
                    "50px 15px",

                  color:
                    "#667085",
                }}
              >
                Pilih salah satu temuan.
              </div>
            )}
          </aside>
        </div>
      </div>
    </main>
  );
}

// ============================================================
// SUMMARY CARD
// ============================================================

function SummaryCard({
  value,
  label,
  description,
  color,
}: {
  value: number;
  label: string;
  description: string;
  color: string;
}) {
  return (
    <div
      style={{
        background:
          "white",

        border:
          "1px solid #eaecf0",

        borderRadius:
          13,

        padding:
          15,
      }}
    >
      <div
        style={{
          fontSize:
            23,

          fontWeight:
            750,

          color,
        }}
      >
        {value}
      </div>

      <div
        style={{
          marginTop:
            3,

          fontSize:
            12,

          fontWeight:
            650,

          color:
            "#344054",
        }}
      >
        {label}
      </div>

      <div
        style={{
          marginTop:
            3,

          fontSize:
            10,

          color:
            "#98a2b3",
        }}
      >
        {description}
      </div>
    </div>
  );
}

// ============================================================
// FEATURE CARD
// ============================================================

function FeatureCard({
  number,
  icon,
  title,
  description,
}: {
  number: string;
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div
      style={{
        background:
          "rgba(255,255,255,0.85)",

        border:
          "1px solid #eaecf0",

        borderRadius:
          17,

        padding:
          22,
      }}
    >
      <div
        style={{
          display:
            "flex",

          justifyContent:
            "space-between",

          alignItems:
            "center",

          marginBottom:
            20,
        }}
      >
        <div
          style={{
            width:
              42,

            height:
              42,

            borderRadius:
              12,

            background:
              "#f3f4f6",

            display:
              "flex",

            alignItems:
              "center",

            justifyContent:
              "center",

            fontSize:
              20,
          }}
        >
          {icon}
        </div>

        <span
          style={{
            fontSize:
              11,

            color:
              "#98a2b3",

            fontWeight:
              800,
          }}
        >
          {number}
        </span>
      </div>

      <h3
        style={{
          margin:
            "0 0 7px",

          fontSize:
            16,
        }}
      >
        {title}
      </h3>

      <p
        style={{
          margin:
            0,

          color:
            "#667085",

          fontSize:
            12,

          lineHeight:
            1.6,
        }}
      >
        {description}
      </p>
    </div>
  );
}

// ============================================================
// DETAIL SECTION
// ============================================================

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        marginTop:
          20,
      }}
    >
      <div
        style={{
          fontSize:
            10,

          fontWeight:
            750,

          color:
            "#667085",

          marginBottom:
            7,

          letterSpacing:
            "0.4px",
        }}
      >
        {title.toUpperCase()}
      </div>

      {children}
    </div>
  );
}