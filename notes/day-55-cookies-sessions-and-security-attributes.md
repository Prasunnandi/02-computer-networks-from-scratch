# Day 55: HTTP State Management: Cookies, Sessions, and Modern Security Attributes

Because HTTP is a stateless protocol (each request is evaluated independently by the server without ambient memory of prior exchanges), web applications require an explicit state-tracking mechanism. RFC 6265 formalizes HTTP State Management via **Cookies**. An origin server transmits a `Set-Cookie` header, and user agents return stored key-value pairs inside the `Cookie` header on subsequent requests. This masterclass examines browser cookie jars, entropy requirements for session identifiers, and modern security attributes (`HttpOnly`, `Secure`, `SameSite`).

---

## 1. The HTTP State Management Protocol Exchange

```text
Browser Client                                 Web Server
      |                                            |
      |--- POST /api/login (User Credentials) ---->|
      |                                            | (Verifies Password)
      |                                            | (Generates 128-bit Session ID)
      |<-- 200 OK ---------------------------------|
      |    Set-Cookie: sid=0x4a9b...; Secure;      |
      |                HttpOnly; SameSite=Lax      |
      |                                            |
      | (Stores sid in encrypted browser cookie jar)
      |                                            |
      |--- GET /api/dashboard -------------------->|
      |    Cookie: sid=0x4a9b...                   | (Authenticates User via sid)
      |<-- 200 OK (Dashboard Data) ----------------|
```

### The Three Critical Security Attributes
1. **`Secure`**: Directs the browser to **never** transmit the cookie over unencrypted HTTP plaintext connections. The cookie is only emitted across TLS (HTTPS), defeating Wi-Fi sniffing and Man-in-the-Middle (MITM) session hijacking.
2. **`HttpOnly`**: Blocks client-side JavaScript APIs (`document.cookie`) from reading or mutating the cookie. This serves as a vital defense-in-depth shield: even if an application suffers a Cross-Site Scripting (XSS) vulnerability, the attacker cannot exfiltrate the session cookie.
3. **`SameSite`**: Governs whether cookies are transmitted during cross-site requests, mitigating Cross-Site Request Forgery (CSRF).

---

## 2. SameSite Mechanics: Strict vs Lax vs None

The `SameSite` attribute controls cookie inclusion based on the relationship between the target URL and the active top-level site displayed in the browser's address bar.

| SameSite Mode | Normal Navigation (`<a>` click) | Form POST (`<form method=POST>`) | Embedded Resources (`<img>`, `<iframe>`) | AJAX / fetch() |
| :--- | :---: | :---: | :---: | :---: |
| **`Strict`** | **BLOCKED** | **BLOCKED** | **BLOCKED** | **BLOCKED** |
| **`Lax`** (Default) | **SENT** | **BLOCKED** | **BLOCKED** | **BLOCKED** |
| **`None`** (Requires `Secure`)| **SENT** | **SENT** | **SENT** | **SENT** |

### The CSRF Defense Spectrum
- Under **`SameSite=Strict`**, if a user clicks a link to `bank.com` from an external email, the browser sends zero cookies. The user arrives unauthenticated.
- Under **`SameSite=Lax`**, top-level safe GET navigations include cookies, but cross-site `POST` requests do not, eliminating CSRF attacks that forge form submissions.
- **`SameSite=None; Secure`** is reserved exclusively for cross-origin iframes, embedded widgets, and third-party tracking pixels.

---

### Browser & Reverse Proxy Cookie Jar C Struct
Modern HTTP user agents and session border controllers store parsed cookie entries in an in-memory cookie jar structured as follows:

```c
struct http_cookie_entry {
    char     name[64];             /* Cookie identifier name string */
    char     value[256];           /* Session token or encrypted state value */
    char     domain[128];          /* Scope domain restriction */
    char     path[64];             /* URI path prefix restriction */
    uint64_t expires_timestamp;    /* UNIX timestamp expiry (0 for session-only) */
    uint32_t max_age_seconds;      /* Delta seconds lifetime */
    uint8_t  is_secure:1;          /* Enforces TLS-only transport */
    uint8_t  is_httponly:1;        /* Blocks JavaScript document.cookie access */
    uint8_t  is_host_only:1;       /* Scope strictly to exact host without subdomains */
    uint8_t  samesite_policy:2;    /* 0 = None, 1 = Lax, 2 = Strict */
    uint8_t  reserved_bits:3;      /* Reserved flags for future extensions */
} __attribute__((packed));
```

