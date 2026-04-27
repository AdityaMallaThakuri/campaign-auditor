from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from db.database import init_db
from routes.campaigns import router as campaigns_router
from routes.audit import router as audit_router
from routes.replies import router as replies_router
from routes.optimize import router as optimize_router
from routes.config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Smartlead Audit API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router)
app.include_router(audit_router)
app.include_router(replies_router)
app.include_router(optimize_router)
app.include_router(config_router)


@app.get("/health")
def health():
    return {"status": "ok"}
