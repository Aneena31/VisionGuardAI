from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers import claims, dashboard, notifications, providers, scoring, search, system
from api.schemas.common import make_error_response, make_response
from db.database import SessionLocal, init_db
from pipeline import config, ml, stats


load_dotenv()

app = FastAPI(title="VisionGuard AI API", version="0.1.0")

# cors_origins = os.getenv(
#     "CORS_ORIGINS",
#     "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",

# )


app.add_middleware(
    CORSMiddleware,
    # allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_origins=["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid4()}")
    return await call_next(request)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    artifacts_path = Path(os.getenv("ARTIFACTS_PATH", str(config.DEFAULT_ARTIFACTS_PATH)))
    required = ["scaler.pkl", "isolation_forest.pkl", "pca.pkl", "ml_features.json"]
    if all((artifacts_path / name).exists() for name in required):
        app.state.artifacts = ml.load_artifacts(artifacts_path)
    else:
        app.state.artifacts = None

    db = SessionLocal()
    try:
        app.state.population_stats = stats.get_population_stats(db)
    finally:
        db.close()


app.include_router(dashboard.router)
app.include_router(claims.router)
app.include_router(providers.router)
app.include_router(scoring.router)
app.include_router(system.router)
app.include_router(search.router)
app.include_router(notifications.router)


@app.get("/health")
def health(request: Request):
    return make_response({"status": "ok"}, request.state.request_id)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    status_code = exc.status_code
    code = "NOT_FOUND" if status_code == 404 else "VALIDATION_ERROR" if status_code in [400, 422] else "PIPELINE_ERROR"
    if status_code == 409:
        code = "JOB_ALREADY_EXISTS"
    if status_code == 503:
        code = "AI_SERVICE_UNAVAILABLE"
    request_id = getattr(request.state, "request_id", f"req_{uuid4()}")
    return JSONResponse(
        status_code=status_code,
        content=make_error_response(code, str(exc.detail), status_code, request_id),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", f"req_{uuid4()}")
    return JSONResponse(
        status_code=422,
        content=make_error_response("VALIDATION_ERROR", str(exc), 422, request_id),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", f"req_{uuid4()}")
    return JSONResponse(
        status_code=500,
        content=make_error_response("PIPELINE_ERROR", str(exc), 500, request_id),
    )
