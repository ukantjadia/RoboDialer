from flask import request, jsonify, current_app
from models.locations_model import Location
from models.lead_model import db
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

class LocationController:
    @staticmethod
    def get_all_locations():
        """Get all locations"""
        try:
            locations = Location.query.all()
            current_app.logger.info(f"[Location] Fetched {len(locations)} locations")
            return locations
        except Exception as e:
            current_app.logger.error(f"[Location] Error fetching locations: {str(e)}")
            return []

    @staticmethod
    def get_location_by_id(location_id):
        """Get location by ID"""
        try:
            location = Location.query.get(location_id)
            if not location:
                current_app.logger.warning(f"[Location] Location with ID {location_id} not found")
                return None
            current_app.logger.info(f"[Location] Fetched location with ID: {location_id}")
            return location
        except Exception as e:
            current_app.logger.error(f"[Location] Error fetching location by ID {location_id}: {str(e)}")
            return None

    @staticmethod
    def create_location(form_data):
        """Create new location from form data"""
        try:
            location = Location(
                city_original=form_data.get('city_original', '').strip(),
                state_code=form_data.get('state_code', '').strip().upper(),
                state_original=form_data.get('state_original', '').strip()
            )

            # Validate required fields
            if not location.city_original:
                return False, "City is required"
            if not location.state_code:
                return False, "State code is required"
            if not location.state_original:
                return False, "State original is required"

            db.session.add(location)
            db.session.commit()
            current_app.logger.info(f"[Location] Created new location: {location.city_original}, {location.state_code}")
            return True, "Location created successfully!"
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] IntegrityError creating location: {str(e)}")
            return False, f"Location already exists or invalid data: {str(e)}"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] Error creating location: {str(e)}")
            return False, f"Error creating location: {str(e)}"

    @staticmethod
    def update_location(location_id, form_data):
        """Update location data"""
        try:
            location = Location.query.get(location_id)
            if not location:
                current_app.logger.warning(f"[Location] Location with ID {location_id} not found")
                return False, "Location not found"

            # Update fields
            if 'city_original' in form_data:
                location.city_original = form_data['city_original'].strip()
            if 'state_code' in form_data:
                location.state_code = form_data['state_code'].strip().upper()
            if 'state_original' in form_data:
                location.state_original = form_data['state_original'].strip()

            # Validate required fields
            if not location.city_original:
                return False, "City is required"
            if not location.state_code:
                return False, "State code is required"
            if not location.state_original:
                return False, "State original is required"

            db.session.commit()
            current_app.logger.info(f"[Location] Updated location with ID: {location_id}")
            return True, "Location updated successfully!"
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] IntegrityError updating location: {str(e)}")
            return False, f"Location update failed: {str(e)}"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] Error updating location: {str(e)}")
            return False, f"Error updating location: {str(e)}"

    @staticmethod
    def delete_location(location_id):
        """Delete location by ID"""
        try:
            location = Location.query.get(location_id)
            if not location:
                current_app.logger.warning(f"[Location] Location with ID {location_id} not found")
                return False, "Location not found"

            db.session.delete(location)
            db.session.commit()
            current_app.logger.info(f"[Location] Deleted location with ID: {location_id}")
            return True, "Location deleted successfully!"
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] Error deleting location: {str(e)}")
            return False, f"Error deleting location: {str(e)}"

    @staticmethod
    def search_locations_by_city(city):
        """Search locations by city name"""
        try:
            locations = Location.query.filter(
                Location.city_original.ilike(f"%{city}%")
            ).all()
            current_app.logger.info(f"[Location] Found {len(locations)} locations for city: {city}")
            return locations
        except Exception as e:
            current_app.logger.error(f"[Location] Error searching locations by city: {str(e)}")
            return []

    @staticmethod
    def search_locations_by_state(state_code):
        """Search locations by state code"""
        try:
            locations = Location.query.filter(
                Location.state_code.ilike(f"%{state_code.upper()}%")
            ).all()
            current_app.logger.info(f"[Location] Found {len(locations)} locations for state: {state_code}")
            return locations
        except Exception as e:
            current_app.logger.error(f"[Location] Error searching locations by state: {str(e)}")
            return []

    @staticmethod
    def get_unique_states():
        """Get all unique states with their codes"""
        try:
            states = db.session.query(
                Location.state_code,
                Location.state_original
            ).distinct().all()
            
            state_list = [
                {
                    'state_code': state[0],
                    'state_original': state[1]
                }
                for state in states
            ]
            
            current_app.logger.info(f"[Location] Found {len(state_list)} unique states")
            return state_list
        except Exception as e:
            current_app.logger.error(f"[Location] Error getting unique states: {str(e)}")
            return []

    @staticmethod
    def get_cities_by_state(state_code):
        """Get all cities for a specific state"""
        try:
            cities = Location.query.filter(
                Location.state_code == state_code.upper()
            ).with_entities(Location.city_original).distinct().all()
            
            city_list = [city[0] for city in cities]
            current_app.logger.info(f"[Location] Found {len(city_list)} cities for state: {state_code}")
            return city_list
        except Exception as e:
            current_app.logger.error(f"[Location] Error getting cities by state: {str(e)}")
            return []

    @staticmethod
    def get_states_with_cities():
        """Return a dict: {state_code: [city1, city2, ...], ...} from the locations table"""
        try:
            locations = Location.query.all()
            state_city_map = {}
            for loc in locations:
                state = loc.state_code
                city = loc.city_original
                if state not in state_city_map:
                    state_city_map[state] = set()
                state_city_map[state].add(city)
            
            # Convert sets to sorted lists
            state_city_map = {state: sorted(list(cities)) for state, cities in state_city_map.items()}
            current_app.logger.info(f"[Location] Generated state-city map with {len(state_city_map)} states")
            return state_city_map
        except Exception as e:
            current_app.logger.error(f"[Location] Error getting states with cities: {str(e)}")
            return {}

    @staticmethod
    def bulk_create_locations(locations_data):
        """Create multiple locations at once"""
        try:
            created_count = 0
            errors = []

            for location_data in locations_data:
                try:
                    location = Location(
                        city_original=location_data.get('city_original', '').strip(),
                        state_code=location_data.get('state_code', '').strip().upper(),
                        state_original=location_data.get('state_original', '').strip()
                    )

                    # Validate required fields
                    if not location.city_original or not location.state_code or not location.state_original:
                        errors.append(f"Missing required fields for location: {location_data}")
                        continue

                    db.session.add(location)
                    created_count += 1

                except Exception as e:
                    errors.append(f"Error creating location {location_data}: {str(e)}")

            db.session.commit()
            current_app.logger.info(f"[Location] Bulk created {created_count} locations")
            return True, f"Successfully created {created_count} locations", errors
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[Location] Error in bulk create: {str(e)}")
            return False, f"Error in bulk create: {str(e)}", errors

    @staticmethod
    def to_dict(location):
        """Convert Location object to dictionary"""
        return {
            'id': location.id,
            'city_original': location.city_original,
            'state_code': location.state_code,
            'state_original': location.state_original
        } 