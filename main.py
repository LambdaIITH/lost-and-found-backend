from typing import Union

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.responses import RedirectResponse,HTMLResponse
from fastapi.security import OAuth2AuthorizationCodeBearer
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pydantic import BaseModel
import aiosql
import aiohttp
from fastapi import FastAPI, HTTPException
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
    cursor_factory=RealDictCursor,
)

print("Opened database successfully!")

app = FastAPI()
oauth2_scheme = OAuth2AuthorizationCodeBearer(authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth", tokenUrl="http://localhost:8000/auth/callback",scopes={"openid": "OpenID Connect",
        "email": "Email address",
        "profile": "User profile information",})

def get_access_token(request: Request, token: str = Depends(oauth2_scheme)) -> str:
    # Verify and decode the access token from the cookie
    try:
        # Verify the ID token and get the user's email address
        id_info = id_token.verify_oauth2_token(token, requests.Request(), CLIENT_ID)
        email : str = id_info["email"]
    except Exception as error:
        print(error)
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    return email

queries = aiosql.from_path("./queries.sql", "psycopg2")




@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path == "/login" or request.url.path == "/" or request.url.path == "/auth/callback":
        response = await call_next(request)
        return response
    
    try:
        # Try to get the access token from the cookie
        # was using curl requests to test eveything so didn't have a cookie
        access_token = request.cookies["access_token"] 
    except KeyError:
        # If the access token is not present, redirect the user to the login page
        return RedirectResponse(url="/login")

    # Authenticate the user using the access token
    request.state.user = get_access_token(request, token=access_token)

    # Call the next middleware or route handler in the chain
    response = await call_next(request)

    return response

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    # Redirect the user to Google's authentication page
    auth_uri : str = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&response_type=code&scope=email&redirect_uri=http://localhost:8000/auth/callback"
    return RedirectResponse(auth_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request, response: Response):

    # Exchange the authorization code for an access token
    authorization_code : str = request.query_params["code"]
    
    token_url : str = "https://oauth2.googleapis.com/token"
    
    # token_payload is the data that is sent to the token_url
    token_payload : dict = {
        "code": authorization_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET_ID,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:8000/auth/callback"
    }
    token_response = req.post(token_url, data=token_payload)
    token_data = token_response.json()
    access_token = token_data.get("access_token")
    
    # Set a cookie with the access token and redirect the user to the home page
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return RedirectResponse("/")

@app.get("/")
def read_root():
    return {"Hello": "World"}

# http://127.0.0.1:8000/items/{item_id}
# this is an API that lets the user who lost an item to update the status of the item 
# will use aiosql to query the database
class FoundItem(BaseModel):
    item_id: int
    user_email: str

@app.patch("/items/{item_id}")
def update_item_status(request: Request,found_item: FoundItem, email: str = Depends(get_access_token)):
    #item_id = request.match_info['item_id']
    # update the status of the item
    
    if email != found_item.user_email:
        raise HTTPException(status_code=403, detail="Forbidden")

    # gets the information of the item to be edited
    res_raw = queries.get_item_by_id(conn, item_id=item_id)
    
    # checks if the item exists
    if (res_raw == None):
        raise HTTPException(status_code=409, detail="Item not found")

    # converts the result to a json object
    res_get = json.dumps(res_raw, default=str)
    res_get = json.loads(res_get)


    if (len(res_get) == 0):
        raise HTTPException(status_code=409, detail="Item not found")

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


# http://127.0.0.1:8000/items/?sort=name
@app.get("/items/")
async def get_all_items(sort: str = None):
    if (sort == None):
        sort = "date_of_posting"

    res_raw = queries.get_all_items(conn)

    if (res_raw == None):
        raise HTTPException(status_code=409, detail="No Items found")

    # converts the result to a json object
    res_get = json.dumps(res_raw, default=str)
    res_get = json.loads(res_get)

    # sorts the result based on the parameter
    try:
        res_get = sorted(res_get, key=lambda k: k[sort])
    except:
        raise HTTPException(status_code=409, detail="Invalid sort parameter")

    if (len(res_get) == 0):
        raise HTTPException(status_code=409, detail="No Items found")


    raise HTTPException(status_code=200, detail=res_get)

class lostItem(BaseModel):
     name: str
     description: str
     user_email: str

# http://127.0.0.1:8000/items/
@app.post("/items")
def create_item(request: Request, item: lostItem, email: str = Depends(get_access_token)):
    user_email = item.user_email
    name = item.name
    description = item.description

    if email != user_email:
        raise HTTPException(status_code=403, detail="Forbidden")
    res = queries.create_item(conn, user_email=user_email, name=name, description=description)

    conn.commit()

    if (res):
        raise HTTPException(status_code=200, detail="Item created successfully")
    else:
        raise HTTPException(status_code=400, detail="Item creation failed")

