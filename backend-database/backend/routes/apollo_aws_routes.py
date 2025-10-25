from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from flask_login import login_required, current_user
from config.config import config
import re


# Blueprint for Apollo-backed lookups
apollo_bp = Blueprint('apollo', __name__, url_prefix='/api/apollo')


# DynamoDB resources (tables will be supplied via config by the app owner)
dynamodb = boto3.resource(
    'dynamodb',
    region_name=config.AWS_REGION,
)

# Organization and People tables for Apollo data
# The concrete table names and GSIs are expected to be provided in config
org_table = dynamodb.Table(getattr(config, 'APOLLO_ORG_TABLE_NAME'))
people_table = dynamodb.Table(getattr(config, 'APOLLO_PER_TABLE_NAME'))


def _now():
    return datetime.now().isoformat()


def _norm_text(value: str) -> str:
    if not isinstance(value, str):
        return ''
    value = value.strip().lower()
    value = re.sub(r'\s+', ' ', value)
    return value


def _norm_domain(value: str) -> str:
    if not isinstance(value, str):
        return ''
    v = value.strip().lower()
    v = re.sub(r'^https?://', '', v)  # strip protocol
    v = v.split('/')[0]               # keep host only
    return v


@apollo_bp.route('/enrich/apollo-search-company', methods=['POST'])
@login_required
def apollo_search_company():
    """Search companies by name using a GSI on company name.

    Expected payload: {"company_name": "Microsoft", "page": 1, "per_page": 10}
    Uses a GSI (config.DDB_APOLLO_GSI_COMPANY_NAME) whose PK is the normalized name.
    """
    try:
        data = request.get_json() or {}
        company_name = data.get('company_name', '')
        per_page = int(data.get('per_page', 10))
        last_key = data.get('page_token')  # opaque ExclusiveStartKey, optional

        if not company_name:
            return jsonify({
                'success': False,
                'message': 'company_name is required',
                'timestamp': _now()
            }), 400

        # Query by company name (primary key)
        query_kwargs = {
            'KeyConditionExpression': 'company = :n',
            'ExpressionAttributeValues': {':n': company_name},
            'Limit': max(1, min(100, per_page)),
        }
        if last_key:
            query_kwargs['ExclusiveStartKey'] = last_key

        response = org_table.query(**query_kwargs)
        items = response.get('Items', [])

        return jsonify({
            'success': True,
            'message': f'Found {len(items)} companies for name: {company_name}',
            'companies': items,
            'page_token': response.get('LastEvaluatedKey'),
            'timestamp': _now()
        })
    except ClientError as e:
        return jsonify({
            'success': False,
            'message': f'Database error: {e.response["Error"]["Message"]}',
            'timestamp': _now()
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': _now()
        }), 500


@apollo_bp.route('/enrich/apollo-enrich-company', methods=['POST'])
@login_required
def apollo_enrich_company_by_domain():
    """Enrich company by domain using a GSI on domain/website.

    Expected payload: {"domain": "microsoft.com"}
    Uses GSI (config.DDB_APOLLO_GSI_DOMAIN) whose PK is company_domain_norm.
    """
    try:
        data = request.get_json() or {}
        domain = data.get('domain', '')
        if not domain:
            return jsonify({
                'success': False,
                'message': 'domain is required',
                'timestamp': _now()
            }), 400

        domain_norm = _norm_domain(domain)
        # Use website-index GSI
        response = org_table.query(
            IndexName='website-index',
            KeyConditionExpression='website = :d',
            ExpressionAttributeValues={':d': domain_norm}
        )

        items = response.get('Items', [])
        if not items:
            return jsonify({
                'success': False,
                'message': f'No company found for domain: {domain}',
                'timestamp': _now()
            }), 404

        return jsonify({
            'success': True,
            'message': 'Company enrich success',
            'data': items[0],
            'timestamp': _now()
        })
    except ClientError as e:
        return jsonify({
            'success': False,
            'message': f'Database error: {e.response["Error"]["Message"]}',
            'timestamp': _now()
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': _now()
        }), 500


