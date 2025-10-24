from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from api.db.database import get_db  
from api.v1.models.user import User 
from api.v1.schemas.UserRegister import UserCreate, UserSignin
from api.utils.authentication import hash_password, verify_password, create_access_token
from jose import jwt
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os
blacklisted_tokens = set()


load_dotenv(".env")
ALGORITHM = os.getenv("ALGORITHM")
SECRET_KEY = os.getenv("SECRET")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

auth = APIRouter(prefix="/auth", tags=["Authentication"])

# User Registration
@auth.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_pwd = hash_password(user_data.password)

    # Create new user
    new_user = User(
        first_name=user_data.firstname,
        last_name=user_data.lastname,
        username=user_data.username,
        email=user_data.email,
        password=hashed_pwd
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}

# User Login
@auth.post("/login")
def login(user_data: UserSignin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate JWT
    access_token = create_access_token(data={"sub": user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}

# Retrieve Logged-in User Profile
@auth.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user


@auth.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    blacklisted_tokens.add(token)
    return {"message": "Logged out successfully"}
