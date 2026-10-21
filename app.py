from pathlib import Path
from threading import Thread, Lock
from uuid import uuid4
from time import time
import logging

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from process_document import process_document
from pseudonymization.reidentifier import reidentify_file


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

FRONTEND_DIR = BASE_DIR / "frontend"
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx"}
ALLOWED_TEXT_EXTENSIONS = {".txt"}

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)

app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================
# JOB MANAGEMENT
# ============================================================

# Stores the progress and result of each processing job.
jobs = {}

# Protects access to the jobs dictionary.
jobs_lock = Lock()

# Your existing pipeline uses shared JSON files.
# This lock prevents two documents from processing simultaneously.
processing_lock = Lock()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_extension(filename):
    return Path(filename).suffix.lower()


def is_allowed_file(filename, extensions):
    return (
        bool(filename)
        and get_extension(filename) in extensions
    )


def create_unique_upload_path(filename):
    """
    Generate a unique filename to avoid upload collisions.
    """

    safe_name = secure_filename(filename)

    if not safe_name:
        raise ValueError("Invalid filename.")

    extension = get_extension(safe_name)
    stem = Path(safe_name).stem

    unique_name = f"{stem}_{uuid4().hex}{extension}"

    return UPLOAD_DIR / unique_name


def update_job(job_id, **values):
    """
    Safely update the status of a processing job.
    """

    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(values)
            jobs[job_id]["updated_at"] = time()


def get_output_file(result):
    """
    Validate the output path returned by the existing pipeline.
    """

    if not result:
        raise RuntimeError(
            "The processing pipeline returned no output path."
        )

    output_path = Path(result)

    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    output_path = output_path.resolve()
    allowed_directory = OUTPUT_DIR.resolve()

    if allowed_directory not in output_path.parents:
        raise RuntimeError(
            "The generated document is outside the output directory."
        )

    if not output_path.is_file():
        raise FileNotFoundError(
            "The sanitized document could not be found."
        )

    return output_path


# ============================================================
# BACKGROUND DOCUMENT PROCESSING
# ============================================================

def process_document_job(job_id, input_path):
    """
    Run the existing pipeline in the background.

    The pipeline reports progress through a callback.
    """

    try:
        update_job(
            job_id,
            status="processing",
            percent=5,
            stage="Starting",
            message="Preparing your document..."
        )

        # Serialize jobs because the current pipeline writes
        # intermediate results to shared JSON files.
        with processing_lock:

            # Callback invoked by process_document.py.
            def progress_callback(progress):
                update_job(
                    job_id,
                    percent=progress["percent"],
                    stage=progress["stage"],
                    message=progress["message"]
                )

            # Call the existing document pipeline.
            result = process_document(
                str(input_path),
                progress_callback=progress_callback
            )

            # Validate the generated document.
            output_path = get_output_file(result)

        # Processing completed successfully.
        update_job(
            job_id,
            status="completed",
            percent=100,
            stage="Completed",
            message="Your sanitized document is ready.",
            output_filename=output_path.name
        )

        logger.info(
            "Job %s completed: %s",
            job_id,
            output_path.name
        )

    except Exception:
        logger.exception(
            "Document processing failed for job %s",
            job_id
        )

        update_job(
            job_id,
            status="failed",
            stage="Failed",
            message=(
                "Document processing failed. "
                "Check the backend terminal for details."
            )
        )

    finally:
        # Remove the temporary original uploaded file.
        if input_path.exists():
            try:
                input_path.unlink()
            except OSError:
                logger.exception(
                    "Could not remove temporary upload: %s",
                    input_path
                )


# ============================================================
# FRONTEND ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def index():
    index_file = FRONTEND_DIR / "index.html"

    if not index_file.is_file():
        return (
            "Frontend not found. Create frontend/index.html first.",
            404
        )

    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/css/<path:filename>", methods=["GET"])
def serve_css(filename):
    return send_from_directory(
        FRONTEND_DIR / "css",
        filename
    )


@app.route("/js/<path:filename>", methods=["GET"])
def serve_javascript(filename):
    return send_from_directory(
        FRONTEND_DIR / "js",
        filename
    )


# ============================================================
# BACKEND HEALTH CHECK
# ============================================================

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "success",
        "message": "PrivacyForge backend is running."
    }), 200


# ============================================================
# START DOCUMENT SANITIZATION
# ============================================================

