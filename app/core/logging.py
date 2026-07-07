import logging
import sys


_logger = None


def get_logger(name="maratron"):
    """Return a configured logger. Creates on first call."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        _logger.addHandler(handler)
    return _logger