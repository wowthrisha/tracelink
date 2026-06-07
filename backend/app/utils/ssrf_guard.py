"""
SSRF Protection Guard
---------------------
Validates webhook/outbound URLs against:
  - RFC 1918 private address ranges
  - Loopback (127.x.x.x / ::1)
  - Link-local (169.254.x.x / AWS IMDS, GCP metadata)
  - IPv6 ULA (fc00::/7)
  - Known dangerous hostnames (localhost, metadata.google.internal, etc.)
  - DNS rebinding: resolves the hostname and validates ALL returned IPs

DNS resolution is intentionally synchronous (socket.getaddrinfo) because:
  1. It runs on the validator path (write, not hot path)
  2. Async DNS libraries add dependency weight for marginal gain here
  3. The result is validated before any outbound connection is made

Usage:
    from app.utils.ssrf_guard import validate_ssrf_url
    safe_url = validate_ssrf_url(raw_url)   # raises HTTPException on failure
"""
import ipaddress
import logging
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# RFC 1918 + special ranges to block
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("169.254.0.0/16"),    # link-local / AWS IMDS / GCP metadata
    ipaddress.ip_network("100.64.0.0/10"),     # shared address space (RFC 6598)
    ipaddress.ip_network("192.0.0.0/24"),      # IETF protocol assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3
    ipaddress.ip_network("240.0.0.0/4"),       # reserved (Class E)
    ipaddress.ip_network("0.0.0.0/8"),         # this network
    # IPv6
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("::/128"),            # unspecified
]

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "metadata.google.internal",
    "metadata",
    "169.254.169.254",    # AWS/GCP/Azure IMDS (also caught by IP check)
    "fd00::ec2",           # AWS IPv6 IMDS
    "instance-data",       # EC2 legacy alias
})


def _is_blocked_ip(addr: str) -> bool:
    """Return True if addr falls in any blocked range."""
    try:
        parsed = ipaddress.ip_address(addr)
    except ValueError:
        return True  # unparseable — block by default
    if parsed.is_loopback or parsed.is_link_local or parsed.is_reserved:
        return True
    for net in _BLOCKED_NETWORKS:
        if parsed in net:
            return True
    return False


def validate_ssrf_url(url: str, *, allow_http: bool = True) -> str:
    """
    Validate that a URL is safe for server-side outbound delivery.

    Raises HTTPException(422) on any violation.
    Returns the stripped, validated URL on success.

    Parameters
    ----------
    url        : Raw URL string from user input.
    allow_http : When False, only https:// is permitted. Default True (webhooks
                 may legitimately use http for internal test servers in dev, but
                 this should be False for any production-facing feature).
    """
    url = url.strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")

    if len(url) > 2048:
        raise HTTPException(status_code=422, detail="url must be ≤ 2048 characters")

    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=422, detail="url is malformed")

    if not allow_http and parsed.scheme != "https":
        raise HTTPException(status_code=422, detail="url must use https://")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=422, detail="url must start with http:// or https://")

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="url has no hostname")

    if not parsed.netloc:
        raise HTTPException(status_code=422, detail="url has no host")

    # Block dangerous hostnames before DNS resolution
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        logger.warning("ssrf_block_hostname url=%r hostname=%r", url, hostname)
        raise HTTPException(status_code=422, detail="url hostname is not allowed")

    # Check if hostname is a raw IP (no DNS lookup needed, still check range)
    try:
        raw_ip = ipaddress.ip_address(hostname)
        if _is_blocked_ip(str(raw_ip)):
            logger.warning("ssrf_block_raw_ip url=%r ip=%r", url, hostname)
            raise HTTPException(
                status_code=422,
                detail="url resolves to a private or reserved IP address",
            )
        return url  # valid raw IP in public space
    except ValueError:
        pass  # not a raw IP — proceed with DNS lookup

    # DNS resolution — block if ANY resolved address is private
    try:
        addr_infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        logger.warning("ssrf_dns_fail url=%r hostname=%r error=%s", url, hostname, exc)
        raise HTTPException(
            status_code=422,
            detail="url hostname could not be resolved",
        )

    if not addr_infos:
        raise HTTPException(status_code=422, detail="url hostname resolved to no addresses")

    for af, _socktype, _proto, _canonname, sockaddr in addr_infos:
        resolved_ip = sockaddr[0]
        if _is_blocked_ip(resolved_ip):
            logger.warning(
                "ssrf_block_resolved_ip url=%r hostname=%r resolved=%r",
                url, hostname, resolved_ip,
            )
            raise HTTPException(
                status_code=422,
                detail="url resolves to a private or reserved IP address",
            )

    return url
