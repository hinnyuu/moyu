use serde::Deserialize;
use std::fs;
use std::path::Path;
use std::time::Duration;

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct GatewayConfig {
    pub schema_version: u32,
    pub enabled: bool,
    pub listen: Listen,
    pub cert: CertPaths,
    pub reload: Reload,
    pub upstream: Upstream,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Listen {
    pub ipv4: String,
    pub ipv6: String,
    pub port: u16,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct CertPaths {
    pub cert_file: String,
    pub key_file: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Reload {
    pub on_start: bool,
    pub poll_interval: String,
    pub watch: bool,
    pub signal: bool,
    pub api: AdminApi,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct AdminApi {
    pub enabled: bool,
    pub listen: String,
    pub token_file: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Upstream {
    pub url: String,
}

impl GatewayConfig {
    pub fn load(path: &Path) -> Result<Self, String> {
        let text = fs::read_to_string(path)
            .map_err(|error| format!("读取配置 {} 失败: {error}", path.display()))?;
        serde_yaml::from_str(&text).map_err(|error| format!("解析配置失败: {error}"))
    }

    pub fn poll_interval(&self) -> Result<Option<Duration>, String> {
        parse_duration(&self.reload.poll_interval)
    }
}

pub fn parse_duration(text: &str) -> Result<Option<Duration>, String> {
    let text = text.trim();
    if text.is_empty() || text == "0" || text == "0s" {
        return Ok(None);
    }
    let split = text
        .find(|character: char| !character.is_ascii_digit())
        .ok_or_else(|| format!("时间间隔缺少单位: {text}"))?;
    let value: u64 = text[..split]
        .parse()
        .map_err(|_| format!("时间间隔非法: {text}"))?;
    let unit = &text[split..];
    let millis = match unit {
        "ms" => value,
        "s" => value.saturating_mul(1_000),
        "m" => value.saturating_mul(60_000),
        "h" => value.saturating_mul(3_600_000),
        _ => return Err(format!("未知时间单位: {text}")),
    };
    Ok(Some(Duration::from_millis(millis)))
}

#[cfg(test)]
mod tests {
    use super::*;

    const YAML: &str = r#"
schemaVersion: 1
enabled: true
listen:
  ipv4: "0.0.0.0"
  ipv6: "::"
  port: 443
cert:
  certFile: /certs/tls.crt
  keyFile: /certs/tls.key
reload:
  onStart: true
  pollInterval: "30s"
  watch: false
  signal: true
  api:
    enabled: true
    listen: "127.0.0.1:9443"
    tokenFile: /run/secrets/gateway_reload_token
upstream:
  url: "http://api:8000"
"#;

    #[test]
    fn parses_config() {
        let config: GatewayConfig = serde_yaml::from_str(YAML).expect("config");
        assert_eq!(config.listen.port, 443);
        assert_eq!(config.cert.cert_file, "/certs/tls.crt");
        assert_eq!(config.upstream.url, "http://api:8000");
        assert_eq!(
            config.poll_interval().expect("duration"),
            Some(Duration::from_secs(30))
        );
    }

    #[test]
    fn rejects_unknown_fields() {
        let yaml = YAML.replace("enabled: true", "enabled: true\nunknown: true");
        assert!(serde_yaml::from_str::<GatewayConfig>(&yaml).is_err());
    }

    #[test]
    fn parses_durations() {
        assert_eq!(parse_duration("0s").expect("zero"), None);
        assert_eq!(
            parse_duration("500ms").expect("ms"),
            Some(Duration::from_millis(500))
        );
        assert_eq!(
            parse_duration("2m").expect("m"),
            Some(Duration::from_secs(120))
        );
        assert!(parse_duration("10").is_err());
        assert!(parse_duration("10d").is_err());
    }
}
