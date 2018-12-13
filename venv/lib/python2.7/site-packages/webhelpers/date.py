"""Date and time helpers."""

from datetime import datetime
import time

__all__ = ["distance_of_time_in_words", "time_ago_in_words"]

def _process_carryover(deltas, carry_over):
    """A helper function to process negative deltas based on the deltas
    and the list of tuples that contain the carry over values"""
    for smaller, larger, amount in carry_over:
        if deltas[smaller] < 0:
            deltas[larger] -= 1
            deltas[smaller] += amount


def _pluralize_granularity(granularity):
    """Pluralize the given granularity"""
    if 'century' == granularity:
        return "centuries"
    return granularity + "s"


def _delta_string(delta, granularity):
    """Return the string to use for the given delta and ordinality"""
    if 1 == delta:
        return "1 " + granularity
    elif delta > 1:
        return str(delta) + " " + _pluralize_granularity(granularity)


def _is_leap_year(year):
    if year % 4 == 0 and year % 400 != 0:
        return True
    return False


def distance_of_time_in_words(from_time, to_time=0, granularity="second",
                              round=False):
    """
    Return the absolute time-distance string for two datetime objects,
    ints or any combination you can dream of.
    
    If times are integers, they are interpreted as seconds from now.
    
    ``granularity`` dictates where the string calculation is stopped.
    If set to seconds (default) you will receive the full string. If
    another accuracy is supplied you will receive an approximation.
    Available granularities are:
    'century', 'decade', 'year', 'month', 'day', 'hour', 'minute',
    'second'
    
    Setting ``round`` to true will increase the result by 1 if the fractional
    value is greater than 50% of the granularity unit.
    
    Examples:

    >>> distance_of_time_in_words(86399, round=True, granularity='day')
    '1 day'
    >>> distance_of_time_in_words(86399, granularity='day')
    'less than 1 day'
    >>> distance_of_time_in_words(86399)
    '23 hours, 59 minutes and 59 seconds'
    >>> distance_of_time_in_words(datetime(2008,3,21, 16,34),
    ... datetime(2008,2,6,9,45))
    '1 month, 15 days, 6 hours and 49 minutes'
    >>> distance_of_time_in_words(datetime(2008,3,21, 16,34), 
    ... datetime(2008,2,6,9,45), granularity='decade')
    'less than 1 decade'
    >>> distance_of_time_in_words(datetime(2008,3,21, 16,34), 
    ... datetime(2008,2,6,9,45), granularity='second')
    '1 month, 15 days, 6 hours and 49 minutes'
    """
    granularities = ['century', 'decade', 'year', 'month', 'day', 'hour',
                     'minute', 'second']
    
    # 15 days in the month is a gross approximation, but this
    # value is only used if rounding to the nearest month
    granularity_size = {'century': 10, 'decade': 10, 'year': 10, 'month': 12,
                        'day': 15, 'hour': 24, 'minute': 60, 'second': 60 }
    
    if granularity not in granularities:
        raise ValueError("Please provide a valid granularity: %s" %
                        (granularities))
    
    # Get everything into datetimes
    if isinstance(from_time, int):
        from_time = datetime.fromtimestamp(time.time()+from_time)
    
    if isinstance(to_time, int):
        to_time = datetime.fromtimestamp(time.time()+to_time)
    
    # Ensure that the to_time is the larger
    if from_time > to_time:
        s = from_time
        from_time = to_time
        to_time = s
    # Stop if the tiems are equal
    elif from_time == to_time:
        return "0 " + _pluralize_granularity(granularity)
                
    # Collect up all the differences
    deltas = {'century': 0, 'decade': 0, 'year': 0, 'month': 0, 'day': 0,
              'hour': 0, 'minute': 0, 'second' : 0}

    # Collect the easy deltas
    for field in ['month', 'hour', 'day', 'minute', 'second']:
        deltas[field] = getattr(to_time,field) - getattr(from_time,field)
    
    # deal with year, century and decade    
    delta_year = to_time.year - from_time.year
    if delta_year >= 100:
        deltas['century'] = delta_year // 100
    if delta_year % 100 >= 10:
        deltas['decade'] = delta_year // 10 - deltas['century'] * 10
    if delta_year % 10:
        deltas['year'] = delta_year % 10
            
    # Now we need to deal with the negative deltas, as we move from
    # the smallest granularity to the largest when we encounter a negative
    # we will 'borrow' from the next highest value.  Because to_time is
    # the larger of the two, 
    carry_over = [('second', 'minute', granularity_size['second']),
                  ('minute', 'hour', granularity_size['minute']),
                  ('hour', 'day', granularity_size['hour'])]
    
    _process_carryover(deltas, carry_over)
            
    # Day is its own special animal.  We need to deal with negative days
    # differently depending on what months we are spanning across.  We need to
    # look up the from_time.month value in order to bring the number of days
    # to the end of the month.
    month_carry = [None, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if deltas['day'] < 0:
        deltas['month'] -= 1
        # Deal with leap years
        if (from_time.month) == 2 and _is_leap_year(from_time.year):
            deltas['day'] += 29
        else:
            deltas['day'] += month_carry[from_time.month]
    
    carry_over = [('month', 'year', granularity_size['month']),
                  ('year', 'decade', granularity_size['year']),
                  ('decade', 'century', granularity_size['decade'])]
    
    _process_carryover(deltas, carry_over)
    
    # Display the differences we care about, at this point we should only have
    # positive deltas
    return_strings = []
    for g in granularities:
        delta = deltas[g]
        # This is the finest granularity we will display
        if g == granularity:
            # We can only use rounding if the granularity is higher than
            # seconds
            if round and g != 'second':
                i = granularities.index(g)
                # Get the next finest granularity and it's delta
                g_p = granularities[i + 1]
                delta_p = deltas[g_p]
                # Determine if we should round up
                if delta_p > granularity_size[g_p] / 2:
                    delta += 1
                
                if delta != 0:
                    return_strings.append(_delta_string(delta, g))
                
                if not return_strings:
                    return "less than 1 " + granularity
                break
                
            else:
                if delta != 0:
                    return_strings.append(_delta_string(delta, g))

                # We're not rounding, check to see if we have encountered
                # any deltas to display, if not our time difference
                # is less than our finest granularity
                if not return_strings:
                    return "less than 1 " + granularity
                break
        # Read the value and continue   
        else:          
            if delta != 0:
                return_strings.append(_delta_string(delta, g))

    if len(return_strings) == 1:
        return return_strings[0]
    return ", ".join(return_strings[:-1]) + " and " + return_strings[-1]


def time_ago_in_words(from_time, granularity="second", round=False):
    """
    Return approximate-time-distance string for ``from_time`` till now.

    Same as ``distance_of_time_in_words`` but the endpoint is now.
    """
    return distance_of_time_in_words(from_time, datetime.now(), 
        granularity, round)

