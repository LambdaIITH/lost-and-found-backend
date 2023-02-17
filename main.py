from typing import Union

from fastapi import FastAPI
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os

DATABASE = os.getenv("DATABASE")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASS = os.getenv("POSTGRES_PASS")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

conn = psycopg2.connect(
    database=DATABASE,
    user=POSTGRES_USER,
    password=POSTGRES_PASS,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    cursor_factory=RealDictCursor,
)

print("Opened database successfully!")

app = FastAPI()

# http://127.0.0.1:8000/
@app.get("/")
def read_root():
    return {"Hello": "World"}
