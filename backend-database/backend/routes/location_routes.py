from flask import Blueprint, request, jsonify, current_app
from controllers.location_controller import LocationController
from flask_login import login_required, current_user
from functools import wraps
import logging

# Create Blueprint
location_bp = Blueprint('location', __name__)

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401
        if not current_user.is_admin():
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function

@location_bp.route('/api/locations', methods=['GET'])
@login_required
def get_locations():
    """Get all locations"""
    try:
        locations = LocationController.get_all_locations()
        locations_data = [LocationController.to_dict(loc) for loc in locations]
        
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(locations_data)} locations",
            "data": locations_data
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting locations: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve locations"
        }), 500

@location_bp.route('/api/locations/<int:location_id>', methods=['GET'])
@login_required
def get_location(location_id):
    """Get location by ID"""
    try:
        location = LocationController.get_location_by_id(location_id)
        if not location:
            return jsonify({
                "status": "error",
                "message": "Location not found"
            }), 404
        
        location_data = LocationController.to_dict(location)
        return jsonify({
            "status": "success",
            "message": "Location retrieved successfully",
            "data": location_data
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting location {location_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve location"
        }), 500

@location_bp.route('/api/locations', methods=['POST'])
@login_required
@admin_required
def create_location():
    """Create new location"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        success, message = LocationController.create_location(data)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            }), 201
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 400
    except Exception as e:
        current_app.logger.error(f"[Location API] Error creating location: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to create location"
        }), 500

@location_bp.route('/api/locations/<int:location_id>', methods=['PUT'])
@login_required
@admin_required
def update_location(location_id):
    """Update location"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "No data provided"
            }), 400

        success, message = LocationController.update_location(location_id, data)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 400
    except Exception as e:
        current_app.logger.error(f"[Location API] Error updating location {location_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to update location"
        }), 500

@location_bp.route('/api/locations/<int:location_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_location(location_id):
    """Delete location"""
    try:
        success, message = LocationController.delete_location(location_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": message
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 404
    except Exception as e:
        current_app.logger.error(f"[Location API] Error deleting location {location_id}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to delete location"
        }), 500

@location_bp.route('/api/locations/search/city', methods=['GET'])
@login_required
def search_locations_by_city():
    """Search locations by city name"""
    try:
        city = request.args.get('city', '')
        if not city:
            return jsonify({
                "status": "error",
                "message": "City parameter is required"
            }), 400

        locations = LocationController.search_locations_by_city(city)
        locations_data = [LocationController.to_dict(loc) for loc in locations]
        
        return jsonify({
            "status": "success",
            "message": f"Found {len(locations_data)} locations for city '{city}'",
            "data": locations_data
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error searching locations by city: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to search locations"
        }), 500

@location_bp.route('/api/locations/search/state', methods=['GET'])
@login_required
def search_locations_by_state():
    """Search locations by state code"""
    try:
        state_code = request.args.get('state_code', '')
        if not state_code:
            return jsonify({
                "status": "error",
                "message": "State code parameter is required"
            }), 400

        locations = LocationController.search_locations_by_state(state_code)
        locations_data = [LocationController.to_dict(loc) for loc in locations]
        
        return jsonify({
            "status": "success",
            "message": f"Found {len(locations_data)} locations for state '{state_code}'",
            "data": locations_data
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error searching locations by state: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to search locations"
        }), 500

@location_bp.route('/api/locations/states', methods=['GET'])
@login_required
def get_states():
    """Get all unique states"""
    try:
        states = LocationController.get_unique_states()
        
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(states)} unique states",
            "data": states
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting states: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve states"
        }), 500

@location_bp.route('/api/locations/states/<state_code>/cities', methods=['GET'])
@login_required
def get_cities_by_state(state_code):
    """Get all cities for a specific state"""
    try:
        cities = LocationController.get_cities_by_state(state_code)
        
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(cities)} cities for state '{state_code}'",
            "data": {
                "state_code": state_code,
                "cities": cities
            }
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting cities for state {state_code}: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve cities"
        }), 500

@location_bp.route('/api/locations/states-with-cities', methods=['GET'])
@login_required
def get_states_with_cities():
    """Get all states with their cities"""
    try:
        state_city_map = LocationController.get_states_with_cities()
        
        return jsonify({
            "status": "success",
            "message": f"Retrieved {len(state_city_map)} states with cities",
            "data": state_city_map
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting states with cities: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve states with cities"
        }), 500

@location_bp.route('/api/locations/bulk', methods=['POST'])
@login_required
@admin_required
def bulk_create_locations():
    """Create multiple locations at once"""
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({
                "status": "error",
                "message": "Data must be a list of locations"
            }), 400

        success, message, errors = LocationController.bulk_create_locations(data)
        
        response_data = {
            "status": "success" if success else "error",
            "message": message,
            "errors": errors
        }
        
        status_code = 201 if success else 400
        return jsonify(response_data), status_code
    except Exception as e:
        current_app.logger.error(f"[Location API] Error in bulk create: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to create locations"
        }), 500

@location_bp.route('/api/locations/stats', methods=['GET'])
@login_required
def get_location_stats():
    """Get location statistics"""
    try:
        all_locations = LocationController.get_all_locations()
        states = LocationController.get_unique_states()
        state_city_map = LocationController.get_states_with_cities()
        
        total_cities = sum(len(cities) for cities in state_city_map.values())
        
        stats = {
            "total_locations": len(all_locations),
            "total_states": len(states),
            "total_cities": total_cities,
            "states_with_most_cities": sorted(
                [(state, len(cities)) for state, cities in state_city_map.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
        
        return jsonify({
            "status": "success",
            "message": "Location statistics retrieved successfully",
            "data": stats
        }), 200
    except Exception as e:
        current_app.logger.error(f"[Location API] Error getting location stats: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to retrieve location statistics"
        }), 500 