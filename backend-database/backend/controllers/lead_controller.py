from flask import request, redirect, render_template, flash, url_for, jsonify, current_app
from models.lead_model import db, Lead
from models.audit_logs_model import AuditLog
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from sqlalchemy import text
from controllers.search_log_controller import SearchLogController
from flask_login import current_user
import time
import re
import logging
from thefuzz import fuzz
import threading
from models.user_model import User
from routes.apollo_aws_routes import (
    apollo_people_lookup,
    apollo_company_lookup_by_name,
    apollo_company_lookup_by_domain,
)
from routes.growjo_aws_apis.growjo_aws_routes import (
    growjo_query_companies_by_names,
    growjo_query_by_industry_location,
)
from models.edit_lead_drafts_model import EditLeadDraft
from models.user_lead_drafts_model import UserLeadDraft
from models.audit_log_model import LeadAuditLog
from models.user_subscription_model import UserSubscription
from models.locations_model import Location
from data.industry_names.industry_names import INDUSTRIES
from models.industry_naics_mapping_model import IndustryNAICSMappings

_industries_cache = {"data": None, "timestamp": None}
_cache_lock = threading.Lock()

class LeadController:
    @staticmethod
    def get_all_leads():
        """Get all leads for view, with optional search and filters from request.args"""
        query = Lead.query.filter_by(deleted=False)
        args = request.args

        # Basic search across multiple fields
        search = args.get('search', '').strip()
        if search:
            current_app.logger.info(f"[Lead] Search applied: {search}")
            search_pattern = f"%{search.lower()}%"
            query = query.filter(
                db.or_(
                    db.func.lower(Lead.company).like(search_pattern),
                    db.func.lower(Lead.owner_first_name).like(search_pattern),
                    db.func.lower(Lead.owner_last_name).like(search_pattern),
                    db.func.lower(Lead.owner_email).like(search_pattern),
                    db.func.lower(Lead.phone).like(search_pattern),
                    db.func.lower(Lead.owner_title).like(search_pattern),
                    db.func.lower(Lead.city).like(search_pattern),
                    db.func.lower(Lead.state).like(search_pattern),
                    db.func.lower(Lead.website).like(search_pattern),
                    db.func.lower(Lead.company_linkedin).like(search_pattern),
                    db.func.lower(Lead.industry).like(search_pattern),
                    db.func.lower(Lead.product_category).like(search_pattern),
                    db.func.lower(Lead.business_type).like(search_pattern),
                    db.func.lower(Lead.status).like(search_pattern),
                )
            )

        # Individual filters
        if args.get('company'):
            current_app.logger.info(f"[Lead] Filter by company: {args.get('company')}")
            query = query.filter(Lead.company == args.get('company'))
        if args.get('location'):
            current_app.logger.info(f"[Lead] Filter by location: {args.get('location')}")
            location = args.get('location')
            if ',' in location:
                city, state = [x.strip() for x in location.split(',', 1)]
                query = query.filter(Lead.city == city, Lead.state == state)
            else:
                query = query.filter(db.or_(Lead.city == location, Lead.state == location))
        if args.get('role'):
            current_app.logger.info(f"[Lead] Filter by role: {args.get('role')}")
            query = query.filter(Lead.owner_title == args.get('role'))
        if args.get('status'):
            current_app.logger.info(f"[Lead] Filter by status: {args.get('status')}")
            query = query.filter(Lead.status == args.get('status'))
        if args.get('revenue'):
            current_app.logger.info(f"[Lead] Filter by revenue: {args.get('revenue')}")
            try:
                revenue_val = float(args.get('revenue').replace('$','').replace('M','000000').replace('K','000'))
                query = query.filter(Lead.revenue >= revenue_val)
            except:
                pass

        # Advanced filter for revenue
        adv_field = args.get('adv_field_0')
        adv_operator = args.get('adv_operator_0')
        adv_value = args.get('adv_value_0')
        if adv_field == 'revenue' and adv_operator and adv_value:
            try:
                revenue_val = float(adv_value)
                if adv_operator == 'less':
                    query = query.filter(Lead.revenue < revenue_val)
                elif adv_operator == 'greater':
                    query = query.filter(Lead.revenue > revenue_val)
                elif adv_operator == 'equals':
                    query = query.filter(Lead.revenue == revenue_val)
            except Exception as e:
                current_app.logger.error(f"Error parsing advanced revenue filter: {e}")

        try:
            leads = query.order_by(Lead.updated_at.desc()).all()
            current_app.logger.info(f"[Lead] Fetched {len(leads)} leads with applied filters.")
            return leads
        except Exception as e:
            current_app.logger.error(f"[Lead] Error fetching leads: {str(e)}")
            return []

    @staticmethod
    def get_lead_by_id(lead_id):
        """Get lead by ID"""
        try:
            lead = Lead.query.filter_by(lead_id=lead_id).first_or_404()
            current_app.logger.info(f"[Lead] Fetched lead with ID: {lead_id}")
            return lead
        except Exception as e:
            current_app.logger.error(f"[Lead] Error fetching lead by ID {lead_id}: {str(e)}")
            return None

    @staticmethod
    def get_leads_by_ids(lead_ids):
        """Get multiple leads by their IDs"""
        # return Lead.query.filter(Lead.id.in_(lead_ids), Lead.deleted==False).all()
        return Lead.query.filter(Lead.lead_id.in_(lead_ids)).all()

    @staticmethod
    def create_lead(form_data):
        """Create new lead from form data"""
        # # --- NAICS Categorization (Future Implementation) ---
        # # 1. Map industry to NAICS codes
        # industry_str = form_data.get('industry', '')
        # naics_data = LeadController._map_industry_to_naics(industry_str)

        # Create lead with basic information
        lead = Lead(
            # Base data
            search_keyword=form_data.get('search_keyword', {}),

            # Company info
            company=form_data.get('company', ''),
            website=form_data.get('website', ''),
            industry=form_data.get('industry', ''),
            # # Add NAICS data to the new lead object
            # naics_code=naics_data.get('similar_naics_industry_code'),
            # naics_industry_name=naics_data.get('similar_naics_industry_name'),
            # naics_parent_code=naics_data.get('parent_naics_industry_code'),
            # naics_parent_name=naics_data.get('parent_naics_industry_name'),
            product_category=form_data.get('product_category', ''),
            business_type=form_data.get('business_type', ''),
            employees=form_data.get('employees', None),
            revenue=form_data.get('revenue', None),
            year_founded=form_data.get('year_founded', ''),
            bbb_rating=form_data.get('bbb_rating', ''),

            # Location
            street=form_data.get('street', ''),
            city=form_data.get('city', ''),
            state=form_data.get('state', ''),

            # Company contact
            company_phone=form_data.get('company_phone', ''),
            company_linkedin=form_data.get('company_linkedin', ''),

            # Owner/contact info
            owner_first_name=form_data.get('owner_first_name', ''),
            owner_last_name=form_data.get('owner_last_name', ''),
            owner_title=form_data.get('owner_title', ''),
            owner_linkedin=form_data.get('owner_linkedin', ''),
            owner_phone_number=form_data.get('owner_phone_number', ''),
            owner_email=form_data.get('owner_email', ''),
            phone=form_data.get('phone', ''),

            # Source
            source=form_data.get('source', 'manual')
        )

        # Handle dynamic fields if provided
        if form_data.getlist('dynamic_field_name[]') and form_data.getlist('dynamic_field_value[]'):
            field_names = form_data.getlist('dynamic_field_name[]')
            field_values = form_data.getlist('dynamic_field_value[]')

            for i in range(len(field_names)):
                if field_names[i] and field_values[i]:
                    # Set attribute if it exists on Lead model
                    field_name = field_names[i]
                    if hasattr(lead, field_name):
                        setattr(lead, field_name, field_values[i])

        try:
            db.session.add(lead)
            db.session.commit()
            current_app.logger.info("Lead added successfully!")
            return True, "Lead added successfully!"
        except IntegrityError as e:
            db.session.rollback()
            if "lead_owner_email_key" in str(e):
                current_app.logger.warning(f"Error: Email address '{lead.owner_email}' is already in use. Please use a different email.")
                return False, f"Error: Email address '{lead.owner_email}' is already in use. Please use a different email."
            elif "lead_phone_key" in str(e):
                current_app.logger.warning(f"Error: Phone number '{lead.phone}' is already in use. Please use a different phone number.")
                return False, f"Error: Phone number '{lead.phone}' is already in use. Please use a different phone number."
            else:
                current_app.logger.error(f"Error adding lead: {str(e)}")
                return False, f"Error adding lead: {str(e)}"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding lead: {str(e)}")
            return False, f"Error adding lead: {str(e)}"

    @staticmethod
    def update_lead(lead_id, form_data):
        """Update lead data"""
        try:
            lead = Lead.query.get(lead_id)
            if not lead:
                current_app.logger.warning("Lead not found")
                return False, "Lead not found"

            # Handle numeric fields - convert empty strings to None
            employees = form_data.get('employees')
            revenue = form_data.get('revenue')
            year_founded = form_data.get('year_founded')

            # Handle employees
            if employees and str(employees).strip():
                try:
                    lead.employees = int(employees)
                except (ValueError, TypeError):
                    lead.employees = None
            else:
                lead.employees = None

            # Handle revenue
            if revenue is not None and str(revenue).strip():
                try:
                    if isinstance(revenue, (int, float)):
                        lead.revenue = float(revenue)
                    else:
                        lead.revenue = float(str(revenue).strip())
                except (ValueError, TypeError):
                    lead.revenue = None
            else:
                lead.revenue = None

            # Handle year_founded - allow empty, "-"
            if year_founded and year_founded.strip() and year_founded.strip() != '-':
                try:
                    lead.year_founded = int(year_founded.strip())
                except ValueError:
                    # If not a valid number, store as string or None
                    lead.year_founded = year_founded.strip() if year_founded.strip() else None
            else:
                lead.year_founded = None

            # Update other fields
            lead.company = form_data.get('company')
            lead.website = form_data.get('website') or None
            lead.industry = form_data.get('industry') or None
            lead.product_category = form_data.get('product_category') or None
            lead.business_type = form_data.get('business_type') or None
            lead.bbb_rating = form_data.get('bbb_rating') or None
            lead.street = form_data.get('street') or None
            lead.city = form_data.get('city') or None
            lead.state = form_data.get('state') or None
            lead.company_phone = form_data.get('company_phone') or None
            lead.company_linkedin = form_data.get('company_linkedin') or None
            lead.owner_first_name = form_data.get('owner_first_name') or None
            lead.owner_last_name = form_data.get('owner_last_name') or None
            # Handle owner_email - allow empty or validate format
            owner_email = form_data.get('owner_email', '').strip()
            if owner_email and '@' in owner_email:
                lead.owner_email = owner_email
            else:
                lead.owner_email = None
            lead.owner_title = form_data.get('owner_title') or None
            lead.owner_linkedin = form_data.get('owner_linkedin') or None
            lead.owner_phone_number = form_data.get('owner_phone_number') or None
            lead.source = form_data.get('source')
            lead.status = form_data.get('status', 'new')
            lead.updated_at = datetime.utcnow()

            db.session.commit()
            current_app.logger.info("Lead updated successfully")
            return True, "Lead updated successfully"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating lead: {str(e)}")
            return False, f"Error updating lead: {str(e)}"

    @staticmethod
    def delete_lead(lead_id, current_user=None):
        """Soft delete lead by ID"""
        lead = Lead.query.filter_by(lead_id=lead_id, deleted=False).first_or_404()

        try:
            # Store old values for audit log
            old_values = lead.to_dict()

            # Mark as deleted
            lead.deleted = True
            lead.deleted_at = datetime.utcnow()

            # Create audit log entry
            if current_user:
                AuditLog.log_change(
                    user_id=getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None) or str(current_user),
                    action_type='delete',
                    table_affected='leads',
                    record_id=str(lead_id),
                    old_values=old_values,
                    new_values={'deleted': True, 'deleted_at': lead.deleted_at.isoformat()},
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )

            db.session.commit()
            current_app.logger.info("Lead deleted successfully!")
            return True, "Lead deleted successfully!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting lead: {str(e)}")
            return False, f"Error deleting lead: {str(e)}"

    @staticmethod
    def delete_multiple_leads(lead_ids, current_user=None):
        """Soft delete multiple leads by their IDs"""
        if not lead_ids:
            current_app.logger.warning("No leads selected for deletion.")
            return False, "No leads selected for deletion."

        try:
            # Get all leads to be deleted
            leads = Lead.query.filter(
                Lead.lead_id.in_(lead_ids),
                Lead.deleted == False
            ).all()

            if not leads:
                current_app.logger.warning("No leads found with the specified IDs.")
                return False, "No leads found with the specified IDs."

            now = datetime.utcnow()
            deleted_count = 0

            for lead in leads:
                old_values = lead.to_dict()
                lead.deleted = True
                lead.deleted_at = now
                deleted_count += 1

                if current_user:
                    AuditLog.log_change(
                        user_id=getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None) or str(current_user),
                        action_type='delete',
                        table_affected='leads',
                        record_id=str(lead.lead_id),
                        old_values=old_values,
                        new_values={'deleted': True, 'deleted_at': now.isoformat()},
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string
                    )

            db.session.commit()
            current_app.logger.info(f"{deleted_count} leads deleted successfully!")
            return True, f"{deleted_count} leads deleted successfully!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting leads: {str(e)}")
            return False, f"Error deleting leads: {str(e)}"

    @staticmethod
    def restore_lead(lead_id, current_user=None):
        """Restore a soft-deleted lead"""
        lead = Lead.query.filter_by(lead_id=lead_id).first_or_404()

        try:
            # Store old values for audit log
            old_values = lead.to_dict()

            # Restore lead
            lead.deleted = False
            lead.deleted_at = None

            # Create audit log entry
            if current_user:
                AuditLog.log_change(
                    user_id=getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None) or str(current_user),
                    action_type='update',
                    table_affected='leads',
                    record_id=str(lead_id),
                    old_values=old_values,
                    new_values={'deleted': False, 'deleted_at': None},
                    ip_address=request.remote_addr,
                    user_agent=request.user_agent.string
                )

            db.session.commit()
            current_app.logger.info("Lead restored successfully!")
            return True, "Lead restored successfully!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error restoring lead: {str(e)}")
            return False, f"Error restoring lead: {str(e)}"

    @staticmethod
    def restore_multiple_leads(lead_ids, current_user=None):
        """Restore multiple soft-deleted leads"""
        if not lead_ids:
            current_app.logger.warning("No leads selected for restoration.")
            return False, "No leads selected for restoration."

        try:
            # Get all leads to be restored
            leads = Lead.query.filter(Lead.lead_id.in_(lead_ids)).all()

            if not leads:
                current_app.logger.warning("No leads found with the specified IDs.")
                return False, "No leads found with the specified IDs."

            # Restore leads and create audit logs
            for lead in leads:
                old_values = lead.to_dict()
                lead.deleted = False
                lead.deleted_at = None

                if current_user:
                    AuditLog.log_change(
                        user_id=getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None) or str(current_user),
                        action_type='update',
                        table_affected='leads',
                        record_id=str(lead.lead_id),
                        old_values=old_values,
                        new_values={'deleted': False, 'deleted_at': None},
                        ip_address=request.remote_addr,
                        user_agent=request.user_agent.string
                    )

            db.session.commit()
            current_app.logger.info(f"{len(leads)} leads restored successfully!")
            return True, f"{len(leads)} leads restored successfully!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error restoring leads: {str(e)}")
            return False, f"Error restoring leads: {str(e)}"

    @staticmethod
    def get_leads_json():
        """Get all leads as JSON for API"""
        leads = Lead.query.filter_by(deleted=False).all()
        return [lead.to_dict() for lead in leads]

    @staticmethod
    def normalize_company_name(name):
        if not name:
            return ''
        return re.sub(r'[^a-zA-Z0-9 ]', '', name).strip().lower()

    @staticmethod
    def find_duplicate_lead(lead_data):
        """Find a duplicate lead using lead_id, composite key, company, or contact info."""
        Lead = globals()['Lead']  # for staticmethod context
        db = globals()['db']
        logging = globals()['logging']
        # 1. Check by lead_id
        if lead_data.get('lead_id'):
            lead = Lead.query.filter_by(lead_id=lead_data['lead_id']).first()
            if lead:
                current_app.logger.info(f"Duplicate found by lead_id")
                return lead, 'lead_id'
        # 2. Composite key: normalized company + owner_email + phone
        company = LeadController.normalize_company_name(lead_data.get('company', ''))
        owner_email = str(lead_data.get('owner_email', '')).strip().lower()
        phone = str(lead_data.get('phone', '')).strip()
        # Validate email: must contain '@'
        if '@' not in owner_email:
            owner_email = ''
        # Validate phone: must be numeric (after removing non-digits)
        phone_numeric = re.sub(r'\D', '', phone)
        if not phone_numeric:
            phone = ''
        else:
            phone = phone_numeric
        if company and owner_email and phone:
            lead = Lead.query.filter(
                db.func.lower(db.func.replace(db.func.replace(db.func.replace(Lead.company, '-', ''), '.', ''), ',', '')) == company,
                db.func.lower(Lead.owner_email) == owner_email,
                Lead.phone == phone,
                Lead.deleted == False
            ).first()
            if lead:
                current_app.logger.info(f"Duplicate found by composite (company+email+phone)")
                return lead, 'composite (company+email+phone)'
        # 3. Normalized company only
        if company:
            lead = Lead.query.filter(
                db.func.lower(db.func.replace(db.func.replace(db.func.replace(Lead.company, '-', ''), '.', ''), ',', '')) == company,
                Lead.deleted == False
            ).first()
            if lead:
                current_app.logger.info(f"Duplicate found by company only")
                return lead, 'company only'
        # 4. owner_email or phone only
        query = Lead.query
        conditions = []
        if owner_email:
            conditions.append(Lead.owner_email == owner_email)
        if phone:
            conditions.append(Lead.phone == phone)
        if conditions:
            lead = query.filter(db.or_(*conditions)).first()
            if lead:
                current_app.logger.info(f"Duplicate found by email or phone only")
                return lead, 'email or phone only'
        return None, None

    @staticmethod
    def update_existing_lead(existing_lead, lead_data):
        logging = globals()['logging']
        updated = False
        updated_fields = []
        for key, value in lead_data.items():
            if hasattr(existing_lead, key):
                current_value = getattr(existing_lead, key)
                if value not in [None, '', 'N/A'] and current_value != value:
                    setattr(existing_lead, key, value)
                    updated = True
                    updated_fields.append(key)
                    logging.info(f"Updated field '{key}': '{current_value}' -> '{value}'")
            else:
                logging.warning(f"Skipping key '{key}': not in Lead model")
        return updated, updated_fields

    @staticmethod
    def create_new_lead(lead_data):
        Lead = globals()['Lead']
        db = globals()['db']
        logging = globals()['logging']
        clean_data = {k: v for k, v in lead_data.items() if v is not None and v != ""}
        lead = Lead(**clean_data)
        db.session.add(lead)
        db.session.commit()
        logging.info(f"Added new lead with ID: {lead.lead_id}")
        return lead

    @staticmethod
    def add_or_update_lead_by_match(lead_data):
        """Add a new lead or update existing lead by matching lead_id, company+email+phone, or email/phone only"""
        # # --- NAICS Categorization (Future Implementation) ---
        # # If we are creating a new lead, map its industry to NAICS.
        # if not LeadController.find_duplicate_lead(lead_data)[0]:
        #     industry_str = lead_data.get('industry', '')
        #     naics_data = LeadController._map_industry_to_naics(industry_str)
        #     if naics_data:
        #         lead_data['naics_code'] = naics_data.get('similar_naics_industry_code')
        #         lead_data['naics_industry_name'] = naics_data.get('similar_naics_industry_name')
        #         lead_data['naics_parent_code'] = naics_data.get('parent_naics_industry_code')
        #         lead_data['naics_parent_name'] = naics_data.get('parent_naics_industry_name')

        try:
            current_app.logger.info(f"Processing lead: {lead_data.get('company')}")
            existing_lead, match_type = LeadController.find_duplicate_lead(lead_data)
            if existing_lead:
                current_app.logger.info(f"Duplicate found by {match_type}")
                updated, updated_fields = LeadController.update_existing_lead(existing_lead, lead_data)
                try:
                    if updated:
                        db.session.commit()
                        msg = {
                            "status": "updated",
                            "message": f"Lead was found as a duplicate (matched by {match_type}) and has been updated.",
                            "updated_fields": updated_fields,
                            "match_type": match_type,
                            "lead_id": existing_lead.lead_id
                        }
                        current_app.logger.info(msg["message"])
                        return (True, msg)
                    else:
                        msg = {
                            "status": "no_change",
                            "message": f"Lead was found as a duplicate (matched by {match_type}) but no changes were needed.",
                            "match_type": match_type,
                            "lead_id": existing_lead.lead_id
                        }
                        current_app.logger.info(msg["message"])
                        return (True, msg)
                except Exception as e:
                    db.session.rollback()
                    msg = {
                        "status": "error",
                        "message": f"Error updating duplicate lead (matched by {match_type}): {str(e)}",
                        "match_type": match_type
                    }
                    current_app.logger.error(msg["message"])
                    return (False, msg)
            else:
                try:
                    lead = LeadController.create_new_lead(lead_data)
                    msg = {
                        "status": "created",
                        "message": "Lead was created successfully (no duplicate found).",
                        "lead_id": lead.lead_id
                    }
                    current_app.logger.info(msg["message"])
                    return (True, msg)
                except Exception as e:
                    db.session.rollback()
                    msg = {
                        "status": "error",
                        "message": f"Error creating new lead: {str(e)}"
                    }
                    current_app.logger.error(msg["message"])
                    return (False, msg)
        except IntegrityError as e:
            db.session.rollback()
            msg = {
                "status": "error",
                "message": f"IntegrityError while adding/updating lead: {str(e)}"
            }
            current_app.logger.error(msg["message"])
            return (False, msg)
        except Exception as e:
            db.session.rollback()
            msg = {
                "status": "error",
                "message": f"General exception while adding/updating lead: {str(e)}"
            }
            current_app.logger.error(msg["message"])
            return (False, msg)

    @staticmethod
    def search_leads_by_industry_location(industry, location, current_user=None):
        """Search leads by industry and location, with plan-based filtering/masking."""
        try:
            query = Lead.query.filter_by(deleted=False)
            if industry:
                try:
                    # Ensure proper encoding and handle special characters
                    industry_clean = str(industry).encode('utf-8', errors='ignore').decode('utf-8')
                    # Support comma-separated multiple industries by building an OR over tokens
                    tokens = [t.strip() for t in industry_clean.split(',') if t and t.strip()]
                    if len(tokens) > 1:
                        or_conditions = [Lead.industry.ilike(f"%{t}%") for t in tokens]
                        query = query.filter(db.or_(*or_conditions))
                    else:
                        query = query.filter(Lead.industry.ilike(f"%{industry_clean}%"))
                except Exception as e:
                    current_app.logger.error(f"[Lead] Error processing industry filter: {str(e)}")
                    # Fallback to simple filter
                    query = query.filter(Lead.industry.ilike(f"%{str(industry)}%"))

            if location:
                if ',' in location:
                    # Split location into city and state
                    city_part, state_part, country_part = [part.strip() for part in location.split(',')]
                    location_filter = db.and_(
                        Lead.city.ilike(city_part),
                        Lead.state.ilike(state_part),
                        Lead.country.ilike(country_part)
                    )
                    not_null_or_empty = db.and_(
                        Lead.city.isnot(None) & (Lead.city != ''),
                        Lead.state.isnot(None) & (Lead.state != ''),
                        Lead.country.isnot(None) & (Lead.country != '')
                    )
                    query = query.filter(location_filter, not_null_or_empty)
                # else:
                #     location_stripped = location.strip()
                #     if len(location_stripped) == 2:
                #         # Treat as state code, exact match
                #         location_filter = Lead.state.ilike(location_stripped)
                #         not_null_or_empty = Lead.state.isnot(None) & (Lead.state != '')
                #         query = query.filter(location_filter, not_null_or_empty)
                #     else:
                #         # Treat as city, exact match
                #         location_filter = Lead.city.ilike(location_stripped)
                #         not_null_or_empty = Lead.city.isnot(None) & (Lead.city != '')
                #         query = query.filter(location_filter, not_null_or_empty)

            leads = query.all()
            # Filter each lead to only include the specified fields
            allowed_fields = [
                'lead_id', 'company', 'industry', 'street', 'city', 'state',
                'bbb_rating', 'company_phone', 'website', 'country'
            ]
            leads = [
                {field: getattr(lead, field, None) for field in allowed_fields}
                for lead in leads
            ]

            current_app.logger.info(f"[Lead] Found {len(leads)} leads for industry='{industry}', location='{location}'")

            processed_results = []

            allowed_fields_free = [
                'lead_id', 'company', 'industry', 'street', 'city', 'state',
                'bbb_rating', 'company_phone', 'website', 'country']

            for lead in leads:
                lead_dict = {}
                # Check user role and tier
                if current_user and hasattr(current_user, 'role') and current_user.role != 'user':
                    # Non-user roles get full details
                    lead_dict = lead
                elif current_user and hasattr(current_user, 'tier') and current_user.tier == 'free':
                    # Filter and mask for Free plan (only for regular users)
                    for field in allowed_fields_free:
                        if field in lead:
                            value = lead[field]
                            if field == 'company_phone':
                                # Always mask, even if empty
                                last4 = str(value)[-4:] if value and len(str(value)) > 4 else ''
                                lead_dict[field] = '********' + last4
                            elif field == 'owner_email':
                                # Always mask, even if empty
                                if value:
                                    email_parts = str(value).split('@')
                                    if len(email_parts) > 1:
                                        lead_dict[field] = f"{email_parts[0][0] if email_parts[0] else ''}***@{email_parts[1]}"
                                    else:
                                        lead_dict[field] = f"{email_parts[0][0] if email_parts[0] else ''}***@******"
                                else:
                                    lead_dict[field] = "***@*****.***"
                            elif value is not None and value != '':
                                lead_dict[field] = value
                            else:
                                lead_dict[field] = value if value is not None else ''
                else:
                    # Return full details for other plans
                    lead_dict = lead

                processed_results.append(lead_dict)

            return processed_results
        except Exception as e:
            current_app.logger.error(f"[Lead] Error searching leads by industry/location: {str(e)}")
            return []

    @staticmethod
    def search_leads_by_industries_location_new(industries, location=None, current_user=None):
        """
        Search leads by a list of industries plus optional location, reusing
        search_leads_by_industry_location logic per industry and de-duplicating results.

        Args:
            industries (list[str]): List of industry names
            location (str|None): Optional location string "City, State, Country" format
            current_user: Flask-Login current_user for masking rules

        Returns:
            list[dict]: Same shape as search_leads_by_industry_location output
        """
        try:
            # Validate and normalize input list
            if not industries or not isinstance(industries, (list, tuple)):
                return []

            cleaned = []
            for item in industries:
                if isinstance(item, str):
                    # Split comma-separated values into tokens
                    parts = [p.strip() for p in item.split(',') if p and p.strip()]
                    if parts:
                        cleaned.extend(parts)

            if not cleaned:
                return []

            aggregated = []
            seen_ids = set()

            # Deduplicate while preserving order
            seen_token = set()
            deduped = []
            for token in cleaned:
                if token.lower() not in seen_token:
                    seen_token.add(token.lower())
                    deduped.append(token)

            for ind in deduped:
                try:
                    # Ensure the industry string is properly encoded
                    industry_clean = str(ind).encode('utf-8', errors='ignore').decode('utf-8')
                    results = LeadController.search_leads_by_industry_location(industry_clean, location, current_user)
                    for r in results:
                        lead_id = r.get('lead_id')
                        if lead_id not in seen_ids:
                            seen_ids.add(lead_id)
                            aggregated.append(r)
                except Exception as e:
                    current_app.logger.error(f"[Lead] Error processing industry '{ind}': {str(e)}")
                    continue

            return aggregated
        except Exception as e:
            current_app.logger.error(f"[Lead] Error searching leads by industries/location: {str(e)}")
            return []

    @staticmethod
    def search_leads_by_industry_location_old(industry=None, location=None):
        """Search leads by industry and location (for API), with search_logs caching"""
        # Temporarily commenting out caching logic to ensure function returns Lead instances for decorator
        # start_time = time.time()
        # # Normalize and hash the search
        # search_hash = SearchLogController.normalize_and_hash(industry, location)
        # # Check if log exists
        # log = SearchLogController.get_log_by_hash(search_hash)
        # if log and log.search_parameters:
        #     # Increment result_count and update timestamp
        #     log.result_count += 1
        #     log.searched_at = datetime.utcnow()
        #     db.session.commit()
        #     return log.search_parameters  # Already JSON serializable

        # If no log found or caching is off, search leads
        query = Lead.query.filter_by(deleted=False)
        if industry:
            query = query.filter(db.func.lower(Lead.industry) == industry.lower())

        if location:
            # Restore location filtering to search city, state, or street and exclude nulls/empty
            # Search in city, state, or street
            location_filter = db.or_(
                Lead.city.ilike(f"%{location}%"),
                Lead.state.ilike(f"%{location}%"),
                Lead.street.ilike(f"%{location}%") # Add street to the search
            )
            # Ensure at least one of city, state, or street is not null/empty
            not_null_or_empty = db.or_(
                Lead.city.isnot(None) & (Lead.city != ''),
                Lead.state.isnot(None) & (Lead.state != ''),
                Lead.street.isnot(None) & (Lead.street != '')
            )
            query = query.filter(location_filter, not_null_or_empty)

        leads = query.all()

        # Temporarily commenting out search logging
        # exec_time = int((time.time() - start_time) * 1000)
        # # Log the search
        # user_id = getattr(current_user, 'id', None) or getattr(current_user, 'user_id', None)
        # if user_id:
        #     search_query = f"industry: {industry}, location: {location}"
        #     SearchLogController.log_search(
        #         user_id=user_id,
        #         search_query=search_query,
        #         search_hash=search_hash,
        #         search_parameters=[lead.to_dict() for lead in leads], # Log dictionary representation
        #         result_count=len(leads),
        #         execution_time_ms=exec_time
        #     )

        return leads # Return list of Lead model instances for the decorator

    @staticmethod
    def get_unique_industries():
        """Return a normalized, unique, sorted list of industries from the Lead table."""
        try:
            industries_query = db.session.query(Lead.industry).filter(
                Lead.industry.isnot(None),
                Lead.industry != '',
                Lead.deleted == False
            ).distinct().all()
            industries = [row[0] for row in industries_query]
            # Normalize: strip, remove empty, deduplicate, sort
            normalized = sorted(set(i.strip() for i in industries if i and i.strip()))
            current_app.logger.info(f"[Lead] Found {len(normalized)} unique industries.")
            return normalized
        except Exception as e:
            current_app.logger.error(f"[Lead] Error getting unique industries: {str(e)}")
            return []

    @staticmethod
    def get_states_with_cities():
        """Return a dict: {country: {state_code: [city1, city2, ...], ...}, ...} from the locations table."""
        locations = Location.query.all()
        country_state_city_map = {}
        for loc in locations:
            country = loc.country
            state = loc.state_code
            city = loc.city_original
            if country not in country_state_city_map:
                country_state_city_map[country] = {}
            if state not in country_state_city_map[country]:
                country_state_city_map[country][state] = set()
            country_state_city_map[country][state].add(city)
        # Convert sets to sorted lists
        for country in country_state_city_map:
            country_state_city_map[country] = {state: sorted(list(cities)) for state, cities in country_state_city_map[country].items()}
        return country_state_city_map

    @staticmethod
    def get_clustered_industries(similarity_threshold: int = 85) -> list:
        """
        Processes a list of industries to cluster them into high-level categories.

        Args:
            similarity_threshold (int): The fuzzy matching score (0-100) required to
                                        group two industries together.

        Returns:
            A dictionary containing the clean list of clustered industries.
        """
        raw_industries = LeadController.get_unique_industries()
        if not raw_industries:
            return []

        # List of common, non-descriptive words to remove.
        suffixes_to_remove = [
            'services', 'service', 'solutions', 'consulting', 'systems',
            'agency', 'firm', 'group', 'company', 'inc', 'ltd', 'llc',
            'advisory', 'management', 'technologies', 'technology'
        ]

        # Build a regex pattern to match these words at the end of a string
        suffix_pattern = r'\b(' + '|'.join(suffixes_to_remove) + r')\b'

        def _normalize(text: str) -> str:
            text = text.lower()
            # Remove content in parentheses
            text = re.sub(r'\(.*\?)', '', text)
            # Remove punctuation and special characters except '-'
            text = re.sub(r'[^\w\s-]', ' ', text)
            # Remove common suffixes
            text = re.sub(suffix_pattern, '', text, flags=re.IGNORECASE)

            return ' '.join(text.split())

        normalized_industries = sorted(
            list(set(_normalize(name) for name in raw_industries)),
            key=len
        )

        # Sort by length and cluster
        clusters = []
        for industry_name in normalized_industries:
            if not industry_name:
                continue

            # Check if this industry fits into an existing cluster
            found_match = False
            for cluster_rep in clusters:
                score = fuzz.token_set_ratio(industry_name, cluster_rep)
                if score > similarity_threshold:
                    found_match = True
                    break

            # If no match was found, this is a new, unique cluster
            if not found_match:
                clusters.append(industry_name)

        # Post-process for clean output: title case and sort alphabetically
        final_clusters = sorted([c.title() for c in clusters])
        current_app.logger.info(f"[Lead] Clustered {len(raw_industries)} unique industries into {len(final_clusters)}.")
        return final_clusters

    @staticmethod
    def get_clustered_industries_v2(
        similarity_threshold: int = 60,
    ) -> list:
        """
        Normalizes and clusters a list of industries against a predefined industry list,
        """
        with _cache_lock:
            is_cache_valid = False
            if _industries_cache["data"] and _industries_cache["timestamp"]:
                # Check if the cache is less than 24 hours old
                if datetime.now() - _industries_cache["timestamp"] < timedelta(days=1):
                    is_cache_valid = True

            if is_cache_valid:
                current_app.logger.info("Serving clustered industries from daily cache.")
                return _industries_cache["data"]

            raw_industries = LeadController.get_unique_industries()
            if not raw_industries:
                return []

            def _normalize(text: str) -> str:
                text = text.lower()
                text = re.sub(r'\(.*\?)', '', text) # remove text in parentheses
                text = re.sub(r"'", '', text) # remove '
                text = re.sub(r'[^\w\s-]', ' ', text) # remove punctuation except hyphens
                return ' '.join(text.split())

            normalized_unique_industries = set(_normalize(name) for name in raw_industries if name)

            final_clusters = set()

            final_clusters
            for raw_industry in normalized_unique_industries:
                best_match = None
                highest_score = 0

                for common_industry in INDUSTRIES:
                    score = fuzz.partial_ratio(common_industry.lower(), raw_industry)
                    if score > highest_score:
                        highest_score = score
                        best_match = common_industry

                # If we found a strong match, use the common industry name
                if highest_score >= similarity_threshold:
                    final_clusters.add(best_match)
                else:
                    final_clusters.add(raw_industry)

            final_list = list(final_clusters)
            sorted_clusters = sorted([c.title() for c in list(final_list)])

            # Caching
            _industries_cache["data"] = sorted_clusters
            _industries_cache["timestamp"] = datetime.now()

            current_app.logger.info(f"Clustered {len(raw_industries)} industries into {len(sorted_clusters)} categories and cached the result.")

            return sorted_clusters

    @staticmethod
    def search_persons_by_filters(person_name, industry=None, business_type=None, year_founded=None, country=None, state=None, city=None):
        """
        Search persons by exact case-insensitive matching with additional filters.

        Args:
            person_name (str): Required person name to search for
            industry (str, optional): Industry filter
            business_type (str, optional): Business type filter
            year_founded (str, optional): Year founded filter
            country (str, optional): Country filter
            state (str, optional): State filter
            city (str, optional): City filter

        Returns:
            dict: {"total": count, "persons": [lead.to_dict()], "error": message if any}
        """
        try:
            # Validate required field
            if not person_name:
                return {"error": "person_name is required", "total": 0, "persons": []}

            # Normalize person name
            normalized_input = re.sub(r'\s+', ' ', person_name or '').strip().lower()
            if not normalized_input:
                return {"error": "person_name is required", "total": 0, "persons": []}

            current_app.logger.info(f"[Lead] Searching persons with filters: person_name='{person_name}', industry='{industry}', business_type='{business_type}', year_founded='{year_founded}', location='{country}, {state}, {city}'")

            # Base query (no deleted filter as requested)
            query = Lead.query

            # Build normalized SQL expressions for person name
            norm_first = db.func.lower(
                db.func.trim(
                    db.func.regexp_replace(db.func.coalesce(Lead.owner_first_name, ''), r'\s+', ' ', 'g')
                )
            )
            norm_last = db.func.lower(
                db.func.trim(
                    db.func.regexp_replace(db.func.coalesce(Lead.owner_last_name, ''), r'\s+', ' ', 'g')
                )
            )
            norm_full = db.func.lower(
                db.func.trim(
                    db.func.regexp_replace(
                        db.func.concat(
                            db.func.coalesce(Lead.owner_first_name, ''),
                            ' ',
                            db.func.coalesce(Lead.owner_last_name, '')
                        ),
                        r'\s+', ' ', 'g'
                    )
                )
            )

            # Apply person name filter
            if ' ' in normalized_input:
                # Expecting "First Last" exact match
                query = query.filter(norm_full == normalized_input)
            else:
                # Single-word: match either first or last name exactly
                query = query.filter(db.or_(norm_first == normalized_input, norm_last == normalized_input))

            # Apply additional filters if provided
            if industry:
                norm_industry = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.industry, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_industry == industry.lower().strip())

            if business_type:
                norm_business_type = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.business_type, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_business_type == business_type.lower().strip())

            if year_founded:
                # Convert to string since year_founded is String type in database
                query = query.filter(Lead.year_founded == str(year_founded))

            if country:
                norm_country = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.country, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_country == country.lower().strip())

            if state:
                norm_state = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.state, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_state == state.lower().strip())

            if city:
                norm_city = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.city, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_city == city.lower().strip())

            # Apply sorting priority: person_name, industry, business_type, year_founded, location
            query = query.order_by(
                Lead.owner_first_name.asc(),
                Lead.owner_last_name.asc(),
                Lead.industry.asc(),
                Lead.business_type.asc(),
                Lead.year_founded.asc(),
                Lead.country.asc(),
                Lead.state.asc(),
                Lead.city.asc()
            )

            total = query.count()
            rows = query.limit(100).all()

            # Apollo enrichment (best-effort, never fail the endpoint)
            apollo_people = []
            try:
                # Try by full name only (primary key)
                if person_name:
                    apollo_people = apollo_people_lookup(name=person_name, limit=25) or []
                # If not found and a company filter exists, try by organization name
                if not apollo_people and industry is None and business_type is None and year_founded is None:
                    # Use company filter analogs when provided via location (none here), so skip
                    pass
            except Exception as _:
                apollo_people = []

            current_app.logger.info(f"[Lead] Found {total} persons matching criteria, returning {len(rows)} (limited to 100)")

            return {
                "total": total,
                "persons": [lead.to_dict() for lead in rows],
                "apollo_people": apollo_people,
            }

        except Exception as e:
            current_app.logger.error(f"[Lead] Error searching persons: {str(e)}")
            return {"error": f"Error searching persons: {str(e)}", "total": 0, "persons": []}

    @staticmethod
    def search_companies_by_filters(company_name, industry=None, business_type=None, year_founded=None, country=None, state=None, city=None):
        """
        Search companies by exact case-insensitive matching with additional filters.

        Args:
            company_name (str): Required company name to search for
            industry (str, optional): Industry filter
            business_type (str, optional): Business type filter
            year_founded (str, optional): Year founded filter
            country (str, optional): Country filter
            state (str, optional): State filter
            city (str, optional): City filter

        Returns:
            dict: {"total": count, "companies": [lead.to_dict()], "error": message if any}
        """
        try:
            # Validate required field
            if not company_name:
                return {"error": "company_name is required", "total": 0, "companies": []}

            # Normalize company name
            normalized_company = re.sub(r'\s+', ' ', company_name or '').strip().lower()
            if not normalized_company:
                return {"error": "company_name is required", "total": 0, "companies": []}

            current_app.logger.info(f"[Lead] Searching companies with filters: company_name='{company_name}', industry='{industry}', business_type='{business_type}', year_founded='{year_founded}', location='{country}, {state}, {city}'")

            # Base query (no deleted filter as requested)
            query = Lead.query

            # Normalized company expression in SQL
            norm_company = db.func.lower(
                db.func.trim(
                    db.func.regexp_replace(db.func.coalesce(Lead.company, ''), r'\s+', ' ', 'g')
                )
            )

            # Apply company name filter
            query = query.filter(norm_company == normalized_company)

            # Apply additional filters if provided
            if industry:
                norm_industry = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.industry, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_industry == industry.lower().strip())

            if business_type:
                norm_business_type = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.business_type, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_business_type == business_type.lower().strip())

            if year_founded:
                # Convert to string since year_founded is String type in database
                query = query.filter(Lead.year_founded == str(year_founded))

            if country:
                norm_country = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.country, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_country == country.lower().strip())

            if state:
                norm_state = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.state, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_state == state.lower().strip())

            if city:
                norm_city = db.func.lower(
                    db.func.trim(
                        db.func.regexp_replace(db.func.coalesce(Lead.city, ''), r'\s+', ' ', 'g')
                    )
                )
                query = query.filter(norm_city == city.lower().strip())

            # Apply sorting priority: company_name, industry, business_type, year_founded, location
            query = query.order_by(
                Lead.company.asc(),
                Lead.industry.asc(),
                Lead.business_type.asc(),
                Lead.year_founded.asc(),
                Lead.country.asc(),
                Lead.state.asc(),
                Lead.city.asc()
            )

            total = query.count()
            rows = query.limit(100).all()

            # Apollo enrichment (best-effort, never fail the endpoint)
            apollo_companies = []
            try:
                if company_name:
                    apollo_companies = apollo_company_lookup_by_name(company_name=company_name, limit=25) or []
                if not apollo_companies and (industry is None and business_type is None and year_founded is None):
                    # If user passed a website in company_name accidentally, try domain lookup too
                    if isinstance(company_name, str) and '.' in company_name:
                        from routes.apollo_aws_routes import _norm_domain
                        apollo_companies = apollo_company_lookup_by_domain(_norm_domain(company_name)) or []
            except Exception as _:
                apollo_companies = []

            current_app.logger.info(f"[Lead] Found {total} companies matching criteria, returning {len(rows)} (limited to 100)")

            # Growjo enrichment (best-effort)
            growjo_companies = []
            try:
                payload_names = [company_name] if company_name else []
                batch = growjo_query_companies_by_names(payload_names) if payload_names else []
                # Flatten items lists
                for entry in (batch or []):
                    for it in entry.get('items', []):
                        growjo_companies.append(it)
                # If location filters are provided, try industry+location query as well
                if industry and (city or state or country):
                    # Build location string like "City, State, Country"
                    parts = []
                    if city:
                        parts.append(str(city))
                    if state:
                        parts.append(str(state))
                    if country:
                        parts.append(str(country))
                    if parts:
                        loc = ', '.join(parts)
                        res = growjo_query_by_industry_location(industry, loc) or {}
                        growjo_companies.extend(res.get('items', []))
            except Exception as _:
                growjo_companies = []

            return {
                "total": total,
                "companies": [lead.to_dict() for lead in rows],
                "apollo_companies": apollo_companies,
                "growjo_companies": growjo_companies,
            }

        except Exception as e:
            current_app.logger.error(f"[Lead] Error searching companies: {str(e)}")
            return {"error": f"Error searching companies: {str(e)}", "total": 0, "companies": []}

    @staticmethod
    def batch_lookup_companies(company_names):
        """
        Batch lookup company_ids for multiple company names.
        EXACT Python equivalent of the working SQL query.
        """
        try:
            current_app.logger.info(f"[Lead] Batch lookup for {len(company_names)} companies")

            results = []
            found_count = 0
            not_found_count = 0

            for company_name in company_names:
                company_name = company_name.strip()
                if not company_name:
                    continue

                current_app.logger.info(f"[Lead] Searching for company: '{company_name}'")

                # ✅ EXACT Python equivalent of your working SQL:
                # SELECT lead_id, company, company_id, industry, source
                # FROM leads
                # WHERE deleted = false AND company ILIKE 'PayPal'
                # LIMIT 10;

                lead = Lead.query.filter(
                    Lead.deleted == False,
                    Lead.company.ilike(f"%{company_name}%")  # This is ILIKE equivalent
                ).first()

                if lead and lead.company_id:
                    results.append({
                        'company_name': company_name,
                        'company_id': lead.company_id,
                        'found': True,
                        'industry': lead.industry,
                        'website': lead.website,
                        'source': lead.source,
                        'matched_company': lead.company
                    })
                    found_count += 1
                    current_app.logger.info(f"[Lead] FOUND: '{company_name}' -> '{lead.company}' (ID: {lead.company_id})")
                else:
                    results.append({
                        'company_name': company_name,
                        'company_id': None,
                        'found': False,
                        'industry': None,
                        'website': None,
                        'source': None,
                        'matched_company': None
                    })
                    not_found_count += 1
                    current_app.logger.info(f"[Lead] NOT FOUND: '{company_name}'")

            current_app.logger.info(f"[Lead] Batch lookup completed. Found: {found_count}, Not found: {not_found_count}")

            return {
                'status': 'success',
                'message': f'Batch lookup completed. Found: {found_count}, Not found: {not_found_count}',
                'data': {
                    'results': results,
                    'summary': {
                        'total_requested': len(company_names),
                        'found': found_count,
                        'not_found': not_found_count
                    }
                }
            }

        except Exception as e:
            current_app.logger.error(f"[Lead] Error in batch company lookup: {str(e)}")
            return {'status': 'error', 'message': f'Error in batch company lookup: {str(e)}', 'data': None}

    # --- NEW NAICS-BASED INDUSTRY FUNCTIONS ---
    @staticmethod
    def get_parent_naics_industries():
        """
        [NEW] Fetches the unique parent NAICS industries from the new mapping table.
        This is intended to replace get_clustered_industries_v2.
        """
        try:
            # This requires the new IndustryNAICSMappings model and table.
            parent_industries = db.session.query(
                IndustryNAICSMappings.Parent_NAICS_Industry_Name,
                IndustryNAICSMappings.Parent_NAICS_Industry_Code
            ).distinct().order_by(IndustryNAICSMappings.Parent_NAICS_Industry_Name).all()

            results = [
                {"name": name, "code": code}
                for name, code in parent_industries
            ]
            current_app.logger.info(f"[NAICS] Fetched {len(results)} unique parent NAICS industries.")
            return results
        except Exception as e:
            current_app.logger.error(f"[NAICS] Error fetching parent NAICS industries: {str(e)}")
            return []

    @staticmethod
    def _map_industry_to_naics(industry_string):
        """
        [NEW HELPER] Finds the corresponding NAICS data for a given industry string.
        """
        if not industry_string:
            return {}
        try:
            # This requires the new IndustryNAICSMappings model and table.
            from models.industry_naics_mapping_model import IndustryNAICSMappings
            mapping = IndustryNAICSMappings.query.filter(
                db.func.lower(IndustryNAICSMappings.exact_industry) == db.func.lower(industry_string.strip())
            ).first()

            if mapping:
                return mapping.to_dict()
            return {}
        except Exception as e:
            current_app.logger.error(f"[NAICS] Error mapping industry '{industry_string}': {str(e)}")
            return {}

    @staticmethod
    def get_naics_data(parent_name=None, child_name=None):
        """
        [NEW] Fetches NAICS hierarchical data from the database.
        - If no params, returns all parents with their children.
        - If parent_name, returns that parent and its children.
        - If child_name, returns that child's parent and siblings.
        """
        try:
            # Base query for all mappings
            base_query = db.session.query(
                IndustryNAICSMappings.parent_naics_industry_name,
                IndustryNAICSMappings.parent_naics_industry_code,
                IndustryNAICSMappings.similar_naics_industry_name,
                IndustryNAICSMappings.similar_naics_industry_code
            ).distinct().order_by(
                IndustryNAICSMappings.parent_naics_industry_name,
                IndustryNAICSMappings.similar_naics_industry_name
            )

            if child_name:
                # Find the parent of the given child
                child_mapping = IndustryNAICSMappings.query.filter(
                    db.func.lower(IndustryNAICSMappings.similar_naics_industry_name) == child_name.lower()
                ).first()
                if not child_mapping:
                    return {"error": "Child category not found"}, 404
                # Set parent_name to the found parent to use the logic below
                parent_name = child_mapping.parent_naics_industry_name

            if parent_name:
                # Filter by a specific parent
                base_query = base_query.filter(
                    db.func.lower(IndustryNAICSMappings.parent_naics_industry_name) == parent_name.lower()
                )

            all_mappings = base_query.all()
            if not all_mappings:
                return [], 200

            # Structure the data
            results = {}
            for p_name, p_code, s_name, s_code in all_mappings:
                if p_name not in results:
                    results[p_name] = {
                        "parent_name": p_name,
                        "parent_code": p_code,
                        "children_count": 0,
                        "children": []
                    }
                # For now, count is 0 as lead table is not ready for this
                results[p_name]["children"].append({"name": s_name, "code": s_code})
                results[p_name]["children_count"] = len(results[p_name]["children"])

            # If a specific child was requested, we need to return the parent object and its children
            if child_name and parent_name in results:
                return {
                    "parent": {
                        "parent_name": results[parent_name]["name"],
                        "parent_code": results[parent_name]["code"],
                        "children_count": results[parent_name]["children_count"],
                        "children": results[parent_name]["children"]
                    }
                }, 200

            return list(results.values()), 200

        except Exception as e:
            current_app.logger.error(f"[NAICS] Error fetching NAICS data: {str(e)}")
            return {"error": f"An error occurred: {str(e)}"}, 500

    @staticmethod
    def get_exact_industries_by_parent_child(parent_name, child_name=None, use_child=True):
        """
        [NEW] Returns a list of distinct exact industries filtered by:
        - parent_name (optional)
        - child_name (optional; used only when use_child=True)

        Query logic:
        - If parent_name provided, filter by IndustryNAICSMappings.parent_naics_industry_name == parent_name (case-insensitive)
        - If use_child is True and child_name provided, filter by
          IndustryNAICSMappings.similar_naics_industry_name == child_name (case-insensitive)
        - If only child_name provided (no parent), search by child only

        Response: (list[str], http_status_code)
        """
        try:
            # Validate that at least one parameter is provided
            if not parent_name and not child_name:
                return {"error": "At least one of 'parent' or 'child' is required"}, 400

            # Base query selecting distinct exact industries
            query = db.session.query(
                IndustryNAICSMappings.exact_industry
            )

            # Apply parent filter if provided
            if parent_name and str(parent_name).strip():
                query = query.filter(
                    db.func.lower(IndustryNAICSMappings.parent_naics_industry_name) == str(parent_name).strip().lower()
                )

            # Apply child filter if provided and use_child is True
            if use_child and child_name and str(child_name).strip():
                query = query.filter(
                    db.func.lower(IndustryNAICSMappings.similar_naics_industry_name) == str(child_name).strip().lower()
                )

            rows = query.distinct().order_by(IndustryNAICSMappings.exact_industry).all()
            results = []
            for r in rows:
                if r and r[0]:
                    try:
                        # Ensure proper encoding
                        clean_industry = str(r[0]).encode('utf-8', errors='ignore').decode('utf-8')
                        if clean_industry.strip():
                            results.append(clean_industry)
                    except Exception as e:
                        current_app.logger.error(f"[NAICS] Error processing exact industry: {str(e)}")
                        continue
            return results, 200

        except Exception as e:
            current_app.logger.error(f"[NAICS] Error fetching exact industries: {str(e)}")
            return {"error": f"An error occurred: {str(e)}"}, 500

    @staticmethod
    def get_hierarchical_naics_data():
        """
        [NEW] Returns hierarchical NAICS data: Parent -> Children -> Exact Industries
        Optimized with single query and in-memory grouping for better performance.

        Returns: (list[dict], http_status_code)
        """
        try:
            # Single optimized query to get all data at once
            all_data = db.session.query(
                IndustryNAICSMappings.parent_naics_industry_name,
                IndustryNAICSMappings.parent_naics_industry_code,
                IndustryNAICSMappings.similar_naics_industry_name,
                IndustryNAICSMappings.similar_naics_industry_code,
                IndustryNAICSMappings.exact_industry
            ).order_by(
                IndustryNAICSMappings.parent_naics_industry_name,
                IndustryNAICSMappings.similar_naics_industry_name,
                IndustryNAICSMappings.exact_industry
            ).all()

            # Group data in memory for better performance
            hierarchy = {}

            for parent_name, parent_code, child_name, child_code, exact_industry in all_data:
                # Skip rows with null parent or child names
                if not parent_name or not child_name:
                    continue

                # Initialize parent if not exists
                if parent_name not in hierarchy:
                    hierarchy[parent_name] = {
                        "parent_name": parent_name,
                        "parent_code": parent_code or "",
                        "children": {}
                    }

                # Initialize child if not exists
                if child_name not in hierarchy[parent_name]["children"]:
                    hierarchy[parent_name]["children"][child_name] = {
                        "child_name": child_name,
                        "child_code": child_code or "",
                        "exact_industries": []
                    }

                # Add exact industry if it exists
                if exact_industry and exact_industry.strip():
                    hierarchy[parent_name]["children"][child_name]["exact_industries"].append(exact_industry)

            # Convert to final structure and sort
            result = []
            for parent_name in sorted(hierarchy.keys()):
                parent_data = hierarchy[parent_name]
                children_list = []

                for child_name in sorted(parent_data["children"].keys()):
                    child_data = parent_data["children"][child_name]
                    # Remove duplicates and sort exact industries (filter out None values)
                    exact_industries = [ei for ei in child_data["exact_industries"] if ei is not None]
                    child_data["exact_industries"] = sorted(list(set(exact_industries)))
                    children_list.append(child_data)

                parent_data["children"] = children_list
                result.append(parent_data)

            current_app.logger.info(f"[NAICS] Hierarchical data: {len(result)} parents with children and exact industries")
            return result, 200

        except Exception as e:
            current_app.logger.error(f"[NAICS] Error fetching hierarchical NAICS data: {str(e)}")
            return {"error": f"An error occurred: {str(e)}"}, 500