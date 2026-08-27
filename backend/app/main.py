from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from enum import Enum
import uvicorn
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.orchestrator_graph import orchestrator

SECRET_KEY = "super-secret-key-for-prototype"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login")

app = FastAPI(title="BusinessIntelligence.AI Engine")

users_db = {}

class PersonaType(str, Enum):
    admin = "admin"
    analyst = "analyst"

class UserCreate(BaseModel):
    username: str
    password: str
    persona: PersonaType

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    persona: PersonaType

class VarianceRequest(BaseModel):
    csv_path: str
    analysis_date: str

class VarianceResponse(BaseModel):
    narrative: str
    evidence_json: str

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users_db.get(username)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/signup", status_code=status.HTTP_201_CREATED)
async def signup_endpoint(user: UserCreate):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="User already exists")
    
    users_db[user.username] = {
        "username": user.username,
        "hashed_password": get_password_hash(user.password),
        "persona": user.persona
    }
    return {"message": "User created"}

@app.post("/api/v1/login", response_model=Token)
async def login_endpoint(user: UserLogin):
    db_user = users_db.get(user.username)
    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.username, "persona": db_user["persona"]})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        persona=db_user["persona"]
    )

@app.post("/api/v1/analyze-variance", response_model=VarianceResponse)
async def analyze_variance_endpoint(request: VarianceRequest, current_user: dict = Depends(get_current_user)):
    try:
        if current_user.get("persona") not in [PersonaType.admin, PersonaType.analyst]:
            raise HTTPException(status_code=403, detail="Not authorized to perform analysis")

        initial_state = {
            "csv_path": request.csv_path,
            "analysis_date": request.analysis_date,
            "evidence_json": "",
            "historical_r2_score": 0.0,
            "narrative": ""
        }
        
        result = orchestrator.invoke(initial_state)
        
        return VarianceResponse(
            narrative=result["narrative"],
            evidence_json=result["evidence_json"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
