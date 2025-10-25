from flask import Blueprint, request, jsonify, current_app, render_template
from controllers.contact_controller import ContactController
from models.contact_model import Contact, db
from flask_login import login_required
from models.lead_model import Lead

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/api/contacts/', methods=['GET'])
@login_required
def list_contacts():
    lead_id = request.args.get('lead_id')
    if lead_id:
        contacts = ContactController.get_contacts_for_lead(lead_id)
    else:
        contacts = Contact.query.all()
    return jsonify([c.to_dict() for c in contacts])

@contact_bp.route('/api/contacts/all', methods=['GET'])
@login_required
def list_all_contacts():
    """Return all contacts in the database, with all lead fields prefixed as 'lead_'."""
    current_app.logger.info("[Contact API] list_all_contacts called")
    try:
        contacts = Contact.query.all()
        result = []
        for c in contacts:
            d = c.to_dict()
            lead = Lead.query.filter_by(lead_id=c.lead_id).first()
            if lead:
                lead_dict = lead.to_dict()
                for k, v in lead_dict.items():
                    d[f'lead_{k}'] = v
            result.append(d)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"[Contact API] Error retrieving all contacts: {str(e)}")
        return jsonify({'error': f'Failed to retrieve all contacts: {str(e)}'}), 500

@contact_bp.route('/api/contacts/<contact_id>', methods=['GET'])
@login_required
def get_contact(contact_id):
    contact = Contact.query.get(contact_id)
    if not contact:
        return jsonify({'error': 'Contact not found'}), 404
    return jsonify(contact.to_dict())

@contact_bp.route('/api/contacts/', methods=['POST'])
@login_required
def create_contact():
    data = request.json
    lead_id = data.get('lead_id')
    if not lead_id:
        return jsonify({'error': 'lead_id is required'}), 400
    is_primary = data.get('is_primary', False)
    contact, created, reason = ContactController.add_contact(lead_id, data, is_primary)
    if not created:
        return jsonify({'error': 'Duplicate contact', 'contact': contact.to_dict()}), 409
    db.session.commit()
    return jsonify(contact.to_dict()), 201

@contact_bp.route('/api/contacts/<contact_id>', methods=['PUT'])
@login_required
def update_contact(contact_id):
    data = request.json
    contact = ContactController.update_contact(contact_id, data)
    if not contact:
        return jsonify({'error': 'Contact not found'}), 404
    return jsonify(contact.to_dict())

@contact_bp.route('/api/contacts/<contact_id>', methods=['DELETE'])
@login_required
def delete_contact(contact_id):
    success = ContactController.delete_contact(contact_id)
    if not success:
        return jsonify({'error': 'Contact not found'}), 404
    return jsonify({'status': 'deleted'})

@contact_bp.route('/contacts/all_view', methods=['GET'])
@login_required
def view_all_contacts_page():
    """Display the page to view all contacts."""
    current_app.logger.info("[Contact] view_all_contacts_page called")
    return render_template('all_contacts.html')
