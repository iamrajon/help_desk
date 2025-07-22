import logging

def get_logger(name=None):
    """
    Returns a logger with the given name.
    If name is None, returns the root logger.
    """
    return logging.getLogger(name or __name__)