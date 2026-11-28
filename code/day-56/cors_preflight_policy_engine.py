"""
Day 56: CORS (Cross-Origin Resource Sharing) Preflight Policy Engine
Pure Python standard library implementation of W3C CORS preflight evaluation.
Validates Origin headers, handles preflight OPTIONS requests, and strictly rejects
invalid configurations such as wildcard '*' origins combined with credentials.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CorsPolicy:
    """Defines server-side CORS security configuration."""
    allowed_origins: Set[str] = field(default_factory=set)  # e.g., {"proto-tls://app.example.com"} or {"*"}
    allowed_methods: Set[str] = field(default_factory=lambda: {"GET", "POST", "HEAD"})
    allowed_headers: Set[str] = field(default_factory=lambda: {"content-type", "authorization"})
    exposed_headers: Set[str] = field(default_factory=lambda: {"x-request-id", "content-length"})
    allow_credentials: bool = False
    max_age_seconds: int = 600  # 10 minutes cache for preflight OPTIONS


@dataclass
class CorsDecision:
    """Result of CORS evaluation for a given request."""
    is_allowed: bool
    status_code: int
    headers: Dict[str, str] = field(default_factory=dict)
    rejection_reason: Optional[str] = None


class CorsPolicyEngine:
    """Evaluates HTTP requests against CORS security specifications."""

    def __init__(self, policy: CorsPolicy):
        self.policy = policy
        # W3C Security Rule: Cannot use wildcard origin when allow_credentials is True
        if self.policy.allow_credentials and "*" in self.policy.allowed_origins:
            raise ValueError(
                "Insecure CORS policy: Wildcard '*' allowed_origins is prohibited "
                "when allow_credentials is True (W3C CORS spec violation)."
            )

    def is_origin_allowed(self, origin: str) -> bool:
        """Checks if the origin is permitted by policy."""
        if "*" in self.policy.allowed_origins:
            return True
        return origin.lower() in {o.lower() for o in self.policy.allowed_origins}

    def evaluate_preflight(
        self,
        origin: Optional[str],
        request_method: Optional[str],
        request_headers: Optional[List[str]] = None
    ) -> CorsDecision:
        """
        Evaluates an HTTP preflight OPTIONS request.
        RFC / W3C preflight requires Origin and Access-Control-Request-Method.
        """
        if not origin:
            return CorsDecision(
                is_allowed=False,
                status_code=400,
                rejection_reason="Preflight request missing Origin header"
            )

        if not self.is_origin_allowed(origin):
            return CorsDecision(
                is_allowed=False,
                status_code=403,
                rejection_reason=f"Origin '{origin}' not permitted by CORS policy"
            )

        if not request_method:
            return CorsDecision(
                is_allowed=False,
                status_code=400,
                rejection_reason="Preflight missing Access-Control-Request-Method header"
            )

        req_method_norm = request_method.upper()
        if req_method_norm not in {m.upper() for m in self.policy.allowed_methods}:
            return CorsDecision(
                is_allowed=False,
                status_code=403,
                rejection_reason=f"Method '{req_method_norm}' not allowed by CORS policy"
            )

        # Check requested headers
        req_headers_list = [h.strip().lower() for h in (request_headers or []) if h.strip()]
        allowed_headers_norm = {h.lower() for h in self.policy.allowed_headers}
        disallowed = [h for h in req_headers_list if h not in allowed_headers_norm]
        if disallowed:
            return CorsDecision(
                is_allowed=False,
                status_code=403,
                rejection_reason=f"Requested headers not permitted: {', '.join(disallowed)}"
            )

        # Construct successful preflight response headers
        response_headers = {
            "Access-Control-Allow-Origin": origin if self.policy.allow_credentials else ("*" if "*" in self.policy.allowed_origins else origin),
            "Access-Control-Allow-Methods": ", ".join(sorted(self.policy.allowed_methods)),
            "Access-Control-Allow-Headers": ", ".join(sorted(self.policy.allowed_headers)),
            "Access-Control-Max-Age": str(self.policy.max_age_seconds),
            "Vary": "Origin"
        }

        if self.policy.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"

        return CorsDecision(is_allowed=True, status_code=204, headers=response_headers)

    def evaluate_simple_request(
        self,
        origin: Optional[str]
    ) -> CorsDecision:
        """
        Evaluates a regular or simple cross-origin request (GET, POST, etc.).
        """
        if not origin:
            # Same-origin or non-browser request without Origin header
            return CorsDecision(is_allowed=True, status_code=200)

        if not self.is_origin_allowed(origin):
            return CorsDecision(
                is_allowed=False,
                status_code=403,
                rejection_reason=f"Origin '{origin}' rejected"
            )

        response_headers = {
            "Access-Control-Allow-Origin": origin if self.policy.allow_credentials else ("*" if "*" in self.policy.allowed_origins else origin),
            "Vary": "Origin"
        }
        if self.policy.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"
        if self.policy.exposed_headers:
            response_headers["Access-Control-Expose-Headers"] = ", ".join(sorted(self.policy.exposed_headers))

        return CorsDecision(is_allowed=True, status_code=200, headers=response_headers)


def main():
    print("=================================================================")
    print("Testing Day 56: CORS Preflight Policy Engine")
    print("=================================================================")

    # Test 1: Wildcard origin with credentials must raise ValueError
    try:
        CorsPolicyEngine(CorsPolicy(allowed_origins={"*"}, allow_credentials=True))
        assert False, "Should have raised ValueError on wildcard + credentials"
    except ValueError as e:
        print("[PASS] Successfully blocked insecure wildcard with credentials:", e)

    # Test 2: Standard API policy
    policy = CorsPolicy(
        allowed_origins={"proto-tls://dashboard.internal.net", "proto-tls://admin.internal.net"},
        allowed_methods={"GET", "POST", "PUT", "DELETE", "OPTIONS"},
        allowed_headers={"authorization", "content-type", "x-custom-token"},
        exposed_headers={"x-server-execution-time"},
        allow_credentials=True,
        max_age_seconds=3600
    )
    engine = CorsPolicyEngine(policy)

    # Test 3: Valid preflight OPTIONS
    preflight = engine.evaluate_preflight(
        origin="proto-tls://dashboard.internal.net",
        request_method="PUT",
        request_headers=["authorization", "content-type"]
    )
    assert preflight.is_allowed
    assert preflight.status_code == 204
    assert preflight.headers["Access-Control-Allow-Origin"] == "proto-tls://dashboard.internal.net"
    assert preflight.headers["Access-Control-Allow-Credentials"] == "true"
    assert "PUT" in preflight.headers["Access-Control-Allow-Methods"]
    print("[PASS] Preflight OPTIONS request successfully evaluated and approved.")

    # Test 4: Disallowed Origin
    rejected_origin = engine.evaluate_preflight(
        origin="proto-tls://malicious-site.attacker.com",
        request_method="GET"
    )
    assert not rejected_origin.is_allowed
    assert rejected_origin.status_code == 403
    print(f"[PASS] Disallowed origin correctly rejected: {rejected_origin.rejection_reason}")

    # Test 5: Disallowed Method
    rejected_method = engine.evaluate_preflight(
        origin="proto-tls://dashboard.internal.net",
        request_method="PATCH"
    )
    assert not rejected_method.is_allowed
    assert rejected_method.status_code == 403
    print(f"[PASS] Disallowed method correctly rejected: {rejected_method.rejection_reason}")

    # Test 6: Disallowed Header
    rejected_header = engine.evaluate_preflight(
        origin="proto-tls://dashboard.internal.net",
        request_method="POST",
        request_headers=["authorization", "x-unapproved-header"]
    )
    assert not rejected_header.is_allowed
    assert rejected_header.status_code == 403
    print(f"[PASS] Disallowed custom header correctly rejected: {rejected_header.rejection_reason}")

    # Test 7: Simple Request evaluation
    simple_req = engine.evaluate_simple_request(origin="proto-tls://dashboard.internal.net")
    assert simple_req.is_allowed
    assert simple_req.headers["Access-Control-Allow-Origin"] == "proto-tls://dashboard.internal.net"
    assert "x-server-execution-time" in simple_req.headers["Access-Control-Expose-Headers"]
    print("[PASS] Simple GET/POST request evaluation successful.")

    print("\nALL DAY 56 CORS POLICY ENGINE TESTS PASSED (100% SUCCESS)!")


if __name__ == "__main__":
    main()
