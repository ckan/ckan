

def _groups_intersect( groups_A, groups_B ):
    """ Return true if any of the groups in A are also in B (or size
        of intersection > 0).  If both are empty for now we will allow it """
    ga = set(groups_A)
    gb = set(groups_B)
    
    return len( ga.intersection( gb ) ) > 0
    