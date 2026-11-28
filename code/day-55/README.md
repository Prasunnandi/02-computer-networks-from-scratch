# Day 55: HTTP Cookie Jar & Session Security Lab Tutorial

Welcome to Day 55 of Computer Networks from Scratch. Today, you will build an RFC 6265 HTTP Cookie Jar and security attribute validator, implementing `Secure`, `HttpOnly`, `SameSite`, and modern `__Host-` / `__Secure-` prefix rules.

---

## 1. What Are We Building & Why Does It Matter?

HTTP is stateless. To identify users across requests, web applications store session tokens inside browser cookies (`Set-Cookie` and `Cookie` headers).

Without proper security attributes, cookies expose users to devastating attacks:
- **Missing `Secure`**: Cookies are leaked in plaintext over public Wi-Fi.
- **Missing `HttpOnly`**: Cross-Site Scripting (XSS) attacks steal session tokens via `document.cookie`.
- **Missing `SameSite`**: Cross-Site Request Forgery (CSRF) allows malicious sites to forge authenticated state mutations.
- **Subdomain Injection**: Insecure subdomains overwrite parent domain session cookies.

In this lab, you implement a hardened Cookie Jar enforcing modern security standards.

---

## 2. Python Concepts for Beginners

### A. Python Enums for SameSite Modes
Model `Strict`, `Lax`, and `None` using enumeration types:
```python
import enum

class SameSiteMode(enum.Enum):
    STRICT = "Strict"
    LAX = "Lax"
    NONE = "None"
```

### B. Header Parsing with Semicolon Splitting
Extract directive tokens from raw HTTP header strings:
```python
directives = [d.strip() for d in header_str.split(";")]
```

### C. String Prefixes for Standardized Enforcements
Verify security prefixes like `__Host-`:
```python
if name.startswith("__Host-"):
    if not is_secure or not is_host_only:
        raise ValueError("Invalid __Host- prefix attributes")
```

---

## 3. Step-by-Step Code Walkthrough

1. **`HTTPCookie` Dataclass**: Models cookie attributes (`name`, `value`, `domain`, `path`, `secure`, `httponly`, `samesite`, `is_host_only`).
2. **`CookieJar` Class**:
   - `parse_set_cookie()`:
     - Parses directives (`Domain`, `Path`, `Max-Age`, `Secure`, `HttpOnly`, `SameSite`).
     - Enforces RFC 6265bis `__Secure-` and `__Host-` prefix rules.
     - Enforces that `SameSite=None` requires the `Secure` flag.
   - `get_cookies_for_request()`:
     - Prunes expired cookies.
     - Checks domain scoping (host-only vs subdomain match).
     - Suppresses `Secure` cookies on unencrypted connections.
     - Suppresses `SameSite=Strict` and `SameSite=Lax` cookies on cross-site requests.
3. **`main()` Test Suite**: Validates secure session storage, plaintext transmission blocks, CSRF SameSite suppression, and `__Host-` prefix validation.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-55/cookie_jar_session_manager.py
```

Expected output:
```text
=== Day 55: HTTP Cookie Jar & Session Security Engine ===
[*] Test 1 Passed: Valid session cookie accepted: Stored cookie 'sid' successfully
[*] Test 2 Passed: Secure cookie withheld over plaintext HTTP connection
[*] Test 3 Passed: SameSite=Strict blocked cookie on cross-site request (CSRF Defense)
[*] Test 4 Passed: Enforced __Host- prefix validation: REJECTED: __Host- cookie requires Secure, Path=/, and Host-Only (no Domain attribute)
[*] Test 5 Passed: Valid __Host- cookie accepted: Stored cookie '__Host-TOKEN' successfully
All HTTP Cookie Jar & Session Security assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **`ValueError: 'strict' is not a valid SameSiteMode`**: Use `.capitalize()` when converting user strings to match enum members (`Strict`, `Lax`, `None`).
- **Domain Matching Dots**: When checking subdomains, always use `target.endswith("." + domain)` to prevent `bad-site.com` from matching `site.com`.

---

## 6. Beginner Exercises & Challenges

1. **Implement Path Scoping**: Update `get_cookies_for_request()` to verify that the request URI path matches or is a subpath of the cookie's `path` attribute.
2. **Add LRU Cookie Quota Eviction**: When a domain exceeds 50 cookies, evict the cookie with the oldest creation timestamp.
3. **Export to Netscape `cookies.txt`**: Write an exporter serializing the jar into standard tab-delimited Netscape format used by `curl` and `wget`.
