import logging
from logging.handlers import RotatingFileHandler
import os

def setup_agentic_logging(log_file=None):
    """
    Set up dedicated logging for the backend_agentic service.
    Creates a separate log file specifically for agentic operations.
    """
    if log_file is None:
        # Create log file in the backend_agentic directory
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agentic_backend.log')
    
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create rotating file handler for agentic logs
    handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=7  # Keep 7 backup files
    )
    
    # Create formatter with more detailed format for agentic operations
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(name)s:%(module)s:%(lineno)d: %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Create dedicated logger for agentic backend
    agentic_logger = logging.getLogger('agentic_backend')
    agentic_logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers to avoid duplicates
    agentic_logger.handlers.clear()
    agentic_logger.addHandler(handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    agentic_logger.propagate = False
    
    # Also create loggers for specific agentic components
    component_loggers = [
        'agentic_backend.routes',
        'agentic_backend.workers',
        'agentic_backend.services',
        'agentic_backend.llm',
        'agentic_backend.aggregator',
        'agentic_backend.context',
        'agentic_backend.faiss_rag'
    ]
    
    for component in component_loggers:
        comp_logger = logging.getLogger(component)
        comp_logger.setLevel(logging.DEBUG)
        comp_logger.handlers.clear()
        comp_logger.addHandler(handler)
        comp_logger.propagate = False
    
    # Capture third-party library logs that are related to agentic operations
    third_party_loggers = [
        'selector_events',
        '_base_client', 
        '_trace',
        '_client',
        '_internal',
        'SentenceTransformer',
        'connectionpool',
        'loader',
        'httpcore',
        'httpx',
        'openai',
        'deepseek',
        'langchain',
        'faiss'
    ]
    
    # Create a filter to only capture logs when agentic operations are running
    class AgenticContextFilter(logging.Filter):
        def filter(self, record):
            # Only capture third-party logs if they're happening in agentic context
            # We can detect this by checking if any agentic loggers are active
            import threading
            thread_name = threading.current_thread().name
            # Capture logs from main thread or threads with agentic in name
            return 'agentic' in thread_name.lower() or thread_name == 'MainThread'
    
    agentic_filter = AgenticContextFilter()
    
    for lib_logger_name in third_party_loggers:
        lib_logger = logging.getLogger(lib_logger_name)
        # Don't clear handlers for third-party loggers, just add our handler
        lib_logger.addHandler(handler)
        lib_logger.addFilter(agentic_filter)
        # Set level to INFO to reduce noise from DEBUG logs
        lib_logger.setLevel(logging.INFO)
    
    # Log initialization
    agentic_logger.info("Agentic backend logging initialized")
    agentic_logger.info(f"Log file: {log_file}")
    
    return agentic_logger

def get_agentic_logger(name=None):
    """
    Get the agentic logger instance.
    
    Args:
        name: Optional name for the logger (e.g., 'agentic_backend.workers.scraper')
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f'agentic_backend.{name}')
    return logging.getLogger('agentic_backend')

class AgenticLogContext:
    """
    Context manager to temporarily redirect all logs to agentic logger during operations.
    """
    
    def __init__(self):
        self.original_handlers = {}
        self.agentic_handler = None
        
    def __enter__(self):
        # Get the agentic handler
        agentic_logger = logging.getLogger('agentic_backend')
        if agentic_logger.handlers:
            self.agentic_handler = agentic_logger.handlers[0]
            
            # Temporarily add agentic handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(self.agentic_handler)
            
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove agentic handler from root logger
        if self.agentic_handler:
            root_logger = logging.getLogger()
            if self.agentic_handler in root_logger.handlers:
                root_logger.removeHandler(self.agentic_handler)

def capture_all_logs_to_agentic():
    """
    Utility function to capture all logs to agentic logger.
    Call this at the start of agentic operations.
    """
    agentic_logger = logging.getLogger('agentic_backend')
    if agentic_logger.handlers:
        handler = agentic_logger.handlers[0]
        
        # Add handler to root logger to capture all logs
        root_logger = logging.getLogger()
        if handler not in root_logger.handlers:
            root_logger.addHandler(handler)
            
        # Also add to common third-party loggers
        common_loggers = [
            'asyncio', 'urllib3', 'requests', 'httpx', 'openai', 
            'langchain', 'sentence_transformers', 'transformers',
            'torch', 'numpy', 'pandas', 'faiss'
        ]
        
        for logger_name in common_loggers:
            logger = logging.getLogger(logger_name)
            if handler not in logger.handlers:
                logger.addHandler(handler)

def log_capture_status():
    """
    Utility function to check which loggers are being captured by agentic logging.
    """
    agentic_logger = get_agentic_logger()
    if not agentic_logger.handlers:
        agentic_logger.warning("No agentic handlers found!")
        return
    
    handler = agentic_logger.handlers[0]
    
    # Check root logger
    root_logger = logging.getLogger()
    root_has_handler = handler in root_logger.handlers
    
    agentic_logger.info(f"Agentic log capture status:")
    agentic_logger.info(f"  - Root logger has agentic handler: {root_has_handler}")
    agentic_logger.info(f"  - Agentic log file: {handler.baseFilename}")
    agentic_logger.info(f"  - Total agentic handlers: {len(agentic_logger.handlers)}")
    
    # Check some common third-party loggers
    third_party_loggers = ['selector_events', '_base_client', '_trace', 'SentenceTransformer']
    for logger_name in third_party_loggers:
        logger = logging.getLogger(logger_name)
        has_handler = handler in logger.handlers
        agentic_logger.info(f"  - {logger_name} has agentic handler: {has_handler}")

def clear_agentic_log_capture():
    """
    Remove agentic handlers from root and third-party loggers.
    Useful for cleanup or testing.
    """
    agentic_logger = get_agentic_logger()
    if not agentic_logger.handlers:
        return
    
    handler = agentic_logger.handlers[0]
    
    # Remove from root logger
    root_logger = logging.getLogger()
    if handler in root_logger.handlers:
        root_logger.removeHandler(handler)
    
    # Remove from third-party loggers
    all_loggers = [logging.getLogger(name) for name in logging.Logger.manager.loggerDict]
    for logger in all_loggers:
        if handler in logger.handlers:
            logger.removeHandler(handler)
    
    agentic_logger.info("Cleared agentic log capture from all loggers")