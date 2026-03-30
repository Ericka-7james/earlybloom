import React, { useRef, useState } from "react";
import CommonModal from "../common/CommonModal.jsx";
import BloomHire from "../../assets/bloombug/BloomHire.png";
import {
  saveResumeRecord,
  buildResumeUiCache,
  cacheResumeUiState,
} from "../../lib/resumes";

function isPdfFile(file) {
  if (!file) {
    return false;
  }

  const isPdfMimeType = file.type === "application/pdf";
  const hasPdfExtension = file.name.toLowerCase().endsWith(".pdf");

  return isPdfMimeType || hasPdfExtension;
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
      const savedResume = await saveResumeRecord({
        originalFilename: file.name,
        fileSizeBytes: file.size,
        fileType: file.type || "application/pdf",
        parseStatus: "pending",
        rawText: null,
        parsedJson: null,
        parseWarnings: [],
      });

      const cachedResume = buildResumeUiCache(file, savedResume);

      cacheResumeUiState(cachedResume);
      setResumeError("");
      onResumeSaved?.(cachedResume);
    } catch (error) {
      console.error("Failed to save resume record:", error);
      setResumeError("We couldn't save your resume right now. Please try again.");
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
            {isSavingResume ? "Saving..." : "Upload file"}
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