@apollo_bp.route('/enrich/apollo-enrich-people', methods=['POST'])
@login_required
def apollo_enrich_people():
    """Enrich people by name/org/domain using People GSIs.

    Inputs (at least one required): name (string), organization_name (string), domain (string)
    - If domain provided: query by org_domain_norm (GSI)
    - Else if organization_name provided: query by org_name_norm (GSI)
    - Else if name provided: query by full_name_norm (GSI)
    """
    try:
        data = request.get_json() or {}
        name = data.get('name')
        org_name = data.get('organization_name')
        domain = data.get('domain')
        per_page = int(data.get('per_page', 10))
        last_key = data.get('page_token')

        if not any([name, org_name, domain]):
            return jsonify({
                'success': False,
                'message': 'Provide at least one of: name, organization_name, domain',
                'timestamp': _now()
            }), 400

        # Determine access path
        if domain:
            # Resolve people by first finding the org (organization_id) via website-index
            org_resp = org_table.query(
                IndexName='website-index',
                KeyConditionExpression='website = :d',
                ExpressionAttributeValues={':d': _norm_domain(domain)}
            )
            org_items = org_resp.get('Items', [])
            if not org_items:
                return jsonify({'success': True, 'people': [], 'message': 'No organization for domain'} )

            # Prefer field names in order
            org_id = (
                org_items[0].get('organization_id') or
                org_items[0].get('company_id') or
                org_items[0].get('id')
            )
            if not org_id:
                return jsonify({'success': True, 'people': [], 'message': 'Org found but no id present'})

            index_name = 'current_organization_ids-index'
            key_expr = 'current_organization_ids = :p'
            eav = {':p': org_id}
            filter_expr = None
            if name:
                filter_expr = 'full_name = :fn'
                eav[':fn'] = _norm_text(name)
        elif org_name:
            pk = _norm_text(org_name)
            current_app.logger.info(f"Querying people by organization name: {pk} adn org nam {org_name}")
            index_name = 'organization_name-index'  # GSI for organization name
            key_expr = 'organization_name = :p'
            eav = {':p': pk}
            filter_expr = None
            if name:
                filter_expr = 'full_name = :fn'
                eav[':fn'] = _norm_text(name)
        else:
            # Query by primary key full_name (no GSI)
            pk = _norm_text(name)
            index_name = None
            key_expr = 'full_name = :p'
            eav = {':p': pk}
            filter_expr = None

        query_kwargs = {
            'KeyConditionExpression': key_expr,
            'ExpressionAttributeValues': eav,
            'Limit': max(1, min(100, per_page)),
        }
        if index_name:
            query_kwargs['IndexName'] = index_name
        if filter_expr:
            query_kwargs['FilterExpression'] = filter_expr
        if last_key:
            query_kwargs['ExclusiveStartKey'] = last_key

        response = people_table.query(**query_kwargs)
        items = response.get('Items', [])

        return jsonify({
            'success': True,
            'message': f'Returned {len(items)} people',
            'people': items,
            'page_token': response.get('LastEvaluatedKey'),
            'timestamp': _now()
        })
    except ClientError as e:
        return jsonify({
            'success': False,
            'message': f'Database error: {e.response["Error"]["Message"]}',
            'timestamp': _now()
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': _now()
        }), 500


@apollo_bp.route('/enrich/apollo-search-people', methods=['POST'])
@login_required
def apollo_search_people():
    """Search people by list of organization domains (mixed search).

    Expected payload: {"q_organization_domains_list": ["microsoft.com", ...], "per_page": 10}
    Queries GSI on org_domain_norm for each domain and unions results in-memory.
    """
    try:
        data = request.get_json() or {}
        domains = data.get('q_organization_domains_list', [])
        org_ids = data.get('q_organization_ids_list', [])
        per_page = int(data.get('per_page', 10))

        if isinstance(domains, str):
            domains = [d.strip() for d in domains.split(',') if d.strip()]

        if not domains and not org_ids:
            return jsonify({
                'success': False,
                'message': 'Provide q_organization_domains_list or q_organization_ids_list',
                'timestamp': _now()
            }), 400

        limit = max(1, min(100, per_page))

        merged = []

        # 1) If org ids provided, query people directly via current_organization_ids-index
        for oid in (org_ids or []):
            try:
                resp = people_table.query(
                    IndexName='current_organization_ids-index',
                    KeyConditionExpression='current_organization_ids = :p',
                    ExpressionAttributeValues={':p': oid},
                    Limit=limit
                )
                merged.extend(resp.get('Items', []))
            except ClientError as e:
                current_app.logger.warning(f"Query failed for org id {oid}: {e}")
                continue

        # 2) Resolve domains -> org ids via website-index, then query people
        for d in (domains or []):
            try:
                org_resp = org_table.query(
                    IndexName='website-index',
                    KeyConditionExpression='website = :d',
                    ExpressionAttributeValues={':d': _norm_domain(d)}
                )
                for org in org_resp.get('Items', []):
                    oid = org.get('organization_id') or org.get('company_id') or org.get('id')
                    if not oid:
                        continue
                    p_resp = people_table.query(
                        IndexName='current_organization_ids-index',
                        KeyConditionExpression='current_organization_ids = :p',
                        ExpressionAttributeValues={':p': oid},
                        Limit=limit
                    )
                    merged.extend(p_resp.get('Items', []))
            except ClientError as e:
                current_app.logger.warning(f"Domain resolve failed for {d}: {e}")
                continue

        return jsonify({
            'success': True,
            'message': f'Returned {len(merged)} people across {len(domains)} domains',
            'people': merged,
            'timestamp': _now()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Internal server error: {str(e)}',
            'timestamp': _now()
        }), 500