Field Alignment Breakdown:
- String buffers (`name`, `value`, `domain`, `path`): Explicit maximum bounded lengths preventing heap buffer overruns.
- `expires_timestamp` (8 bytes): Epoch timestamp for lifecycle expiration checking.
- `max_age_seconds` (4 bytes): Remaining relative lifetime in seconds.
- Bitfields (1 byte total): `is_secure`, `is_httponly`, `is_host_only`, and `samesite_policy` packed into a single byte.

---

## 3. Mathematical Entropy of Session Identifiers

A session identifier is an authentication token. If an attacker can guess or predict a valid session identifier, they attain complete account takeover without knowing the user's password.

### Entropy Calculation Formula
Let $A$ be the alphabet size of the token encoding (e.g. Hexadecimal = 16 characters; Base64 = 64 characters).
Let $L$ be the character length of the token string.
The total entropy $H$ in bits is:

$$H = L \cdot \log_2(A)$$

For a 32-character hexadecimal token:
$$H = 32 \times \log_2(16) = 32 \times 4 = 128\text{ bits}$$

### Birthday Paradox Collision Probability
Given $k$ active concurrent sessions and an entropy space of $N = 2^H$:

$$P(\text{Collision}) \approx 1 - e^{-\frac{k^2}{2N}} = 1 - e^{-\frac{k^2}{2^{H+1}}}$$

For $H = 128$ bits and $k = 10^9$ (one billion active enterprise sessions):
$$P(\text{Collision}) \approx \frac{10^{18}}{2^{129}} \approx 1.46 \times 10^{-21} \quad (\text{Cryptographically Impossible!})$$

---

## 4. Compilable C Implementation: Secure Session Token Generator & Cookie Formatter

Compile with: `gcc -O2 -Wall -Wextra session_generator.c -o session_generator`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#define TOKEN_BYTES 16 /* 128 bits of cryptographic entropy */

int generate_secure_token(char *out_hex, size_t max_len) {
    if (max_len < (TOKEN_BYTES * 2 + 1)) return -1;

    unsigned char raw_bytes[TOKEN_BYTES];
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) {
        perror("Failed to open /dev/urandom");
        return -1;
    }

    if (read(fd, raw_bytes, TOKEN_BYTES) != TOKEN_BYTES) {
        perror("Failed to read entropy");
        close(fd);
        return -1;
    }
    close(fd);

    for (int i = 0; i < TOKEN_BYTES; i++) {
        sprintf(out_hex + (i * 2), "%02x", raw_bytes[i]);
    }
    out_hex[TOKEN_BYTES * 2] = '\0';
    return 0;
}

void build_set_cookie_header(char *out_header, size_t max_len, const char *token) {
    snprintf(out_header, max_len,
             "Set-Cookie: SESSIONID=%s; Path=/; Max-Age=86400; Secure; HttpOnly; SameSite=Lax",
             token);
}

