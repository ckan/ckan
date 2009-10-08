import ckan.model as model

def get_rating(package):
    return package.get_average_rating(), len(package.ratings)

def set_my_rating(c, package, rating):
    if c.user:
        username = c.user
        user_or_ip = model.User.by_name(username)
        q = model.Rating.query.filter_by(package=package, user=user_or_ip)
    else:
        user_or_ip = c.author
        q = model.Rating.query.filter_by(package=package, user_ip_address=user_or_ip)
    set_rating(user_or_ip, package, rating)

def set_rating(user_or_ip, package, rating):
    user = None
    if isinstance(user_or_ip, model.User):
        user = user_or_ip
        rating_query = model.Rating.query.filter_by(package=package, user=user)
    else:
        ip = user_or_ip
        rating_query = model.Rating.query.filter_by(package=package, user_ip_address=ip)
    rating = float(rating)
    
    if rating_query.count():
        rating_obj = rating_query.one()
        rating_obj.rating = rating
    elif user:
        model.Rating(package=package,
                     user=user,
                     rating=rating)
    else:
        model.Rating(package=package,
                     user_ip_address=ip,
                     rating=rating)
    model.repo.commit_and_remove()
