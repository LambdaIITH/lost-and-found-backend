from typing import Union
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, HTMLResponse
import aiosql
from functools import wraps

# load environment variables
load_dotenv(".env")
DATABASE = os.getenv("DATABASE")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASS = os.getenv("POSTGRES_PASS")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
SECRET_KEY = os.getenv("SECRET_KEY")

conn = psycopg2.connect(
    database=DATABASE,
    user=POSTGRES_USER,
    password=POSTGRES_PASS,
    host=POSTGRES_HOST,
    port=POSTGRES_PORT,
    cursor_factory=RealDictCursor,
)

def user_check(func):
    @wraps(func)
    async def innerfunction(*args, **kwargs):
        user = kwargs['request'].session.get('user')
        lost_email = queries.get_email(conn, id=kwargs['id'])
        if user is not None:
            user_email = user['email']
            if user_email == lost_email[0]['seller_email']:
                return await func(*args, **kwargs)
        return {"error": "You are not the owner of this item"}
    return innerfunction

def is_authenticated(func):
    @wraps(func)
    async def innerfunction(*args, **kwargs):
        user = kwargs['request'].session.get('user')
        if user is not None:
            return await func(*args, **kwargs)
        return {"error": "You are not logged in"}
    return innerfunction

app = FastAPI()
queries = aiosql.from_path("init.sql", "psycopg2")
# queries.create_schema(conn)
conn.commit()

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
oauth = OAuth()
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    client_kwargs={
        'scope': 'openid email profile'
    }
)

class lostItem(BaseModel):
    item_name: str
    description: str

# http://127.0.0.1:8000/
@app.get("/")
def read_root(request: Request):
    user = request.session.get('user')
    if user:
        return user['name']
    return {"Hello": "World"}

# http://127.0.0.1:8000/login
#route for login using google
@app.route('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth')
    return await oauth.google.authorize_redirect(request, redirect_uri)

#route for callback after login
@app.route('/auth')
async def auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTMLResponse(f'<h1>{error.error}</h1>')
    user = await oauth.google.parse_id_token(request, token)
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')

# http://127.0.0.1:8000/lost
# Route to add lost item
@app.post('/lost')
@is_authenticated
async def lost_item(request:Request, item: lostItem):
    queries.insert_item(conn, name=item.item_name, description=item.description, user_email=request.session.get('user')['email'])
    conn.commit()

# Route to get all lost items
@app.get('/get-items')
async def get_items():
    items = queries.get_all_items(conn)
    return items

# Route to get update status of lost item
@app.put('/update-item/{id}')
@user_check
async def update_item(request:Request, id):
    queries.update_item(conn, id=id)
    conn.commit()
    
@app.post('/add_user/{phone_number}}')
async def add_user(phone_number, request: Request):
    queries.add_user(conn, name=request.session.get('user')['name'], email=request.session.get('user')['name'], phone_number=phone_number)
    conn.commit()