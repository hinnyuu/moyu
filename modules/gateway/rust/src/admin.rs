use bytes::Bytes;
use http_body_util::{combinators::BoxBody, BodyExt, Full};
use hyper::body::Incoming;
use hyper::header::{AUTHORIZATION, CONTENT_TYPE};
use hyper::{Request, Response, StatusCode};
use hyper_util::rt::{TokioExecutor, TokioIo};
use serde_json::json;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use subtle::ConstantTimeEq;
use tokio::net::TcpListener;

use crate::certs::CertStore;
use crate::proxy::{BoxError, ProxyBody};

pub struct AdminState {
    pub store: Arc<CertStore>,
    pub token_file: PathBuf,
    pub reloads: Arc<AtomicU64>,
}

pub async fn serve(listener: TcpListener, state: Arc<AdminState>) -> std::io::Result<()> {
    loop {
        let (stream, _peer) = listener.accept().await?;
        let state = state.clone();
        tokio::spawn(async move {
            let io = TokioIo::new(stream);
            let service = hyper::service::service_fn(move |request| handle(request, state.clone()));
            let builder = hyper_util::server::conn::auto::Builder::new(TokioExecutor::new());
            if let Err(error) = builder.serve_connection(io, service).await {
                eprintln!("moyu-gateway: admin connection error: {error}");
            }
        });
    }
}

async fn handle(
    request: Request<Incoming>,
    state: Arc<AdminState>,
) -> Result<Response<ProxyBody>, hyper::Error> {
    if !authorized(&request, &state.token_file) {
        return Ok(json_response(
            StatusCode::UNAUTHORIZED,
            json!({"code": "unauthorized", "message": "缺少或错误的 Bearer token"}),
        ));
    }
    match (request.method().as_str(), request.uri().path()) {
        ("GET", "/status") | ("GET", "/admin/cert/status") => Ok(json_response(
            StatusCode::OK,
            json!({
                "status": "ok",
                "cert_loaded_at": state.store.loaded_at(),
                "cert_sha256": state.store.cert_sha256(),
                "reloads": state.reloads.load(Ordering::Relaxed),
            }),
        )),
        ("POST", "/reload") | ("POST", "/admin/cert/reload") => match state.store.reload() {
            Ok(()) => {
                state.reloads.fetch_add(1, Ordering::Relaxed);
                Ok(json_response(
                    StatusCode::OK,
                    json!({
                        "status": "reloaded",
                        "cert_loaded_at": state.store.loaded_at(),
                        "cert_sha256": state.store.cert_sha256(),
                    }),
                ))
            }
            Err(error) => Ok(json_response(
                StatusCode::INTERNAL_SERVER_ERROR,
                json!({"code": "reload_failed", "message": error}),
            )),
        },
        ("GET", "/healthz") => Ok(json_response(StatusCode::OK, json!({"status": "ok"}))),
        _ => Ok(json_response(
            StatusCode::NOT_FOUND,
            json!({"code": "not_found", "message": "未知管理路径"}),
        )),
    }
}

fn authorized(request: &Request<Incoming>, token_file: &PathBuf) -> bool {
    let expected = match std::fs::read_to_string(token_file) {
        Ok(text) => text.trim().to_string(),
        Err(_) => return false,
    };
    if expected.is_empty() {
        return false;
    }
    let provided = request
        .headers()
        .get(AUTHORIZATION)
        .and_then(|value| value.to_str().ok())
        .unwrap_or("");
    let provided = match provided.strip_prefix("Bearer ") {
        Some(value) => value,
        None => return false,
    };
    provided.as_bytes().ct_eq(expected.as_bytes()).unwrap_u8() == 1
}

fn json_response(status: StatusCode, value: serde_json::Value) -> Response<ProxyBody> {
    let body: BoxBody<Bytes, BoxError> = Full::new(Bytes::from(value.to_string()))
        .map_err(|never| match never {})
        .boxed();
    Response::builder()
        .status(status)
        .header(CONTENT_TYPE, "application/json; charset=utf-8")
        .body(body)
        .unwrap_or_else(|_| {
            Response::new(
                Full::new(Bytes::new())
                    .map_err(|never| match never {})
                    .boxed(),
            )
        })
}
