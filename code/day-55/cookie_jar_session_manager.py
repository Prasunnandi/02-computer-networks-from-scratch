"""
Day 55: HTTP Cookie Jar & Session Security Engine
100% pure Python standard library implementation of RFC 6265 cookie management,
Secure/HttpOnly/SameSite flags, domain scoping, and __Host- / __Secure- prefix rules.
"""

from dataclasses import dataclass, field
import enum
import time
from typing import Dict, List, Optional, Tuple


class SameSiteMode(enum.Enum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"


@dataclass
class HTTPCookie:
    name: str
    value: str
    domain: str
    path: str = "/"
    max_age_sec: Optional[int] = None
    created_time: float = field(default_factory=time.time)
    secure: bool = False
    httponly: bool = False
    samesite: SameSiteMode = SameSiteMode.LAX
    is_host_only: bool = True  # True if Domain attribute was omitted

    def is_expired(self, now: float) -> bool:
        if self.max_age_sec is None:
            return False  # Session cookie (survives until browser close)
        return (now - self.created_time) >= self.max_age_sec


class CookieJar:
    """Manages browser cookie storage, security validation, and transmission filtering."""

    def __init__(self):
        # Maps domain -> List[HTTPCookie]
        self.jar: Dict[str, List[HTTPCookie]] = {}

    def parse_set_cookie(self, set_cookie_str: str, request_domain: str, is_tls: bool, now: float) -> Tuple[bool, str]:
        """Parses and validates incoming Set-Cookie header against security rules."""
        parts = [p.strip() for p in set_cookie_str.split(";")]
        if not parts or "=" not in parts[0]:
            return False, "Malformed Set-Cookie format"

        name_val = parts[0].split("=", 1)
        name, val = name_val[0].strip(), name_val[1].strip()

        domain = request_domain
        path = "/"
        max_age = None
        secure = False
        httponly = False
        samesite = SameSiteMode.LAX
        is_host_only = True

        for p in parts[1:]:
            p_lower = p.lower()
            if p_lower == "secure":
                secure = True
            elif p_lower == "httponly":
                httponly = True
            elif p_lower.startswith("domain="):
                domain = p.split("=", 1)[1].lstrip(".")
                is_host_only = False
            elif p_lower.startswith("path="):
                path = p.split("=", 1)[1]
            elif p_lower.startswith("max-age="):
                max_age = int(p.split("=", 1)[1])
            elif p_lower.startswith("samesite="):
                mode_str = p.split("=", 1)[1].capitalize()
                samesite = SameSiteMode(mode_str)

        # RFC 6265bis Prefix Rule 1: __Secure- requires Secure flag and HTTPS
        if name.startswith("__Secure-"):
            if not secure or not is_tls:
                return False, "REJECTED: __Secure- cookie requires Secure flag over HTTPS"

        # RFC 6265bis Prefix Rule 2: __Host- requires Secure, Path=/, HTTPS, and NO Domain attribute
        if name.startswith("__Host-"):
            if not secure or not is_tls or path != "/" or not is_host_only:
                return False, "REJECTED: __Host- cookie requires Secure, Path=/, and Host-Only (no Domain attribute)"

        # SameSite=None requires Secure flag
        if samesite == SameSiteMode.NONE and not secure:
            return False, "REJECTED: SameSite=None requires Secure flag"

        cookie = HTTPCookie(
            name=name, value=val, domain=domain, path=path,
            max_age_sec=max_age, created_time=now,
            secure=secure, httponly=httponly, samesite=samesite,
            is_host_only=is_host_only
        )

        if domain not in self.jar:
            self.jar[domain] = []
        # Replace existing cookie with same name and path
        self.jar[domain] = [c for c in self.jar[domain] if not (c.name == name and c.path == path)]
        self.jar[domain].append(cookie)

        return True, f"Stored cookie '{name}' successfully"

    def get_cookies_for_request(
        self,
        target_domain: str,
        is_tls: bool,
        is_cross_site: bool,
        now: float
    ) -> List[HTTPCookie]:
        """Filters cookies eligible for transmission based on security policies."""
        result = []
        for domain, cookies in self.jar.items():
            for c in cookies:
                if c.is_expired(now):
                    continue

                # Domain match: host-only vs subdomain match
                if c.is_host_only:
                    if target_domain != c.domain:
                        continue
                else:
                    if not (target_domain == c.domain or target_domain.endswith("." + c.domain)):
                        continue

                # Secure check: do not send over plaintext HTTP
                if c.secure and not is_tls:
                    continue

                # SameSite check:
                if is_cross_site:
                    if c.samesite in (SameSiteMode.STRICT, SameSiteMode.LAX):
                        continue  # Blocked on cross-site requests!

                result.append(c)

        return result


def main():
    print("=== Day 55: HTTP Cookie Jar & Session Security Engine ===")

    jar = CookieJar()
    now = 1000.0

    # Test 1: Store secure HttpOnly session cookie
    header1 = "sid=secret123; Path=/; Secure; HttpOnly; SameSite=Strict"
    ok, msg = jar.parse_set_cookie(header1, "bank.com", is_tls=True, now=now)
    assert ok is True
    print(f"[*] Test 1 Passed: Valid session cookie accepted: {msg}")

    # Test 2: Insecure plaintext HTTP rejects Secure cookie transmission
    cookies_http = jar.get_cookies_for_request("bank.com", is_tls=False, is_cross_site=False, now=now)
    assert len(cookies_http) == 0
    print("[*] Test 2 Passed: Secure cookie withheld over plaintext HTTP connection")

    # Test 3: SameSite=Strict blocks transmission on cross-site requests
    cookies_cross = jar.get_cookies_for_request("bank.com", is_tls=True, is_cross_site=True, now=now)
    assert len(cookies_cross) == 0
    print("[*] Test 3 Passed: SameSite=Strict blocked cookie on cross-site request (CSRF Defense)")

    # Test 4: RFC 6265bis __Host- prefix validation
    # Malformed __Host- specifying a Domain attribute -> REJECTED
    bad_host_header = "__Host-TOKEN=abc; Domain=bank.com; Path=/; Secure"
    ok, msg = jar.parse_set_cookie(bad_host_header, "bank.com", is_tls=True, now=now)
    assert ok is False
    assert "REJECTED: __Host-" in msg
    print(f"[*] Test 4 Passed: Enforced __Host- prefix validation: {msg}")

    # Valid __Host- cookie
    good_host_header = "__Host-TOKEN=abc; Path=/; Secure; HttpOnly"
    ok, msg = jar.parse_set_cookie(good_host_header, "bank.com", is_tls=True, now=now)
    assert ok is True
    print(f"[*] Test 5 Passed: Valid __Host- cookie accepted: {msg}")

    print("All HTTP Cookie Jar & Session Security assertions passed successfully!")


if __name__ == "__main__":
    main()
