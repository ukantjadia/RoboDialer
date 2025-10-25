from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from models.user_model import User
from models.user_subscription_model import UserSubscription
from models.lead_model import Lead, db
from models.plan_model import Plan
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
import logging
import boto3
from config.config import config

dashboard_bp = Blueprint('dashboard', __name__)

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.is_admin() and current_user.role != 'developer'):
            return jsonify({"error": "Unauthorized access"}), 403
        return f(*args, **kwargs)
    return decorated_function

@dashboard_bp.route('/admin/dashboard')
@login_required
@super_admin_required
def admin_dashboard():
    """Render the admin dashboard page"""
    return render_template('admin/dashboard.html')

def format_revenue(amount):
    """Format revenue to be more readable with T(rillion), B(illion), M(illion)"""
    if amount >= 1_000_000_000_000:
        return f"${amount / 1_000_000_000_000:.1f}T"
    elif amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    else:
        return f"${amount:,.0f}"

@dashboard_bp.route('/api/admin/dashboard/stats')
@login_required
@super_admin_required
def get_dashboard_stats():
    """Get overall dashboard statistics"""
    try:
        current_app.logger.info("Starting to fetch dashboard stats")

        # Total users (only user and student roles)
        try:
            total_users = User.query.filter(
                User.role.in_(['user', 'student'])
            ).count()
            current_app.logger.info(f"Total users count: {total_users}")
        except Exception as e:
            current_app.logger.error(f"Error counting users: {str(e)}")
            raise

        # Premium users (users with paid subscriptions, only user and student roles)
        try:
            premium_tiers = [
                'bronze', 'silver', 'gold', 'platinum',
                'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual',
                'student_monthly', 'student_semester', 'student_annual',
                'call_outreach'
            ]
            premium_users = User.query.filter(
                User.tier.in_(premium_tiers),
                User.status == 'active',
                User.role.in_(['user', 'student'])
            ).count()
            current_app.logger.info(f"Premium users count: {premium_users}")
        except Exception as e:
            current_app.logger.error(f"Error counting premium users: {str(e)}")
            raise

        # Total leads and active leads
        try:
            total_leads = Lead.query.count()
            active_leads = Lead.query.filter(Lead.deleted == False).count()
            current_app.logger.info(f"Total leads count: {total_leads}, Active leads: {active_leads}")
        except Exception as e:
            current_app.logger.error(f"Error counting leads: {str(e)}")
            raise

        # Get total revenue from leads and calculate average
        try:
            leads_with_revenue = Lead.query.filter(
                Lead.revenue.isnot(None),
                Lead.deleted == False
            ).all()

            total_revenue = sum(lead.revenue for lead in leads_with_revenue if isinstance(lead.revenue, (int, float)))
            avg_revenue_per_lead = total_revenue / len(leads_with_revenue) if leads_with_revenue else 0

            # Get previous month's revenue for comparison
            last_month = datetime.utcnow() - timedelta(days=30)
            last_month_revenue = sum(
                lead.revenue
                for lead in leads_with_revenue
                if isinstance(lead.revenue, (int, float)) and lead.created_at < last_month
            )

            revenue_growth = ((total_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 0

            # Calculate revenue breakdown by industry
            industry_breakdown = {}
            for lead in leads_with_revenue:
                if not isinstance(lead.revenue, (int, float)):
                    continue

                industry = lead.industry or 'Unknown'
                if industry not in industry_breakdown:
                    industry_breakdown[industry] = {
                        'count': 0,
                        'revenue': 0,
                        'avg_revenue': 0
                    }
                industry_breakdown[industry]['count'] += 1
                industry_breakdown[industry]['revenue'] += lead.revenue

            # Calculate average revenue per industry and format numbers
            for industry in industry_breakdown:
                count = industry_breakdown[industry]['count']
                revenue = industry_breakdown[industry]['revenue']
                industry_breakdown[industry]['avg_revenue'] = revenue / count if count > 0 else 0
                industry_breakdown[industry]['revenue_formatted'] = format_revenue(revenue)
                industry_breakdown[industry]['avg_revenue_formatted'] = format_revenue(industry_breakdown[industry]['avg_revenue'])

            # Sort industries by revenue in descending order and get top 10
            sorted_industries = dict(list(sorted(
                industry_breakdown.items(),
                key=lambda x: (-x[1]['revenue'], x[0])  # Sort by revenue desc, then by name asc
            ))[:10])  # Take only top 10

            # Calculate total revenue for percentage calculation
            total_industry_revenue = sum(data['revenue'] for data in sorted_industries.values())

            # Add percentage to each industry
            for industry_data in sorted_industries.values():
                industry_data['percentage'] = (industry_data['revenue'] / total_industry_revenue * 100) if total_industry_revenue > 0 else 0

            current_app.logger.info(f"Total revenue: {total_revenue}, Avg per lead: {avg_revenue_per_lead}")
        except Exception as e:
            current_app.logger.error(f"Error calculating revenue stats: {str(e)}")
            current_app.logger.exception("Full traceback for revenue calculation error:")
            total_revenue = 0
            avg_revenue_per_lead = 0
            revenue_growth = 0
            sorted_industries = {}

        response_data = {
            'total_users': total_users,
            'premium_users': premium_users,
            'total_leads': total_leads,
            'active_leads': active_leads,
            'leads_with_revenue': len(leads_with_revenue),
            'revenue': {
                'total': format_revenue(total_revenue),
                'total_raw': total_revenue,  # For calculations
                'average_per_lead': format_revenue(avg_revenue_per_lead),
                'growth_percentage': round(revenue_growth, 1),
                'previous_month': format_revenue(last_month_revenue),
                'breakdown': sorted_industries  # Add back the breakdown
            },
            'monthly_growth': calculate_monthly_growth_for_roles(['user', 'student'])
        }

        current_app.logger.info("Successfully compiled dashboard stats")
        return jsonify(response_data)

    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard_stats: {str(e)}")
        current_app.logger.exception("Full traceback:")
        return jsonify({
            'error': 'Failed to fetch dashboard statistics',
            'details': str(e)
        }), 500

@dashboard_bp.route('/api/admin/dashboard/revenue-chart')
@login_required
@super_admin_required
def get_revenue_chart():
    """Get revenue data for charts"""
    try:
        # Get revenue data for the last 12 months
        revenue_data = []
        total_leads_data = []
        avg_revenue_data = []

        for i in range(12):
            date = datetime.utcnow() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

            # Get leads for this month
            monthly_leads = Lead.query.filter(
                Lead.created_at >= month_start,
                Lead.created_at <= month_end,
                Lead.deleted == False
            ).all()

            # Get leads with revenue
            leads_with_revenue = [
                lead for lead in monthly_leads
                if lead.revenue and isinstance(lead.revenue, (int, float))
            ]

            # Calculate metrics
            monthly_revenue = sum(lead.revenue for lead in leads_with_revenue)
            avg_revenue = monthly_revenue / len(leads_with_revenue) if leads_with_revenue else 0

            month_data = {
                'month': month_start.strftime('%Y-%m'),
                'date': month_start.strftime('%B %Y'),
                'revenue': monthly_revenue,
                'revenue_formatted': format_revenue(monthly_revenue),
                'total_leads': len(monthly_leads),
                'leads_with_revenue': len(leads_with_revenue),
                'avg_revenue': avg_revenue,
                'avg_revenue_formatted': format_revenue(avg_revenue)
            }

            revenue_data.append(month_data)

        revenue_data.reverse()  # Show oldest to newest

        return jsonify({
            'revenue_data': revenue_data
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching revenue chart data: {str(e)}")
        current_app.logger.exception("Full traceback:")
        return jsonify({
            'error': 'Failed to fetch revenue chart data',
            'details': str(e)
        }), 500

@dashboard_bp.route('/api/admin/dashboard/user-growth')
@login_required
@super_admin_required
def get_user_growth():
    """Get user growth data for charts"""
    try:
        # Get user growth data for the last 12 months
        growth_data = []
        for i in range(12):
            date = datetime.utcnow() - timedelta(days=30*i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

            # Count users created in this month
            new_users = User.query.filter(
                User.created_at >= month_start,
                User.created_at <= month_end
            ).count()

            # Count premium users created in this month
            new_premium_users = User.query.filter(
                User.created_at >= month_start,
                User.created_at <= month_end,
                User.tier.in_(['bronze', 'silver', 'gold', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual', 'student_monthly', 'student_semester', 'student_annual', 'call_outreach'])
            ).count()

            growth_data.append({
                'month': month_start.strftime('%Y-%m'),
                'new_users': new_users,
                'new_premium_users': new_premium_users,
                'date': month_start.strftime('%B %Y')
            })

        growth_data.reverse()  # Show oldest to newest

        return jsonify({
            'growth_data': growth_data
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching user growth data: {str(e)}")
        return jsonify({'error': 'Failed to fetch user growth data'}), 500

@dashboard_bp.route('/api/admin/dashboard/top-companies')
@login_required
@super_admin_required
def get_top_companies_api():
    """Get top companies by revenue"""
    try:
        # Query companies with non-null revenue, ordered by revenue
        top_companies = Lead.query.filter(
            Lead.revenue.isnot(None),
            Lead.revenue > 0,  # Only include companies with positive revenue
            Lead.deleted == False
        ).order_by(
            Lead.revenue.desc()  # Sort by revenue in descending order
        ).limit(10).all()

        companies_data = []
        for company in top_companies:
            # Format revenue for display
            revenue_display = 'N/A'
            if company.revenue:
                if company.revenue >= 1000000000:
                    revenue_display = f'${int(company.revenue/1000000000)}B'
                elif company.revenue >= 1000000:
                    revenue_display = f'${int(company.revenue/1000000)}M'
                else:
                    revenue_display = f'${int(company.revenue):,}'

            # Format location
            location = f"{company.city}, {company.state}" if company.city and company.state else (company.city or company.state or 'N/A')

            companies_data.append({
                'name': company.company or 'Unknown Company',
                'revenue': revenue_display,  # Move revenue to front since it's the main sorting criteria
                'industry': company.industry or 'Unknown',
                'location': location
            })

        return jsonify({
            'top_companies': companies_data
        })
    except Exception as e:
        current_app.logger.error(f"Error fetching top companies: {str(e)}")
        return jsonify({'error': 'Failed to fetch top companies'}), 500

@dashboard_bp.route('/api/admin/dashboard/grand-total-leads')
@login_required
def get_grand_total_leads():
    """
    Return a single grand_total_leads number combining SQL leads with DynamoDB items.

    - SQL count: Lead.query.count()
    - DynamoDB count: table.item_count (approximate, eventually consistent)
    """
    try:
        # SQL leads count
        sql_total_leads = Lead.query.count()

        # DynamoDB approximate item count
        try:
            dynamodb = boto3.resource('dynamodb', region_name=config.AWS_REGION)
            table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)
            dynamo_item_count = table.item_count
        except Exception as dynamo_error:
            current_app.logger.warning(f"DynamoDB error, using SQL count only: {str(dynamo_error)}")
            dynamo_item_count = 0

        grand_total = int(sql_total_leads) + int(dynamo_item_count or 0)

        return jsonify({
            'success': True,
            'message': 'Grand total leads calculated',
            'data': {
                'sql_total_leads': sql_total_leads,
                'dynamo_item_count': dynamo_item_count,
                'grand_total_leads': grand_total
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error calculating grand total leads: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to calculate grand total leads',
            'details': str(e)
        }), 500



def calculate_revenue():
    """Calculate total revenue based on subscription tiers"""
    try:
        # Define tier prices (updated to match choose_plan.html)
        tier_prices = {
            'bronze': 19.00,
            'silver': 49.00,
            'gold': 99.00,
            'platinum': 199.00,
            'bronze_annual': 199.00,
            'silver_annual': 499.00,
            'gold_annual': 999.00,
            'platinum_annual': 1999.00,
            'student_monthly': 19.99,
            'student_semester': 99.99,
            'student_annual': 179.99,
            'call_outreach': 149.99
        }

        # Get all active premium users
        premium_users = User.query.filter(
            User.tier.in_(list(tier_prices.keys())),
            User.status == 'active'
        ).all()

        total_revenue = 0
        tier_breakdown = {}

        for user in premium_users:
            price = tier_prices.get(user.tier, 0)
            total_revenue += price

            if user.tier not in tier_breakdown:
                tier_breakdown[user.tier] = {'count': 0, 'revenue': 0}
            tier_breakdown[user.tier]['count'] += 1
            tier_breakdown[user.tier]['revenue'] += price

        return {
            'total': round(total_revenue, 2),
            'breakdown': tier_breakdown
        }
    except Exception as e:
        current_app.logger.error(f"Error calculating revenue: {str(e)}")
        return {'total': 0, 'breakdown': {}}

def calculate_monthly_revenue(start_date, end_date):
    """Calculate revenue for a specific month"""
    try:
        tier_prices = {
            'bronze': 19.00,
            'silver': 49.00,
            'gold': 99.00,
            'platinum': 199.00,
            'bronze_annual': 199.00,
            'silver_annual': 499.00,
            'gold_annual': 999.00,
            'platinum_annual': 1999.00,
            'student_monthly': 19.99,
            'student_semester': 99.99,
            'student_annual': 179.99,
            'call_outreach': 149.99
        }

        # Get users who were active during this period
        users = User.query.filter(
            User.created_at <= end_date,
            User.tier.in_(list(tier_prices.keys())),
            User.status == 'active'
        ).all()

        monthly_revenue = 0
        for user in users:
            # Check if user was active during this month
            if user.created_at <= end_date:
                price = tier_prices.get(user.tier, 0)
                monthly_revenue += price

        return round(monthly_revenue, 2)
    except Exception as e:
        current_app.logger.error(f"Error calculating monthly revenue: {str(e)}")
        return 0

def calculate_monthly_growth_for_roles(allowed_roles):
    """Calculate monthly growth percentages for specific roles"""
    try:
        # Current month
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

        # Previous month
        prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        prev_month_end = current_month_start - timedelta(seconds=1)

        # Count users for current and previous month
        current_month_users = User.query.filter(
            User.created_at >= current_month_start,
            User.created_at <= current_month_end,
            User.role.in_(allowed_roles)
        ).count()

        prev_month_users = User.query.filter(
            User.created_at >= prev_month_start,
            User.created_at <= prev_month_end,
            User.role.in_(allowed_roles)
        ).count()

        # Calculate growth percentage
        if prev_month_users > 0:
            user_growth = ((current_month_users - prev_month_users) / prev_month_users) * 100
        else:
            user_growth = 100 if current_month_users > 0 else 0

        # Calculate premium user growth
        current_month_premium = User.query.filter(
            User.created_at >= current_month_start,
            User.created_at <= current_month_end,
            User.role.in_(allowed_roles),
            User.tier.in_(['bronze', 'silver', 'gold', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual', 'student_monthly', 'student_semester', 'student_annual', 'call_outreach'])
        ).count()

        prev_month_premium = User.query.filter(
            User.created_at >= prev_month_start,
            User.created_at <= prev_month_end,
            User.role.in_(allowed_roles),
            User.tier.in_(['bronze', 'silver', 'gold', 'platinum', 'bronze_annual', 'silver_annual', 'gold_annual', 'platinum_annual', 'student_monthly', 'student_semester', 'student_annual', 'call_outreach'])
        ).count()

        if prev_month_premium > 0:
            premium_growth = ((current_month_premium - prev_month_premium) / prev_month_premium) * 100
        else:
            premium_growth = 100 if current_month_premium > 0 else 0

        return {
            'user_growth': round(user_growth, 2),
            'premium_growth': round(premium_growth, 2)
        }
    except Exception as e:
        current_app.logger.error(f"Error calculating monthly growth: {str(e)}")
        return {'user_growth': 0, 'premium_growth': 0}