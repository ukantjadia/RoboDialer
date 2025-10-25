from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required  # Re-enabled auth
from datetime import datetime
from typing import Dict
import uuid

from models.lead_model import db
from models.finance_report_gen.financial_file_model import FinancialFile
from models.finance_report_gen.financial_report_upload_model import FinancialReportUpload
from models.finance_report_gen.column_mapping_model import ColumnMapping
from models.finance_report_gen.normalized_financial_data_model import NormalizedFinancialData


fin_file_bp = Blueprint("fin_file", __name__)


@fin_file_bp.route("/api/fin/files/health", methods=["GET"])
@login_required  # Re-enabled for production
def health() -> Dict[str, str]:
    return {"health": "ok"}


@fin_file_bp.route("/api/fin/files", methods=["GET"])
@login_required  # Re-enabled for production
def list_files():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        upload_id = request.args.get("upload_id")
        status = request.args.get("status")
        file_type = request.args.get("file_type")

        q = FinancialFile.query
        if upload_id:
            try:
                q = q.filter(FinancialFile.upload_id == uuid.UUID(upload_id))
            except Exception:
                return jsonify({"error": "Invalid upload_id"}), 400
        if status:
            q = q.filter(FinancialFile.status == status)
        if file_type:
            q = q.filter(FinancialFile.file_type == file_type)

        q = q.order_by(FinancialFile.created_at.desc())
        pagination = q.paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "items": [i.to_dict() for i in pagination.items],
        }), 200
    except Exception as e:
        current_app.logger.error(f"[FinFile][List] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_file_bp.route("/api/fin/files/<string:file_id>", methods=["GET"])
@login_required  # Re-enabled for production
def get_file(file_id: str):
    try:
        try:
            fid = uuid.UUID(file_id)
        except Exception:
            return jsonify({"error": "Invalid file_id"}), 400

        obj = FinancialFile.query.filter_by(file_id=fid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404
        return jsonify(obj.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"[FinFile][Get] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_file_bp.route("/api/fin/files", methods=["POST"])
@login_required  # Re-enabled for production
def create_file():
    try:
        data = request.get_json(silent=True) or {}

        # Enforce required fields on insert (all except optional 'processing_completed_at')
        required_fields = [
            "upload_id",
            "file_name",
            "file_extension",
            "processed_file_path",
            "file_size",
            "detected_periodicity",
            "user_selected_periodicity",
            "file_type",
            "status",
            "column_count",
            "row_count",
            "processing_started_at",
        ]
        missing = []
        for f in required_fields:
            v = data.get(f, None)
            if v is None or (isinstance(v, str) and not v.strip()):
                missing.append(f)
        if missing:
            return jsonify({"error": "Missing required fields", "missing_fields": missing}), 400

        upload_id = data.get("upload_id")
        if not upload_id:
            return jsonify({"error": "upload_id is required"}), 400
        try:
            upload_uuid = uuid.UUID(upload_id)
        except Exception:
            return jsonify({"error": "upload_id must be a valid UUID"}), 400

        # 1) Parent upload existence
        parent = FinancialReportUpload.query.filter_by(upload_id=upload_uuid).first()
        if not parent:
            return jsonify({"error": "Parent financial_report_upload not found"}), 404

        # Extract and validate fields
        file_name = (data.get("file_name") or "").strip()
        file_extension = (data.get("file_extension") or "").strip().lower()
        file_type = data.get("file_type")
        status = data.get("status", "uploaded")
        file_size = data.get("file_size")
        detected_periodicity = data.get("detected_periodicity")
        user_selected_periodicity = data.get("user_selected_periodicity")

        # 2) Required and uniqueness check
        if not file_name or not file_extension:
            return jsonify({"error": "file_name and file_extension are required"}), 400
        allow_duplicate = bool(data.get("allow_duplicate", False))
        if not allow_duplicate:
            dup = (
                FinancialFile.query
                .filter(FinancialFile.upload_id == upload_uuid, FinancialFile.file_name == file_name)
                .first()
            )
            if dup:
                return jsonify({"error": "Duplicate file for this upload (file_name + upload_id)"}), 409

        # 3) Extension validation
        allowed_extensions = {".csv", ".xlsx", ".zip"}
        if not file_extension.startswith("."):
            file_extension = f".{file_extension}"
        if file_extension not in allowed_extensions:
            return jsonify({"error": f"Invalid file_extension. Allowed: {sorted(list(allowed_extensions))}"}), 400

        # 4) File type consistency
        allowed_file_types = {"income_statement", "balance_sheet", "cash_flow", "unknown"}
        if file_type and file_type not in allowed_file_types:
            return jsonify({"error": f"Invalid file_type. Allowed: {sorted(list(allowed_file_types))}"}), 400

        # 5) File size sanity
        if file_size is not None:
            try:
                file_size_int = int(file_size)
            except Exception:
                return jsonify({"error": "file_size must be an integer"}), 400
            max_file_bytes = int(current_app.config.get("FIN_DB_MAX_FILE_BYTES", 2_147_483_648))  # 2GB default
            if file_size_int < 0 or file_size_int > max_file_bytes:
                return jsonify({"error": f"file_size out of bounds (0..{max_file_bytes})"}), 400
        else:
            file_size_int = None

        # 6) Periodicity consistency
        allowed_periodicity = {"monthly", "quarterly", "annual"}
        if detected_periodicity and detected_periodicity not in allowed_periodicity:
            return jsonify({"error": f"Invalid detected_periodicity. Allowed: {sorted(list(allowed_periodicity))}"}), 400
        if user_selected_periodicity and user_selected_periodicity not in allowed_periodicity:
            return jsonify({"error": f"Invalid user_selected_periodicity. Allowed: {sorted(list(allowed_periodicity))}"}), 400
        if user_selected_periodicity and detected_periodicity and user_selected_periodicity != detected_periodicity:
            current_app.logger.info(
                f"[FinFile][Create] Periodicity differs: detected={detected_periodicity}, user_selected={user_selected_periodicity}"
            )

        # 7) Status validation: must be one of model enums; default 'uploaded'
        allowed_status = {"uploaded", "headers_extracted", "mapped", "normalized", "error"}
        if status not in allowed_status:
            return jsonify({"error": f"Invalid status. Allowed: {sorted(list(allowed_status))}"}), 400

        obj = FinancialFile(
            upload_id=upload_uuid,
            file_name=file_name,
            file_extension=file_extension,
            processed_file_path=data.get("processed_file_path"),
            file_size=file_size_int,
            detected_periodicity=detected_periodicity,
            user_selected_periodicity=user_selected_periodicity,
            file_type=file_type,
            status=status,
            column_count=data.get("column_count"),
            row_count=data.get("row_count"),
            processing_started_at=_parse_dt(data.get("processing_started_at")),
            processing_completed_at=_parse_dt(data.get("processing_completed_at")),
        )

        # Timestamp logic
        if obj.processing_completed_at and not obj.processing_started_at:
            return jsonify({"error": "processing_started_at must be set if processing_completed_at is provided"}), 400
        if obj.processing_started_at and obj.processing_completed_at and obj.processing_started_at > obj.processing_completed_at:
            return jsonify({"error": "processing_started_at must be earlier than processing_completed_at"}), 400

        db.session.add(obj)
        db.session.commit()
        return jsonify(obj.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinFile][Create] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_file_bp.route("/api/fin/files/<string:file_id>", methods=["PUT", "PATCH"])
@login_required  # Re-enabled for production
def update_file(file_id: str):
    try:
        try:
            fid = uuid.UUID(file_id)
        except Exception:
            return jsonify({"error": "Invalid file_id"}), 400

        obj = FinancialFile.query.filter_by(file_id=fid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404

        data = request.get_json(silent=True) or {}

        # Immutable fields
        for imm in ["upload_id", "file_id"]:
            if imm in data and str(data[imm]) != str(getattr(obj, imm)):
                return jsonify({"error": f"{imm} is immutable"}), 400

        # Validate values before setting
        if "file_extension" in data:
            ext = (data.get("file_extension") or "").strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext not in {".csv", ".xlsx", ".zip"}:
                return jsonify({"error": "Invalid file_extension. Allowed: ['.csv', '.xlsx', '.zip']"}), 400
            obj.file_extension = ext

        if "file_name" in data:
            fn = (data.get("file_name") or "").strip()
            if not fn:
                return jsonify({"error": "file_name cannot be empty"}), 400
            # Optional: uniqueness on rename within same upload
            exists = (
                FinancialFile.query
                .filter(FinancialFile.upload_id == obj.upload_id, FinancialFile.file_name == fn, FinancialFile.file_id != obj.file_id)
                .first()
            )
            if exists:
                return jsonify({"error": "Another file with same name exists in this upload"}), 409
            obj.file_name = fn

        if "file_type" in data:
            if data["file_type"] not in {"income_statement", "balance_sheet", "cash_flow", "unknown"}:
                return jsonify({"error": "Invalid file_type"}), 400
            obj.file_type = data["file_type"]

        if "file_size" in data:
            try:
                fs = int(data["file_size"]) if data["file_size"] is not None else None
            except Exception:
                return jsonify({"error": "file_size must be an integer"}), 400
            if fs is not None:
                max_file_bytes = int(current_app.config.get("FIN_DB_MAX_FILE_BYTES", 2_147_483_648))
                if fs < 0 or fs > max_file_bytes:
                    return jsonify({"error": f"file_size out of bounds (0..{max_file_bytes})"}), 400
            obj.file_size = fs

        if "detected_periodicity" in data:
            dp = data.get("detected_periodicity")
            if dp and dp not in {"monthly", "quarterly", "annual"}:
                return jsonify({"error": "Invalid detected_periodicity"}), 400
            obj.detected_periodicity = dp

        if "user_selected_periodicity" in data:
            up = data.get("user_selected_periodicity")
            if up and up not in {"monthly", "quarterly", "annual"}:
                return jsonify({"error": "Invalid user_selected_periodicity"}), 400
            if up and obj.detected_periodicity and up != obj.detected_periodicity:
                current_app.logger.info(
                    f"[FinFile][Update] Periodicity differs: detected={obj.detected_periodicity}, user_selected={up}"
                )
            obj.user_selected_periodicity = up

        if "processed_file_path" in data:
            p = data.get("processed_file_path")
            if p is not None:
                if not isinstance(p, str):
                    return jsonify({"error": "processed_file_path must be a string"}), 400
                if len(p) > 500:
                    return jsonify({"error": "processed_file_path too long (max 500)"}), 400
                obj.processed_file_path = p.strip()
            else:
                # allow clearing the field
                obj.processed_file_path = None

        if "status" in data:
            new_status = data["status"]
            allowed_status = ["uploaded", "headers_extracted", "mapped", "normalized", "error"]
            if new_status not in allowed_status:
                return jsonify({"error": f"Invalid status. Allowed: {allowed_status}"}), 400
            if obj.status != new_status:
                # Status transition rules
                order = {"uploaded": 0, "headers_extracted": 1, "mapped": 2, "normalized": 3}
                if new_status == "error":
                    pass  # error allowed anytime
                else:
                    if obj.status == "error":
                        return jsonify({"error": "Cannot transition from error to a non-error status"}), 400
                    # only allow next step (no skipping) or same
                    curr = order.get(obj.status, -1)
                    nxt = order.get(new_status, -1)
                    if nxt - curr != 1:
                        return jsonify({"error": f"Invalid status transition {obj.status} -> {new_status}"}), 400
                obj.status = new_status

        if "column_count" in data:
            obj.column_count = data["column_count"]
        if "row_count" in data:
            obj.row_count = data["row_count"]

        if "processing_started_at" in data:
            obj.processing_started_at = _parse_dt(data.get("processing_started_at"))
        if "processing_completed_at" in data:
            obj.processing_completed_at = _parse_dt(data.get("processing_completed_at"))

        # processing timestamps logic
        if obj.processing_completed_at and not obj.processing_started_at:
            return jsonify({"error": "processing_started_at must be set if processing_completed_at is provided"}), 400
        if obj.processing_started_at and obj.processing_completed_at and obj.processing_started_at > obj.processing_completed_at:
            return jsonify({"error": "processing_started_at must be earlier than processing_completed_at"}), 400

        obj.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(obj.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinFile][Update] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_file_bp.route("/api/fin/files/<string:file_id>", methods=["DELETE"])
@login_required  # Re-enabled for production
def delete_file(file_id: str):
    try:
        try:
            fid = uuid.UUID(file_id)
        except Exception:
            return jsonify({"error": "Invalid file_id"}), 400

        obj = FinancialFile.query.filter_by(file_id=fid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404

        # Delete all related data and then the file
        deleted_norm = NormalizedFinancialData.query.filter_by(file_id=fid).delete(synchronize_session=False)
        deleted_mappings = ColumnMapping.query.filter_by(file_id=fid).delete(synchronize_session=False)
        current_app.logger.info(f"[FinFile][Delete] Deleted {deleted_norm} normalized rows and {deleted_mappings} column mappings for file {fid}")

        db.session.delete(obj)
        db.session.commit()
        return jsonify({"deleted": True, "file_id": file_id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinFile][Delete] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# Helpers

def _parse_dt(value):
    """Parse ISO8601 string to datetime or return None."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None
