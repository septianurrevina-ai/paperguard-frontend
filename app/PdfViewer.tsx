"use client";

import { Document, Page, pdfjs } from "react-pdf";

import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";

pdfjs.GlobalWorkerOptions.workerSrc =
  `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

type PdfViewerProps = {
  file: string;
  pageNumber: number;
  onDocumentLoadSuccess: (data: {
    numPages: number;
  }) => void;
  onPageLoad: (page: {
    getViewport: (options: {
      scale: number;
    }) => {
      width: number;
      height: number;
    };
  }) => void;
};

export default function PdfViewer({
  file,
  pageNumber,
  onDocumentLoadSuccess,
  onPageLoad,
}: PdfViewerProps) {
  return (
    <Document
      file={file}
      onLoadSuccess={onDocumentLoadSuccess}
      loading={
        <div
          style={{
            background: "white",
            padding: 60,
            textAlign: "center",
            color: "#667085",
          }}
        >
          Membuka dokumen...
        </div>
      }
      error={
        <div
          style={{
            background: "white",
            padding: 30,
            color: "#b42318",
            textAlign: "center",
          }}
        >
          PDF gagal dibuka. Silakan coba unggah ulang.
        </div>
      }
    >
      <Page
        pageNumber={pageNumber}
        width={800}
        onLoadSuccess={onPageLoad}
      />
    </Document>
  );
}