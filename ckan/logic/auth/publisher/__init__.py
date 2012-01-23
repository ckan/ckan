

def _groups_intersect( groups_A, groups_B ):
    """ Return true if any of the groups in A are also in B (or size
        of intersection > 0)"""
    return len( set( groups_A ).intersection( set(groups_B) ) ) > 0
    