//! Endpoint + TLS policy configuration.

use std::time::Duration;

/// WebSocket endpoint configuration.
#[derive(Debug, Clone)]
pub struct WsConfig {
    /// Full URL, e.g. `wss://gateway.example.com/syntra/v1/ws`.
    /// The path MUST be `/syntra/v1/ws` (case-sensitive, no trailing slash
    /// variant unless the deployment documents aliasing).
    pub url: String,
    /// When false (default), only `wss://` is accepted. Set true only for
    /// loopback endpoints (`ws://127.0.0.1/...`); production
    /// builds MUST NOT enable it.
    pub allow_insecure: bool,
    /// Expected host for TLS hostname verification is derived from the URL;
    /// this override exists only for tests with custom resolvers and
    /// changes the `Host` header the client sends.
    pub sni_override: Option<String>,
    /// TCP + TLS + WS Upgrade timeout.
    pub connect_timeout: Duration,
    /// Close grace period for in-flight results (SNTR-HS-006/013).
    pub close_grace: Duration,
    /// Ping interval for transport liveness (WS section 1I).
    pub ping_interval: Duration,
    /// Pong latency allowance after each Ping interval: silence longer than
    /// `ping_interval + pong_timeout` closes the connection (typically code
    /// 1001) with `UNAVAILABLE` to in-flight RPCs.
    pub pong_timeout: Duration,
    /// Bound for one outbound write: exceeding it closes a slow receiver
    /// (typically 1001) instead of queueing unboundedly (WS section 1L).
    pub write_grace: Duration,
}

impl WsConfig {
    pub fn secure(url: impl Into<String>) -> Self {
        Self {
            url: url.into(),
            allow_insecure: false,
            sni_override: None,
            connect_timeout: Duration::from_secs(10),
            close_grace: Duration::from_secs(2),
            ping_interval: Duration::from_secs(30),
            pong_timeout: Duration::from_secs(10),
            write_grace: Duration::from_secs(5),
        }
    }

    /// Development-only plaintext endpoint. Emits an insecure-mode warning
    /// at connect time and refuses non-loopback hosts, even with
    /// `allow_insecure` set (defense against accidental public plaintext).
    pub fn insecure_dev(url: impl Into<String>) -> Self {
        Self {
            url: url.into(),
            allow_insecure: true,
            sni_override: None,
            connect_timeout: Duration::from_secs(10),
            close_grace: Duration::from_secs(2),
            ping_interval: Duration::from_secs(30),
            pong_timeout: Duration::from_secs(10),
            write_grace: Duration::from_secs(5),
        }
    }
}

/// Parsed + validated endpoint.
#[derive(Debug, Clone)]
pub struct Endpoint {
    pub scheme: String,
    pub host: String,
    pub port: Option<u16>,
    pub path: String,
    pub is_secure: bool,
}

impl Endpoint {
    pub fn parse(
        url_str: &str,
        allow_insecure: bool,
    ) -> Result<Self, crate::error::TransportError> {
        let url = url::Url::parse(url_str)
            .map_err(|e| crate::error::TransportError::InvalidUrl(format!("invalid url: {e}")))?;
        // Credentials MUST NOT travel in URL/query (SNTR-ASEC-003, SNTR-TSEC-021).
        if !url.username().is_empty() || url.password().is_some() {
            return Err(crate::error::TransportError::InvalidUrl(
                "credentials must not appear in the URL".to_string(),
            ));
        }
        if url.query().map(looks_like_secret).unwrap_or(false) {
            return Err(crate::error::TransportError::InvalidUrl(
                "query must not carry credential patterns".to_string(),
            ));
        }
        let scheme = url.scheme().to_string();
        let is_secure = match scheme.as_str() {
            "wss" => true,
            "ws" => {
                if !allow_insecure {
                    return Err(crate::error::TransportError::InsecureDenied(
                        "ws:// requires explicit insecure-dev opt-in".to_string(),
                    ));
                }
                false
            }
            _ => {
                return Err(crate::error::TransportError::InvalidUrl(format!(
                    "scheme must be ws or wss, got {scheme}"
                )))
            }
        };
        let path = url.path().to_string();
        if path != crate::ENDPOINT_PATH {
            return Err(crate::error::TransportError::InvalidUrl(format!(
                "path must be {}, got {path}",
                crate::ENDPOINT_PATH
            )));
        }
        let host = url.host_str().unwrap_or("").to_string();
        if host.is_empty() {
            return Err(crate::error::TransportError::InvalidUrl(
                "missing host".to_string(),
            ));
        }
        // A development opt-in never authorizes credentials over public
        // plaintext. Inspect the parsed host, not a spoofable string prefix.
        if !is_secure && !url.host().is_some_and(is_loopback) {
            return Err(crate::error::TransportError::InsecureDenied(
                "plaintext WS is restricted to loopback hosts".to_string(),
            ));
        }
        Ok(Self {
            scheme,
            host,
            port: url.port(),
            path,
            is_secure,
        })
    }
}

