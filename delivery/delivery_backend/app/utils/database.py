import mysql.connector
from mysql.connector import pooling
import config

# Cria um pool de conexões para melhor performance
connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=5,
    pool_reset_session=True,
    host="localhost",
    database="eucomida",
    user="user",
    password="1234"
)

def get_connection():
    """
    Retorna uma conexão do pool.
    """
    return connection_pool.get_connection()