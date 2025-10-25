from flask import current_app, Blueprint, request, jsonify
from flask_login import login_required
from controllers.finance_report_gen.finance_kpi_controller import FileKPICalculationEngine
import uuid

fin_kpi_cal_bp = Blueprint("fin_kpi_cal", __name__)


@fin_kpi_cal_bp.route('/api/fin/kpi', methods=['POST'])
@login_required
def upload_finance_kpi():
    try:
        data = request.get_json()  # Parse JSON properly
        upload_id = data.get('upload_id')
        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400
        try:
            uuid.UUID(upload_id)  # Validate UUID (raises ValueError if invalid)
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        engine = FileKPICalculationEngine()
        summary = engine.calculate_upload_kpi(upload_id=upload_id)
        # If there are failures, surface them with appropriate HTTP status
        upload_summary = summary.get("upload_summary", {})
        overall_status = upload_summary.get("overall_status")
        failed_files = summary.get("failed_files", [])

        if overall_status in ("failed", "partial") or failed_files:
            status_code = 207 if overall_status == "partial" else 400
            return jsonify(summary), status_code
        return jsonify(summary)  # Return JSON

    except Exception as e:
        current_app.logger.error(f"API error: {str(e)}")
        return jsonify({"error":f"Error Occured during procesing File {e}"}), 500



# # Test route for file_id
# @fin_kpi_cal_bp.route('/api/fin/kpi', methods=['POST'])
# def finance_kpi_cal():
#     try:
#         data = request.get_json()  # Parse JSON properly
#         file_id = data.get('file_id')
#         if not file_id:
#             return jsonify({"error": "Missing file_id"}), 400
#         try:
#             uuid.UUID(file_id)  # Validate UUID (raises ValueError if invalid)
#         except ValueError:
#             return jsonify({"error": "Invalid file_id format"}), 400

#         engine = FileKPICalculationEngine()
#         summary = engine.calculate_file_kpi(file_id=file_id)
#         return jsonify(summary)  # Return JSON
#     except Exception as e:
#         current_app.logger.error(f"API error: {str(e)}")
#         return jsonify({"error": str(e)}), 500
