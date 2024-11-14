from ckan.plugins.toolkit import ValidationError

def max_30_days_validator(value):
    if value > 30 or value <= 0:
        raise ValidationError("The 'recent_active_days' value cannot exceed 30 days and less than 0.")
    return value