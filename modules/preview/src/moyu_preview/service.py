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
    "hls": "application/vnd.apple.mpegurl",
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
        status = 404 if exc.code in (
            "asset_not_found",
            "profile_unknown",
            "preview_not_found",
        ) else 415
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

    @app.get("/preview/{asset_id}/{profile}/{filename}")
    async def preview_file(asset_id: str, profile: str, filename: str):
        if filename in (".", "..") or "/" in filename or "\\" in filename:
            raise PreviewError("preview_not_found", "非法预览文件")
        playlist = provider.preview_path(asset_id, profile)
        base = playlist.parent.resolve()
        target = (base / filename).resolve()
        if target.parent != base or not target.is_file():
            raise PreviewError("preview_not_found", "预览文件不存在")
        if target.suffix == ".m3u8":
            media = MEDIA_TYPES["hls"]
        elif target.suffix == ".ts":
            media = "video/mp2t"
        else:
            media = "application/octet-stream"
        return FileResponse(target, media_type=media, filename=filename)

    @app.post("/purge/{asset_id}", status_code=204)
    async def purge(asset_id: str):
        provider.delete(asset_id)

    return app
