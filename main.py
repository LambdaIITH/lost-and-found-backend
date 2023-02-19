from typing import Union

from fastapi import FastAPI
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pydantic import BaseModel
import aiosql
import aiohttp
from fastapi import FastAPI, HTTPException
import json

load_dotenv()

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
queries = aiosql.from_path("./queries.sql", "psycopg2")

# http://127.0.0.1:8000/
@app.get("/")
def read_root():
    return {"Hello": "World"}

# http://127.0.0.1:8000/items/{item_id}
# this is an API that lets the user who lost an item to update the status of the item 
# will use aiosql to query the database
@app.patch("/items/{item_id}")
def update_item_status(item_id: int):
    #item_id = request.match_info['item_id']
    # update the status of the item

    # gets the information of the item to be edited
    res_raw = queries.get_item_by_id(conn, item_id=item_id)
    
    # checks if the item exists
    if (res_raw == None):
        raise HTTPException(status_code=404, detail="Item not found")

    # converts the result to a json object
    res_get = json.dumps(res_raw, default=str)
    res_get = json.loads(res_get)


    if (len(res_get) == 0):
        raise HTTPException(status_code=404, detail="Item not found")

    # swaps the curernt status of the item
    if (res_get[0]["status"] == 1):
        res = queries.update_item_status(conn, item_id=item_id, status = 'FALSE')
    else:
        res = queries.update_item_status(conn, item_id=item_id, status = 'TRUE')

    conn.commit()

    if (res):
        raise HTTPException(status_code=200, detail="Status updated successfully")
    else:
        raise HTTPException(status_code=400, detail="Status update failed")


# http://127.0.0.1:8000/items/?sort=date
@app.get("/items/")
async def get_all_items(sort: str = None):
    if (sort == None):
        sort = "date_of_posting"

    print(sort)

    res_raw = queries.get_all_items(conn)

    if (res_raw == None):
        raise HTTPException(status_code=404, detail="No Items found")

    # converts the result to a json object
    res_get = json.dumps(res_raw, default=str)
    res_get = json.loads(res_get)

    # sorts the result based on the parameter
    try:
        res_get = sorted(res_get, key=lambda k: k[sort])
    except:
        raise HTTPException(status_code=404, detail="Invalid sort parameter")

    if (len(res_get) == 0):
        raise HTTPException(status_code=404, detail="No Items found")


    raise HTTPException(status_code=200, detail=res_get)