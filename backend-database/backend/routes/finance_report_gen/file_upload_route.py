from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any
from flask_login import login_required, current_user

# Import helper using the same module layout as other controllers
from controllers.finance_report_gen.file_upload_controller import FileUpload


fin_file_upload_bp = Blueprint("fin_file_upload", __name__)


@fin_file_upload_bp.route("/api/fin/health", methods=["GET"])
def health() -> Dict[str, str]:
    return {"health": "ok"}


@fin_file_upload_bp.route("/api/fin/upload", methods=["POST"])
@login_required
def upload_files():
    try:
        current_app.logger.info("[Upload] DB-backed upload request received")

        if "file" not in request.files:
            current_app.logger.warning("[Upload] No files provided in request")
            return jsonify({"error": "No files provided"}), 400

        uploaded_files = request.files.getlist("file")
        uploaded_files = [f for f in uploaded_files if f and f.filename]
        if not uploaded_files:
            current_app.logger.warning("[Upload] Files list present but empty filenames")
            return jsonify({"error": "No valid files selected"}), 400

        # Optional metadata from form
        form_meta: Dict[str, Any] = {
            "industry": request.form.get("industry"),
            "data_granularity": request.form.get("data_granularity"),
            "notes": request.form.get("notes"),
        }

        file_upload = FileUpload()
        result = file_upload.process_and_persist_upload(
            files=uploaded_files,
            user_id=current_user.user_id,
            form_meta=form_meta,
        )

        return jsonify(result), 200

    except Exception as e:
        current_app.logger.error(f"[Upload] Server error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@fin_file_upload_bp.app_errorhandler(413)
def too_large(e):
    return jsonify({"error": "Request too large"}), 413