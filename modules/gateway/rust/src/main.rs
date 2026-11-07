mod admin;
mod certs;
mod config;
mod proxy;

use config::GatewayConfig;
use hyper::Uri;
use socket2::{Domain, Protocol, Socket, Type};
use std::net::{IpAddr, SocketAddr};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::net::TcpListener;

fn main() {
    if let Err(error) = run() {
        eprintln!("moyu-gateway: {error}");
        std::process::exit(1);
    }
}

#[tokio::main]
async fn run() -> Result<(), String> {
    let path = std::env::var("MOYU_GATEWAY_CONFIG")
        .map_err(|_| "缺少 MOYU_GATEWAY_CONFIG 环境变量".to_string())?;
    let config = GatewayConfig::load(Path::new(&path))?;
    if config.schema_version != 1 {
        return Err(format!(
            "不支持的 gateway schemaVersion: {}",
            config.schema_version
        ));
    }
    if !config.enabled {
        println!("moyu-gateway: disabled");
        return Ok(());
    }

    rustls::crypto::ring::default_provider()
        .install_default()
        .map_err(|_| "无法安装 rustls crypto provider".to_string())?;

    let store = certs::CertStore::load(
        Path::new(&config.cert.cert_file),
        Path::new(&config.cert.key_file),
    )?;
    if config.reload.on_start {
        eprintln!("moyu-gateway: certificate loaded at startup");
    }
    let acceptor = proxy::acceptor(store.clone());
    let upstream: Uri = config
        .upstream
        .url
        .parse()
        .map_err(|error| format!("upstream URL 非法: {error}"))?;
    let client = proxy::build_client();
    let reloads = Arc::new(AtomicU64::new(0));

    if config.reload.api.enabled {
        let address: SocketAddr = config
            .reload
            .api
            .listen
            .parse()
            .map_err(|error| format!("管理 API 地址非法: {error}"))?;
        let listener = TcpListener::bind(address)
            .await
            .map_err(|error| format!("管理 API 监听失败: {error}"))?;
        let state = Arc::new(admin::AdminState {
            store: store.clone(),
            token_file: std::path::PathBuf::from(&config.reload.api.token_file),
            reloads: reloads.clone(),
        });
        tokio::spawn(async move {
            if let Err(error) = admin::serve(listener, state).await {
                eprintln!("moyu-gateway: admin server stopped: {error}");
            }
        });
    }

    if config.reload.watch {
        let cert = std::path::PathBuf::from(&config.cert.cert_file);
        let key = std::path::PathBuf::from(&config.cert.key_file);
        let store = store.clone();
        let reloads = reloads.clone();
        std::thread::spawn(move || {
            use notify::{RecursiveMode, Watcher};
            let names = [
                cert.file_name().map(|name| name.to_os_string()),
                key.file_name().map(|name| name.to_os_string()),
            ];
            let (sender, receiver) = std::sync::mpsc::channel();
            let mut watcher = match notify::recommended_watcher(move |result| {
                let _ = sender.send(result);
            }) {
                Ok(watcher) => watcher,
                Err(error) => {
                    eprintln!("moyu-gateway: watch 初始化失败: {error}");
                    return;
                }
            };
            for path in [&cert, &key] {
                if let Some(parent) = path.parent() {
                    if let Err(error) = watcher.watch(parent, RecursiveMode::NonRecursive) {
                        eprintln!("moyu-gateway: watch {} 失败: {error}", parent.display());
                    }
                }
            }
            let _watcher = watcher;
            for result in receiver {
                match result {
                    Ok(event) => {
                        let relevant = event.paths.iter().any(|path| {
                            names
                                .iter()
                                .flatten()
                                .any(|name| path.file_name() == Some(name.as_os_str()))
                        });
                        if relevant {
                            std::thread::sleep(Duration::from_millis(200));
                            match store.reload() {
                                Ok(()) => {
                                    reloads.fetch_add(1, Ordering::Relaxed);
                                    eprintln!("moyu-gateway: certificate reloaded (watch)");
                                }
                                Err(error) => {
                                    eprintln!("moyu-gateway: watch reload failed: {error}")
                                }
                            }
                        }
                    }
                    Err(error) => eprintln!("moyu-gateway: watch error: {error}"),
                }
            }
        });
    }

    if let Some(interval) = config.poll_interval()? {
        let store = store.clone();
        let reloads = reloads.clone();
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(interval).await;
                match store.reload() {
                    Ok(()) => {
                        reloads.fetch_add(1, Ordering::Relaxed);
                        eprintln!("moyu-gateway: certificate reloaded");
                    }
                    Err(error) => eprintln!("moyu-gateway: certificate reload failed: {error}"),
                }
            }
        });
    }

    #[cfg(unix)]
    if config.reload.signal {
        let store = store.clone();
        let reloads = reloads.clone();
        tokio::spawn(async move {
            let mut signal =
                match tokio::signal::unix::signal(tokio::signal::unix::SignalKind::hangup()) {
                    Ok(signal) => signal,
                    Err(error) => {
                        eprintln!("moyu-gateway: SIGHUP handler failed: {error}");
                        return;
                    }
                };
            while signal.recv().await.is_some() {
                match store.reload() {
                    Ok(()) => {
                        reloads.fetch_add(1, Ordering::Relaxed);
                        eprintln!("moyu-gateway: certificate reloaded (SIGHUP)");
                    }
                    Err(error) => eprintln!("moyu-gateway: SIGHUP reload failed: {error}"),
                }
            }
        });
    }

    let mut handles = Vec::new();
    for address in [&config.listen.ipv4, &config.listen.ipv6] {
        if address.trim().is_empty() {
            continue;
        }
        let listener = bind(address, config.listen.port).await?;
        let acceptor = acceptor.clone();
        let client = client.clone();
        let upstream = upstream.clone();
        handles.push(tokio::spawn(async move {
            if let Err(error) = proxy::serve(listener, acceptor, client, upstream).await {
                eprintln!("moyu-gateway: listener stopped: {error}");
            }
        }));
    }
    if handles.is_empty() {
        return Err("没有配置可用的监听地址".into());
    }

    tokio::signal::ctrl_c()
        .await
        .map_err(|error| format!("等待退出信号失败: {error}"))?;
    Ok(())
}

async fn bind(address: &str, port: u16) -> Result<TcpListener, String> {
    let ip: IpAddr = address
        .parse()
        .map_err(|error| format!("监听地址非法 {address}: {error}"))?;
    let domain = if ip.is_ipv6() {
        Domain::IPV6
    } else {
        Domain::IPV4
    };
    let socket = Socket::new(domain, Type::STREAM, Some(Protocol::TCP))
        .map_err(|error| format!("创建 socket 失败: {error}"))?;
    if ip.is_ipv6() {
        socket
            .set_only_v6(true)
            .map_err(|error| format!("设置 IPV6_V6ONLY 失败: {error}"))?;
    }
    socket
        .set_reuse_address(true)
        .map_err(|error| format!("设置 SO_REUSEADDR 失败: {error}"))?;
    socket
        .bind(&SocketAddr::new(ip, port).into())
        .map_err(|error| format!("绑定 {ip}:{port} 失败: {error}"))?;
    socket
        .listen(1024)
        .map_err(|error| format!("监听 {ip}:{port} 失败: {error}"))?;
    socket
        .set_nonblocking(true)
        .map_err(|error| format!("设置非阻塞失败: {error}"))?;
    let listener: std::net::TcpListener = socket.into();
    TcpListener::from_std(listener).map_err(|error| format!("转换为 tokio listener 失败: {error}"))
}
