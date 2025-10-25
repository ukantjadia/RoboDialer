from flask import Blueprint, request, jsonify
from flask_login import login_required
from controllers.company_news_insight_controller import CompanyNewsInsightController

news_insight_bp = Blueprint('news_insight', __name__)

@news_insight_bp.route('/api/news_insights/', methods=['POST'])
@login_required
def create_news_insight():
    data = request.get_json()
    insight = CompanyNewsInsightController.create_insight(data)
    return jsonify(insight.to_dict()), 201

@news_insight_bp.route('/api/news_insights/', methods=['GET'])
@login_required
def list_news_insights():
    insights = CompanyNewsInsightController.list_insights()
    return jsonify([i.to_dict() for i in insights]), 200

@news_insight_bp.route('/api/news_insights/<int:insight_id>', methods=['GET'])
@login_required
def get_news_insight(insight_id):
    insight = CompanyNewsInsightController.get_insight(insight_id)
    if not insight:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(insight.to_dict()), 200

@news_insight_bp.route('/api/news_insights/<int:insight_id>', methods=['PUT'])
@login_required
def update_news_insight(insight_id):
    data = request.get_json()
    insight = CompanyNewsInsightController.update_insight(insight_id, data)
    if not insight:
        return jsonify({'error': 'Not found or forbidden'}), 404
    return jsonify(insight.to_dict()), 200

@news_insight_bp.route('/api/news_insights/<int:insight_id>', methods=['DELETE'])
@login_required
def delete_news_insight(insight_id):
    success = CompanyNewsInsightController.delete_insight(insight_id)
    if not success:
        return jsonify({'error': 'Not found or forbidden'}), 404
    return jsonify({'message': 'Deleted'}), 200

@news_insight_bp.route('/api/news_insights/standalone/', methods=['POST'])
@login_required
def create_standalone_news_insight():
    data = request.get_json()
    insight = CompanyNewsInsightController.create_standalone_insight(data)
    return jsonify(insight.to_dict()), 201

@news_insight_bp.route('/api/news_insights/standalone/', methods=['GET'])
@login_required
def list_standalone_news_insights():
    insights = CompanyNewsInsightController.list_standalone_insights()
    return jsonify([i.to_dict() for i in insights]), 200