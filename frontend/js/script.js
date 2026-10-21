const documentInput = document.getElementById("document-input");
const browseButton = document.getElementById("browse-button");
const dropZone = document.getElementById("drop-zone");
const sanitizeButton = document.getElementById("sanitize-button");

const selectedFileCard = document.getElementById("selected-file");
const fileNameElement = document.getElementById("file-name");
const fileSizeElement = document.getElementById("file-size");

const progressCard = document.getElementById("progress-card");
const progressTitle = document.getElementById("progress-title");
const progressMessage = document.getElementById("progress-message");
const progressFill = document.getElementById("progress-fill");
const spinner = document.getElementById("spinner");

const resultCard = document.getElementById("result-card");
const resultMessage = document.getElementById("result-message");
const resultFilename = document.getElementById("result-filename");
const downloadButton = document.getElementById("download-button");

const errorCard = document.getElementById("error-card");
const errorMessage = document.getElementById("error-message");

const textInput = document.getElementById("text-input");
const browseTextButton = document.getElementById("browse-text-button");
const selectedTextFile = document.getElementById("selected-text-file");
const textFileName = document.getElementById("text-file-name");
const textFileSize = document.getElementById("text-file-size");
const reidentifyButton = document.getElementById("reidentify-button");

const reidentifyResult = document.getElementById("reidentify-result");
const reidentifyMessage = document.getElementById("reidentify-message");
const reidentifyFilename = document.getElementById("reidentify-filename");
const reidentifyDownload = document.getElementById("reidentify-download");

const reidentifyError = document.getElementById("reidentify-error");
const reidentifyErrorMessage = document.getElementById(
    "reidentify-error-message"
);

let selectedDocument = null;
let selectedText = null;


// ======================================================
// HELPERS
// ======================================================

function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) {
        return `${(bytes / 1024).toFixed(1)} KB`;
    }

    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function isAllowedDocument(file) {
    const extension = file.name.split(".").pop().toLowerCase();

    return ["pdf", "docx", "pptx"].includes(extension);
}

function showElement(element) {
    element.classList.remove("hidden");
}

function hideElement(element) {
    element.classList.add("hidden");
}

function hideSanitizationMessages() {
    hideElement(progressCard);
    hideElement(resultCard);
    hideElement(errorCard);
}

function hideReidentificationMessages() {
    hideElement(reidentifyResult);
    hideElement(reidentifyError);
}

function showSanitizationError(message) {
    errorMessage.textContent = message;
    showElement(errorCard);
}

function showReidentificationError(message) {
    reidentifyErrorMessage.textContent = message;
    showElement(reidentifyError);
}


// ======================================================
// NAVIGATION
// ======================================================

const navigationButtons = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");

navigationButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const selectedPage = button.dataset.page;

        navigationButtons.forEach((item) => {
            item.classList.toggle("active", item === button);
        });

        pages.forEach((page) => {
            page.classList.toggle(
                "active",
                page.id === `${selectedPage}-page`
            );
        });

        document.getElementById("page-title").textContent =
            selectedPage === "sanitize"
                ? "Document Sanitization"
                : "Re-identification";

        document.getElementById("breadcrumb-page").textContent =
            selectedPage.toUpperCase();

        hideSanitizationMessages();
        hideReidentificationMessages();
    });
});


// ======================================================
// DOCUMENT SELECTION
// ======================================================

browseButton.addEventListener("click", () => {
    documentInput.click();
});

documentInput.addEventListener("change", () => {
    if (documentInput.files.length > 0) {
        selectDocument(documentInput.files[0]);
    }
});

function selectDocument(file) {
    hideSanitizationMessages();

    if (!isAllowedDocument(file)) {
        selectedDocument = null;
        documentInput.value = "";

        sanitizeButton.disabled = true;

        showSanitizationError(
            "Unsupported format. Select a PDF, DOCX, or PPTX file."
        );

        hideElement(selectedFileCard);
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        selectedDocument = null;
        documentInput.value = "";

        sanitizeButton.disabled = true;

        showSanitizationError(
            "The selected file exceeds the 50 MB upload limit."
        );

        hideElement(selectedFileCard);
        return;
    }

    selectedDocument = file;

    fileNameElement.textContent = file.name;
    fileSizeElement.textContent = formatFileSize(file.size);

    showElement(selectedFileCard);

    sanitizeButton.disabled = false;
}

document.getElementById("remove-file").addEventListener("click", () => {
    selectedDocument = null;
    documentInput.value = "";

    hideElement(selectedFileCard);
    hideSanitizationMessages();

    sanitizeButton.disabled = true;
});


// ======================================================
// DRAG AND DROP
// ======================================================

["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.add("drag-over");
    });
});

["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
        event.preventDefault();
        dropZone.classList.remove("drag-over");
    });
});

dropZone.addEventListener("drop", (event) => {
    const files = event.dataTransfer.files;

    if (files.length > 0) {
        selectDocument(files[0]);
    }
});


