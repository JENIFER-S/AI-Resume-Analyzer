import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=os.getenv("MYSQL_PASSWORD"),
    database="resume_analyzer"
)

print("Database Connected Successfully!")
conn.close()