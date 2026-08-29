from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from enum import Enum
import uvicorn
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from orchestrator_graph import orchestrator
import duckdb
from middlewares/corsMiddleware import setup_cors

SECRET_KEY = "super-secret-key-for-prototype"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
DB_FILE = "business_intelligence.db"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/login")

app = FastAPI(title="BusinessIntelligence.AI Engine")

setup_cors(app)

def init_db():
    conn = duckdb.connect(DB_FILE)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            userId VARCHAR PRIMARY KEY,
            Encrypted_password VARCHAR NOT NULL,
            persona VARCHAR NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS KPIs (
            date DATE PRIMARY KEY,
            total_revenue DOUBLE,
            conversion_rate DOUBLE,
            aov DOUBLE,
            return_rate DOUBLE,
            total_orders INTEGER,
            total_sessions INTEGER,
            daily_ad_spend DOUBLE,
            cac DOUBLE
        )
    """)
    conn.close()

init_db()

def get_db_connection():
    return duckdb.connect(DB_FILE)

class PersonaType(str, Enum):
    manager = "manager"
    analyst = "analyst"

class UserCreate(BaseModel):
    userId: str
    password: str
    persona: PersonaType

class UserLogin(BaseModel):
    userId: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    persona: PersonaType

class VarianceRequest(BaseModel):
    target_kpi: str
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
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        conn = get_db_connection()
        result = conn.execute("SELECT * FROM Users WHERE userId = ?", [user_id]).fetchone()
        conn.close()
        
        if result is None:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        return {"userId": result[0], "Encrypted_password": result[1], "persona": result[2]}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/signup", status_code=status.HTTP_201_CREATED)
async def signup_endpoint(user: UserCreate):
    conn = get_db_connection()
    existing_user = conn.execute("SELECT userId FROM Users WHERE userId = ?", [user.userId]).fetchone()
    
    if existing_user:
        conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    
    encrypted_password = get_password_hash(user.password)
    conn.execute(
        "INSERT INTO Users (userId, Encrypted_password, persona) VALUES (?, ?, ?)",
        [user.userId, encrypted_password, user.persona.value]
    )
    conn.commit()
    conn.close()
    
    return {"message": "User created"}

@app.post("/api/v1/login", response_model=Token)
async def login_endpoint(user: UserLogin):
    conn = get_db_connection()
    db_user = conn.execute("SELECT * FROM Users WHERE userId = ?", [user.userId]).fetchone()
    conn.close()
    
    if not db_user or not verify_password(user.password, db_user[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.userId, "persona": db_user[2]})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        persona=db_user[2]
    )

@app.post("/api/v1/analyze-variance", response_model=VarianceResponse)
async def analyze_variance_endpoint(request: VarianceRequest, current_user: dict = Depends(get_current_user)):
    try:
        MANAGER_ALLOWED_KPIS = ["total_revenue", "conversion_rate", "aov", "return_rate"]
        
        if current_user["persona"] == PersonaType.manager.value:
            if request.target_kpi not in MANAGER_ALLOWED_KPIS:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Manager persona is not authorized to analyze {request.target_kpi}"
                )
        elif current_user["persona"] != PersonaType.analyst.value:
            raise HTTPException(status_code=403, detail="Unauthorized persona")

        initial_state = {
            "target_kpi": request.target_kpi,
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
