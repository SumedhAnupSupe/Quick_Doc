import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("apaar_nexus")


def create_app() -> FastAPI:
    s = get_settings()
    s.assert_safe()
    app = FastAPI(
        title=f"{s.app_name} API",
        description="AICTE Student Data Management & Verification Platform (prototype). "
        "Uses synthetic data; NOT connected to AICTE, APAAR, Aadhaar, DigiLocker or any "
        "government verification service.",
        version="0.1.0",
        docs_url=None if s.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if s.is_production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_origin_list, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def guards(request: Request, call_next):
        cid = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.correlation_id = cid
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > s.max_request_bytes:
            return JSONResponse({"code": "payload_too_large", "detail": "Request body too large"}, 413)
        response = await call_next(request)
        response.headers["X-Request-ID"] = cid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse({"code": exc.code, "detail": exc.message}, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errs = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        return JSONResponse({"code": "validation_failed", "detail": "Invalid request", "errors": errs}, 422)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("Unhandled error on %s", request.url.path)  # stack trace stays server-side
        return JSONResponse({"code": "internal_error", "detail": "Internal server error"}, 500)

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok", "service": s.app_name}

    app.include_router(auth_router, prefix=s.api_prefix)
    app.include_router(users_router, prefix=s.api_prefix)
    return app


app = create_app()
