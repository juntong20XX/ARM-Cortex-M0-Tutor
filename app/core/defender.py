"""
Used for retrying upon encountering errors, reporting errors, exiting.
"""
import logging
from tenacity import retry, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)


def error_handle_fatal(retry_state):
    """
    An error cannot be fixed. The function will print debug text and stop app.
    """
    try:
        result = retry_state.outcome.result()
    except Exception as err:
        logger.error("An error cannot be fixed.", str(err), err.args,f"At {retry_state.fn}",
                     "with", retry_state.args, retry_state.kwargs)
    else:
        logger.error("An error cannot be fixed. An unexpected value attached", result)


def error_handle_warning(retry_state):
    """

    """
    # TODO
    try:
        result = retry_state.outcome.result()
    except Exception as err:
        logger.warning("A warning: an issue occurred.", str(err), err.args, f"At {retry_state.fn}",
                       "with", retry_state.args, retry_state.kwargs)
    else:
        logger.warning("A warning: an unexpected value attached", result)