@apollo_bp.route('/health', methods=['GET'])
@login_required
def apollo_health():
    """Basic health for Apollo tables"""
    try:
        return jsonify({
            'success': True,
            'message': 'Apollo routes healthy',
            'data': {
                'org_table': org_table.name,
                'people_table': people_table.name,
                'region': org_table.meta.client.meta.region_name,
            },
            'timestamp': _now()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Health check failed: {str(e)}',
            'timestamp': _now()
        }), 500


# -------------------------
# Non-route helper methods
# -------------------------
def apollo_people_lookup(name: str = None, organization_name: str = None, domain: str = None, limit: int = 10):
    """
    Core Apollo people lookup used by both routes and LeadController.
    Mirrors /enrich/apollo-enrich-people behavior but is importable.
    """
    try:
        if not any([name, organization_name, domain]):
            return []

        index_name = None
        key_expr = None
        eav = {}
        filter_expr = None

        if domain:
            # Resolve org id via org website index
            org_resp = org_table.query(
                IndexName='website-index',
                KeyConditionExpression='website = :d',
                ExpressionAttributeValues={':d': _norm_domain(domain)}
            )
            org_items = org_resp.get('Items', [])
            if not org_items:
                return []
            org_id = (
                org_items[0].get('organization_id') or
                org_items[0].get('company_id') or
                org_items[0].get('id')
            )
            if not org_id:
                return []
            index_name = 'current_organization_ids-index'
            key_expr = 'current_organization_ids = :p'
            eav = {':p': org_id}
            if name:
                filter_expr = 'full_name = :fn'
                eav[':fn'] = _norm_text(name)
        elif organization_name:
            index_name = 'organization_name-index'
            key_expr = 'organization_name = :p'
            eav = {':p': _norm_text(organization_name)}
            if name:
                filter_expr = 'full_name = :fn'
                eav[':fn'] = _norm_text(name)
        else:
            # primary key full_name
            key_expr = 'full_name = :p'
            eav = {':p': _norm_text(name)}

        q = {
            'KeyConditionExpression': key_expr,
            'ExpressionAttributeValues': eav,
            'Limit': max(1, min(100, int(limit))),
        }
        if index_name:
            q['IndexName'] = index_name
        if filter_expr:
            q['FilterExpression'] = filter_expr

        resp = people_table.query(**q)
        return resp.get('Items', [])
    except Exception:
        return []


def apollo_company_lookup_by_name(company_name: str, limit: int = 10):
    """Query org table by company name primary key."""
    try:
        if not company_name:
            return []
        resp = org_table.query(
            KeyConditionExpression='company = :n',
            ExpressionAttributeValues={':n': _norm_text(company_name)},
            Limit=max(1, min(100, int(limit)))
        )
        return resp.get('Items', [])
    except Exception:
        return []


def apollo_company_lookup_by_domain(domain: str):
    """Query org table by domain via website-index."""
    try:
        if not domain:
            return []
        resp = org_table.query(
            IndexName='website-index',
            KeyConditionExpression='website = :d',
            ExpressionAttributeValues={':d': _norm_domain(domain)}
        )
        return resp.get('Items', [])
    except Exception:
        return []
