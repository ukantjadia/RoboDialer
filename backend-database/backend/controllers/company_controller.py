from flask import current_app
from models.lead_model import db
from models.company_model import Company
from models.company_credit_allocation_model import CompanyCreditAllocation
from models.user_model import User
from models.credits_log_model import CreditsLog
from datetime import datetime, timedelta
import uuid
from models.credit_transfer_log_model import CreditTransferLog

class CompanyController:
    
    @staticmethod
    def create_company(name, domain=None, industry=None, size='medium', subscription_tier=None, created_by=None, parent_company_id=None):
        """Create a new company account"""
        try:
            # Validate subscription tier
            valid_tiers = ['silver', 'gold', 'platinum', 'silver_annual', 'gold_annual', 'platinum_annual']
            # only validate if subscription_tier is filled
            if subscription_tier and subscription_tier not in valid_tiers:
                return False, f"Invalid subscription tier. Must be one of: {', '.join(valid_tiers)}"
            
            # Check if domain already exists
            if domain and Company.query.filter_by(domain=domain).first():
                return False, "Company with this domain already exists"
            
            # Validate parent company if provided
            if parent_company_id:
                parent_company = Company.query.get(parent_company_id)
                if not parent_company:
                    return False, "Parent company not found"
                if not created_by or not created_by.can_manage_company() or str(created_by.company_id) != str(parent_company_id):
                    return False, "You don't have permission to create sub-companies for this company"
            
            # Build kwargs for Company.create
            company_kwargs = dict(
                name=name,
                domain=domain,
                industry=industry,
                size=size,
                parent_company_id=parent_company_id,
                created_by=created_by
            )
            if subscription_tier:
                company_kwargs['subscription_tier'] = subscription_tier
            
            # Create company
            company = Company.create(**company_kwargs)
            
            # If created_by is provided, make them company admin
            if created_by:
                created_by.company_id = company.company_id
                created_by.is_company_admin = True
                created_by.company_role = 'admin'
                db.session.commit()
            
            # Initial allocation for admin: platinum = 0, else = total_credits
            initial_alloc = 0 if (company.subscription_tier or '').lower().startswith('platinum') else company.total_credits
            if not CompanyCreditAllocation.get_active_allocation(company.company_id, created_by.user_id):
                CompanyCreditAllocation.create(
                    company_id=company.company_id,
                    user_id=created_by.user_id,
                    credits_allocated=initial_alloc,
                    allocated_by=created_by.user_id,
                    notes='Initial allocation for company admin'
                )
            
            company_type = "sub-company" if parent_company_id else "company"
            current_app.logger.info(f"{company_type.title()} '{name}' created successfully with tier {company.subscription_tier}")
            return True, company
            
        except Exception as e:
            current_app.logger.error(f"Error creating company: {str(e)}")
            db.session.rollback()
            return False, f"Failed to create company: {str(e)}"

    @staticmethod
    def create_sub_company(parent_company_id, name, domain=None, industry=None, size='medium', subscription_tier='silver', created_by=None):
        """Create a new sub-company account"""
        return CompanyController.create_company(
            name=name,
            domain=domain,
            industry=industry,
            size=size,
            subscription_tier=subscription_tier,
            created_by=created_by,
            parent_company_id=parent_company_id
        )

    @staticmethod
    def get_company(company_id):
        """Get company by ID"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False, "Company not found"
            return True, company
        except Exception as e:
            current_app.logger.error(f"Error getting company: {str(e)}")
            return False, f"Failed to get company: {str(e)}"

    @staticmethod
    def update_company(company_id, **kwargs):
        """Update company information"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            
            company.update(**kwargs)
            current_app.logger.info(f"Company '{company.name}' updated successfully")
            return True, company
            
        except Exception as e:
            current_app.logger.error(f"Error updating company: {str(e)}")
            db.session.rollback()
            return False, f"Failed to update company: {str(e)}"

    @staticmethod
    def remove_member(company_id, user_id, removed_by=None):
        """Remove a member from the company"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            user = User.query.get(user_id)
            if not user or str(user.company_id) != str(company_id):
                return False, "User not found in company"
            # Deactivate credit allocations
            allocations = CompanyCreditAllocation.get_company_allocations(company_id)
            for allocation in allocations:
                if allocation.user_id == user_id:
                    allocation.deactivate()
            # Remove user from company
            user.company_id = None
            user.is_company_admin = False
            user.company_role = 'member'
            db.session.commit()
            current_app.logger.info(f"User {user.username} removed from company '{company.name}'")
            return True, user
        except Exception as e:
            current_app.logger.error(f"Error removing member: {str(e)}")
            db.session.rollback()
            return False, f"Failed to remove member: {str(e)}"

    @staticmethod
    def allocate_credits(company_id, user_id, credits, allocated_by=None, notes=None):
        """Allocate credits to a company member"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            user = User.query.get(user_id)
            # Ensure company_id comparison uses the same type
            if not user or str(user.company_id) != str(company_id):
                return False, "User not found in company"
            # Check if company has enough credits (skip for platinum/unlimited)
            if not company.subscription_tier.lower().startswith('platinum'):
                total_allocated = sum([a.credits_allocated for a in company.credit_allocations if a.is_active and a.user_id != user_id])
                if total_allocated + credits > company.total_credits:
                    return False, f"Not enough company credits. Available: {company.total_credits - total_allocated}"
            # Check for existing allocation
            existing_allocation = CompanyCreditAllocation.get_active_allocation(company_id, user_id)
            if existing_allocation:
                # Set allocation to the new value (not add)
                existing_allocation.update_allocation(
                    credits,
                    allocated_by,
                    notes
                )
                allocation = existing_allocation
            else:
                # Create new allocation
                allocation = CompanyCreditAllocation.create(
                    company_id=company_id,
                    user_id=user_id,
                    credits_allocated=credits,
                    allocated_by=allocated_by,
                    notes=notes
                )
            current_app.logger.info(f"Allocated {credits} credits to user {user.username} in company '{company.name}' (set mode)")
            return True, allocation
        except Exception as e:
            current_app.logger.error(f"Error allocating credits: {str(e)}")
            db.session.rollback()
            return False, f"Failed to allocate credits: {str(e)}"

    @staticmethod
    def use_company_credits(user_id, amount, service_type:str = None):
        """Use credits from company allocation"""
        try:
            user = User.query.get(user_id)
            if not user or not user.company_id:
                return False, "User not part of a company"
            
            # Get active allocation
            allocation = CompanyCreditAllocation.get_active_allocation(user.company_id, user_id)
            if not allocation:
                return False, "No active credit allocation found"
            
            # Check if enough credits
            if allocation.credits_used + amount > allocation.credits_allocated:
                return False, "Insufficient allocated credits"
            
            # Use credits
            if not allocation.use_credits(amount):
                return False, "Failed to use credits"

            CreditsLog.log_usage(
                team_id=None,
                user_id=user_id,
                amount=amount,
                reason=f"Used {amount} company credits for {service_type or 'a service'}.",
                reference_type=service_type 
            )
            
            # Update company usage
            company = user.get_company()
            if company and company.subscription_tier != 'platinum':
                company.credits_used += amount
                db.session.commit()
            
            current_app.logger.info(f"Used {amount} credits for user {user.username} in company")
            return True, allocation
            
        except Exception as e:
            current_app.logger.error(f"Error using company credits: {str(e)}")
            db.session.rollback()
            return False, f"Failed to use credits: {str(e)}"

    @staticmethod
    def delete_company(company_id):
        """Delete a company and all its sub-companies"""
        try:
            company = Company.query.get(company_id)
            if not company:
                return False, "Company not found"
            
            # Get sub-companies count for logging
            sub_companies_count = len(company.get_all_sub_companies_recursive())
            
            # Delete company and all sub-companies
            company.delete_with_sub_companies()
            
            current_app.logger.info(f"Company '{company.name}' and {sub_companies_count} sub-companies deleted successfully")
            return True, f"Company and {sub_companies_count} sub-companies deleted successfully"
            
        except Exception as e:
            current_app.logger.error(f"Error deleting company: {str(e)}")
            db.session.rollback()
            return False, f"Failed to delete company: {str(e)}"

    @staticmethod
    def create_company_member(company_id, username, email, password, created_by=None):
        """Create a new company member directly (no initial credit allocation)"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            if not company.can_add_member():
                return False, f"Company has reached maximum member limit ({company.max_members})"
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                return False, "User with this email already exists"
            existing_username = User.query.filter_by(username=username).first()
            if existing_username:
                return False, "Username already taken"
            new_user = User(
                username=username,
                email=email,
                role='company_member',
                tier=company.subscription_tier,  # Set tier to match company
                company_id=company_id,
                company_role='member',
                is_company_admin=False,
                is_email_verified=True  # Skip email verification for company-created users
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            db.session.refresh(new_user)  # Ensure user is refreshed from DB
            current_app.logger.info(f"New company member {username} ({email}) created for company '{company.name}' with tier {company.subscription_tier}")
            return True, new_user
        except Exception as e:
            current_app.logger.error(f"Error creating company member: {str(e)}")
            db.session.rollback()
            return False, f"Failed to create company member: {str(e)}"

    @staticmethod
    def edit_member_credits(company_id, user_id, credits, edited_by=None):
        try:
            allocation = CompanyCreditAllocation.get_active_allocation(company_id, user_id)
            if not allocation:
                return False, "No active credit allocation found"
            allocation.update_allocation(credits, edited_by, notes="Edited by company admin")
            current_app.logger.info(f"Credits for user {user_id} in company {company_id} updated to {credits}")
            return True, allocation
        except Exception as e:
            current_app.logger.error(f"Error editing member credits: {str(e)}")
            db.session.rollback()
            return False, f"Failed to edit member credits: {str(e)}"

    @staticmethod
    def get_company_analytics(company_id):
        """Get company analytics and usage statistics"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            
            members = company.get_members()
            allocations = CompanyCreditAllocation.get_company_allocations(company_id)
            
            total_allocated = sum([a.credits_allocated for a in allocations])
            total_used = sum([a.credits_used for a in allocations])
            
            analytics = {
                'company': company.to_dict(),
                'member_count': len(members),
                'max_members': company.max_members,
                'total_credits_allocated': total_allocated,
                'total_credits_used': total_used,
                'credits_remaining': total_allocated - total_used,
                'usage_percentage': (total_used / total_allocated * 100) if total_allocated > 0 else 0,
                'members': [member.to_dict() for member in members],
                'allocations': [allocation.to_dict() for allocation in allocations]
            }
            
            return True, analytics
            
        except Exception as e:
            current_app.logger.error(f"Error getting company analytics: {str(e)}")
            return False, f"Failed to get analytics: {str(e)}"

    @staticmethod
    def reset_company_credits(company_id):
        """Reset company credits (monthly/annual reset)"""
        try:
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            
            # Reset company credits
            company.reset_credits()
            
            # Reset all member allocations
            allocations = CompanyCreditAllocation.get_company_allocations(company_id)
            for allocation in allocations:
                allocation.credits_used = 0
                allocation.allocated_at = datetime.utcnow()
            
            db.session.commit()
            
            current_app.logger.info(f"Reset credits for company '{company.name}'")
            return True, company
            
        except Exception as e:
            current_app.logger.error(f"Error resetting company credits: {str(e)}")
            db.session.rollback()
            return False, f"Failed to reset credits: {str(e)}"

    @staticmethod
    def transfer_credits_between_members(company_id, from_user_id, to_user_id, amount, note=None):
        """Transfer credits from one member to another within the same company"""
        try:
            if from_user_id == to_user_id:
                return False, "Cannot transfer credits to yourself."
            # Validate both users are in the same company
            from_user = User.query.get(from_user_id)
            to_user = User.query.get(to_user_id)
            if not from_user or not to_user:
                return False, "User not found."
            if str(from_user.company_id) != str(company_id) or str(to_user.company_id) != str(company_id):
                return False, "Both users must be in the same company."
            # Get company
            success, company = CompanyController.get_company(company_id)
            if not success:
                return False, company
            # Get allocations
            from_alloc = CompanyCreditAllocation.get_active_allocation(company_id, from_user_id)
            to_alloc = CompanyCreditAllocation.get_active_allocation(company_id, to_user_id)
            # --- Platinum logic: always allow transfer, skip allocation check ---
            if company.subscription_tier and company.subscription_tier.lower().startswith('platinum'):
                # Platinum: always allow transfer, even if from_alloc is None or insufficient
                if to_alloc:
                    to_alloc.credits_allocated += amount
                else:
                    CompanyCreditAllocation.create(
                        company_id=company_id,
                        user_id=to_user_id,
                        credits_allocated=amount,
                        allocated_by=from_user_id,
                        notes="Received from member transfer"
                    )
                db.session.commit()
                # Log transfer
                log = CreditTransferLog(
                    company_id=company_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    amount=amount,
                    note=note
                )
                db.session.add(log)
                db.session.commit()
                return True, log.to_dict()
            # --- Non-platinum: check allocation as before ---
            if not from_alloc or from_alloc.credits_allocated < amount:
                return False, "Insufficient credits to transfer."
            # Transfer credits
            from_alloc.credits_allocated -= amount
            if to_alloc:
                to_alloc.credits_allocated += amount
            else:
                CompanyCreditAllocation.create(
                    company_id=company_id,
                    user_id=to_user_id,
                    credits_allocated=amount,
                    allocated_by=from_user_id,
                    notes="Received from member transfer"
                )
            db.session.commit()
            # Log transfer
            log = CreditTransferLog(
                company_id=company_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount=amount,
                note=note
            )
            db.session.add(log)
            db.session.commit()
            return True, log.to_dict()
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to transfer credits: {str(e)}" 