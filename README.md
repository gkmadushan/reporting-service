alembic init alambic  #to init alembic in the project
alembic.ini # set the database query string
alembic revision -m "init" # to init alembic (init is the comments, new versions also write the same way)
alembic upgrade head # to run the upgrade


generate db models using SQL code gen
sqlacodegen postgresql://postgres:pswdrd123@db/knowledge_base
