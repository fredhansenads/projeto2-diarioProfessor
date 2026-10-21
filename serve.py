"""WSGI entry point for hosts allowing a persistent Python process."""
import ipaddress
import os

from waitress import serve
from config.wsgi import application


def server_options():
    options = {"host": os.getenv("WAITRESS_HOST", "127.0.0.1"),
               "port": int(os.getenv("PORT", "8000")), "threads": 4,
               "max_request_body_size": 2 * 1024 * 1024,
               "clear_untrusted_proxy_headers": True}
    proxy = os.getenv("WAITRESS_TRUSTED_PROXY", "").strip()
    if proxy:
        ipaddress.ip_address(proxy)  # Reject wildcard and ambiguous proxy trust.
        options.update(trusted_proxy=proxy, trusted_proxy_count=1,
                       trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"})
    return options


if __name__ == "__main__":
    serve(application, **server_options())
