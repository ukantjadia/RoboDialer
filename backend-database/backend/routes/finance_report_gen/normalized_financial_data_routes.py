from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import uuid
import pandas as pd

from models.lead_model import db
from models.finance_report_gen.normalized_financial_data_model import NormalizedFinancialData
from models.finance_report_gen.financial_file_model import FinancialFile
from controllers.finance_report_gen.normalized_financial_data_controller import NormalizedDataController

fin_normalized_data_bp = Blueprint('fin_normalized_data', __name__)


# Helpers

def _parse_uuid(value: str):
    try:
        return uuid.UUID(str(value))
    except Exception:
        return None


def _parse_date(value: str):
    if not value:
        return None
    try:
        # Expecting YYYY-MM-DD
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


@fin_normalized_data_bp.route('/api/fin/normalized_data', methods=['GET'])
@login_required
def list_normalized_data():
    try:
        # Pagination
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 200)

        # Filters
        file_id = request.args.get('file_id')
        metric_name = request.args.get('metric_name')
        start_from = request.args.get('start_from')  # period_start_date >=
        start_to = request.args.get('start_to')      # period_start_date <=
        end_from = request.args.get('end_from')      # period_end_date >=
        end_to = request.args.get('end_to')          # period_end_date <=
        data_type = request.args.get('data_type')
        validation_status = request.args.get('validation_status')
        outlier_flag = request.args.get('outlier_flag')

        q = NormalizedFinancialData.query

        if file_id:
            fid = _parse_uuid(file_id)
            if not fid:
                return jsonify({"error": "Invalid file_id"}), 400
            q = q.filter(NormalizedFinancialData.file_id == fid)

        if metric_name:
            q = q.filter(NormalizedFinancialData.metric_name.ilike(f"%{metric_name}%"))

        sf, st = _parse_date(start_from), _parse_date(start_to)
        ef, et = _parse_date(end_from), _parse_date(end_to)
        if sf:
            q = q.filter(NormalizedFinancialData.period_start_date >= sf)
        if st:
            q = q.filter(NormalizedFinancialData.period_start_date <= st)
        if ef:
            q = q.filter(NormalizedFinancialData.period_end_date >= ef)
        if et:
            q = q.filter(NormalizedFinancialData.period_end_date <= et)

        if data_type:
            q = q.filter(NormalizedFinancialData.data_type == data_type)
        if validation_status:
            q = q.filter(NormalizedFinancialData.validation_status == validation_status)
        if outlier_flag is not None:
            if outlier_flag.lower() in ('true', '1'):
                q = q.filter(NormalizedFinancialData.outlier_flag.is_(True))
            elif outlier_flag.lower() in ('false', '0'):
                q = q.filter(NormalizedFinancialData.outlier_flag.is_(False))

        q = q.order_by(NormalizedFinancialData.created_at.desc())
        pagination = q.paginate(page=page, per_page=per_page, error_out=False)

        items = [row.to_dict() for row in pagination.items]
        return jsonify({
            "items": items,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages
        }), 200
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@fin_normalized_data_bp.route('/api/fin/normalized_data/<record_id>', methods=['GET'])
@login_required
def get_normalized_record(record_id: str):
    rid = _parse_uuid(record_id)
    if not rid:
        return jsonify({"error": "Invalid record_id"}), 400

    row = NormalizedFinancialData.query.get(rid)
    if not row:
        return jsonify({"error": "Record not found"}), 404
    return jsonify(row.to_dict()), 200


# SINGLE POST ENDPOINT (bulk-friendly): computes values & inserts rows
@fin_normalized_data_bp.route('/api/fin/normalized_data', methods=['POST'])
@login_required
def insert_normalized_data():
    """
    Accepts JSON:
    {
      "file_id": "<uuid>",
      "frequency": "monthly" | "weekly",           # optional, default monthly
      "file_type": "...",                          # optional
      "upload_id": "<uuid>",                       # optional (trace)
      "rows": [                                    # preferred input
        {"metric_name": "Revenue", "period_label": "Jan 2024", "original_value": "₹1,23,456.78"},
        ...
      ]
      # Optionally (legacy) accept "wide": {"metric_col": "Metric", "records": [ {<wide row dict>}, ... ]}
    }
    """
    body = request.get_json(silent=True) or {}
    file_id = body.get("file_id")
    frequency = body.get("frequency", "monthly")
    file_type = body.get("file_type")
    upload_id = body.get("upload_id")

    if not file_id:
        return jsonify({"error": "file_id is required"}), 400
    fid = _parse_uuid(file_id)
    if not fid:
        return jsonify({"error": "Invalid file_id"}), 400

    rows = body.get("rows")
    wide = body.get("wide")

    # Build DataFrame if wide payload is provided (legacy/back-compat)
    df = None
    metric_col = None
    if isinstance(wide, dict):
        metric_col = wide.get("metric_col")
        records = wide.get("records") or []
        if records:
            try:
                import pandas as pd
                df = pd.DataFrame(records)
            except Exception:
                return jsonify({"error": "Invalid 'wide.records' payload"}), 400

    # Use the legacy method for backward compatibility
    payload, status = NormalizedDataController.normalize_and_store(
        file_id=str(fid),
        df=df,
        rows=rows,
        file_type=file_type,
        frequency=frequency,
        upload_id=str(upload_id) if upload_id else None,
        metric_col=metric_col
    )
    return jsonify(payload), status