fn looks_like_secret(q: &str) -> bool {
    let l = q.to_ascii_lowercase();
    l.contains("token") || l.contains("credential") || l.contains("auth") || l.contains("secret")
}

fn is_loopback(host: url::Host<&str>) -> bool {
    match host {
        url::Host::Domain(name) => name == "localhost",
        url::Host::Ipv4(ip) => std::net::IpAddr::V4(ip).is_loopback(),
        url::Host::Ipv6(ip) => std::net::IpAddr::V6(ip).is_loopback(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_credentials_in_url() {
        assert!(Endpoint::parse("wss://user:pass@h/syntra/v1/ws", false).is_err());
        assert!(Endpoint::parse("wss://h/syntra/v1/ws?token=abc", false).is_err());
    }

    #[test]
    fn enforces_path_and_scheme() {
        assert!(Endpoint::parse("wss://h/syntra/v1/ws", false).is_ok());
        assert!(Endpoint::parse("wss://h/syntra/v1/ws/", false).is_err());
        assert!(Endpoint::parse("ws://h/syntra/v1/ws", false).is_err());
        assert!(Endpoint::parse("ws://127.0.0.1/syntra/v1/ws", true).is_ok());
        assert!(Endpoint::parse("https://h/syntra/v1/ws", false).is_err());
    }

    #[test]
    fn plaintext_requires_loopback_even_with_dev_opt_in() {
        for host in [
            "example.com",
            "127.evil.example",
            "127.0.0.1.example.com",
            "localhost.example.com",
            "192.168.1.2",
            "0.0.0.0",
            "[::]",
            "[2001:db8::1]",
            "[::ffff:127.0.0.1]",
        ] {
            let cfg = WsConfig::insecure_dev(format!("ws://{host}/syntra/v1/ws"));
            assert!(
                matches!(
                    Endpoint::parse(&cfg.url, cfg.allow_insecure),
                    Err(crate::error::TransportError::InsecureDenied(_))
                ),
                "plaintext must be denied for {host}"
            );
            assert!(Endpoint::parse(&format!("wss://{host}/syntra/v1/ws"), false).is_ok());
        }
    }

    #[test]
    fn plaintext_accepts_only_parsed_loopback_addresses_and_localhost() {
        for host in [
            "localhost",
            "LOCALHOST",
            "127.0.0.1",
            "127.23.45.67",
            "[::1]",
            "[0:0:0:0:0:0:0:1]",
        ] {
            let url = format!("ws://{host}/syntra/v1/ws");
            assert!(Endpoint::parse(&url, true).is_ok(), "loopback: {host}");
            assert!(matches!(
                Endpoint::parse(&url, false),
                Err(crate::error::TransportError::InsecureDenied(_))
            ));
            assert!(Endpoint::parse(&format!("ws://u:p@{host}/syntra/v1/ws"), true).is_err());
            assert!(Endpoint::parse(&format!("{url}?token=abc"), true).is_err());
        }
    }
}
