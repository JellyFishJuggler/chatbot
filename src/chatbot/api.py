from fastapi import FastAPI, Depends, HTTPException, Response, Request, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from pwdlib import PasswordHash

from chatbot.database import sessionMaker, engine
import chatbot.model
from sqlalchemy.orm import Session
from chatbot.model import User  
from chatbot.llm_model import _responseChatBot, getHistory

import jwt
from datetime import datetime, timezone, timedelta

from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
import os

import random

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from io import BytesIO
from pypdf import PdfReader
from src.chatbot.llm.rag import ingest_text

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Allows all headers (including Authorization bearer tokens)
)

#python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'

security = HTTPBearer()

pwd_hash = PasswordHash.recommended()

chatbot.model.Base.metadata.create_all(bind=engine)


def get_current_user(request: Request):

    token = request.cookies.get('access_token')

    if not token:
        raise HTTPException(status_code=401, detail='Not Authorized')

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username : str = payload.get('sub')
        if username is None:
            raise HTTPException(status_code=401, detail='Invalid authentication credentials')
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail='Could not validate crednetials')


def create_access_token(data: dict):

    to_encode = data.copy()
    exp_time = datetime.now(timezone.utc) + timedelta(minutes=10)
    to_encode.update({"exp":exp_time})

    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encode_jwt


def get_db():
    db = sessionMaker()
    
    try:
        yield db
    finally:
        db.close()

def send_otp_email(receiver_email: str, otp: str):
    sender_email = os.getenv('SMTP_EMAIL')
    sender_password = os.getenv('SMTP_PASSWORD')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    try:
        port = int(os.getenv('SMTP_PORT', '587'))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="SMTP_PORT must be a number.") from exc

    if not sender_email or not sender_password:
        raise HTTPException(
            status_code=500,
            detail="SMTP_EMAIL and SMTP_PASSWORD must be configured."
        )

    message = MIMEMultipart("alternative")
    message["Subject"] = "Your AI Chat Platform Verification Code"
    message["From"] = sender_email
    message["To"] = receiver_email

    text = f"Your verification code is: {otp}"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4; border-radius: 8px;">
        <h2 style="color: #bb86fc;">Account Verification</h2>
        <p>Thank you for signing up! Use the verification code below to activate your account:</p>
        <div style="font-size: 24px; font-weight: bold; background: #fff; padding: 10px; width: fit-content; border-radius: 4px; letter-spacing: 4px; color: #333;">
            {otp}
        </div>
        <p style="color: #666; font-size: 12px; margin-top: 20px;">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """

    message.attach(MIMEText(text, 'plain'))
    message.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP(smtp_server, port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"--- [EMAIL SUCCESS] OTP successfully sent to {receiver_email} ---")

    except (OSError, smtplib.SMTPException) as e:
        print(f"--- [EMAIL ERROR] Failed to send email: {e} ---")
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP email. Check the SMTP host, port, TLS, and credentials."
        ) from e

class Signup(BaseModel):
    username: str
    password: str
    mail: str

class Login(BaseModel):
    username:str
    password:str

class Chat(BaseModel):
    message: str

class VerifyOTP(BaseModel):
    username:str
    otp:str

@app.get('/')
def home():
    return {"api_status" : "live"}

@app.get('/me')
def current_session(currentUser: str = Depends(get_current_user)):
    return {"username": currentUser}

@app.post('/login') 
def login(credentials: Login, response: Response, database: Session = Depends(get_db)):

    user = database.query(User).filter(credentials.username == User.username).first()
    if not user:
        return {"error" : "No such user exists.", "login" : "failed"}

    if not user.is_verified:
        return {"error" : "Please verify your account first."}

    if not pwd_hash.verify(credentials.password, user.password):
        return {"error" : "Wrong password. Login Failed. Try again."}
    
    encoded_token = create_access_token(data={'sub':user.username})

    response.set_cookie(
        key='access_token',
        value=encoded_token,
        httponly=True,
        secure=False,
        samesite='lax',
        max_age=600
    )
    
    return {"login" : "success", "username" : user.username, "access_token" : encoded_token, "token_type" : "bearer"}


@app.post('/logout')
def logout(response: Response):
    response.delete_cookie(
        key='access_token',
        httponly=True,
        secure=False,
        samesite='lax'
    )
    return {"logout": "success"}

@app.post('/signup')
def signup(credentials: Signup, database: Session = Depends(get_db)):

    existing_user = database.query(User).filter(credentials.username == User.username).first()
    if existing_user:
        if (
            not existing_user.is_verified
            and existing_user.mail == credentials.mail
            and pwd_hash.verify(credentials.password, existing_user.password)
        ):
            generatedOTP = str(random.randint(1000,9999))
            existing_user.otp = generatedOTP
            database.flush()
            send_otp_email(existing_user.mail, generatedOTP)
            database.commit()
            return {"signin": "success"}
        return {"error" : "Username taken"}

    existing_mail = database.query(User).filter(credentials.mail == User.mail).first()
    if existing_mail:
        return {"error" : "Account exists with this mail."}

    generatedOTP = str(random.randint(1000,9999))

    newUser = User(
        username = credentials.username,
        password = pwd_hash.hash(credentials.password),
        mail = credentials.mail,
        otp=generatedOTP,
        is_verified=False
    )

    database.add(newUser)
    database.flush()
    send_otp_email(credentials.mail, generatedOTP)
    database.commit()

    return {"signin" : "success"}


@app.post('/verify-otp')
def verify_otp(credentials: VerifyOTP, response: Response, database: Session = Depends(get_db)):

    user = database.query(User).filter(credentials.username == User.username).first()
    if not user:
        return {"error"  : "User not found."}

    if user.otp != credentials.otp:
        return {"otp_status" : "Invalid OTP"}


    user.is_verified = True
    user.otp = ""
    database.commit()

    encoded_token = create_access_token(data={'sub': user.username})
    response.set_cookie(
        key='access_token',
        value=encoded_token,
        httponly=True,
        secure=False,
        samesite='lax',
        max_age=600
    )

    return {
        "verification": "success",
        "message": "Account verified successfully.",
        "username": user.username
    }

@app.post('/chat')
def chat(credentials: Chat, currentUser: str = Depends(get_current_user)):

    userInput = credentials.message
    response = _responseChatBot(_humanMessage=userInput, thread_id=currentUser)

    return {
        "username" : currentUser,
        "HumanMessage" : userInput,
        "AIMessage" : response
    }


@app.post('/upload')
async def upload(file:UploadFile = File(...), currentUser: str = Depends(get_current_user)):

    raw_bytes = await file.read()
    if file.filename.lower().endswith('.txt'):
        text = raw_bytes.decode('utf-8')
    elif file.filename.lower().endswith('.pdf'):
        reader = PdfReader(BytesIO(raw_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise HTTPException(status_code=404, detail="This file format is not supported.")

    ingest_text(text,currentUser,file.filename)
    return {
        "message" : f"{file.filename} uploaded successfully."
    }


@app.get('/history')
def _getHistory(thread_id:str = Depends(get_current_user)) -> dict:
    return {"history":getHistory(thread_id=thread_id)}