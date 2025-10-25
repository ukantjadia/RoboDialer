# backend/config/logging_config.py

import logging
import sys

def setup_logger():
    """
    Configures a centralized logger for the application.
    This should be called once when the application starts.
    """
    
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s"
    
    # Create a handler to write log messages to the console (standard output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S"))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            console_handler,
        ]
    )