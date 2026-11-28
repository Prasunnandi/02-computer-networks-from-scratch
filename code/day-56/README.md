# Day 56: CORS Preflight Policy Engine

## 1. What Are We Building & Why Does It Matter?
Modern web security enforces the Same-Origin Policy (SOP), which isolates web applications from accessing resources across different origins (scheme, host, and port). When a frontend web application running on `proto-tls://dashboard.corp.net` needs to fetch sensitive data from an API hosted on `proto-tls://api.corp.net`, browser security requires Cross-Origin Resource Sharing (CORS).

Under standard browser rules, any cross-origin request that modifies server state or includes custom authorization headers cannot be executed silently. Before making potentially destructive requests (such as `PUT`, `DELETE`, or requests carrying custom headers like `Authorization` or `Content-Type: application/json`), modern browsers issue an automatic **Preflight OPTIONS** request asking the server for explicit permission.

If the server does not return the proper `Access-Control-Allow-*` headers matching the request's exact criteria, the browser intercepts the network response and raises a CORS security error in the client application console. Furthermore, W3C security standards strictly forbid servers from using wildcard `*` origins while enabling cookies or session credentials (`Access-Control-Allow-Credentials: true`). In this lab, we build an RFC/W3C-compliant CORS Preflight Policy Engine from scratch using pure Python to parse, validate, and respond to cross-origin requests.

## 2. Python Concepts for Beginners
Here are the foundational Python concepts used in this lab:

- **Sets for Fast Lookups**:
  Python `set` objects store unique items and provide $O(1)$ constant-time membership lookups:
  ```python
  allowed = {"GET", "POST", "PUT"}
  if "DELETE" in allowed:  # Evaluates in constant O(1) time
      pass
  ```
- **Dataclasses with Default Factories**:
  When storing mutable collections (like sets or dictionaries) inside a `@dataclass`, Python requires `field(default_factory=set)` to avoid sharing the same mutable collection across all instances:
  ```python
  from dataclasses import dataclass, field

  @dataclass
  class Config:
      origins: set = field(default_factory=set)
      headers: dict = field(default_factory=dict)
  ```
- **String Normalization**:
  HTTP methods and header names must be compared case-insensitively. In Python, normalize all string values using `.lower()` or `.upper()` before set membership checks:
  ```python
  normalized_header = header_name.strip().lower()
  ```
- **Exception Raising for Security Invariants**:
  When an insecure configuration is detected during initialization, the engine raises a `ValueError` immediately:
  ```python
  if self.policy.allow_credentials and "*" in self.policy.allowed_origins:
      raise ValueError("Insecure CORS configuration detected!")
  ```

## 3. Step-by-Step Code Walkthrough
1. **`CorsPolicy` Data Structure**: Defines which origins, HTTP methods, and headers are allowed, whether credentials (cookies/tokens) are permitted, and how long browsers may cache the preflight response (`Access-Control-Max-Age`).
2. **Spec Compliance Enforcement**: In `__init__`, the engine checks if `allow_credentials` is True and `*` is in `allowed_origins`. If so, it raises an immediate `ValueError` to prevent deploying an insecure server configuration that could leak user sessions.
3. **`is_origin_allowed()`**: Checks if the incoming origin is present in the allowed set or if wildcard access is enabled for unauthenticated resources.
4. **`evaluate_preflight()`**: Inspects incoming preflight OPTIONS requests:
   - Validates the presence of the `Origin` header.
   - Validates the requested HTTP method in `Access-Control-Request-Method` against permitted methods.
   - Validates each header listed in `Access-Control-Request-Headers`.
   - Generates the standard CORS response headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers`, `Access-Control-Max-Age`, and `Vary: Origin`) with HTTP status 204 No Content.
5. **`evaluate_simple_request()`**: Handles regular requests (e.g. GET/POST), generating origin headers and `Access-Control-Expose-Headers` so browser JavaScript can inspect custom server response headers.

## 4. How to Run & Expected Output
Run the Python script directly from the project root:
```bash
python code/day-56/cors_preflight_policy_engine.py
```

Expected terminal output:
```text
=================================================================
Testing Day 56: CORS Preflight Policy Engine
=================================================================
[PASS] Successfully blocked insecure wildcard with credentials: Insecure CORS policy: Wildcard '*' allowed_origins is prohibited when allow_credentials is True (W3C CORS spec violation).
[PASS] Preflight OPTIONS request successfully evaluated and approved.
[PASS] Disallowed origin correctly rejected: Origin 'proto-tls://malicious-site.attacker.com' not permitted by CORS policy
[PASS] Disallowed method correctly rejected: Method 'PATCH' not allowed by CORS policy
[PASS] Disallowed custom header correctly rejected: Requested headers not permitted: x-unapproved-header
[PASS] Simple GET/POST request evaluation successful.

ALL DAY 56 CORS POLICY ENGINE TESTS PASSED (100% SUCCESS)!
```

## 5. Common Python Errors & Troubleshooting
- **`ValueError: Insecure CORS policy`**:
  *Cause*: You configured `allow_credentials=True` and passed `allowed_origins={"*"}`.
  *Fix*: Provide explicit domain origins (e.g., `{"proto-tls://app.domain.com"}`) instead of the wildcard `*`.
- **`KeyError` when checking headers**:
  *Cause*: Accessing dictionary headers without standardizing case (e.g. looking for `Content-Type` when stored as `content-type`).
  *Fix*: Always convert header names to lowercase before dictionary lookups or set membership tests.
- **Empty Preflight Result**:
  *Cause*: Preflight requests must return status code `204 No Content` or `200 OK` with headers; ensure headers are packed into the `CorsDecision` object.
- **`TypeError: unhashable type: 'list'`**:
  *Cause*: Attempting to insert a list into a Python `set`.
  *Fix*: Convert lists to tuples or sets of individual strings.

## 6. Beginner Exercises & Challenges
1. **Regex Origin Matching**: Extend `is_origin_allowed()` to support wildcard subdomains (e.g., `proto-tls://*.internal.net`) using Python's `re` module and compiled pattern caching.
2. **Audit Logging**: Add an audit callback function that logs every blocked cross-origin attempt with timestamp, client IP, requested method, and rejection reason into a structured log file.
3. **Preflight Cache Expiration Simulator**: Implement a client-side preflight cache dictionary that stores `(origin, method)` entries and checks `max_age_seconds` before sending repeated preflight requests.
4. **Vary Header Validator**: Write a test verifying that whenever `Access-Control-Allow-Origin` dynamically echoes the request origin, the HTTP `Vary: Origin` header is always present to prevent proxy cache poisoning.
