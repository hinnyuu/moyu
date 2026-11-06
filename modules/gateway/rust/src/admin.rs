use bytes::Bytes;
use http_body_util::{combinators::BoxBody, BodyExt, Full};
use hyper::body::Incoming;
use hyper::header::{AUTHORIZATION, CONTENT_TYPE};
use hyper::{Request, Response, StatusCode};
use hyper_util::rt::{TokioExecutor, TokioIo};
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
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
            r#"{"code":"unauthorized","message":"缺少或错误的 Bearer token"}"#,
        ));
    }
    match (request.method().as_str(), request.uri().path()) {
        ("GET", "/status") => {
            let body = format!(
                r#"{{"status":"ok","cert_loaded_at":"{}","reloads":{}}}"#,
                state.store.loaded_at(),
                state.reloads.load(Ordering::Relaxed)
            );
            Ok(json_response(StatusCode::OK, &body))
        }
        ("POST", "/reload") => match state.store.reload() {
            Ok(()) => {
                state.reloads.fetch_add(1, Ordering::Relaxed);
                let body = format!(
                    r#"{{"status":"reloaded","cert_loaded_at":"{}"}}"#,
                    state.store.loaded_at()
                );
                Ok(json_response(StatusCode::OK, &body))
            }
            Err(error) => Ok(json_response(
                StatusCode::INTERNAL_SERVER_ERROR,
                &format!(r#"{{"code":"reload_failed","message":{}}}"#, escape(&error)),
            )),
        },
        ("GET", "/healthz") => Ok(json_response(StatusCode::OK, r#"{"status":"ok"}"#)),
        _ => Ok(json_response(
            StatusCode::NOT_FOUND,
            r#"{"code":"not_found","message":"未知管理路径"}"#,
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
    let prefix = "Bearer ";
    if !provided.starts_with(prefix) {
        return false;
    }
    provided[prefix.len()..] == expected
}

fn json_response(status: StatusCode, text: &str) -> Response<ProxyBody> {
    let body: BoxBody<Bytes, BoxError> = Full::new(Bytes::from(text.to_string()))
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

fn escape(text: &str) -> String {
    serde_json::to_string(text).unwrap_or_else(|_| "\"error\"".to_string())
}
