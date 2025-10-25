from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_required, current_user
from controllers.company_controller import CompanyController
from models.company_model import Company
from models.company_credit_allocation_model import CompanyCreditAllocation
from models.user_model import User
from models.lead_model import db
from utils.decorators import admin_required, developer_required
from flask import current_app
import uuid
from models.plan_model import Plan

bp = Blueprint('company', __name__)

@bp.route('/api/companies', methods=['POST'])
@login_required
def create_company():
    """Create a new company account"""
    data = request.get_json()
    
    # Check if user has required tier (silver or higher)
    required_tiers = ['silver', 'gold', 'platinum', 'silver_annual', 'gold_annual', 'platinum_annual']
    if current_user.tier not in required_tiers:
        return jsonify({'error': 'Company accounts require Silver tier or higher'}), 403
    
    # Check if user is already part of a company
    if current_user.company_id:
        return jsonify({'error': 'User is already part of a company'}), 400
    
    required_fields = ['name']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        success, result = CompanyController.create_company(
            name=data['name'],
            domain=data.get('domain'),
            industry=data.get('industry'),
            size=data.get('size', 'medium'),
            subscription_tier=data.get('subscription_tier'),
            created_by=current_user,
            parent_company_id=data.get('parent_company_id')
        )
        
        if success:
            return jsonify(result.to_dict()), 201
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error creating company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/sub-companies', methods=['POST'])
@login_required
def create_sub_company(company_id):
    """Create a new sub-company account"""
    data = request.get_json()
    
    # Check if user can manage this company
    if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
        return jsonify({'error': 'Access denied'}), 403
    
    required_fields = ['name']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        success, result = CompanyController.create_sub_company(
            parent_company_id=company_id,
            name=data['name'],
            domain=data.get('domain'),
            industry=data.get('industry'),
            size=data.get('size', 'medium'),
            subscription_tier=data.get('subscription_tier'),
            created_by=current_user
        )
        
        if success:
            return jsonify(result.to_dict()), 201
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error creating sub-company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>', methods=['GET'])
@login_required
def get_company(company_id):
    """Get company information"""
    try:
        # Check if user has access to this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        success, result = CompanyController.get_company(company_id)
        if success:
            company_data = result.to_dict()
            # Add sub-companies information
            sub_companies = result.get_sub_companies()
            company_data['sub_companies'] = [sub.to_dict() for sub in sub_companies]
            company_data['sub_companies_count'] = len(sub_companies)
            
            # Add parent company information if this is a sub-company
            if result.is_sub_company():
                parent_company = result.get_parent_company()
                if parent_company:
                    company_data['parent_company'] = {
                        'company_id': str(parent_company.company_id),
                        'name': parent_company.name
                    }
            
            return jsonify(company_data)
        else:
            return jsonify({'error': result}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>', methods=['PUT'])
@login_required
def update_company(company_id):
    """Update company information"""
    try:
        # Check if user can manage this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        success, result = CompanyController.update_company(company_id, **data)
        
        if success:
            return jsonify(result.to_dict())
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error updating company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/members', methods=['GET'])
@login_required
def get_company_members(company_id):
    """Get all company members"""
    try:
        # Check if user has access to this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        success, company = CompanyController.get_company(company_id)
        if not success:
            return jsonify({'error': company}), 404
        
        members = company.get_members()
        members_data = []
        for member in members:
            member_data = member.to_dict()
            # Get credit allocation info
            allocation = CompanyCreditAllocation.get_active_allocation(company_id, member.user_id)
            if allocation:
                member_data['credits_allocated'] = allocation.credits_allocated
                member_data['credits_used'] = allocation.credits_used
                member_data['credits_remaining'] = allocation.credits_allocated - allocation.credits_used
            else:
                member_data['credits_allocated'] = 0
                member_data['credits_used'] = 0
                member_data['credits_remaining'] = 0
            members_data.append(member_data)
        
        return jsonify({
            'company': company.to_dict(),
            'members': members_data,
            'total_members': len(members_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting company members: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/members', methods=['POST'])
@login_required
def create_member(company_id):
    """Create a new company member"""
    try:
        # Check if user can manage this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        data = request.get_json()
        required_fields = ['username', 'email', 'password']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        success, result = CompanyController.create_company_member(
            company_id=company_id,
            username=data['username'],
            email=data['email'],
            password=data['password'],
            created_by=current_user
        )
        if success:
            return jsonify(result.to_dict()), 201
        else:
            return jsonify({'error': result}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating member: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/members/<user_id>', methods=['DELETE'])
@login_required
def remove_member(company_id, user_id):
    """Remove a member from the company"""
    try:
        # Check if user can manage this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        success, result = CompanyController.remove_member(
            company_id=company_id,
            user_id=user_id,
            removed_by=current_user.user_id
        )
        
        if success:
            return jsonify({'message': 'Member removed successfully'}), 200
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error removing member: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/allocate-credits', methods=['POST'])
@login_required
def allocate_credits(company_id):
    """Allocate credits to a company member"""
    try:
        # Check if user can manage this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        required_fields = ['user_id', 'credits']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        success, result = CompanyController.allocate_credits(
            company_id=company_id,
            user_id=data['user_id'],
            credits=data['credits'],
            allocated_by=current_user.user_id,
            notes=data.get('notes')
        )
        
        if success:
            return jsonify(result.to_dict()), 200
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error allocating credits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/edit-credits', methods=['POST'])
@login_required
def edit_credits(company_id):
    """Edit credits for a company member"""
    try:
        # Check if user can manage this company
        if not current_user.can_manage_company() and str(current_user.company_id) != company_id:
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        required_fields = ['user_id', 'credits']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        success, result = CompanyController.edit_member_credits(
            company_id=company_id,
            user_id=data['user_id'],
            credits=data['credits'],
            edited_by=current_user.user_id
        )
        
        if success:
            return jsonify(result.to_dict()), 200
        else:
            return jsonify({'error': result}), 400
            
    except Exception as e:
        current_app.logger.error(f"Error editing credits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/my-company', methods=['GET'])
@login_required
def get_my_company():
    """Get current user's company information"""
    try:
        if not current_user.company_id:
            return jsonify({'error': 'User is not part of a company'}), 404
        
        success, company = CompanyController.get_company(current_user.company_id)
        if success:
            company_data = company.to_dict()
            # Add member count
            company_data['member_count'] = company.get_member_count()
            # Add sub-companies information
            sub_companies = company.get_sub_companies()
            company_data['sub_companies'] = [sub.to_dict() for sub in sub_companies]
            company_data['sub_companies_count'] = len(sub_companies)
            
            # Add parent company information if this is a sub-company
            if company.is_sub_company():
                parent_company = company.get_parent_company()
                if parent_company:
                    company_data['parent_company'] = {
                        'company_id': str(parent_company.company_id),
                        'name': parent_company.name
                    }
            
            return jsonify(company_data)
        else:
            return jsonify({'error': company}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting user company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/my-credits', methods=['GET'])
@login_required
def get_my_company_credits():
    """Get current user's company credit allocation"""
    try:
        if not current_user.company_id:
            return jsonify({'error': 'User is not part of a company'}), 404
        
        allocation = CompanyCreditAllocation.get_active_allocation(
            current_user.company_id, 
            current_user.user_id
        )
        
        if allocation:
            return jsonify(allocation.to_dict())
        else:
            return jsonify({'error': 'No credit allocation found'}), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting user credits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/company/dashboard')
@login_required
def company_dashboard():
    """Company dashboard page"""
    if not current_user.company_id:
        return render_template('company/no_company.html')
    
    return render_template('company/dashboard.html')


# Admin routes
@bp.route('/admin/companies')
@login_required
@admin_required
def admin_companies():
    """Admin page to view all companies"""
    companies = Company.query.all()
    companies_info = []
    for company in companies:
        # Get plan name from Plan table
        plan = Plan.query.filter(Plan.plan_name.ilike(company.subscription_tier)).first()
        plan_name = plan.plan_name if plan else company.subscription_tier
        # Get admin(s)
        admins = User.query.filter_by(company_id=company.company_id, is_company_admin=True).all()
        # Get all members
        members = User.query.filter_by(company_id=company.company_id).all()
        companies_info.append({
            'company': company,
            'plan_name': plan_name,
            'admins': admins,
            'members': members
        })
    return render_template('admin/companies.html', companies=companies_info)

@bp.route('/api/admin/companies/<company_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_company(company_id):
    """Delete a company and all its sub-companies (admin only)"""
    try:
        success, result = CompanyController.delete_company(company_id)
        
        if success:
            return jsonify({'message': result}), 200
        else:
            return jsonify({'error': result}), 400
        
    except Exception as e:
        current_app.logger.error(f"Error deleting company: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/api/companies/<company_id>/members/<user_id>', methods=['DELETE'])
@login_required
def api_remove_member(company_id, user_id):
    if not current_user.is_company_admin:
        return jsonify({'error': 'Access denied'}), 403
    success, result = CompanyController.remove_member(
        company_id=company_id,
        user_id=user_id,
        removed_by=current_user.user_id
    )
    if success:
        return jsonify({'message': 'Member removed'}), 200
    else:
        return jsonify({'error': result}), 400

@bp.route('/api/companies/<company_id>/transfer-credits', methods=['POST'])
@login_required
def transfer_credits(company_id):
    """Transfer credits from one member to another within the same company (MVP)"""
    data = request.get_json()
    from_user_id = data.get('from_user_id')
    to_user_id = data.get('to_user_id')
    amount = data.get('amount')
    note = data.get('note')
    # Only allow if current_user is from_user or admin
    if str(current_user.user_id) != str(from_user_id) and not current_user.is_company_admin:
        return jsonify({'error': 'Access denied'}), 403
    success, result = CompanyController.transfer_credits_between_members(
        company_id=company_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        amount=amount,
        note=note
    )
    if success:
        return jsonify({'message': 'Transfer successful', 'log': result}), 200
    else:
        return jsonify({'error': result}), 400 