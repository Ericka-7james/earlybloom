import React, { useEffect, useMemo, useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";

import CommonModal from "../common/CommonModal.jsx";
import BloomHire from "../../assets/bloombug/BloomHire.png";
import {
  saveAndVerifyResumeRecord,
  buildResumeUiCache,
  cacheResumeUiState,
  parseResumeRecord,
  requireAuthenticatedSession,
} from "../../lib/resumes.js";

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url
).toString();

function isPdfFile(file) {
  if (!file) {
    return false;
  }

  const isPdfMimeType = file.type === "application/pdf";
  const hasPdfExtension = file.name.toLowerCase().endsWith(".pdf");

  return isPdfMimeType || hasPdfExtension;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "Unknown size";
  }

  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const kb = bytes / 1024;
  if (kb < 1024) {
    return `${Math.round(kb)} KB`;
  }

  const mb = kb / 1024;
  return `${mb.toFixed(mb >= 10 ? 0 : 1)} MB`;
}

function formatParseStatus(parseStatus) {
  if (!parseStatus) {
    return "No status yet";
  }

  return String(parseStatus)
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

async function extractPdfText(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const pageTexts = [];

  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const textContent = await page.getTextContent();

    const pageText = textContent.items
      .map((item) => ("str" in item ? item.str : ""))
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();

    if (pageText) {
      pageTexts.push(pageText);
    }
  }

  return pageTexts.join("\n\n").trim();
}