@app.route("/api/sanitize", methods=["POST"])
def sanitize_document():

    uploaded_file = request.files.get("document")

    if uploaded_file is None:
        return jsonify({
            "status": "error",
            "message": "No document was uploaded."
        }), 400

    if not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Please select a document."
        }), 400

    if not is_allowed_file(
        uploaded_file.filename,
        ALLOWED_DOCUMENT_EXTENSIONS
    ):
        return jsonify({
            "status": "error",
            "message": "Upload a PDF, DOCX, or PPTX file."
        }), 400

    input_path = None

    try:
        # Save the uploaded file using a unique filename.
        input_path = create_unique_upload_path(
            uploaded_file.filename
        )

        uploaded_file.save(input_path)

        job_id = uuid4().hex

        # Register the job before starting the worker.
        with jobs_lock:
            jobs[job_id] = {
                "status": "queued",
                "percent": 0,
                "stage": "Queued",
                "message": "Document uploaded. Waiting for processing.",
                "output_filename": None,
                "created_at": time(),
                "updated_at": time()
            }

        # Start processing in the background.
        worker = Thread(
            target=process_document_job,
            args=(job_id, input_path),
            daemon=True
        )

        worker.start()

        # Return immediately so JavaScript can poll for progress.
        return jsonify({
            "status": "success",
            "message": "Document accepted for processing.",
            "job_id": job_id,
            "status_url": f"/api/jobs/{job_id}"
        }), 202

    except Exception:
        logger.exception("Could not start the processing job.")

        if input_path and input_path.exists():
            try:
                input_path.unlink()
            except OSError:
                logger.exception("Could not remove temporary upload.")

        return jsonify({
            "status": "error",
            "message": "Could not start document processing."
        }), 500


# ============================================================
# REAL-TIME JOB STATUS
# ============================================================

@app.route("/api/jobs/<job_id>", methods=["GET"])
def get_job_status(job_id):

    with jobs_lock:
        job = jobs.get(job_id)

        if job is None:
            return jsonify({
                "status": "error",
                "message": "Job not found. The server may have restarted."
            }), 404

        response = {
            "status": job["status"],
            "percent": job["percent"],
            "stage": job["stage"],
            "message": job["message"]
        }

        if job["status"] == "completed":
            response["output_filename"] = job["output_filename"]

            response["download_url"] = (
                f"/api/download/{job['output_filename']}"
            )

        return jsonify(response), 200


# ============================================================
# DOWNLOAD SANITIZED DOCUMENTS
# ============================================================

@app.route("/api/download/<path:filename>", methods=["GET"])
def download_document(filename):

    safe_filename = secure_filename(filename)

    if not safe_filename or safe_filename != filename:
        return jsonify({
            "status": "error",
            "message": "Invalid filename."
        }), 400

    output_path = (OUTPUT_DIR / safe_filename).resolve()

    if OUTPUT_DIR.resolve() not in output_path.parents:
        return jsonify({
            "status": "error",
            "message": "Invalid output path."
        }), 400

    if not output_path.is_file():
        return jsonify({
            "status": "error",
            "message": "The requested document was not found."
        }), 404

    return send_from_directory(
        OUTPUT_DIR,
        safe_filename,
        as_attachment=True
    )


# ============================================================
# RE-IDENTIFICATION
# ============================================================

@app.route("/api/reidentify", methods=["POST"])
def reidentify_analysis():

    uploaded_file = request.files.get("document")

    if uploaded_file is None or not uploaded_file.filename:
        return jsonify({
            "status": "error",
            "message": "Please upload a text file."
        }), 400

    if not is_allowed_file(
        uploaded_file.filename,
        ALLOWED_TEXT_EXTENSIONS
    ):
        return jsonify({
            "status": "error",
            "message": "Only .txt files are supported."
        }), 400

    input_path = None

    try:
        input_path = create_unique_upload_path(
            uploaded_file.filename
        )

        uploaded_file.save(input_path)

        # Use your existing re-identification module.
        result = reidentify_file(str(input_path))

        if not result:
            raise RuntimeError(
                "The re-identification module returned no output."
            )

        output_path = Path(result)

        if not output_path.is_absolute():
            output_path = BASE_DIR / output_path

        output_path = output_path.resolve()

        if OUTPUT_DIR.resolve() not in output_path.parents:
            raise RuntimeError(
                "The re-identified file is outside the output directory."
            )

        if not output_path.is_file():
            raise FileNotFoundError(
                "The re-identified file was not found."
            )

        return jsonify({
            "status": "success",
            "message": "Re-identification completed successfully.",
            "output_filename": output_path.name,
            "download_url": f"/api/download/{output_path.name}"
        }), 200

    except Exception:
        logger.exception("Re-identification failed.")

        return jsonify({
            "status": "error",
            "message": (
                "Re-identification failed. "
                "Check the backend terminal for details."
            )
        }), 500

    finally:
        if input_path and input_path.exists():
            try:
                input_path.unlink()
            except OSError:
                logger.exception(
                    "Could not remove temporary text file."
                )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "status": "error",
        "message": "File too large. Maximum upload size is 50 MB."
    }), 413


@app.errorhandler(404)
def page_not_found(error):

    if request.path.startswith("/api/"):
        return jsonify({
            "status": "error",
            "message": "API endpoint or file not found."
        }), 404

    return "Page not found.", 404


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
