"""FastAPI application factory for the moyu HTTP API.

The app only orchestrates: config, storage, uploads, preview and job records.
It never runs the pack pipeline; workers claim jobs from the same storage.
"""

import asyncio
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from moyu_config import ConfigError, ConfigProvider
from moyu_preview import PreviewError, PreviewProvider
from moyu_storage import AssetStore, JobStore, StorageError
from moyu_uploads import UploadError, UploadSessionStore

from .auth import AuthError, AuthManager

ERROR_STATUS = {
    "auth_required": 401,
    "session_invalid": 401,
    "session_expired": 401,
    "bootstrap_invalid": 401,
    "password_mismatch": 401,
    "csrf_invalid": 403,
    "not_configured": 409,
    "already_configured": 409,
    "revision_conflict": 409,
    "schema_invalid": 400,
    "invalid_request": 400,
    "invalid_size": 400,
    "invalid_offset": 400,
    "offset_mismatch": 409,
    "chunk_too_large": 413,
    "upload_too_large": 413,
    "quota_exceeded": 507,
    "asset_not_found": 404,
    "unknown_config": 404,
    "job_not_found": 404,
    "session_not_found": 404,
    "profile_unknown": 404,
    "preview_unsupported": 415,
    "upload_incomplete": 409,
    "upload_closed": 409,
    "session_closed": 409,
}


def _status_for(code, default=400):
    return ERROR_STATUS.get(code, default)


def _error_body(code, message, details=None, module=""):
    return {
        "code": code,
        "message": message,
        "details": details or [],
        "module": module,
    }