function ResumeUploadModal({
  isOpen,
  onClose,
  onResumeSaved,
  resumeFile = null,
}) {
  const [resumeError, setResumeError] = useState("");
  const [isSavingResume, setIsSavingResume] = useState(false);
  const [selectedFileMeta, setSelectedFileMeta] = useState(null);
  const [uploadState, setUploadState] = useState("idle");
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      setResumeError("");
      setIsSavingResume(false);
      setSelectedFileMeta(null);
      setUploadState("idle");
    }
  }, [isOpen]);

  const currentResumeSummary = useMemo(() => {
    if (!resumeFile) {
      return null;
    }

    return {
      name: resumeFile.name || "Saved resume",
      parseStatus: formatParseStatus(resumeFile.parseStatus),
      uploadedAt: resumeFile.uploadedAt || null,
      fileSizeLabel: resumeFile.size ? formatFileSize(resumeFile.size) : null,
    };
  }, [resumeFile]);

  async function persistResumeFile(file) {
    setIsSavingResume(true);
    setUploadState("processing");
    setResumeError("");
    setSelectedFileMeta({
      name: file.name,
      sizeLabel: formatFileSize(file.size),
    });

    try {
      const rawText = await extractPdfText(file);

      if (!rawText) {
        throw new Error("No extractable text found in PDF.");
      }

      await requireAuthenticatedSession();

      const savedResume = await saveAndVerifyResumeRecord({
        originalFilename: file.name,
        fileSizeBytes: file.size,
        fileType: file.type || "application/pdf",
        parseStatus: "pending",
        rawText: null,
        parsedJson: null,
        parseWarnings: [],
      });

      const parseResult = await parseResumeRecord({
        resumeId: savedResume.id,
        rawText,
        fileType: file.type || "application/pdf",
        extractionMethod: "pdfjs_text",
      });

      const cachedResume = buildResumeUiCache(file, {
        ...savedResume,
        parse_status: parseResult.parse_status,
      });

      cacheResumeUiState(cachedResume);
      setUploadState("success");
      setResumeError("");
      onResumeSaved?.(cachedResume);
    } catch (error) {
      console.error("Failed to save or parse resume:", error);
      setUploadState("error");
      setResumeError(
        error?.message ||
          "We couldn't process your resume right now. Please try again."
      );
    } finally {
      setIsSavingResume(false);
    }
  }

  async function handleResumeFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    if (!isPdfFile(file)) {
      setUploadState("error");
      setResumeError("Please upload a PDF resume.");
      setSelectedFileMeta({
        name: file.name,
        sizeLabel: formatFileSize(file.size),
      });
      event.target.value = "";
      return;
    }

    await persistResumeFile(file);
    event.target.value = "";
  }

  async function handleResumeDrop(event) {
    event.preventDefault();

    if (isSavingResume) {
      return;
    }

    const file = event.dataTransfer.files?.[0];

    if (!file) {
      return;
    }

    if (!isPdfFile(file)) {
      setUploadState("error");
      setResumeError("Please upload a PDF resume.");
      setSelectedFileMeta({
        name: file.name,
        sizeLabel: formatFileSize(file.size),
      });
      return;
    }

    await persistResumeFile(file);
  }

  function handleResumeDragOver(event) {
    event.preventDefault();
  }

  function handleClose() {
    if (isSavingResume) {
      return;
    }

    setResumeError("");
    setSelectedFileMeta(null);
    setUploadState("idle");
    onClose?.();
  }

  const hasSavedResume = Boolean(currentResumeSummary);
  const showSuccessMessage = uploadState === "success" && !resumeError;
  const showErrorMessage = uploadState === "error" && Boolean(resumeError);

  return (
    <CommonModal
      isOpen={isOpen}
      title="Upload your resume"
      onClose={handleClose}
      size="sm"
      iconImage={BloomHire}
      iconAlt="EarlyBloom resume upload icon"
    >
      <div
        className="resume-upload-modal"
        style={{ display: "grid", gap: "1rem" }}
      >
        <div style={{ display: "grid", gap: "0.45rem" }}>
          <p className="card-title">Make your search feel more tailored</p>
          <p className="card-copy">
            Upload a PDF resume so EarlyBloom can personalize your job flow and
            show cleaner resume signals.
          </p>
        </div>

        {hasSavedResume ? (
          <div
            className="section-card section-card--soft"
            style={{ gap: "0.75rem", padding: "1rem" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: "0.75rem",
                alignItems: "flex-start",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: "0.25rem", minWidth: 0 }}>
                <p className="section-label">Current resume</p>
                <p
                  className="card-title"
                  style={{
                    fontSize: "1rem",
                    overflowWrap: "anywhere",
                  }}
                >
                  {currentResumeSummary.name}
                </p>
              </div>

              <span className="tag-chip">
                {currentResumeSummary.parseStatus}
              </span>
            </div>

            <div
              style={{
                display: "flex",
                gap: "0.5rem",
                flexWrap: "wrap",
                alignItems: "center",
              }}
            >
              {currentResumeSummary.fileSizeLabel ? (
                <span className="card-meta">
                  {currentResumeSummary.fileSizeLabel}
                </span>
              ) : null}
              {currentResumeSummary.uploadedAt ? (
                <span className="card-meta">
                  Saved {new Date(currentResumeSummary.uploadedAt).toLocaleDateString()}
                </span>
              ) : null}
            </div>
          </div>
        ) : null}

        <button
          type="button"
          className="filter-trigger-card"
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleResumeDrop}
          onDragOver={handleResumeDragOver}
          disabled={isSavingResume}
          aria-busy={isSavingResume}
          style={{
            padding: "1rem",
            gap: "0.65rem",
          }}
        >
          <span className="filter-trigger-card__label">
            {isSavingResume
              ? "Processing your resume..."
              : hasSavedResume
                ? "Replace resume"
                : "Choose a PDF resume"}
          </span>

          <span className="filter-trigger-card__value">
            Drag and drop a file here, or tap to browse.
          </span>

          <span className="filter-trigger-card__meta">
            PDF only. Cleaner text extraction works best with text-based PDFs.
          </span>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="resume-upload-modal__input"
          onChange={handleResumeFileChange}
          disabled={isSavingResume}
          hidden
        />

        {selectedFileMeta ? (
          <div
            className="section-card"
            style={{ gap: "0.45rem", padding: "0.9rem 1rem" }}
          >
            <p className="section-label">
              {isSavingResume ? "Selected file" : "Latest selection"}
            </p>
            <p
              className="card-title"
              style={{ fontSize: "1rem", overflowWrap: "anywhere" }}
            >
              {selectedFileMeta.name}
            </p>
            <p className="card-meta">{selectedFileMeta.sizeLabel}</p>
          </div>
        ) : null}

        {uploadState === "idle" && !resumeError && !selectedFileMeta ? (
          <div className="status-message-card status-message-card--info">
            <p className="status-message-card__title">Ready to upload</p>
            <p className="status-message-card__copy">
              We’ll extract text from your PDF and save it to your account when
              you’re signed in.
            </p>
          </div>
        ) : null}

        {uploadState === "processing" ? (
          <div
            className="status-message-card status-message-card--info"
            role="status"
            aria-live="polite"
          >
            <p className="status-message-card__title">Processing resume</p>
            <p className="status-message-card__copy">
              Extracting text, saving your file record, and preparing resume
              signals.
            </p>
          </div>
        ) : null}

        {showSuccessMessage ? (
          <div
            className="status-message-card status-message-card--success"
            aria-live="polite"
          >
            <p className="status-message-card__title">Resume uploaded</p>
            <p className="status-message-card__copy">
              {selectedFileMeta?.name
                ? `${selectedFileMeta.name} is ready and your tracker can refresh its resume signals.`
                : "Your resume was uploaded successfully."}
            </p>
          </div>
        ) : null}

        {showErrorMessage ? (
          <div
            className="status-message-card status-message-card--error"
            role="alert"
          >
            <p className="status-message-card__title">Upload problem</p>
            <p className="status-message-card__copy">{resumeError}</p>
          </div>
        ) : null}

        <div
          style={{
            display: "flex",
            gap: "0.75rem",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <p className="card-meta" style={{ margin: 0 }}>
            {isSavingResume
              ? "Please keep this window open while we process your file."
              : "You can replace your resume anytime."}
          </p>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="button button--secondary"
              onClick={handleClose}
              disabled={isSavingResume}
            >
              {showSuccessMessage ? "Done" : "Close"}
            </button>
          </div>
        </div>
      </div>
    </CommonModal>
  );
}

export default ResumeUploadModal;