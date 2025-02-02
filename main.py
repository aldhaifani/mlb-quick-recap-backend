# main.py
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Sample FastAPI App")

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI on Cloud Run!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
