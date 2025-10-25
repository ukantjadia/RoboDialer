from flask import Blueprint,request,jsonify,current_app
from controllers.finance_report_gen.saving_mapping_controller import ColumnMappingController,DeleteFileController
from flask_login import login_required

fin_save_mapping_bp = Blueprint('fin_save_mapping',__name__)

@fin_save_mapping_bp.route('/api/fin/save_mapping',methods =['POST'])
@login_required
def save_mapping():
    data = request.get_json()
    return ColumnMappingController.save_column_mapping(data=data)


@fin_save_mapping_bp.route('/api/fin/delete_file/<string:file_id>',methods=["DELETE"])
@login_required
def delete_file(file_id :str):
    return DeleteFileController.delete_file(file_id=file_id)
    
