
from datetime import datetime


def validate_date_range(start_date: str, end_date: str):
    """
    This function validates the date range from start_date to end_date.
    
    Args:
        start_date: The start date.
        end_date: The end date.
    
    Returns:
        True if the input date range is valid, False otherwise.
    """
    try:
        start_date_time = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_time = datetime.strptime(end_date, '%Y-%m-%d')
        if start_date_time > end_date_time:
            return False
    except ValueError:
        return False
    return True

def get_helpers():
    return {
        "validate_date_range": validate_date_range,
    }
