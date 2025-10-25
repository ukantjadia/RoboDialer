import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(log_file=None):
    if log_file is None:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=7)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s:%(lineno)d: %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Also attach handler to Gunicorn error logger if running under Gunicorn
    gunicorn_logger = logging.getLogger('gunicorn.error')
    if gunicorn_logger and not any(isinstance(h, RotatingFileHandler) for h in gunicorn_logger.handlers):
        gunicorn_logger.addHandler(handler)
        gunicorn_logger.setLevel(logging.INFO)