// ======================================================
// SANITIZATION API
// ======================================================
sanitizeButton.addEventListener("click", async () => {
    if (!selectedDocument) {
        showSanitizationError("Select a document first.");
        return;
    }

    hideSanitizationMessages();

    sanitizeButton.disabled = true;

    progressTitle.textContent = "Uploading document";
    progressMessage.textContent =
        "Sending your document to the backend...";

    progressFill.style.width = "0%";

    showElement(progressCard);
    showElement(spinner);

    const formData = new FormData();
    formData.append("document", selectedDocument);

    let polling = false;

    try {
        const response = await fetch("/api/sanitize", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            throw new Error(
                data.message || "Could not start processing."
            );
        }

        const jobId = data.job_id;

        progressTitle.textContent = "Processing document";
        progressMessage.textContent =
            "Waiting for the pipeline to report progress...";

        polling = true;

        while (polling) {
            const statusResponse = await fetch(
                `/api/jobs/${encodeURIComponent(jobId)}`,
                { cache: "no-store" }
            );

            const statusData = await statusResponse.json();

            if (!statusResponse.ok) {
                throw new Error(
                    statusData.message || "Could not retrieve job status."
                );
            }

            const percent = Math.max(
                0,
                Math.min(100, Number(statusData.percent) || 0)
            );

            progressFill.style.width = `${percent}%`;
            progressTitle.textContent = statusData.stage;
            progressMessage.textContent = statusData.message;

            if (statusData.status === "completed") {
                progressFill.style.width = "100%";
                hideElement(spinner);

                resultMessage.textContent = statusData.message;
                resultFilename.textContent =
                    statusData.output_filename;

                downloadButton.href = statusData.download_url;
                downloadButton.setAttribute(
                    "download",
                    statusData.output_filename
                );

                showElement(resultCard);
                polling = false;

            } else if (statusData.status === "failed") {
                throw new Error(statusData.message);

            } else {
                // Poll again after 500 ms.
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }

    } catch (error) {
        hideElement(progressCard);

        showSanitizationError(
            error.message || "Unable to communicate with the backend."
        );

    } finally {
        sanitizeButton.disabled = !selectedDocument;
    }
});

// ======================================================
// TEXT FILE SELECTION
// ======================================================

browseTextButton.addEventListener("click", () => {
    textInput.click();
});

textInput.addEventListener("change", () => {
    if (textInput.files.length > 0) {
        selectTextFile(textInput.files[0]);
    }
});

function selectTextFile(file) {
    hideReidentificationMessages();

    if (!file.name.toLowerCase().endsWith(".txt")) {
        selectedText = null;
        textInput.value = "";

        reidentifyButton.disabled = true;

        showReidentificationError(
            "Please select a .txt file."
        );

        hideElement(selectedTextFile);
        return;
    }

    if (file.size > 50 * 1024 * 1024) {
        selectedText = null;
        textInput.value = "";

        reidentifyButton.disabled = true;

        showReidentificationError(
            "The selected file exceeds the 50 MB upload limit."
        );

        hideElement(selectedTextFile);
        return;
    }

    selectedText = file;

    textFileName.textContent = file.name;
    textFileSize.textContent = formatFileSize(file.size);

    showElement(selectedTextFile);

    reidentifyButton.disabled = false;
}

document.getElementById("remove-text-file").addEventListener("click", () => {
    selectedText = null;
    textInput.value = "";

    hideElement(selectedTextFile);
    hideReidentificationMessages();

    reidentifyButton.disabled = true;
});


// ======================================================
// RE-IDENTIFICATION API
// ======================================================

reidentifyButton.addEventListener("click", async () => {
    if (!selectedText) {
        showReidentificationError("Select a text file first.");
        return;
    }

    hideReidentificationMessages();

    reidentifyButton.disabled = true;
    reidentifyButton.textContent = "Processing...";

    const formData = new FormData();

    formData.append("document", selectedText);

    try {
        const response = await fetch("/api/reidentify", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok || data.status !== "success") {
            throw new Error(
                data.message || "Re-identification failed."
            );
        }

        reidentifyMessage.textContent = data.message;
        reidentifyFilename.textContent = data.output_filename;

        reidentifyDownload.href = data.download_url;

        reidentifyDownload.setAttribute(
            "download",
            data.output_filename
        );

        showElement(reidentifyResult);

    } catch (error) {
        showReidentificationError(
            error.message || "Unable to contact the backend."
        );

    } finally {
        reidentifyButton.disabled = !selectedText;
        reidentifyButton.innerHTML = "Restore Values →";
    }
});


// ======================================================
// BACKEND STATUS
// ======================================================

async function checkBackend() {
    const statusBadge = document.querySelector(".status-badge");

    try {
        const response = await fetch("/api/health");

        if (!response.ok) {
            throw new Error("Backend unavailable");
        }

        statusBadge.title = "Flask backend is responding.";

    } catch (error) {
        statusBadge.title =
            "Cannot contact the Flask backend. Check app.py.";
    }
}

checkBackend();