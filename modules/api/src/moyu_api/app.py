"""FastAPI application factory for the moyu HTTP API.

The app only orchestrates: config, storage, uploads, preview and job records.
It never runs the pack pipeline; workers claim jobs from the same storage.
"""

import asyncio
import base64
import hmac
import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from moyu_config import ConfigError, ConfigProvider
from moyu_preview import PreviewError, PreviewProvider
from moyu_storage import AssetStore, JobStore, StorageError
from moyu_uploads import UploadError, UploadSessionStore

from .auth import AuthError, AuthManager
from .gateway_admin import GatewayAdminClient, GatewayAdminError
from .preview_client import PreviewClient, PreviewClientError
from .rate_limit import LoginRateLimiter

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
    "gateway_disabled": 409,
    "gateway_token_missing": 503,
    "gateway_unreachable": 502,
    "gateway_admin_error": 502,
    "reload_failed": 502,
    "rate_limited": 429,
    "forbidden": 403,
    "user_exists": 409,
    "user_not_found": 404,
    "last_admin": 409,
    "username_invalid": 400,
    "role_invalid": 400,
    "preview_unreachable": 502,
    "preview_service_error": 502,
    "preview_failed": 502,
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


def create_app(
    storage,
    config_provider,
    auth,
    gateway_admin=None,
    preview_client=None,
    tusd_hook_token=None,
    login_limiter=None,
):
    if login_limiter is None:
        login_limiter = LoginRateLimiter()
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
    if preview_client is None:
        service_url = str(preview_config.get("serviceUrl") or "").strip()
        if service_url:
            preview_client = PreviewClient(
                service_url,
                timeout=preview_config.get("timeoutSeconds", 60),
            )
    if gateway_admin is None:
        gateway_config = effective.modules.get("gateway", {})
        reload_api = gateway_config.get("reload", {}).get("api", {})
        if gateway_config.get("enabled") and reload_api.get("enabled"):
            gateway_admin = GatewayAdminClient(
                reload_api.get("tokenFile", ""),
                reload_api.get("listen", ""),
                state_file=Path(config_provider.config_dir)
                / "state"
                / "gateway_token.db",
            )
    if tusd_hook_token is None:
        tusd_hook_token = os.environ.get("MOYU_TUSD_HOOK_TOKEN", "")
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
    app.state.gateway_admin = gateway_admin
    app.state.preview_client = preview_client
    app.state.tusd_hook_token = tusd_hook_token
    app.state.login_limiter = login_limiter

    def current_session(request: Request):
        token = request.cookies.get(auth.cookie_name)
        if not token:
            raise _http(401, "auth_required", "需要登录")
        try:
            return auth.verify_session(token)
        except AuthError as exc:
            raise _http(_status_for(exc.code, 401), exc.code, exc.message, exc.details)

    def require_gateway():
        if gateway_admin is None:
            raise _http(409, "gateway_disabled", "gateway 未启用或管理 API 未配置")
        return gateway_admin

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
        (GatewayAdminError, "gateway"),
        (PreviewClientError, "preview"),
    ):
        register(exc_type, module)

    @app.middleware("http")
    async def limit_json_body(request: Request, call_next):
        is_json_write = (
            request.method in ("POST", "PUT", "PATCH")
            and request.url.path.startswith("/api/v1/")
            and not (
                request.method == "PATCH"
                and request.url.path.startswith("/api/v1/uploads/")
            )
        )
        if is_json_write:
            length = request.headers.get("content-length")
            try:
                too_large = bool(length) and int(length) > max_json_body
            except ValueError:
                too_large = False
            if too_large:
                return JSONResponse(
                    status_code=413,
                    content=_error_body("request_too_large", "请求体过大", [], "api"),
                )
        return await call_next(request)

    @app.middleware("http")
    async def cross_origin_isolation(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Embedder-Policy", "require-corp")
        return response

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "configured": auth.is_configured()}

    def login_key(request: Request):
        return getattr(request.client, "host", "unknown") or "unknown"

    @app.post("/api/v1/auth/session", status_code=204)
    async def login(request: Request, response: Response):
        key = login_key(request)
        if not login_limiter.allow(key):
            raise _http(429, "rate_limited", "登录尝试过多，请稍后再试")
        body = await _json_body(request)
        password = body.get("password")
        try:
            if not auth.is_configured():
                session = auth.setup(
                    body.get("bootstrap_token"), password, body.get("username", "admin")
                )
            else:
                session = auth.login(password, body.get("username", "admin"))
        except AuthError:
            login_limiter.failure(key)
            raise
        login_limiter.success(key)
        auth.set_cookies(response, session)

    @app.post("/api/v1/auth/password/reset", status_code=204)
    async def reset_password(request: Request, response: Response):
        key = login_key(request)
        if not login_limiter.allow(key):
            raise _http(429, "rate_limited", "登录尝试过多，请稍后再试")
        body = await _json_body(request)
        try:
            session = auth.reset_password(
                body.get("bootstrap_token"),
                body.get("password"),
                body.get("username", "admin"),
            )
        except AuthError:
            login_limiter.failure(key)
            raise
        login_limiter.success(key)
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

    def require_admin(session):
        if session.role != "admin":
            raise _http(403, "forbidden", "需要管理员权限")

    @app.get("/api/v1/users")
    async def list_users(session=Depends(current_session)):
        require_admin(session)
        return auth.list_users()

    @app.post("/api/v1/users", status_code=201)
    async def create_user(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        require_admin(session)
        body = await _json_body(request)
        return auth.create_user(
            session.username,
            body.get("username"),
            body.get("password"),
            body.get("role", "operator"),
        )

    @app.delete("/api/v1/users/{username}", status_code=204)
    async def delete_user(
        username: str, request: Request, session=Depends(current_session)
    ):
        require_csrf(request, session)
        require_admin(session)
        auth.delete_user(session.username, username)

    @app.post("/api/v1/users/{username}/password", status_code=204)
    async def change_password(
        username: str, request: Request, session=Depends(current_session)
    ):
        require_csrf(request, session)
        body = await _json_body(request)
        auth.change_password(
            session.username,
            username,
            body.get("password"),
            body.get("old_password"),
        )

    @app.get("/api/v1/config")
    async def read_config(session=Depends(current_session)):
        return config_provider.load().to_dict()

    @app.get("/api/v1/config/audit")
    async def config_audit(limit: int = 100, session=Depends(current_session)):
        return config_provider.audit(limit)

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

    def hook_response(status, body):
        return {"HTTPResponse": {"StatusCode": status, "Body": body}}

    def decode_meta(value):
        if not value:
            return ""
        try:
            return base64.b64decode(str(value)).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return str(value)

    @app.post("/api/v1/internal/tusd/hook")
    async def tusd_hook(request: Request):
        token = request.query_params.get("token") or request.headers.get(
            "X-Moyu-Hook-Token", ""
        )
        if not tusd_hook_token or not hmac.compare_digest(token, tusd_hook_token):
            raise _http(403, "hook_unauthorized", "hook token 不正确")
        payload = await _json_body(request)
        hook_type = payload.get("Type")
        upload = payload.get("Event", {}).get("Upload", {})
        metadata = upload.get("MetaData") or {}
        filename = decode_meta(metadata.get("filename")) or "upload.bin"
        media_type = (
            decode_meta(metadata.get("filetype")) or "application/octet-stream"
        )
        try:
            size = int(upload.get("Size") or 0)
        except (TypeError, ValueError):
            size = 0
        if hook_type == "pre-create":
            if size <= 0:
                return hook_response(400, "缺少上传大小")
            if size > uploads.max_upload_bytes:
                return hook_response(413, "超过上传上限")
            try:
                storage.check_quota(size)
            except StorageError:
                return hook_response(507, "存储配额不足")
            return hook_response(200, "ok")
        if hook_type == "post-finish":
            path = (upload.get("Storage") or {}).get("Path")
            if not path:
                return hook_response(500, "缺少存储路径")
            try:
                asset = assets.register_asset(
                    path, original_name=filename, media_type=media_type
                )
            except StorageError as exc:
                return hook_response(500, exc.message)
            return hook_response(200, asset.id)
        return hook_response(200, "ignored")

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

    @app.patch("/api/v1/uploads/{upload_id}", status_code=204)
    async def append_upload(
        upload_id: str, request: Request, session=Depends(current_session)
    ):
        require_csrf(request, session)
        header = request.headers.get("upload-offset")
        try:
            offset = int(header)
        except (TypeError, ValueError) as exc:
            raise _http(400, "invalid_offset", "缺少或非法的 Upload-Offset") from exc
        data = await request.body()
        new_offset = uploads.append_chunk(upload_id, offset, data)
        return Response(status_code=204, headers={"Upload-Offset": str(new_offset)})

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

    @app.get("/api/v1/jobs/{job_id}/download")
    async def download_job(job_id: str, session=Depends(current_session)):
        job = jobs.get_job(job_id)
        if job.status != "succeeded":
            raise _http(409, "job_not_ready", "任务尚未成功完成")
        output_name = str(job.request.get("output_name") or "delivery.zip")
        path = storage.output_path(job.id, output_name)
        if not path.exists():
            raise _http(404, "output_not_found", "任务输出不存在")
        return FileResponse(path, filename=output_name, media_type="application/zip")

    @app.get("/api/v1/assets/{asset_id}/download")
    async def download_asset(asset_id: str, session=Depends(current_session)):
        asset = assets.get_asset(asset_id)
        path = assets.path_for(asset.id)
        return FileResponse(path, filename=asset.original_name)

    @app.get("/api/v1/previews/{asset_id}/{profile}")
    async def get_preview(asset_id: str, profile: str, session=Depends(current_session)):
        if preview_client is not None:
            body, media = preview_client.generate(asset_id, profile)
            return Response(content=body, media_type=media)
        artifact = previews.generate(asset_id, profile)
        media = {
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "mp4": "video/mp4",
        }.get(artifact.format, "application/octet-stream")
        return FileResponse(artifact.path, media_type=media)

    @app.get("/api/v1/previews/{asset_id}/{profile}/{filename}")
    async def get_preview_file(
        asset_id: str,
        profile: str,
        filename: str,
        session=Depends(current_session),
    ):
        if filename in (".", "..") or "/" in filename or "\\" in filename:
            raise _http(404, "preview_not_found", "非法预览文件")
        if preview_client is not None:
            body, media = preview_client.generate_file(asset_id, profile, filename)
            return Response(content=body, media_type=media)
        artifact = previews.generate(asset_id, profile)
        base = Path(artifact.path).parent.resolve()
        target = (base / filename).resolve()
        if target.parent != base or not target.is_file():
            raise _http(404, "preview_not_found", "预览文件不存在")
        if target.suffix == ".m3u8":
            media = "application/vnd.apple.mpegurl"
        elif target.suffix == ".ts":
            media = "video/mp2t"
        else:
            media = "application/octet-stream"
        return FileResponse(target, media_type=media, filename=filename)

    @app.post("/api/v1/admin/gateway/cert/reload")
    async def gateway_reload(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        return require_gateway().reload_cert()

    @app.get("/api/v1/admin/gateway/cert/status")
    async def gateway_cert_status(session=Depends(current_session)):
        return require_gateway().cert_status()

    @app.post("/api/v1/admin/gateway/token/rotate", status_code=201)
    async def gateway_token_rotate(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        token = require_gateway().rotate_token()
        return {"token": token, "shown_once": True}

    @app.get("/api/v1/admin/gateway/token")
    async def gateway_token_status(session=Depends(current_session)):
        return require_gateway().token_metadata()

    @app.get("/api/v1/admin/gateway/token/audit")
    async def gateway_token_audit(
        limit: int = 100, session=Depends(current_session)
    ):
        return require_gateway().audit(limit)

    @app.delete("/api/v1/admin/gateway/token", status_code=204)
    async def gateway_token_revoke(request: Request, session=Depends(current_session)):
        require_csrf(request, session)
        require_gateway().revoke_token()
        return Response(status_code=204)

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