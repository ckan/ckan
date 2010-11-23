import ckan.model as model

MIN_RATING = 1.0
MAX_RATING = 5.0

class RatingValueException(Exception):
    pass

def get_rating(package):
    return package.get_average_rating(), len(package.ratings)

def set_my_rating(c, package, rating):
    if c.user:
        username = c.user
        user_or_ip = model.User.by_name(username)
        q = model.Session.query(model.Rating).filter_by(package=package, user=user_or_ip)
    else:
        user_or_ip = c.author
        q = model.Session.query(model.Rating).filter_by(package=package, user_ip_address=user_or_ip)
    set_rating(user_or_ip, package, rating)

def set_rating(user_or_ip, package, rating):
    # Rates a package.
    # Caller function does need to create a new_revision,
    # but the commit happens in this one. (TODO leave caller to commit.)
    user = None
    if isinstance(user_or_ip, model.User):
        user = user_or_ip
        rating_query = model.Session.query(model.Rating).filter_by(package=package, user=user)
    else:
        ip = user_or_ip
        rating_query = model.Session.query(model.Rating).filter_by(package=package, user_ip_address=ip)

    try:
        rating = float(rating)
    except TypeError, ValueError:
        raise RatingValueException
    if rating > MAX_RATING or rating < MIN_RATING:
        raise RatingValueException
    
    if rating_query.count():
        rating_obj = rating_query.first()
        rating_obj.rating = rating
    elif user:
        rating = model.Rating(package=package,
                              user=user,
                              rating=rating)
        model.Session.add(rating)
    else:
        rating = model.Rating(package=package,
                              user_ip_address=ip,
                              rating=rating)
        model.Session.add(rating)
    model.repo.commit_and_remove()
    
