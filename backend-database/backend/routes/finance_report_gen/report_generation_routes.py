from flask import Blueprint, request, jsonify, current_app, send_file
from flask_login import login_required
import uuid
import os

from controllers.finance_report_gen.report_generation_controller import ReportGenerationController
from models.finance_report_gen.financial_report_version_model import FinancialReportVersion
from models.lead_model import db

report_gen_bp = Blueprint("report_gen", __name__)


@report_gen_bp.route('/api/fin/report/generate', methods=['POST'])
@login_required
def generate_fin_report():
    try:
        data = request.get_json() or {}
        upload_id = data.get('upload_id')
        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400
        try:
            uuid.UUID(upload_id)
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        controller = ReportGenerationController()
        # Optional inputs
        kpi_results = data.get('kpi_results')  # optional precomputed KPI JSON
        company_details = data.get('company_details')  # optional company context
        payload, status = controller.generate_report(upload_id=upload_id, kpi_results=kpi_results, company_details=company_details)
        return jsonify(payload), status
    except Exception as e:
        current_app.logger.exception("Report generation endpoint failed")
        return jsonify({"error": "Internal server error"}), 500


@report_gen_bp.route('/api/fin/report/versions', methods=['GET'])
@login_required
def list_fin_report_versions():
    try:
        upload_id = request.args.get('upload_id')
        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400
        try:
            upload_uuid = uuid.UUID(upload_id)
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        versions = FinancialReportVersion.query.filter_by(upload_id=upload_uuid).order_by(FinancialReportVersion.created_at.desc()).all()
        return jsonify([v.to_dict() for v in versions]), 200
    except Exception:
        current_app.logger.exception("List report versions failed")
        return jsonify({"error": "Internal server error"}), 500


# Get a single version by version_id
@report_gen_bp.route('/api/fin/report/versions/<version_id>', methods=['GET'])
@login_required
def get_fin_report_version(version_id: str):
    try:
        try:
            version_uuid = uuid.UUID(version_id)
        except ValueError:
            return jsonify({"error": "Invalid version_id format"}), 400
        v = FinancialReportVersion.query.filter_by(version_id=version_uuid).first()
        if not v:
            return jsonify({"error": "Not found"}), 404
        return jsonify(v.to_dict()), 200
    except Exception:
        current_app.logger.exception("Get report version failed")
        return jsonify({"error": "Internal server error"}), 500


# Create a version manually
@report_gen_bp.route('/api/fin/report/versions', methods=['POST'])
@login_required
def create_fin_report_version():
    try:
        data = request.get_json() or {}
        upload_id = data.get('upload_id')
        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400
        try:
            upload_uuid = uuid.UUID(upload_id)
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        # Determine next version number per upload
        from sqlalchemy import func
        next_num = (db.session.query(func.max(FinancialReportVersion.version_number))
                    .filter(FinancialReportVersion.upload_id == upload_uuid)
                    .scalar() or 0) + 1

        v = FinancialReportVersion(
            upload_id=upload_uuid,
            version_number=next_num,
            summary=data.get('summary'),
            insights=data.get('insights'),
            risks=data.get('risks'),
            recommendations=data.get('recommendations'),
            generated_by_llm=bool(data.get('generated_by_llm', False)),
            llm_model_used=data.get('llm_model_used'),
            llm_prompt_version=data.get('llm_prompt_version'),
            download_link_pdf=data.get('download_link_pdf'),
            download_link_excel=data.get('download_link_excel'),
            report_metadata=data.get('report_metadata') or {}
        )
        db.session.add(v)
        db.session.commit()
        return jsonify(v.to_dict()), 201
    except Exception:
        current_app.logger.exception("Create report version failed")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# Update a version
@report_gen_bp.route('/api/fin/report/versions/<version_id>', methods=['PUT'])
@login_required
def update_fin_report_version(version_id: str):
    try:
        try:
            version_uuid = uuid.UUID(version_id)
        except ValueError:
            return jsonify({"error": "Invalid version_id format"}), 400
        v = FinancialReportVersion.query.filter_by(version_id=version_uuid).first()
        if not v:
            return jsonify({"error": "Not found"}), 404

        data = request.get_json() or {}
        # Only update allowed fields
        for field in ['summary', 'insights', 'risks', 'recommendations', 'llm_model_used', 'llm_prompt_version', 'download_link_pdf', 'download_link_excel', 'report_metadata']:
            if field in data:
                setattr(v, field, data[field])
        db.session.commit()
        return jsonify(v.to_dict()), 200
    except Exception:
        current_app.logger.exception("Update report version failed")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# Delete a version
@report_gen_bp.route('/api/fin/report/versions/<version_id>', methods=['DELETE'])
@login_required
def delete_fin_report_version(version_id: str):
    try:
        try:
            version_uuid = uuid.UUID(version_id)
        except ValueError:
            return jsonify({"error": "Invalid version_id format"}), 400
        v = FinancialReportVersion.query.filter_by(version_id=version_uuid).first()
        if not v:
            return jsonify({"error": "Not found"}), 404
        db.session.delete(v)
        db.session.commit()
        return jsonify({"deleted": True, "version_id": version_id}), 200
    except Exception:
        current_app.logger.exception("Delete report version failed")
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


# Download a version
@report_gen_bp.route('/api/fin/report/versions/<version_id>/download', methods=['GET'])
@login_required
def download_fin_report_pdf(version_id: str):
    """Download the generated PDF for a specific report version.
    Resolves the relative path stored in FinancialReportVersion.download_link_pdf
    and streams the file as an attachment.
    """
    try:
        # Validate version_id
        try:
            version_uuid = uuid.UUID(version_id)
        except ValueError:
            return jsonify({"error": "Invalid version_id format"}), 400

        # Lookup version
        v = FinancialReportVersion.query.filter_by(version_id=version_uuid).first()
        if not v:
            return jsonify({"error": "Report version not found"}), 404

        # Ensure we have a stored PDF link
        rel_path = (v.download_link_pdf or '').strip()
        if not rel_path:
            return jsonify({"error": "No PDF available for this version yet"}), 404

        # Resolve absolute path
        try:
            # Use FilePersistenceManager's base path as root
            from utils.finance_file_manager import FilePersistenceManager
            fm = FilePersistenceManager()
            base_root = os.path.normpath(fm.base_path)

            # If rel_path is anchored at data/finance_report_gen/uploads, map to fm.base_path
            norm_rel = rel_path.replace('\\', '/').lstrip('/')
            anchor = 'data/finance_report_gen/uploads/'
            if norm_rel.startswith(anchor):
                tail = norm_rel[len(anchor):]
                abs_path = os.path.join(base_root, tail)
            else:
                # Otherwise, treat it as relative to CWD
                abs_path = os.path.join(os.getcwd(), norm_rel)

            abs_path = os.path.normpath(abs_path)
        except Exception:
            current_app.logger.exception("Failed to resolve PDF file path")
            return jsonify({"error": "Failed to resolve PDF file path"}), 500

        # Check existence
        if not os.path.exists(abs_path):
            return jsonify({"error": "PDF file not found on server", "path": rel_path}), 404

        # Stream file as attachment
        try:
            filename = os.path.basename(abs_path) or 'financial_report.pdf'
            return send_file(abs_path, mimetype='application/pdf', as_attachment=True, download_name=filename)
        except Exception:
            current_app.logger.exception("Failed to stream PDF file")
            return jsonify({"error": "Failed to stream PDF file"}), 500
    except Exception:
        current_app.logger.exception("Download PDF endpoint failed")
        return jsonify({"error": "Internal server error"}), 500