int main(void) {
    char token[TOKEN_BYTES * 2 + 1];
    if (generate_secure_token(token, sizeof(token)) != 0) {
        return EXIT_FAILURE;
    }

    printf("Generated 128-bit Cryptographic Session Token:\n%s\n\n", token);

    char header[512];
    build_set_cookie_header(header, sizeof(header), token);
    printf("HTTP Response Header:\n%s\n", header);

    return EXIT_SUCCESS;
}
```

---

## 5. Cookie Scoping: Domain and Path Hazards

The `Domain` attribute controls cookie visibility across host hierarchies:
- If a server sets `Set-Cookie: sid=123` without an explicit `Domain` attribute, the browser defaults to **Host-Only** mode: the cookie is sent *only* to `api.site.com`, and is withheld from `sub.api.site.com` or `site.com`.
- If a server explicitly specifies `Domain=site.com`, the browser transmits the cookie to `site.com` and **all subdomains** (`dev.site.com`, `corp.site.com`, `user-content.site.com`).

### The Subdomain Takeover Hazard
If an organization allows unprivileged users to host static pages on `pages.corp.com` or suffers a dangling DNS subdomain takeover, an attacker on the subdomain can read cookies scoped to `Domain=corp.com`.

---

## 6. Production Post-Mortem: The Samy MySpace Worm (Cookie Theft via Missing HttpOnly)

### Incident Overview
In October 2005, the *Samy Worm* infected over one million MySpace accounts within 20 hours, becoming the fastest-spreading computer virus in history.

### The Mechanism
1. MySpace permitted users to customize their profile pages with HTML and CSS, attempting to filter out `<script>` tags.
2. Security researcher Samy Kamkar discovered a vulnerability in Microsoft Internet Explorer where JavaScript could be embedded within CSS expressions:
```css
div { background:url('javascript:eval(document.cookie)'); }
```
3. Because MySpace session cookies lacked the `HttpOnly` flag, the script read `document.cookie`.
4. The payload extracted the session ID, made automated HTTP requests to add Samy as a hero on the victim's profile, and appended the worm code to the victim's own profile page.
5. Within 20 hours, over 1,000,000 users were infected, forcing MySpace to take the entire service offline.

### The Defense
If MySpace had configured `HttpOnly` on its session cookie:
```text
Set-Cookie: myspace_session=...; HttpOnly; Secure
```
The browser's JavaScript engine would have returned an empty string upon accessing `document.cookie`, completely neutralizing the worm's ability to hijack user sessions.
---

## 7. Cookie Prefixes: The `__Host-` and `__Secure-` Standards (RFC 6265bis)

Because subdomains can forge cookies for parent domains, attackers utilizing DNS spoofing or cross-subdomain injection can overwrite genuine session cookies. RFC 6265bis introduces cryptographically enforced cookie prefixes:

1. **`__Secure-` Prefix**:
   - The cookie **must** be set over a secure HTTPS connection.
   - The cookie **must** possess the `Secure` attribute.
   ```text
   Set-Cookie: __Secure-ID=123; Secure; Domain=example.com
   ```

2. **`__Host-` Prefix (The Strongest Defense)**:
   - The cookie **must** be set over HTTPS.
   - The cookie **must** possess the `Secure` attribute.
   - The cookie **must NOT** specify a `Domain` attribute (strictly bound to the exact origin host).
   - The cookie **must** specify `Path=/`.
   ```text
   Set-Cookie: __Host-SESSION=abc123xyz; Secure; Path=/; HttpOnly
   ```
If a browser receives a cookie starting with `__Host-` that contains a `Domain=` parameter or is sent over plaintext HTTP, modern browsers reject the cookie unconditionally.

---

## 8. Storage Comparison: HttpOnly Cookies vs LocalStorage

| Security Vector | `HttpOnly` Cookies | Browser `localStorage` / `sessionStorage` |
| :--- | :--- | :--- |
| **Accessible to JavaScript?** | **NO** (`document.cookie` returns empty) | **YES** (`window.localStorage.getItem()`) |
| **XSS Exfiltration Risk** | **Immune** (Token cannot be stolen via JS) | **CRITICAL** (1-line script exfiltrates tokens) |
| **CSRF Vulnerability** | Vulnerable if `SameSite` is absent | **Immune** (Not automatically attached) |
| **Automatic Transmission** | Sent automatically with every HTTP request | Requires manual JavaScript header injection |
| **Max Capacity** | 4,096 bytes per cookie domain | 5 to 10 Megabytes |

### Architectural Conclusion
Authentication and session tokens must **always** reside within `__Host-` prefixed, `HttpOnly`, `Secure`, `SameSite=Lax` cookies. `localStorage` must strictly be reserved for non-sensitive UI settings (dark mode, client layout state).
---

## 9. Browser Cookie Eviction Algorithms: LRU and Size Limits

Web browsers enforce strict storage quotas on cookies to prevent denial-of-service memory exhaustion:
- **Maximum Cookie Size**: 4,096 bytes per cookie (combining name, value, and attributes).
- **Maximum Cookies Per Domain**: Typically 50 to 180 cookies per host.
- **Eviction Strategy**: When a domain exceeds its quota, the browser invokes a **Least Recently Used (LRU)** eviction algorithm, purging cookies with the oldest `Last Accessed` timestamp.

```text
Incoming Set-Cookie on domain with 150 cookies (Quota Full):
1. Scan domain cookie list.
2. Identify cookie with minimum last_access_timestamp.
3. Evict oldest cookie from sqlite3 cookie jar.
4. Insert new cookie.
```

---

## 10. Summary Checklist for Production Session Cookie Configuration

To guarantee enterprise-grade session hygiene, every production `Set-Cookie` header must comply with the following baseline:
- Name format: `__Host-SESSIONID` or `__Secure-SESSIONID`.
- Directives: `Path=/; Secure; HttpOnly; SameSite=Lax`.
- Max-Age: Explicit integer expiration seconds matched to backend session persistence timers.
