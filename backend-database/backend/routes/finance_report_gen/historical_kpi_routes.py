from flask import current_app, Blueprint, request, jsonify
from flask_login import login_required
from controllers.finance_report_gen.historical_kpi_controller import HistoricalKPIController
import uuid

historical_kpi_bp = Blueprint("historical_kpi", __name__)

@historical_kpi_bp.route('/api/fin/kpi/historical/calculate', methods=['POST'])
@login_required
def calculate_historical_kpis():
    """
    Calculate and store historical KPIs
    POST: {"upload_id": "uuid", "period_type": "quarterly"}
    """
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        period_type = data.get('period_type')  # Optional: monthly, quarterly, yearly

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        controller = HistoricalKPIController()
        result = controller.calculate_historical_kpis(upload_id, period_type)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"API error in calculate_historical_kpis: {str(e)}")
        return jsonify({"error": f"Error occurred during historical KPI calculation: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/trends', methods=['GET'])
@login_required
def get_kpi_trends():
    """
    Get KPI trends for charts
    GET: ?upload_id=uuid&kpi_names=Net Profit Margin,ROA&period_type=quarterly&periods=12
    """
    try:
        from urllib.parse import unquote

        upload_id = request.args.get('upload_id')
        kpi_names_str = request.args.get('kpi_names', '')
        period_type = request.args.get('period_type', 'monthly')
        periods = int(request.args.get('periods', 12))

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        # Parse KPI names - handle URL decoding and spaces
        if kpi_names_str:
            # URL decode the string to handle %20 and other encoded characters
            decoded_kpi_names_str = unquote(kpi_names_str)
            # Split by comma and clean up each name
            kpi_names = [name.strip() for name in decoded_kpi_names_str.split(',') if name.strip()]
        else:
            kpi_names = []

        if not kpi_names:
            return jsonify({"error": "No KPI names provided"}), 400

        current_app.logger.info(f"[API] Requested KPI names: {kpi_names}")

        controller = HistoricalKPIController()
        result = controller.get_kpi_trends(upload_id, kpi_names, period_type, periods)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"API error in get_kpi_trends: {str(e)}")
        return jsonify({"error": f"Error occurred while getting KPI trends: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/period-suggestions', methods=['GET'])
@login_required
def get_period_suggestions():
    """
    Get suggested period divisions
    GET: ?upload_id=uuid
    """
    try:
        upload_id = request.args.get('upload_id')

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        controller = HistoricalKPIController()
        result = controller.get_period_division_suggestions(upload_id)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"API error in get_period_suggestions: {str(e)}")
        return jsonify({"error": f"Error occurred while getting period suggestions: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/custom-formula', methods=['POST'])
@login_required
def calculate_custom_kpi():
    """
    Calculate custom KPI with formula
    POST: {"upload_id": "uuid", "formula": "revenue / total_assets", "period_type": "monthly"}
    """
    try:
        data = request.get_json()
        upload_id = data.get('upload_id')
        formula = data.get('formula')
        period_type = data.get('period_type', 'monthly')

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        if not formula:
            return jsonify({"error": "Missing formula"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        controller = HistoricalKPIController()
        result = controller.calculate_custom_kpi(upload_id, formula, period_type)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        current_app.logger.error(f"API error in calculate_custom_kpi: {str(e)}")
        return jsonify({"error": f"Error occurred during custom KPI calculation: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/historical/list', methods=['GET'])
@login_required
def list_historical_kpis():
    """
    List historical KPI data for an upload
    GET: ?upload_id=uuid&kpi_name=Net Profit Margin&period_type=monthly&limit=50
    """
    try:
        from models.finance_report_gen.kpi_historical_data_model import KPIHistoricalData
        from models.lead_model import db

        upload_id = request.args.get('upload_id')
        kpi_name = request.args.get('kpi_name')
        period_type = request.args.get('period_type')
        limit = int(request.args.get('limit', 50))

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        # Build query
        query = KPIHistoricalData.query.filter(KPIHistoricalData.upload_id == upload_id)

        if kpi_name:
            query = query.filter(KPIHistoricalData.kpi_name == kpi_name)

        if period_type:
            query = query.filter(KPIHistoricalData.period_type == period_type)

        # Order by period start date descending and limit
        historical_kpis = query.order_by(KPIHistoricalData.period_start_date.desc()).limit(limit).all()

        # Convert to dict
        kpi_data = [kpi.to_dict() for kpi in historical_kpis]

        return jsonify({
            "success": True,
            "upload_id": upload_id,
            "total_records": len(kpi_data),
            "historical_kpis": kpi_data
        }), 200

    except Exception as e:
        current_app.logger.error(f"API error in list_historical_kpis: {str(e)}")
        return jsonify({"error": f"Error occurred while listing historical KPIs: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/available-kpis', methods=['GET'])
@login_required
def get_available_kpis():
    """
    Get list of available KPIs for an upload
    GET: ?upload_id=uuid
    """
    try:
        from models.finance_report_gen.kpi_historical_data_model import KPIHistoricalData
        from models.lead_model import db

        upload_id = request.args.get('upload_id')

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        # Get unique KPI names for this upload
        kpi_names = db.session.query(KPIHistoricalData.kpi_name, KPIHistoricalData.kpi_category).filter(
            KPIHistoricalData.upload_id == upload_id
        ).distinct().all()

        available_kpis = [
            {
                "kpi_name": kpi_name,
                "kpi_category": kpi_category
            } for kpi_name, kpi_category in kpi_names
        ]

        return jsonify({
            "success": True,
            "upload_id": upload_id,
            "available_kpis": available_kpis,
            "total_kpis": len(available_kpis)
        }), 200

    except Exception as e:
        current_app.logger.error(f"API error in get_available_kpis: {str(e)}")
        return jsonify({"error": f"Error occurred while getting available KPIs: {str(e)}"}), 500

@historical_kpi_bp.route('/api/fin/kpi/historical/periods', methods=['GET'])
@login_required
def get_kpi_data_by_periods():
    """
    Get KPI data organized by all period types (monthly, quarterly, yearly) in one call
    GET: ?upload_id=uuid&limit=1000
    Returns: {periods: {monthly: {monthly1: {kpi1: value}}, quarterly: {quarterly1: {kpi1: value}}, yearly: {yearly1: {kpi1: value}}}}
    """
    try:
        from models.finance_report_gen.kpi_historical_data_model import KPIHistoricalData
        from models.lead_model import db

        upload_id = request.args.get('upload_id')
        limit = int(request.args.get('limit', 1000))

        if not upload_id:
            return jsonify({"error": "Missing upload_id"}), 400

        try:
            uuid.UUID(upload_id)  # Validate UUID
        except ValueError:
            return jsonify({"error": "Invalid upload_id format"}), 400

        # Build query - get all period types except daily
        query = KPIHistoricalData.query.filter(
            KPIHistoricalData.upload_id == upload_id,
            KPIHistoricalData.calculation_status == 'calculated',
            KPIHistoricalData.period_type.in_(['monthly', 'quarterly', 'yearly'])  # Only these three types
        )

        # Order by period type, then by period start date ascending
        historical_kpis = query.order_by(
            KPIHistoricalData.period_type.asc(),
            KPIHistoricalData.period_start_date.asc()
        ).limit(limit).all()

        if not historical_kpis:
            return jsonify({
                "success": False,
                "error": "No historical KPI data found",
                "upload_id": upload_id,
                "periods": {},
                "metadata": {
                    "total_periods": 0,
                    "total_kpis": 0,
                    "kpi_names": [],
                    "period_names": []
                }
            }), 200

        # Organize data by periods with proper naming
        periods_data = {
            "monthly": {},
            "quarterly": {},
            "yearly": {}
        }
        kpi_names_set = set()
        period_names_list = []
        period_type_counts = {'monthly': 0, 'quarterly': 0, 'yearly': 0}

        for kpi_record in historical_kpis:
            period_type = kpi_record.period_type
            period_type_counts[period_type] += 1

            # Create period name like "monthly1", "quarterly1", "yearly1"
            period_name = f"{period_type}{period_type_counts[period_type]}"

            kpi_name = kpi_record.kpi_name
            kpi_value = float(kpi_record.kpi_value) if kpi_record.kpi_value else 0

            # Initialize period if not exists
            if period_name not in periods_data[period_type]:
                periods_data[period_type][period_name] = {}

            # Add KPI value to period
            periods_data[period_type][period_name][kpi_name] = kpi_value

            # Collect metadata
            kpi_names_set.add(kpi_name)

            # Add period info to period_names list (only once per period)
            if not any(p['name'] == period_name for p in period_names_list):
                period_names_list.append({
                    "name": period_name,
                    "start": kpi_record.period_start_date.isoformat(),
                    "end": kpi_record.period_end_date.isoformat()
                })

        # Convert sets to sorted lists for metadata
        kpi_names_list = sorted(list(kpi_names_set))

        # Sort period_names by name
        period_names_list.sort(key=lambda x: x['name'])

        # Calculate total periods across all types
        total_periods = sum(len(periods_data[pt]) for pt in periods_data)

        # Create response
        response_data = {
            "success": True,
            "upload_id": upload_id,
            "periods": periods_data,
            "metadata": {
                "total_periods": total_periods,
                "total_kpis": len(kpi_names_list),
                "kpi_names": kpi_names_list,
                "period_names": period_names_list,
                "period_counts": {
                    "monthly": len(periods_data["monthly"]),
                    "quarterly": len(periods_data["quarterly"]),
                    "yearly": len(periods_data["yearly"])
                },
                "total_records": len(historical_kpis),
                "date_range": {
                    "start": min([kpi.period_start_date for kpi in historical_kpis]).isoformat(),
                    "end": max([kpi.period_end_date for kpi in historical_kpis]).isoformat()
                }
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        current_app.logger.error(f"API error in get_kpi_data_by_periods: {str(e)}")
        return jsonify({"error": f"Error occurred while getting KPI data by periods: {str(e)}"}), 500
