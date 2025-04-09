from functools import wraps
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s", 
    handlers=[
        logging.StreamHandler(), 
    ]
)



def log_execution(description: str):
    """
    Decorator to log function execution when verbosity is enabled.

    Parameters
    ----------
    description : str
        A title describing the log message.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                result = func(self, *args, **kwargs)
                if self.verbosity:
                    self._log(result, description)
                return result
            
            except Exception as e:
                logger.exception(f"Error during {description}: {str(e)}")
                return None
        return wrapper
    return decorator