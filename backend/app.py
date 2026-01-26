from fastapi import FastAPI
from backend.router import router

app = FastAPI(title="Smart CS Agent API")

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Smart CS Agent Backend is running."}
