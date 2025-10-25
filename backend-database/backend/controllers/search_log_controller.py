import base64
import re
import hashlib
from models.search_logs_model import SearchLog
from models.lead_model import db
from flask_login import current_user
from sqlalchemy import and_
from datetime import datetime

class SearchLogController:
    @staticmethod
    # In normalize_and_hash, return the raw bytes
    def normalize_and_hash(industry, location):
        def clean(s):
            s = s or ''
            s = s.lower().strip()
            s = re.sub(r'[^a-z0-9 ]', '', s)
            s = re.sub(r'\s+', ' ', s)
            return s
        norm = f"{clean(industry)}|{clean(location)}"
        hash_bytes = hashlib.sha256(norm.encode('utf-8')).digest()
        return hash_bytes  # return bytes, not base64 string

    @staticmethod
    def get_log_by_hash(search_hash):
        return SearchLog.query.filter_by(search_hash=search_hash).first()

    @staticmethod
    def log_search(user_id, search_query, search_hash, search_parameters, result_count, execution_time_ms):
        # Check if log exists
        log = SearchLog.query.filter_by(search_hash=search_hash).first()
        if log:
            log.result_count += 1
            log.searched_at = datetime.utcnow()
            db.session.commit()
            return log
        else:
            log = SearchLog(
                user_id=user_id,
                search_query=search_query,
                search_hash=search_hash,
                search_parameters=search_parameters,
                result_count=1,
                execution_time_ms=execution_time_ms
            )
            db.session.add(log)
            db.session.commit()
            return log 