from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from typing import Any, Dict
from datetime import datetime
import uuid

from models.lead_model import db
from models.finance_report_gen.financial_report_upload_model import FinancialReportUpload
from models.user_model import User
from models.finance_report_gen.financial_file_model import FinancialFile


fin_report_upload_bp = Blueprint("fin_report_upload", __name__)


@fin_report_upload_bp.route("/api/fin/uploads/health", methods=["GET"])
@login_required
def health() -> Dict[str, str]:
    return {"health": "ok"}


@fin_report_upload_bp.route("/api/fin/uploads", methods=["GET"])
@login_required  # Re-enabled for production
def list_uploads():
    try:
        # Pagination params
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        status = request.args.get("status")  # optional filter
        data_granularity = request.args.get("data_granularity")  # optional filter
        user_id_param = request.args.get("user_id")  # optional filter

        q = FinancialReportUpload.query
        if user_id_param:
            try:
                uid = uuid.UUID(user_id_param)
                q = q.filter(FinancialReportUpload.user_id == uid)
            except Exception:
                return jsonify({"error": "Invalid user_id in query params"}), 400
        if status:
            q = q.filter(FinancialReportUpload.status == status)
        if data_granularity:
            q = q.filter(FinancialReportUpload.data_granularity == data_granularity)

        q = q.order_by(FinancialReportUpload.created_at.desc())
        pagination = q.paginate(page=page, per_page=per_page, error_out=False)

        return (
            jsonify(
                {
                    "page": pagination.page,
                    "per_page": pagination.per_page,
                    "total": pagination.total,
                    "pages": pagination.pages,
                    "items": [item.to_dict() for item in pagination.items],
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.error(f"[FinUpload][List] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_report_upload_bp.route("/api/fin/uploads/<string:upload_id>", methods=["GET"])
@login_required  # Re-enabled for production
def get_upload(upload_id: str):
    try:
        try:
            uid = uuid.UUID(upload_id)
        except Exception:
            return jsonify({"error": "Invalid upload_id"}), 400

        obj = FinancialReportUpload.query.filter_by(upload_id=uid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404
        return jsonify(obj.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"[FinUpload][Get] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_report_upload_bp.route("/api/fin/uploads", methods=["POST"])
@login_required  # Re-enabled for production
def create_upload():
    try:
        data = request.get_json(silent=True) or {}

        # Enforce required fields (all except optional 'notes')
        required_fields = [
            "user_id",
            "industry",
            "data_granularity",
            "status",
            "total_files",
            "processed_files",
        ]
        missing = []
        for f in required_fields:
            v = data.get(f, None)
            if v is None or (isinstance(v, str) and not v.strip()):
                missing.append(f)
        if missing:
            return jsonify({"error": "Missing required fields", "missing_fields": missing}), 400

        # Require user_id explicitly for testing without auth
        user_id_str = data.get("user_id")
        if not user_id_str:
            return jsonify({"error": "user_id is required"}), 400
        try:
            user_uuid = uuid.UUID(user_id_str)
        except Exception:
            return jsonify({"error": "user_id must be a valid UUID"}), 400

        # 1) User validation
        if not User.query.filter_by(user_id=user_uuid).first():
            return jsonify({"error": "user_id not found"}), 404

        # 2) Granularity validation
        data_granularity = data.get("data_granularity")
        allowed_granularity = {"monthly", "quarterly", "annual"}
        if data_granularity and data_granularity not in allowed_granularity:
            return jsonify({"error": f"Invalid data_granularity. Allowed: {sorted(list(allowed_granularity))}"}), 400

        # 3) File count sanity
        total_files = data.get("total_files")
        processed_files = data.get("processed_files")
        if total_files is not None:
            try:
                total_files = int(total_files)
            except Exception:
                return jsonify({"error": "total_files must be an integer"}), 400
            if total_files < 0:
                return jsonify({"error": "total_files must be >= 0"}), 400
        if processed_files is not None:
            try:
                processed_files = int(processed_files)
            except Exception:
                return jsonify({"error": "processed_files must be an integer"}), 400
            if processed_files < 0:
                return jsonify({"error": "processed_files must be >= 0"}), 400
        if processed_files is not None and total_files is not None and processed_files > total_files:
            return jsonify({"error": "processed_files cannot exceed total_files"}), 400

        status = data.get("status", "uploaded")
        allowed_status = ["uploaded", "mapping", "processing", "completed", "error"]
        if status not in allowed_status:
            return jsonify({"error": f"Invalid status. Allowed: {allowed_status}"}), 400

        obj = FinancialReportUpload(
            user_id=user_uuid,
            upload_date=datetime.utcnow(),
            industry=data.get("industry"),
            data_granularity=data_granularity,
            status=status,
            total_files=total_files,
            processed_files=processed_files,
            notes=data.get("notes"),
        )
        db.session.add(obj)
        db.session.commit()
        return jsonify(obj.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinUpload][Create] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_report_upload_bp.route("/api/fin/uploads/<string:upload_id>", methods=["PUT", "PATCH"])
@login_required  # Re-enabled for production
def update_upload(upload_id: str):
    try:
        try:
            uid = uuid.UUID(upload_id)
        except Exception:
            return jsonify({"error": "Invalid upload_id"}), 400

        obj = FinancialReportUpload.query.filter_by(upload_id=uid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404

        data = request.get_json(silent=True) or {}

        # Immutable fields: upload_id, user_id, upload_date
        for imm in ["upload_id", "user_id", "upload_date"]:
            if imm in data and str(data[imm]) != str(getattr(obj, imm)):
                return jsonify({"error": f"{imm} is immutable"}), 400

        # Validate and assign fields
        if "data_granularity" in data:
            if data["data_granularity"] and data["data_granularity"] not in {"monthly", "quarterly", "annual"}:
                return jsonify({"error": "Invalid data_granularity"}), 400
            obj.data_granularity = data.get("data_granularity")

        # File counts
        if "total_files" in data:
            try:
                tf = int(data["total_files"]) if data["total_files"] is not None else None
            except Exception:
                return jsonify({"error": "total_files must be an integer"}), 400
            if tf is not None and tf < 0:
                return jsonify({"error": "total_files must be >= 0"}), 400
            obj.total_files = tf

        if "processed_files" in data:
            try:
                pf = int(data["processed_files"]) if data["processed_files"] is not None else None
            except Exception:
                return jsonify({"error": "processed_files must be an integer"}), 400
            if pf is not None and pf < 0:
                return jsonify({"error": "processed_files must be >= 0"}), 400
            # Ensure processed <= total when both available
            tf_eff = obj.total_files if obj.total_files is not None else None
            if tf_eff is not None and pf is not None and pf > tf_eff:
                return jsonify({"error": "processed_files cannot exceed total_files"}), 400
            obj.processed_files = pf

        if "industry" in data:
            obj.industry = data.get("industry")
        if "notes" in data:
            obj.notes = data.get("notes")

        if "status" in data:
            new_status = data["status"]
            allowed_status = ["uploaded", "mapping", "processing", "completed", "error"]
            if new_status not in allowed_status:
                return jsonify({"error": f"Invalid status. Allowed: {allowed_status}"}), 400
            if obj.status != new_status:
                # Status transitions: do not skip steps
                order = {"uploaded": 0, "mapping": 1, "processing": 2, "completed": 3}
                if new_status == "error":
                    pass
                else:
                    if obj.status == "error":
                        return jsonify({"error": "Cannot transition from error to a non-error status"}), 400
                    curr = order.get(obj.status, -1)
                    nxt = order.get(new_status, -1)
                    if nxt - curr != 1:
                        return jsonify({"error": f"Invalid status transition {obj.status} -> {new_status}"}), 400
                obj.status = new_status

        obj.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(obj.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinUpload][Update] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@fin_report_upload_bp.route("/api/fin/uploads/<string:upload_id>", methods=["DELETE"])
@login_required  # Re-enabled for production
def delete_upload(upload_id: str):
    try:
        try:
            uid = uuid.UUID(upload_id)
        except Exception:
            return jsonify({"error": "Invalid upload_id"}), 400

        obj = FinancialReportUpload.query.filter_by(upload_id=uid).first()
        if not obj:
            return jsonify({"error": "Not found"}), 404

        # Child existence check: prevent hard delete if financial files exist
        child_exists = FinancialFile.query.filter_by(upload_id=uid).first() is not None
        if child_exists:
            return jsonify({"error": "Upload has financial_file children; delete/cleanup them first or enable cascading."}), 409

        db.session.delete(obj)
        db.session.commit()
        return jsonify({"deleted": True, "upload_id": upload_id}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[FinUpload][Delete] Error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
