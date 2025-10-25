from models.contact_model import db, Contact
from models.lead_model import Lead
import uuid
from sqlalchemy import and_
from datetime import datetime
from flask import current_app

class ContactController:
    CONTACT_FIELD_MAPPING = {
        'phone': 'phone',
        'owner phone': 'owner_phone_number',
        'owner_phone': 'owner_phone_number',
        'company phone': 'company_phone',
        'company_phone': 'company_phone',
        'owner_first_name': 'owner_first_name',
        'owner first name': 'owner_first_name',
        'owner_last_name': 'owner_last_name',
        'owner last name': 'owner_last_name',
        'owner title': 'owner_title',
        'owner_title': 'owner_title',
        'owner linkedin': 'owner_linkedin',
        'owner_linkedin': 'owner_linkedin',
        'owner_email': 'owner_email',
        'owner email': 'owner_email',
        'city': 'city',
        'state': 'state',
    }

    @staticmethod
    def add_contact(lead_id, contact_data, is_primary=False):
        """
        Add a contact to a lead, with deduplication logic.
        Returns (contact, created: bool, reason: str)
        """
        try:
            current_app.logger.info(f"[Contact] Attempting to add contact for lead_id={lead_id}, is_primary={is_primary}, add data is {contact_data}")
            # Normalize contact_data: ensure all values are scalars, not Series or single-item lists/tuples
            for k, v in list(contact_data.items()):
                # Handle pandas Series
                if hasattr(v, 'to_list'):
                    vals = v.to_list()
                    contact_data[k] = vals[0] if vals else ''
                elif hasattr(v, 'iloc'):
                    contact_data[k] = v.iloc[0] if not v.empty else ''
                elif isinstance(v, (list, tuple)) and len(v) == 1:
                    contact_data[k] = v[0]
                elif isinstance(v, (list, tuple)) and len(v) == 0:
                    contact_data[k] = ''
            # Deduplication: check if a contact with the same owner first and last name exists for this lead
            # query = Contact.query.filter(Contact.lead_id == lead_id)

            # owner_first_name = contact_data.get('owner_first_name')
            # owner_last_name = contact_data.get('owner_last_name')

            # if owner_first_name is not None:
            #     query = query.filter(Contact.owner_first_name == str(owner_first_name))
            # if owner_last_name is not None:
            #     query = query.filter(Contact.owner_last_name == str(owner_last_name))

            # New Deduplication: Check based on phone numbers and email for the same lead
            query = Contact.query.filter(Contact.lead_id == lead_id)

            dedupe_fields_map = {
                'phone': 'phone',
                'owner phone': 'owner_phone_number',
                'company phone': 'company_phone',
                'owner_email': 'owner_email'
            }

            # Build list of conditions, ensuring that at least one of these fields has a value in contact_data
            # This avoids creating duplicates if all phone/email fields are empty in the incoming data
            has_dedupe_data = False
            conditions = []
            for csv_field, db_field in dedupe_fields_map.items():
                value = contact_data.get(csv_field)
                if value and str(value).strip() != '-': # Check if value is not empty or default placeholder
                    conditions.append(getattr(Contact, db_field) == str(value).strip())
                    has_dedupe_data = True

            # Only apply deduplication query if there's actual data in the dedupe fields
            if has_dedupe_data:
                # Combine conditions with OR for fields that are meant to be unique across all of them (e.g. if any of these phones or email matches)
                # OR if you mean that ALL provided fields must match (e.g. phone AND email AND owner_phone_number match), use and_(*conditions)
                # Based on the request, it seems like if any of them match for the same lead, it's a duplicate.
                # However, for contact deduplication, it's more common for a set of fields to uniquely identify a contact.
                # Given the user's previous request to consider different phone numbers as new rows, I'll assume an OR logic here for uniqueness within the contact table.
                # But if a new row is explicitly requested, it is a new contact. Thus, it should be AND logic for existing logic. Reverting back to previous AND logic based on the user's previous context.
                query = query.filter(*conditions)

            existing = query.first()
            if existing:
                current_app.logger.info(f"[Contact] Duplicate contact found for lead_id={lead_id}, skipping add.")
                current_app.logger.info(f"[Contact] Update contact  for lead_id={lead_id}.")
                 # Update the existing contact with new, non-empty data from the CSV
                is_updated = False
                for csv_field, db_field in ContactController.CONTACT_FIELD_MAPPING.items():
                    if csv_field in contact_data:
                        new_value = str(contact_data[csv_field]).strip()
                        # Only update if the new value is not empty/placeholder
                        if new_value and new_value != '-' and getattr(existing, db_field) != new_value:
                            setattr(existing, db_field, new_value)
                            is_updated = True
                
                existing.updated_at = datetime.utcnow()
                db.session.add(existing)
                return existing, False, 'updated' if is_updated else 'duplicate'

            # Create new contact
            # Map incoming contact_data keys to database column names and ensure values are strings
            processed_contact_data = {}
            for csv_field, db_field in ContactController.CONTACT_FIELD_MAPPING.items():
                value = contact_data.get(csv_field)
                if value is not None:
                    processed_contact_data[db_field] = str(value)

            contact = Contact(
                lead_id=lead_id,
                is_primary=is_primary,
                **processed_contact_data
            )
            db.session.add(contact)
            current_app.logger.info(f"[Contact] Contact added successfully for lead_id={lead_id}, contact_id={contact.contact_id}")
            return contact, True, 'created'
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Contact] Error adding contact for lead_id={lead_id}: {str(e)}")
            return None, False, f'error: {str(e)}'

    @staticmethod
    def get_contacts_for_lead(lead_id):
        try:
            contacts = Contact.query.filter_by(lead_id=lead_id).all()
            current_app.logger.info(f"[Contact] Retrieved {len(contacts)} contacts for lead_id={lead_id}")
            return contacts
        except Exception as e:
            current_app.logger.error(f"[Contact] Error retrieving contacts for lead_id={lead_id}: {str(e)}")
            return []

    @staticmethod
    def update_contact(contact_id, update_data):
        try:
            contact = Contact.query.get(contact_id)
            if not contact:
                current_app.logger.warning(f"[Contact] Contact not found for update: contact_id={contact_id}")
                return None
            for k, v in update_data.items():
                if k in Contact.__table__.columns.keys():
                    setattr(contact, k, v)
            contact.updated_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.info(f"[Contact] Contact updated successfully: contact_id={contact_id}")
            return contact
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Contact] Error updating contact_id={contact_id}: {str(e)}")
            return None

    @staticmethod
    def delete_contact(contact_id):
        try:
            contact = Contact.query.get(contact_id)
            if not contact:
                current_app.logger.warning(f"[Contact] Contact not found for delete: contact_id={contact_id}")
                return False
            db.session.delete(contact)
            db.session.commit()
            current_app.logger.info(f"[Contact] Contact deleted successfully: contact_id={contact_id}")
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Contact] Error deleting contact_id={contact_id}: {str(e)}")
            return False

    @staticmethod
    def get_contact_by_id(contact_id):
        try:
            contact = Contact.query.get(contact_id)
            return contact
        except Exception as e:
            current_app.logger.error(f"[Contact] Error retrieving contact_id={contact_id}: {str(e)}")
            return None