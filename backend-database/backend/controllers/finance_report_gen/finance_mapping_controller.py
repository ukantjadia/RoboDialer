from models.finance_report_gen.standard_column_definitions_model import StandardColumnDefinitions
from flask import current_app
from models.lead_model import db


class StandardColumnDefinitionsController:    
    @staticmethod
    def get_specific_columns():
        try:
            columns = db.session.query(
                StandardColumnDefinitions.column_name,
                StandardColumnDefinitions.column_category,
                StandardColumnDefinitions.applicable_file_types,
                StandardColumnDefinitions.description,
                StandardColumnDefinitions.synonyms
            ).filter(StandardColumnDefinitions.is_active == True).all()
            
            if not columns:
                return {"error":"Standard Columns not found"},404

            # Convert to list of dictionaries
            result = []
            for column in columns:
                result.append({
                    'column_name': column.column_name,
                    'column_category': column.column_category,
                    'applicable_file_types': column.applicable_file_types,
                    'description': column.description,
                    'synonyms': column.synonyms
                })
            
            current_app.logger.info(f"Retrieved {len(result)} standard column definitions")
            return result,200
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving standard column definitions: {str(e)}")
            return {"error":"Error retriving Standard Columns"},500