@fin_normalized_data_bp.route('/api/fin/normalized_data/<record_id>', methods=['PUT', 'PATCH'])
@login_required
def update_normalized_record(record_id: str):
    rid = _parse_uuid(record_id)
    if not rid:
        return jsonify({"error": "Invalid record_id"}), 400

    data = request.get_json(silent=True) or {}

    row = NormalizedFinancialData.query.get(rid)
    if not row:
        return jsonify({"error": "Record not found"}), 404

    try:
        # Updatable fields
        if 'file_id' in data:
            fid = _parse_uuid(data.get('file_id'))
            if not fid:
                return jsonify({"error": "Invalid file_id"}), 400
            row.file_id = fid
        if 'metric_name' in data:
            row.metric_name = data.get('metric_name')
        if 'period_start_date' in data:
            row.period_start_date = _parse_date(data.get('period_start_date'))
        if 'period_end_date' in data:
            row.period_end_date = _parse_date(data.get('period_end_date'))
        if 'value' in data:
            row.value = data.get('value')
        if 'original_value' in data:
            row.original_value = data.get('original_value')
        if 'data_type' in data:
            row.data_type = data.get('data_type')
        if 'validation_status' in data:
            row.validation_status = data.get('validation_status')
        if 'data_quality_score' in data:
            row.data_quality_score = data.get('data_quality_score')
        if 'outlier_flag' in data:
            row.outlier_flag = bool(data.get('outlier_flag'))
        if 'validation_notes' in data:
            row.validation_notes = data.get('validation_notes')

        db.session.commit()
        return jsonify(row.to_dict()), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@fin_normalized_data_bp.route('/api/fin/normalized_data/<record_id>', methods=['DELETE'])
@login_required
def delete_normalized_record(record_id: str):
    rid = _parse_uuid(record_id)
    if not rid:
        return jsonify({"error": "Invalid record_id"}), 400

    row = NormalizedFinancialData.query.get(rid)
    if not row:
        return jsonify({"error": "Record not found"}), 404

    try:
        db.session.delete(row)
        db.session.commit()
        return jsonify({"success": True}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# NEW ENDPOINT: normalize file by file_id
@fin_normalized_data_bp.route('/api/fin/normalized_data/normalize_file', methods=['POST'])
@login_required
def normalize_file_and_store():
    body = request.get_json(silent=True) or {}
    file_id = body.get("file_id")
    transpose = bool(body.get("transpose", False))
    if not file_id:
        return jsonify({"error": "file_id is required"}), 400

    fid = _parse_uuid(file_id)
    if not fid:
        return jsonify({"error": "Invalid file_id"}), 400

    fin_file = FinancialFile.query.get(fid)
    if not fin_file:
        return jsonify({"error": "File not found"}), 404

    try:
        # Delete old normalized rows for this file
        deleted_count = NormalizedFinancialData.query.filter(
            NormalizedFinancialData.file_id == fid
        ).delete()
        db.session.commit()
        replaced_previous = deleted_count > 0

        # Normalize file using the new controller method
        controller = NormalizedDataController()
        payload, status = controller.normalize_file_stage(
            file_id=str(fid),
            frequency="monthly",  # Default frequency, can be made configurable
            force_transpose=transpose
        )

        if status == 200:
            fin_file.status = "normalized"
            fin_file.processing_completed_at = datetime.utcnow()
            db.session.commit()

            # If we replaced an existing normalization, add a helpful message in the response
            if replaced_previous:
                note = f"Old normalization for file_id {fid} was replaced with this normalization ({deleted_count} old rows deleted)."
                if isinstance(payload, dict):
                    # preserve existing payload keys but add flags/message
                    payload.setdefault("messages", [])
                    payload["messages"].append(note)
                    payload["replaced_previous_normalization"] = True
                else:
                    payload = {
                        "replaced_previous_normalization": True,
                        "message": note,
                        "payload": payload,
                    }

        return jsonify(payload), status
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Server error: {str(e)}"}), 500
