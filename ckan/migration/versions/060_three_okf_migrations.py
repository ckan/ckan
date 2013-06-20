# This is a merge of OKF's migrations 58, 59 and 60.
#
# The release-1.7.1-dgu branch of ckan had 2 extra migration steps on top
# of the ones on the release-1.7.1 (OKF) branch:
# 058_activity_index.py
# 059_precalc_cache.py
#
# When moving a DGU db from that branch (so v59) to this branch
# (release-2.0.1-dgu) it needs the OKF migrations 58 and 59. These two plus 60
# are rolled into this one migration:
# 058_add_follower_tables.py
# 059_add_related_count_and_flag.py
# 060_add_system_info_table.py
#
# The only thing to watch out for is if one of these sub-migrations fails -
# they might not be idempotent.

import okf_058_add_follower_tables
import okf_059_add_related_count_and_flag
import okf_060_add_system_info_table

def upgrade(migrate_engine):
    okf_058_add_follower_tables.upgrade(migrate_engine)
    okf_059_add_related_count_and_flag.upgrade(migrate_engine)
    okf_060_add_system_info_table.upgrade(migrate_engine)
