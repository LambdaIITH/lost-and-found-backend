from typing import List, Dict

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pydantic import BaseModel
import aiosql
import aiohttp
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as req
import json


load_dotenv()

DATABASE = os.getenv("DATABASE")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASS = os.getenv("POSTGRES_PASS")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET_ID = os.getenv("CLIENT_SECRET_ID")

conn = psycopg2.connect(
    database=DATABASE,
    user=POSTGRES_USER,
    password=POSTGRES_PASS,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    cursor_factory=RealDictCursor
)

queries = aiosql.from_path("./queries.sql", "psycopg2")
app = FastAPI()
#just a tial commit

#hello world

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl="http://localhost:8000/auth/callback",
    scopes={
        "openid": "OpenID Connect",
        "email": "Email address",
        "profile": "User profile information",
    }
)


def get_access_token(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    try:
        id_info = id_token.verify_oauth2_token(
            token, requests.Request(), CLIENT_ID)
        email = id_info["email"]
    except Exception as error:
        print(error)
        raise HTTPException(
            status_code=401, detail="Invalid or expired access token")
    return email


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in ("/login", "/", "/auth/callback"):
        return await call_next(request)

    try:
        access_token = request.cookies["access_token"]
    except KeyError:
        return RedirectResponse(url="/login")

    request.state.user = get_access_token(request, token=access_token)

    return await call_next(request)


@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    auth_uri = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&response_type=code&scope=email&redirect_uri=http://localhost:8000/auth/callback"
    return RedirectResponse(auth_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request, response: Response):
    authorization_code = request.query_params["code"]
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code": authorization_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET_ID,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/auth/callback",
    }
    token_response = req.post(token_url, data=token_payload)
    token_data = token_response.json()
    access_token = token_data.get("access_token")

    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return RedirectResponse("/")


class FoundItem(BaseModel):
    item_id: int
    user_email: str


@ app.patch("/items/{item_id}")
def update_item_status(
    request: Request,
    found_item: FoundItem,
    item_id: int,
    email: str = Depends(get_access_token)
):
    # Verify user has permission to update the item
    if email != found_item.user_email:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Get information of the item to be edited
    res_raw = queries.get_item_by_id(conn, item_id=item_id)

    # Check if the item exists
    if res_raw is None or len(res_raw) == 0:
        raise HTTPException(status_code=409, detail="Item not found")

    # Convert the result to a JSON object
    res_get = json.loads(json.dumps(res_raw, default=str))

    # Swap the current status of the item
    status = 2 if res_get[0]["status"] == 1 else 1
    res = queries.update_item_status(conn, item_id=item_id, status=status)

    # Check if the update was successful
    if res != 1:
        raise HTTPException(status_code=500, detail="Something went wrong")

    return {"status": "success"}


# http://127.0.0.1:8000/items/?sort=name
@ app.get("/items/")
async def get_all_items(sort: str = "date_of_posting"):
    res_raw = queries.get_all_items(conn)

    if res_raw is None:
        raise HTTPException(status_code=409, detail="No Items found")

    res_get = json.loads(json.dumps(res_raw, default=str))

    try:
        res_get = sorted(res_get, key=lambda k: k[sort])
    except:
        raise HTTPException(status_code=409, detail="Invalid sort parameter")

    if not res_get:
        raise HTTPException(status_code=409, detail="No Items found")

    return res_get


class lostItem(BaseModel):
    name: str
    description: str
    user_email: str


# Define a POST method to create a new item
@ app.post("/items")
def create_item(request: Request, item: lostItem, email: str = Depends(get_access_token)):
    # Extract the required fields from the item object
    user_email = item.user_email
    name = item.name
    description = item.description

    # Check if the user email matches with the email provided in the request
    if email != user_email:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Create a new item in the database
    res = queries.create_item(conn, user_email=user_email,
                              name=name, description=description)
    conn.commit()

    # Check if the item creation was successful
    if res:
        raise HTTPException(
            status_code=200, detail="Item created successfully")
    else:
        raise HTTPException(status_code=400, detail="Item creation failed")
