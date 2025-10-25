from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from controllers.user_lead_draft_controller import UserLeadDraftController

draft_bp = Blueprint('draft_bp', __name__)

@draft_bp.route('/drafts/<string:lead_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite_lead(lead_id):
    """
    Toggles the favorite status of a lead for the current user.
    """
    success, result = UserLeadDraftController.toggle_favorite(current_user.user_id, lead_id)

    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500

    return jsonify(result), 200

@draft_bp.route('/drafts/favorites', methods=['GET'])
@login_required
def get_favorite_leads():
    """
    Gets a list of all favorite leads for the current user.
    """
    success, result = UserLeadDraftController.get_favorite_drafts(current_user.user_id)

    if not success:
        return jsonify({"error": result}), 500

    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/note', methods=['POST'])
@login_required
def add_or_update_note(lead_id):
    """
    Add or update a note for a draft.
    """
    data = None
    try:
        data = request.get_json()
    except Exception:
        pass
    note_content = data.get('note') if data else None
    if note_content is None:
        return jsonify({"error": "Missing note content."}), 400
    success, result = UserLeadDraftController.add_or_update_note(current_user.user_id, lead_id, note_content)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/note', methods=['GET'])
@login_required
def get_note(lead_id):
    """
    Get the note for a draft.
    """
    success, result = UserLeadDraftController.get_note(current_user.user_id, lead_id)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/note', methods=['DELETE'])
@login_required
def delete_note(lead_id):
    """
    Delete the note for a draft.
    """
    success, result = UserLeadDraftController.delete_note(current_user.user_id, lead_id)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/person/favorite', methods=['POST'])
@login_required
def person_toggle_favorite(lead_id):
    """
    Toggles the favorite status of a person for the current user in a draft.
    """
    success, result = UserLeadDraftController.person_toggle_favorite(current_user.user_id, lead_id)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/person/note', methods=['POST'])
@login_required
def person_add_or_update_note(lead_id):
    """
    Add or update a note for a person in a draft.
    """
    data = None
    try:
        data = request.get_json()
    except Exception:
        pass
    note_content = data.get('note') if data else None
    if note_content is None:
        return jsonify({"error": "Missing note content."}), 400
    success, result = UserLeadDraftController.person_add_or_update_note(current_user.user_id, lead_id, note_content)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/person/note', methods=['GET'])
@login_required
def person_get_note(lead_id):
    """
    Get the note for a person in a draft.
    """
    success, result = UserLeadDraftController.person_get_note(current_user.user_id, lead_id)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/<string:lead_id>/person/note', methods=['DELETE'])
@login_required
def person_delete_note(lead_id):
    """
    Delete the note for a person in a draft.
    """
    success, result = UserLeadDraftController.person_delete_note(current_user.user_id, lead_id)
    if not success:
        if "Draft not found" in str(result):
            return jsonify({"error": result}), 404
        return jsonify({"error": result}), 500
    return jsonify(result), 200

@draft_bp.route('/drafts/person/favorites', methods=['GET'])
@login_required
def get_person_favorite_leads():
    """
    Gets a list of all person favorite leads for the current user.
    """
    success, result = UserLeadDraftController.get_person_favorite_drafts(current_user.user_id)
    if not success:
        return jsonify({"error": result}), 500
    return jsonify(result), 200