def _job_dict(job):
    return {
        "id": job.id,
        "status": job.status,
        "request": job.request,
        "progress": job.progress,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _asset_dict(asset):
    return {
        "id": asset.id,
        "original_name": asset.original_name,
        "size": asset.size,
        "sha256": asset.sha256,
        "media_type": asset.media_type,
        "created_at": asset.created_at,
    }


def create_app(storage, config_provider, auth):
    effective = config_provider.load()
    api_config = effective.modules["api"]
    uploads_config = effective.modules["uploads"]
    preview_config = effective.modules["preview"]

    assets = AssetStore(storage)
    jobs = JobStore(storage)
    uploads = UploadSessionStore(
        storage,
        max_upload_bytes=uploads_config["maxUploadBytes"],
        session_ttl_seconds=uploads_config.get("sessionTtlSeconds", 86400),
    )
    previews = PreviewProvider(
        storage,
        cache_dir=preview_config.get("cacheDir"),
        profiles=preview_config.get("profiles"),
        concurrency=preview_config.get("concurrency", 2),
        max_memory_bytes=preview_config.get("maxMemoryBytes", 256 * 1024 * 1024),
        timeout_seconds=preview_config.get("timeoutSeconds", 60),
    )
    max_json_body = int(api_config.get("maxJsonBodyBytes", 1048576))
    tus_base_path = str(uploads_config.get("tusBasePath", "/files")).rstrip("/")

    app = FastAPI(title="moyu API", version="0.0.1-draft")
    app.state.storage = storage
    app.state.config = config_provider
    app.state.auth = auth
    app.state.assets = assets
    app.state.jobs = jobs
    app.state.uploads = uploads
    app.state.previews = previews

    def current_session(request: Request):
        token = request.cookies.get(auth.cookie_name)
        if not token:
            raise _http(401, "auth_required", "需要登录")
        try:
            return auth.verify_session(token)
        except AuthError as exc:
            raise _http(_status_for(exc.code, 401), exc.code, exc.message, exc.details)

    def require_csrf(request: Request, session):
        try:
            auth.verify_csrf(session, request.headers.get("X-CSRF-Token"))
        except AuthError as exc:
            raise _http(403, exc.code, exc.message, exc.details)

    def _http(status, code, message, details=None):
        return HTTPException(
            status_code=status,
            detail=_error_body(code, message, details, "api"),
        )

    @app.exception_handler(HTTPException)
    async def http_error(_request, exc):
        detail = exc.detail
        if not isinstance(detail, dict):
            detail = _error_body("http_error", str(detail), [], "api")
        return JSONResponse(status_code=exc.status_code, content=detail)

    def register(exc_type, module):
        async def handler(_request, exc):
            return JSONResponse(
                status_code=_status_for(getattr(exc, "code", ""), 400),
                content=_error_body(
                    getattr(exc, "code", "error"),
                    getattr(exc, "message", str(exc)),
                    getattr(exc, "details", []),
                    module,
                ),
            )

        app.add_exception_handler(exc_type, handler)

    for exc_type, module in (
        (ConfigError, "config"),
        (StorageError, "storage"),
        (UploadError, "uploads"),
        (PreviewError, "preview"),
        (AuthError, "api"),
    ):
        register(exc_type, module)

    @app.middleware("http")
    async def limit_json_body(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH") and request.url.path.startswith(
            "/api/v1/"
        ):
            length = request.headers.get("content-length")
            if length and int(length) > max_json_body:
                return JSONResponse(
                    status_code=413,
                    content=_error_body("request_too_large", "请求体过大", [], "api"),
                )
        return await call_next(request)

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "configured": auth.is_configured()}

    @app.post("/api/v1/auth/session", status_code=204)
    async def login(request: Request, response: Response):
        body = await _json_body(request)
        password = body.get("password")
        if not auth.is_configured():
            session = auth.setup(body.get("bootstrap_token"), password)
        else:
            session = auth.login(password)
        auth.set_cookies(response, session)

    @app.get("/api/v1/auth/session")
    async def session_info(session=Depends(current_session)):
        return session.to_dict()

    @app.delete("/api/v1/auth/session", status_code=204)
    async def logout(
        request: Request,
        response: Response,
        session=Depends(current_session),
    ):
        require_csrf(request, session)
        auth.clear_cookies(response)

    @app.get("/api/v1/config")
    async def read_config(session=Depends(current_session)):
        return config_provider.load().to_dict()

    @app.get("/api/v1/config/{module}")
    async def read_module(module: str, session=Depends(current_session)):
        current = config_provider.load()
        if module not in current.revisions:
            raise _http(404, "unknown_config", f"未知配置: {module}")
        return {
            "config": current.get(module),
            "revision": current.revisions[module],
        }

    @app.put("/api/v1/config/{module}")
    async def write_module(
        module: str,
        request: Request,
        session=Depends(current_session),
    ):
        require_csrf(request, session)
        body = await _json_body(request)
        patch = body.get("patch")
        if not isinstance(patch, dict):
            raise _http(400, "invalid_patch", "patch 必须是映射")
        result = config_provider.write(module, patch, body.get("revision"))
        return {"config": result.data, "revision": result.revision}

    @app.post("/api/v1/uploads", status_code=201)
    async def create_upload(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        body = await _json_body(request)
        upload_session = uploads.create_session(body)
        return {
            "id": upload_session.id,
            "offset": upload_session.offset,
            "size": upload_session.size,
            "chunk_size": uploads_config.get("chunkSizeBytes"),
            "tus_url": f"{tus_base_path}/{upload_session.id}",
        }

    @app.get("/api/v1/uploads/{upload_id}")
    async def get_upload(upload_id: str, session=Depends(current_session)):
        upload_session = uploads.get_session(upload_id)
        return {
            "id": upload_session.id,
            "filename": upload_session.filename,
            "size": upload_session.size,
            "offset": upload_session.offset,
            "status": upload_session.status,
        }

    @app.post("/api/v1/uploads/{upload_id}/finish", status_code=201)
    async def finish_upload(
        upload_id: str, request: Request, session=Depends(current_session)
    ):
        require_csrf(request, session)
        return _asset_dict(uploads.finish_session(upload_id))

    @app.post("/api/v1/jobs", status_code=202)
    async def create_job(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        body = await _json_body(request)
        job = jobs.create_job(body)
        job = jobs.update_status(job.id, "queued")
        jobs.append_event(job.id, {"phase": "created"})
        return _job_dict(job)

    @app.get("/api/v1/jobs")
    async def list_jobs(
        status: str = None, limit: int = 100, session=Depends(current_session)
    ):
        return [_job_dict(job) for job in jobs.list_jobs(status=status, limit=limit)]

    @app.get("/api/v1/jobs/{job_id}")
    async def get_job(job_id: str, session=Depends(current_session)):
        return _job_dict(jobs.get_job(job_id))

    @app.delete("/api/v1/jobs/{job_id}", status_code=202)
    async def cancel_job(
        job_id: str, request: Request, session=Depends(current_session)
    ):
        require_csrf(request, session)
        return _job_dict(jobs.cancel_job(job_id))

    @app.get("/api/v1/jobs/{job_id}/events")
    async def job_events(job_id: str, session=Depends(current_session)):
        jobs.get_job(job_id)

        async def stream():
            seen = 0
            for _ in range(120):
                events = jobs.events(job_id)
                for event in events[seen:]:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    seen += 1
                current = jobs.get_job(job_id)
                if current.status in ("succeeded", "failed", "canceled"):
                    yield (
                        "event: end\n"
                        f"data: {json.dumps({'status': current.status})}\n\n"
                    )
                    return
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/v1/assets/{asset_id}/download")
    async def download_asset(asset_id: str, session=Depends(current_session)):
        asset = assets.get_asset(asset_id)
        path = assets.path_for(asset.id)
        return FileResponse(path, filename=asset.original_name)

    @app.get("/api/v1/previews/{asset_id}/{profile}")
    async def get_preview(asset_id: str, profile: str, session=Depends(current_session)):
        artifact = previews.generate(asset_id, profile)
        media = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }.get(artifact.format, "application/octet-stream")
        return FileResponse(artifact.path, media_type=media)

    @app.post("/api/v1/admin/gateway/cert/reload")
    async def gateway_reload(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        raise _http(501, "gateway_admin_unavailable", "网关管理接口尚未接入")

    @app.get("/api/v1/admin/gateway/cert/status")
    async def gateway_cert_status(session=Depends(current_session)):
        raise _http(501, "gateway_admin_unavailable", "网关管理接口尚未接入")

    @app.post("/api/v1/admin/gateway/token/rotate", status_code=201)
    async def gateway_token_rotate(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        raise _http(501, "gateway_admin_unavailable", "网关管理接口尚未接入")

    @app.get("/api/v1/admin/gateway/token")
    async def gateway_token_status(session=Depends(current_session)):
        raise _http(501, "gateway_admin_unavailable", "网关管理接口尚未接入")

    @app.delete("/api/v1/admin/gateway/token")
    async def gateway_token_revoke(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        raise _http(501, "gateway_admin_unavailable", "网关管理接口尚未接入")

    web_root = api_config.get("webRoot")
    if web_root and Path(web_root).is_dir():
        app.mount("/", StaticFiles(directory=web_root, html=True), name="web")

    return app


async def _json_body(request: Request):
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=_error_body("invalid_json", "请求体不是合法 JSON", [], "api"),
        ) from exc
    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400,
            detail=_error_body("invalid_json", "请求体必须是对象", [], "api"),
        )
    return body