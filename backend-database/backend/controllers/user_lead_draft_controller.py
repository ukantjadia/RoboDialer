from models.lead_model import db, Lead
from models.user_lead_drafts_model import UserLeadDraft
from flask import current_app
from sqlalchemy.orm.attributes import flag_modified

class UserLeadDraftController:
    @staticmethod
    def toggle_favorite(user_id, lead_id):
        """
        Toggles the 'is_favorite' status for a user's lead draft.
        If a draft doesn't exist for the user and lead, it creates one.
        """
        try:
            # Check if a draft already exists for this user and lead
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()

            if not draft:
                # If no draft exists, return an error. Do not create one.
                current_app.logger.warning(f"User {user_id} tried to favorite lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."

            # If draft exists, toggle its favorite status
            draft.is_favorite = not draft.is_favorite
            action = "favorited" if draft.is_favorite else "unfavorited"
            current_app.logger.info(f"User {user_id} {action} lead {lead_id}.")

            db.session.commit()
            return True, draft.to_dict()

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling favorite for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_favorite_drafts(user_id):
        """
        Retrieves all favorite lead drafts for a specific user.
        """
        try:
            favorite_drafts = UserLeadDraft.query.filter_by(user_id=user_id, is_favorite=True, is_deleted=False).all()
            return True, [draft.to_dict() for draft in favorite_drafts]
        except Exception as e:
            current_app.logger.error(f"Error fetching favorite drafts for user {user_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def add_or_update_note(user_id, lead_id, note_content):
        """
        Adds or updates a note for a user's lead draft (as JSON with content and timestamps).
        """
        from datetime import datetime
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to add/update note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            now = datetime.utcnow().isoformat()
            notes_json = draft.notes or {}
            if not notes_json.get('created_at'):
                notes_json['created_at'] = now
            notes_json['content'] = note_content
            notes_json['updated_at'] = now
            draft.notes = notes_json
            flag_modified(draft, "notes")  # Explicitly mark the field as modified
            db.session.commit()
            current_app.logger.info(f"User {user_id} added/updated note for lead {lead_id}.")
            return True, draft.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding/updating note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_note(user_id, lead_id):
        """
        Retrieves the note for a user's lead draft (as JSON).
        """
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to get note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            return True, draft.notes or {}
        except Exception as e:
            current_app.logger.error(f"Error fetching note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def delete_note(user_id, lead_id):
        """
        Deletes the note for a user's lead draft (clears the notes JSON).
        """
        from datetime import datetime
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to delete note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            draft.notes = None
            db.session.commit()
            current_app.logger.info(f"User {user_id} deleted note for lead {lead_id}.")
            return True, draft.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def person_toggle_favorite(user_id, lead_id):
        """
        Toggles the 'person_is_favorite' status for a user's lead draft.
        """
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to favorite person for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            draft.person_is_favorite = not draft.person_is_favorite
            action = "favorited" if draft.person_is_favorite else "unfavorited"
            current_app.logger.info(f"User {user_id} {action} person for lead {lead_id}.")
            db.session.commit()
            return True, draft.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error toggling person favorite for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def person_add_or_update_note(user_id, lead_id, note_content):
        """
        Adds or updates a note for a user's person (contact) in a lead draft (as JSON with content and timestamps).
        """
        from datetime import datetime
        try:
            current_app.logger.info(f"[DEBUG] Attempting to add/update person note. Content length: {len(note_content)}")
            current_app.logger.info(f"[DEBUG] Note content: {note_content}")

            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to add/update person note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."

            now = datetime.utcnow().isoformat()
            notes_json = draft.person_notes or {}
            current_app.logger.info(f"[DEBUG] Existing notes_json: {notes_json}")

            if not notes_json.get('created_at'):
                notes_json['created_at'] = now
            notes_json['content'] = note_content
            notes_json['updated_at'] = now

            current_app.logger.info(f"[DEBUG] Updated notes_json before save: {notes_json}")
            draft.person_notes = notes_json
            flag_modified(draft, "person_notes")  # Explicitly mark the field as modified

            try:
                db.session.commit()
                current_app.logger.info(f"[DEBUG] Successfully committed changes")
                # Verify the saved data
                saved_draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
                current_app.logger.info(f"[DEBUG] Saved person_notes: {saved_draft.person_notes}")
            except Exception as commit_error:
                current_app.logger.error(f"[DEBUG] Error during commit: {str(commit_error)}")
                raise commit_error

            current_app.logger.info(f"User {user_id} added/updated person note for lead {lead_id}.")
            return True, draft.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding/updating person note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def person_get_note(user_id, lead_id):
        """
        Retrieves the person note for a user's lead draft (as JSON).
        """
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to get person note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            return True, draft.person_notes or {}
        except Exception as e:
            current_app.logger.error(f"Error fetching person note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def person_delete_note(user_id, lead_id):
        """
        Deletes the person note for a user's lead draft (clears the person_notes JSON).
        """
        try:
            draft = UserLeadDraft.query.filter_by(user_id=user_id, lead_id=lead_id, is_deleted=False).first()
            if not draft:
                current_app.logger.warning(f"User {user_id} tried to delete person note for lead {lead_id}, but no draft exists.")
                return False, "Draft not found. User must interact with the lead first."
            draft.person_notes = None
            db.session.commit()
            current_app.logger.info(f"User {user_id} deleted person note for lead {lead_id}.")
            return True, draft.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting person note for user {user_id}, lead {lead_id}: {str(e)}")
            return False, str(e)

    @staticmethod
    def get_person_favorite_drafts(user_id):
        """
        Retrieves all drafts for a user where person_is_favorite is True.
        """
        try:
            favorite_drafts = UserLeadDraft.query.filter_by(user_id=user_id, person_is_favorite=True, is_deleted=False).all()
            return True, [draft.to_dict() for draft in favorite_drafts]
        except Exception as e:
            current_app.logger.error(f"Error fetching person favorite drafts for user {user_id}: {str(e)}")
            return False, str(e)