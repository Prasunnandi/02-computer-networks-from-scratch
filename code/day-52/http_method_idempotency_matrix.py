"""
Day 52: HTTP Method Semantics & Idempotent Mutation Engine
100% pure Python standard library implementation of RFC 7231 / RFC 9110 method semantics,
safe vs idempotent classification, REST state mutation, and automated retry safety.
"""

from dataclasses import dataclass, field
import enum
import time
from typing import Any, Dict, List, Optional, Tuple


class HTTPMethod(enum.Enum):
    GET = "GET"
    HEAD = "HEAD"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    OPTIONS = "OPTIONS"


class ResourceStore:
    """Simulates an in-memory REST database storing JSON-like resource entities."""

    def __init__(self):
        # Database table: resource_id -> entity dictionary
        self.database: Dict[str, Dict[str, Any]] = {}
        self.mutation_counters: Dict[str, int] = {}  # Tracks database write operations

    def get(self, resource_id: str) -> Optional[Dict[str, Any]]:
        return self.database.get(resource_id)

    def put(self, resource_id: str, new_representation: Dict[str, Any]):
        """PUT is Idempotent: completely replaces the resource state."""
        self.database[resource_id] = dict(new_representation)
        self.mutation_counters[resource_id] = self.mutation_counters.get(resource_id, 0) + 1

    def delete(self, resource_id: str) -> bool:
        """DELETE is Idempotent: removing an already deleted entity leaves it absent."""
        if resource_id in self.database:
            del self.database[resource_id]
            self.mutation_counters[resource_id] = self.mutation_counters.get(resource_id, 0) + 1
            return True
        return False

    def post(self, resource_id: str, delta: Dict[str, Any]):
        """POST is Non-Idempotent: mutates or appends subordinate state."""
        if resource_id not in self.database:
            self.database[resource_id] = {"items": []}
        self.database[resource_id]["items"].append(delta)
        self.mutation_counters[resource_id] = self.mutation_counters.get(resource_id, 0) + 1


class HTTPMethodEngine:
    """Validates method safety, idempotency, and executes automated retry logic."""

    SAFE_METHODS = {HTTPMethod.GET, HTTPMethod.HEAD, HTTPMethod.OPTIONS}
    IDEMPOTENT_METHODS = {HTTPMethod.GET, HTTPMethod.HEAD, HTTPMethod.PUT, HTTPMethod.DELETE, HTTPMethod.OPTIONS}

    def __init__(self, store: ResourceStore):
        self.store = store

    @classmethod
    def is_safe(cls, method: HTTPMethod) -> bool:
        return method in cls.SAFE_METHODS

    @classmethod
    def is_idempotent(cls, method: HTTPMethod) -> bool:
        return method in cls.IDEMPOTENT_METHODS

    def execute_with_retries(self, method: HTTPMethod, resource_id: str, payload: Optional[Dict[str, Any]], attempts: int = 3) -> Tuple[bool, str]:
        """
        Executes request. If method is idempotent, automated retries are safe.
        If non-idempotent, retrying on network drops risks duplicate mutations!
        """
        if not self.is_idempotent(method) and attempts > 1:
            return False, "SECURITY ALERT: Automated retries forbidden for non-idempotent method!"

        for i in range(attempts):
            if method == HTTPMethod.GET:
                self.store.get(resource_id)
            elif method == HTTPMethod.PUT:
                self.store.put(resource_id, payload or {})
            elif method == HTTPMethod.DELETE:
                self.store.delete(resource_id)
            elif method == HTTPMethod.POST:
                self.store.post(resource_id, payload or {})

        return True, f"Successfully executed {method.value} with {attempts} execution(s)"


def main():
    print("=== Day 52: HTTP Method Semantics & Idempotent Mutation Engine ===")

    store = ResourceStore()
    engine = HTTPMethodEngine(store)

    # Test 1: Method classification assertions
    assert engine.is_safe(HTTPMethod.GET) is True
    assert engine.is_idempotent(HTTPMethod.GET) is True
    assert engine.is_safe(HTTPMethod.PUT) is False
    assert engine.is_idempotent(HTTPMethod.PUT) is True
    assert engine.is_safe(HTTPMethod.POST) is False
    assert engine.is_idempotent(HTTPMethod.POST) is False
    print("[*] Test 1 Passed: Safety and Idempotency mathematical classifications verified")

    # Test 2: PUT Idempotency - executing 5 identical times leaves exact state
    entity_payload = {"name": "Alice", "role": "Senior Engineer"}
    ok, msg = engine.execute_with_retries(HTTPMethod.PUT, "user_42", entity_payload, attempts=5)
    assert ok is True
    # State is identical to executing once:
    assert store.get("user_42") == entity_payload
    print(f"[*] Test 2 Passed: PUT executed 5 times maintains identical state: {store.get('user_42')}")

    # Test 3: DELETE Idempotency - executing multiple times produces same result
    ok, msg = engine.execute_with_retries(HTTPMethod.DELETE, "user_42", None, attempts=3)
    assert ok is True
    assert store.get("user_42") is None
    print("[*] Test 3 Passed: DELETE executed 3 times leaves resource deleted")

    # Test 4: Automated retry safety check on non-idempotent POST
    # Automated retry of POST is forbidden because it would create duplicate entries!
    ok, msg = engine.execute_with_retries(HTTPMethod.POST, "orders", {"item": "Laptop"}, attempts=3)
    assert ok is False
    assert "Automated retries forbidden" in msg
    print(f"[*] Test 4 Passed: Non-idempotent POST retries rejected: {msg}")

    # Test 5: Single POST execution succeeds
    ok, msg = engine.execute_with_retries(HTTPMethod.POST, "orders", {"item": "Laptop"}, attempts=1)
    assert ok is True
    assert len(store.get("orders")["items"]) == 1
    print(f"[*] Test 5 Passed: Single POST mutation executed cleanly: {store.get('orders')}")

    print("All HTTP Method Semantics assertions passed successfully!")


if __name__ == "__main__":
    main()
