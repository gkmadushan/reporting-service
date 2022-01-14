from fastapi import Header, HTTPException, Depends, status, Cookie, Request
from utils.database import get_db, get_db_config
from utils.email import send_email
import hashlib
import os
import jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
import secrets
import string
from typing import Optional

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
alphabet = string.ascii_letters + string.digits


async def get_token_header(access_token: Optional[str] = Cookie(default=None), request: Request = None):
    user_id = validate_token(access_token)
    if user_id == False:
        raise HTTPException(status_code=401, detail="Authorization Bearer token invalid or expired")
    else:
        return user_id


def hash(plaintext: str):
    return hashlib.sha512(str(plaintext+os.getenv('HASH_SALT')).encode('utf-8')).hexdigest()


def generate_token(user_id,  lifetime=5):
    payload = {
        'exp': datetime.utcnow() + timedelta(days=0, minutes=lifetime),
        'iat': datetime.utcnow(),
        'sub': user_id
    }
    return jwt.encode(
        payload,
        os.getenv('JWT_SECRET'),
        algorithm='HS256'
    )


def refresh_token(refresh_token,  lifetime=5):
    user_id = validate_token(refresh_token)
    if(user_id != False):
        return generate_token(user_id)
    else:
        raise HTTPException(status_code=401, detail="Authorization refresh token invalid or expired")


def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=['HS256'])
        user_id: str = payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="token invalid or expired")

    return user_id


def get_secret_random(size=100):
    return ''.join(secrets.choice(alphabet) for i in range(size))


async def common_params():
    return {}


async def send_email_handler():
    send_email()
