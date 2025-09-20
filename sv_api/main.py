from fastapi import FastAPI
from .routers import health, bible, compose, evaluate

app = FastAPI(title="SV Composer API", version="0.1.0")
app.include_router(health.router)
app.include_router(bible.router)
app.include_router(compose.router)
app.include_router(evaluate.router)
