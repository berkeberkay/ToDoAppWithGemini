from typing import Annotated

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.requests import Request
from database import SessionLocal
from models import User
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi.templating import Jinja2Templates
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "32dfsfsdf147aeuruıaısfkjhasafss23958392skfnksateıweavnn"
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db    # kullanıldığı fonk generator func. denir. returndan farkı birden fazla seq döndürebilir.
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]



bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    username: str
    password: str
    email: str
    first_name: str
    last_name : str
    role : str
    is_active : bool


class Token(BaseModel):
    access_token: str
    token_type: str



def create_access_token(username : str, user_id : int, role : str, exp_delta : timedelta):
    payload = {"sub": username, "id": user_id, "role": role}  # işime yarayacağını düşündüğüm parametreleri kafama göre aldım.
    expire = datetime.now(timezone.utc) + exp_delta
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)




def authenticate_user(db, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    if not bcrypt.verify(password, user.hashed_password):
        return False
    return user

#gidip dependency olarak eklenecek
#decode eder.
async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):   #Bizim kullanıcılarımızdan mı diye kontrol ediyorum ki hacker atmış olabilir vs vs.
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        user_role: str = payload.get("role")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return {"username": username, "id": user_id, "role": user_role}
    except JWTError:
        raise credentials_exception


@router.get("/login-page")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register-page")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/", status_code=201)
async def create_user(db : db_dependency, create_user_request: CreateUserRequest):
    user = User(
        username=create_user_request.username,
        email=create_user_request.email,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=bcrypt.hash(create_user_request.password),
    )

    db.add(user)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(form:Annotated[OAuth2PasswordRequestForm,Depends()], db: db_dependency):
    user = authenticate_user(db,form.username,form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user.username, user.id , user.role, timedelta(minutes=30))
    return {"access_token": token, "token_type": "bearer"} #bearer yollayan kişi gerçek kullanıcı mı kontrolü yapar.