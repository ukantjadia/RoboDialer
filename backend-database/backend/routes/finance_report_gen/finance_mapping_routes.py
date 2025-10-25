from flask import Blueprint
from flask_login import login_required
from controllers.finance_report_gen.finance_mapping_controller import StandardColumnDefinitionsController

fin_stand_col_bp = Blueprint("fin_stand_col",__name__) #Standard column blueprint
@fin_stand_col_bp.route("/api/fin/stand_col",methods=['GET'])

@login_required
def get_stand_col_route():
    "Get all the Standard Cols"
    return StandardColumnDefinitionsController.get_specific_columns()