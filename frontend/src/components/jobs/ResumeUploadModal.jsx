import React, { useRef, useState } from "react";
import * as pdfjsLib from "pdfjs-dist";

import CommonModal from "../common/CommonModal.jsx";
import BloomHire from "../../assets/bloombug/BloomHire.png";
import {
  saveResumeRecord,
  buildResumeUiCache,
  cacheResumeUiState,
  parseResumeRecord,
  getOptionalSession,
  cacheResumeRawText,
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
  const fileInputRef = useRef(null);

  async function persistResumeFile(file) {
    setIsSavingResume(true);

    try {
      const rawText = await extractPdfText(file);

      if (!rawText) {
        throw new Error("No extractable text found in PDF.");
      }

      const session = await getOptionalSession();

      if (!session) {
        const cachedResume = buildResumeUiCache(file, {
          id: null,
          parse_status: "local_only",
          isLocalOnly: true,
        });

        cacheResumeUiState(cachedResume);
        cacheResumeRawText(rawText);

        setResumeError("");
        onResumeSaved?.(cachedResume);
        return;
      }

      const savedResume = await saveResumeRecord({
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
      setResumeError("");
      onResumeSaved?.(cachedResume);
    } catch (error) {
      console.error("Failed to save or parse resume:", error);
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
      setResumeError("Please upload a PDF resume.");
      event.target.value = "";
      return;
    }

    setResumeError("");
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
      setResumeError("Please upload a PDF resume.");
      return;
    }

    setResumeError("");
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
    onClose?.();
  }

  return (
    <CommonModal
      isOpen={isOpen}
      title="Upload your resume"
      onClose={handleClose}
      size="sm"
      iconImage={BloomHire}
      iconAlt="EarlyBloom resume upload icon"
    >
      <div className="resume-upload-modal">
        <p className="resume-upload-modal__text">
          Upload your resume to personalize your job matches.
        </p>

        <button
          type="button"
          className="resume-upload-dropzone"
          onClick={() => fileInputRef.current?.click()}
          onDrop={handleResumeDrop}
          onDragOver={handleResumeDragOver}
          disabled={isSavingResume}
        >
          <span className="resume-upload-dropzone__label">
            {isSavingResume ? "Processing..." : "Upload file"}
          </span>
          <span className="resume-upload-dropzone__hint">PDF only</span>
        </button>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="resume-upload-modal__input"
          onChange={handleResumeFileChange}
          disabled={isSavingResume}
        />

        {resumeError ? (
          <p className="resume-upload-modal__error" role="alert">
            {resumeError}
          </p>
        ) : null}

        {resumeFile ? (
          <p className="resume-upload-modal__success" aria-live="polite">
            Saved resume: {resumeFile.name}
          </p>
        ) : null}
      </div>
    </CommonModal>
  );
}

export default ResumeUploadModal;