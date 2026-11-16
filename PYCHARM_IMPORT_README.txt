RPMS PYTHON PYCHARM PROJECT
===========================

1. Extract the project ZIP.
2. Open the project folder in PyCharm.
3. Configure the Python interpreter if PyCharm asks.
4. Open Terminal and install dependencies:
   pip install -r requirements.txt
5. Configure these environment variables for MySQL:
   RPMS_DB_HOST, RPMS_DB_PORT, RPMS_DB_USER, RPMS_DB_PASSWORD,
   RPMS_DB_NAME, and RPMS_ACTOR_USER_ID
6. Run main.py.

The schema script drops and recreates the database. Run it only when that reset
is intended, then run sql/rpms_sample_data.sql to create demo user ID 1.
