use bytes::Bytes;
use http_body_util::{combinators::BoxBody, BodyExt, Full};
use hyper::body::Incoming;
use hyper::header::{HeaderValue, HOST};
use hyper::{Request, Response, StatusCode, Uri};
use hyper_util::client::legacy::{connect::HttpConnector, Client};
use hyper_util::rt::{TokioExecutor, TokioIo};
use std::convert::Infallible;
use std::sync::Arc;
use tokio::net::TcpListener;
use tokio_rustls::TlsAcceptor;

pub type BoxError = Box<dyn std::error::Error + Send + Sync>;
pub type ProxyBody = BoxBody<Bytes, BoxError>;

const HOP_HEADERS: [&str; 9] = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
];

pub fn build_client() -> Client<HttpConnector, Incoming> {
    Client::builder(TokioExecutor::new()).build_http::<Incoming>()
}

pub fn error_response(status: StatusCode, message: impl Into<String>) -> Response<ProxyBody> {
    let body: ProxyBody = Full::new(Bytes::from(message.into()))
        .map_err(|never| match never {})
        .boxed();
    Response::builder()
        .status(status)
        .header("content-type", "text/plain; charset=utf-8")
        .body(body)
        .unwrap_or_else(|_| {
            Response::new(
                Full::new(Bytes::new())
                    .map_err(|never| match never {})
                    .boxed(),
            )
        })
}

pub async fn serve(
    listener: TcpListener,
    acceptor: TlsAcceptor,
    client: Client<HttpConnector, Incoming>,
    upstream: Uri,
) -> std::io::Result<()> {
    loop {
        let (stream, _peer) = listener.accept().await?;
        let acceptor = acceptor.clone();
        let client = client.clone();
        let upstream = upstream.clone();
        tokio::spawn(async move {
            let tls = match acceptor.accept(stream).await {
                Ok(tls) => tls,
                Err(error) => {
                    eprintln!("moyu-gateway: TLS handshake failed: {error}");
                    return;
                }
            };
            let io = TokioIo::new(tls);
            let service = hyper::service::service_fn(move |request| {
                forward(request, client.clone(), upstream.clone())
            });
            let builder = hyper_util::server::conn::auto::Builder::new(TokioExecutor::new());
            if let Err(error) = builder.serve_connection_with_upgrades(io, service).await {
                eprintln!("moyu-gateway: connection error: {error}");
            }
        });
    }
}

async fn forward(
    mut request: Request<Incoming>,
    client: Client<HttpConnector, Incoming>,
    upstream: Uri,
) -> Result<Response<ProxyBody>, Infallible> {
    let path = request
        .uri()
        .path_and_query()
        .map(|value| value.as_str())
        .unwrap_or("/")
        .to_string();
    let authority = match upstream.authority() {
        Some(authority) => authority.as_str().to_string(),
        None => {
            return Ok(error_response(
                StatusCode::INTERNAL_SERVER_ERROR,
                "upstream 缺少 authority",
            ))
        }
    };
    let scheme = upstream.scheme_str().unwrap_or("http");
    let uri = match format!("{scheme}://{authority}{path}").parse::<Uri>() {
        Ok(uri) => uri,
        Err(error) => {
            return Ok(error_response(
                StatusCode::BAD_REQUEST,
                format!("请求路径非法: {error}"),
            ))
        }
    };
    *request.uri_mut() = uri;
    *request.version_mut() = hyper::Version::HTTP_11;
    let headers = request.headers_mut();
    for name in HOP_HEADERS {
        headers.remove(name);
    }
    if let Ok(value) = HeaderValue::from_str(&authority) {
        headers.insert(HOST, value);
    }

    match client.request(request).await {
        Ok(response) => {
            let (mut parts, body) = response.into_parts();
            for name in HOP_HEADERS {
                parts.headers.remove(name);
            }
            let body = body
                .map_err(|error| -> BoxError { Box::new(error) })
                .boxed();
            Ok(Response::from_parts(parts, body))
        }
        Err(error) => Ok(error_response(
            StatusCode::BAD_GATEWAY,
            format!("上游请求失败: {error}"),
        )),
    }
}

pub fn acceptor(store: Arc<crate::certs::CertStore>) -> TlsAcceptor {
    TlsAcceptor::from(crate::certs::server_config(store))
}
