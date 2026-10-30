"""Exact-host allowlist and HTTPS connections pinned to validated public DNS results."""
import http.client
import ipaddress
import os
import socket
import ssl
import time
from urllib.parse import urlsplit


def validate_url(url):
    allowed = {x.strip().lower() for x in os.getenv(
        'BENCHMARK_ALLOWED_HOSTS', 'www.cso.ie,data.cso.ie,www.seai.ie').split(',') if x.strip()}
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or p.hostname not in allowed or p.username or p.password
                or p.port not in (None, 443) or p.fragment or '\\' in url
                or any(ord(c) <= 32 or ord(c) > 126 for c in url)):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('URL must use HTTPS port 443 and an explicitly allowed host') from None
    return p


def public_addresses(host):
    addresses = list(dict.fromkeys(r[4][0] for r in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast
                            for a in addresses):
        raise ValueError('DNS returned a non-public address')
    return addresses


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address):
        super().__init__(host, timeout=25, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        # Numeric address prevents a second DNS lookup; TLS still verifies the original host.
        family = socket.AF_INET6 if ':' in self.address else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((self.address, 443))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


def secure_fetch(source):
    p = validate_url(source['url'])
    address = public_addresses(p.hostname)[0]
    connection = PinnedHTTPS(p.hostname, address)
    deadline = time.monotonic() + 30
    try:
        target = (p.path or '/') + ('?' + p.query if p.query else '')
        connection.request('GET', target,
                           headers={'User-Agent': 'EcoChoice-DataQuality/1.0', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        # Never follow redirects, including redirects to another allowed host.
        if response.status != 200:
            raise ValueError('Upstream HTTP status ' + str(response.status) + '; redirects are not followed')
        chunks, size = [], 0
        while True:
            if time.monotonic() > deadline:
                raise ValueError('Download deadline exceeded')
            chunk = response.read1(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > 10 * 1024 * 1024:
                raise ValueError('Response exceeds 10 MiB')
            chunks.append(chunk)
        return b''.join(chunks), source['url']
    finally:
        connection.close()
