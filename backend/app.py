from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.router import router

app = FastAPI(title="Smart CS Agent API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Smart CS Agent Backend is running."}
