from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BusinessIntelligence.AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://main.d3s8curp1ny75.amplifyapp.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
