import os
import psycopg2
import psycopg2.extras


def get_db():
    return psycopg2.connect(os.environ["SUPABASE_DB_URL"])
