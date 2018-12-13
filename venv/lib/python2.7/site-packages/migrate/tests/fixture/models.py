from sqlalchemy import *

# test rundiffs in shell
meta_old_rundiffs = MetaData()
meta_rundiffs = MetaData()
meta = MetaData()

tmp_account_rundiffs = Table('tmp_account_rundiffs', meta_rundiffs,
    Column('id', Integer, primary_key=True),
    Column('login', Text()),
    Column('passwd', Text()),
)

tmp_sql_table = Table('tmp_sql_table', meta, Column('id', Integer))
