"""Internal preview HTTP service."""

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from moyu_storage import Storage

from . import PreviewError, PreviewProvider, external

MEDIA_TYPES = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "mp4": "video/mp4",
}


def create_preview_app(storage, preview_config, provider=None):
    if provider is None:
        provider = PreviewProvider(
            storage,
            cache_dir=preview_config.get("cacheDir"),
            profiles=preview_config.get("profiles"),
            concurrency=preview_config.get("concurrency", 2),
            max_memory_bytes=preview_config.get("maxMemoryBytes", 256 * 1024 * 1024),
            timeout_seconds=preview_config.get("timeoutSeconds", 60),
        )
    app = FastAPI(title="moyu preview", version="0.0.1-draft")
    app.state.provider = provider

    @app.exception_handler(PreviewError)
    async def preview_error(_request, exc):
        status = 404 if exc.code in ("asset_not_found", "profile_unknown") else 415
        if exc.code in ("preview_timeout", "preview_busy"):
            status = 503
        return JSONResponse(
            status_code=status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "module": "preview",
            },
        )

    @app.get("/healthz")
    async def health():
        return {
            "status": "ok",
            "ffmpeg": external.ffmpeg_available(),
            "ffprobe": external.ffprobe_available(),
            "oiiotool": external.oiiotool_available(),
        }

    @app.get("/probe/{asset_id}")
    async def probe(asset_id: str):
        return provider.probe(asset_id)

    @app.get("/preview/{asset_id}/{profile}")
    async def preview(asset_id: str, profile: str):
        artifact = provider.generate(asset_id, profile)
        return FileResponse(
            artifact.path,
            media_type=MEDIA_TYPES.get(artifact.format, "application/octet-stream"),
            filename=f"preview.{artifact.format}",
        )

    @app.post("/purge/{asset_id}", status_code=204)
    async def purge(asset_id: str):
        provider.delete(asset_id)

    return app
