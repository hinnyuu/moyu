use arc_swap::ArcSwap;
use rustls::pki_types::{CertificateDer, PrivateKeyDer};
use rustls::server::{ClientHello, ResolvesServerCert};
use rustls::sign::CertifiedKey;
use rustls::ServerConfig;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

pub struct CertStore {
    current: ArcSwap<CertifiedKey>,
    loaded_at: ArcSwap<String>,
    sha256: ArcSwap<String>,
    cert_path: PathBuf,
    key_path: PathBuf,
}

impl CertStore {
    pub fn load(cert_path: &Path, key_path: &Path) -> Result<Arc<Self>, String> {
        let certified = read_certified_key(cert_path, key_path)?;
        let sha256 = file_sha256(cert_path)?;
        let loaded_at = ArcSwap::from_pointee(now_epoch().to_string());
        Ok(Arc::new(Self {
            current: ArcSwap::from(certified),
            loaded_at,
            sha256: ArcSwap::from_pointee(sha256),
            cert_path: cert_path.to_path_buf(),
            key_path: key_path.to_path_buf(),
        }))
    }

    pub fn reload(&self) -> Result<(), String> {
        let certified = read_certified_key(&self.cert_path, &self.key_path)?;
        let sha256 = file_sha256(&self.cert_path)?;
        self.current.store(certified);
        self.sha256.store(Arc::new(sha256));
        self.loaded_at.store(Arc::new(now_epoch().to_string()));
        Ok(())
    }

    pub fn current(&self) -> Arc<CertifiedKey> {
        self.current.load_full()
    }

    pub fn loaded_at(&self) -> String {
        self.loaded_at.load().as_ref().clone()
    }

    pub fn cert_sha256(&self) -> String {
        self.sha256.load().as_ref().clone()
    }
}

pub struct StoreResolver {
    store: Arc<CertStore>,
}

impl StoreResolver {
    pub fn new(store: Arc<CertStore>) -> Self {
        Self { store }
    }
}

impl std::fmt::Debug for StoreResolver {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str("StoreResolver")
    }
}

impl ResolvesServerCert for StoreResolver {
    fn resolve(&self, _hello: ClientHello<'_>) -> Option<Arc<CertifiedKey>> {
        Some(self.store.current())
    }
}

pub fn server_config(store: Arc<CertStore>) -> Arc<ServerConfig> {
    let mut config = ServerConfig::builder()
        .with_no_client_auth()
        .with_cert_resolver(Arc::new(StoreResolver::new(store)));
    config.alpn_protocols = vec![b"h2".to_vec(), b"http/1.1".to_vec()];
    Arc::new(config)
}

fn read_certified_key(cert_path: &Path, key_path: &Path) -> Result<Arc<CertifiedKey>, String> {
    let cert_file = File::open(cert_path)
        .map_err(|error| format!("打开证书 {} 失败: {error}", cert_path.display()))?;
    let certs: Vec<CertificateDer<'static>> = rustls_pemfile::certs(&mut BufReader::new(cert_file))
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| format!("解析证书失败: {error}"))?;
    if certs.is_empty() {
        return Err("证书文件没有证书".into());
    }

    let key_file = File::open(key_path)
        .map_err(|error| format!("打开私钥 {} 失败: {error}", key_path.display()))?;
    let key: PrivateKeyDer<'static> = rustls_pemfile::private_key(&mut BufReader::new(key_file))
        .map_err(|error| format!("解析私钥失败: {error}"))?
        .ok_or("私钥文件没有私钥")?;

    let signing_key = rustls::crypto::ring::sign::any_supported_type(&key)
        .map_err(|error| format!("私钥类型不支持: {error}"))?;
    Ok(Arc::new(CertifiedKey::new(certs, signing_key)))
}

fn file_sha256(path: &Path) -> Result<String, String> {
    let bytes = std::fs::read(path)
        .map_err(|error| format!("读取证书 {} 失败: {error}", path.display()))?;
    let digest = Sha256::digest(&bytes);
    Ok(digest.iter().map(|byte| format!("{byte:02x}")).collect())
}

fn now_epoch() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use rcgen::generate_simple_self_signed;

    fn write_pair(dir: &Path) -> (PathBuf, PathBuf) {
        let certified = generate_simple_self_signed(vec!["localhost".into()]).expect("cert");
        let cert_path = dir.join("cert.pem");
        let key_path = dir.join("key.pem");
        std::fs::write(&cert_path, certified.cert.pem()).expect("cert write");
        std::fs::write(&key_path, certified.key_pair.serialize_pem()).expect("key write");
        (cert_path, key_path)
    }

    #[test]
    fn loads_and_reloads() {
        let dir = tempfile::tempdir().expect("temp");
        let (cert, key) = write_pair(dir.path());
        let store = CertStore::load(&cert, &key).expect("load");
        assert!(!store.loaded_at().is_empty());
        let before = store.cert_sha256();
        assert_eq!(before.len(), 64);

        let mut pem = std::fs::read_to_string(&cert).expect("read cert");
        pem.push('\n');
        std::fs::write(&cert, pem).expect("append newline");
        store.reload().expect("reload");
        assert_ne!(store.cert_sha256(), before);

        let config = server_config(store.clone());
        assert_eq!(config.alpn_protocols.len(), 2);
    }

    #[test]
    fn rejects_missing_files() {
        let dir = tempfile::tempdir().expect("temp");
        assert!(CertStore::load(
            &dir.path().join("missing.crt"),
            &dir.path().join("missing.key")
        )
        .is_err());
    }
}
