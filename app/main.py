from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routers import report
from fastapi.security import OAuth2PasswordBearer
from dependencies import get_db, get_db_config
import sys


app = FastAPI(debug=True)

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

#middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#user routes
app.include_router(report.router)