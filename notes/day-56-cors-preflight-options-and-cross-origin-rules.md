# Day 56: Cross-Origin Resource Sharing (CORS): Same-Origin Policy, Preflight OPTIONS, and Security Headers

The fundamental security model of the web browser is the **Same-Origin Policy (SOP)**. Introduced by Netscape Navigator 2.0, the SOP dictates that a script executing within one origin cannot read or mutate resources residing on an external origin. While the SOP prevents malicious websites from reading a user's private webmail, modern web architectures rely on distributed APIs, microservices, and third-party CDNs. **Cross-Origin Resource Sharing (CORS)**, formalized by the W3C and WHATWG, provides a controlled, opt-in mechanism that allows servers to selectively relax the SOP. This masterclass examines the formal definition of an Origin, Simple Requests vs Preflight `OPTIONS` exchanges, wildcard credential hazards, and server-side verification logic.

---

## 1. Formal Mathematical Definition of an Origin

In web security, an Origin is defined as a 3-tuple consisting of the protocol scheme, host domain/IP, and TCP/UDP port:

$$\text{Origin} = \left( \text{Scheme}, \text{Host}, \text{Port} \right)$$

### The Same-Origin Equality Relation
Two URLs $U_1 = (s_1, h_1, p_1)$ and $U_2 = (s_2, h_2, p_2)$ are considered to share the **Same Origin** if and only if all three components are bitwise identical:

$$\text{IsSameOrigin}(U_1, U_2) \iff (s_1 = s_2) \land (h_1 = h_2) \land (p_1 = p_2)$$

```text
Reference Origin: proto-tls://api.bank.com:443

Comparison URL                              Verdict    Reason
-------------------------------------------------------------------------------------
proto-tls://api.bank.com:443/accounts           SAME       Scheme, host, and port match
proto-clear://api.bank.com:80                      DIFFERENT  Scheme (http) and port (80) differ
proto-tls://api.bank.com:8443                   DIFFERENT  Port (8443 != 443)
proto-tls://auth.bank.com:443                   DIFFERENT  Subdomain differs (auth != api)
proto-tls://bank.com:443                        DIFFERENT  Domain differs (bare domain)
```

---

## 2. Simple Requests vs Preflighted Requests

The browser categorizes all cross-origin requests into either **Simple Requests** or **Preflighted Requests**.

### Simple Requests (Direct Execution)
A request is classified as *Simple* if it satisfies all of the following:
1. HTTP Method is strictly `GET`, `HEAD`, or `POST`.
2. Headers contain only safe-listed headers: `Accept`, `Accept-Language`, `Content-Language`, or `Content-Type`.
3. `Content-Type` is restricted strictly to: `application/x-www-form-urlencoded`, `multipart/form-data`, or `text/plain`.

Under a Simple Request, the browser transmits the payload immediately, appending the `Origin:` header. The server evaluates the origin and responds. If the server does not return `Access-Control-Allow-Origin`, the browser suppresses the response data from the JavaScript runtime.

### Preflighted Requests (Two-Step Exchange)
If a request violates any simple condition (e.g., uses `PUT`, `DELETE`, `PATCH`, or custom headers like `Authorization` or `Content-Type: application/json`), the browser **must execute an HTTP `OPTIONS` preflight handshake** before transmitting the actual payload:

```text
Browser Client                                    API Server
      |                                               |
      |--- 1. OPTIONS /api/data --------------------->| (Preflight Check)
      |    Origin: proto-tls://app.client.com             |
      |    Access-Control-Request-Method: PUT         |
      |    Access-Control-Request-Headers: auth-token |
      |                                               | (Evaluates Policy)
      |<-- 2. 204 No Content / 200 OK ----------------|
      |    Access-Control-Allow-Origin: proto-tls://app...|
      |    Access-Control-Allow-Methods: GET, PUT     |
      |    Access-Control-Allow-Headers: auth-token   |
      |    Access-Control-Max-Age: 86400              | (Caches Preflight for 24h)
      |                                               |
      | (Preflight Approved! Now send actual PUT)     |
      |                                               |
      |--- 3. PUT /api/data ------------------------->| (Actual Request)
      |    Origin: proto-tls://app.client.com             |
      |    auth-token: secret_123                     |
      |<-- 4. 200 OK (Data Updated) ------------------|
      |    Access-Control-Allow-Origin: proto-tls://app...|
```

---

### Kernel & Web Server CORS Policy Engine C Struct
In high-throughput API gateways (e.g. Envoy, NGINX), cross-origin policies are compiled into binary structs for zero-allocation request validation:

```c
struct http_cors_policy {
    uint32_t allowed_origins_hash; /* Hash of permitted origin list or 0xFFFFFFFF for wildcard */
    uint32_t max_age_seconds;      /* Cache duration for Access-Control-Max-Age */
    uint16_t allowed_methods_mask; /* Bitmask: Bit 0=GET, 1=POST, 2=PUT, 3=DELETE, 4=OPTIONS */
    uint16_t exposed_headers_mask; /* Bitmask of exposed response headers */
    uint8_t  allow_credentials:1;  /* Boolean: 1 if Access-Control-Allow-Credentials: true */
    uint8_t  wildcard_origin:1;    /* Boolean: 1 if allowed_origin is '*' */
    uint8_t  reserved_bits:6;      /* Alignment padding bits */
    uint8_t  padding[3];           /* Boundary padding to 16 bytes */
} __attribute__((packed));
```

Field Alignment Breakdown:
- `allowed_origins_hash` (4 bytes): Quick-reject hash filter evaluated prior to string comparison.
- `max_age_seconds` (4 bytes): TTL stored directly in binary format for instant header formatting.
- `allowed_methods_mask` (2 bytes): Bitwise AND validation (`mask & (1 << method_id)`).
- `allow_credentials` & `wildcard_origin` (1 byte total): Crucial bit flags enforcing the W3C security invariant: wildcard origin is strictly forbidden when credentials are enabled.
- Total memory footprint: exactly 16 bytes.

---

## 3. The Access-Control Header Suite

| Header | Sent By | Purpose |
| :--- | :---: | :--- |
| **`Origin`** | Browser | Declares the scheme, host, and port of the calling page. |
| **`Access-Control-Allow-Origin`** | Server | Specifies permitted origins (`*` or specific origin). |
| **`Access-Control-Allow-Methods`**| Server | Comma-separated list of permitted methods (`GET, POST, PUT, DELETE`). |
| **`Access-Control-Allow-Headers`**| Server | Whitelisted custom headers permitted in requests. |
| **`Access-Control-Allow-Credentials`**| Server | Boolean (`true`) allowing cookies/authorization tokens. |
| **`Access-Control-Max-Age`** | Server | Seconds browser may cache preflight result without re-querying. |
| **`Access-Control-Expose-Headers`**| Server | Headers JavaScript can access beyond basic safe-list. |

---

## 4. Compilable C Implementation: High-Performance CORS Preflight Validator

Compile with: `gcc -O2 -Wall -Wextra cors_validator.c -o cors_validator`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_ALLOWED_ORIGINS 3

const char *ALLOWED_ORIGINS[MAX_ALLOWED_ORIGINS] = {
    "proto-tls://dashboard.corp.com",
    "proto-tls://mobile.corp.com",
    "proto-tls://analytics.corp.com"
};

int is_origin_allowed(const char *client_origin) {
    if (!client_origin) return 0;
    for (int i = 0; i < MAX_ALLOWED_ORIGINS; i++) {
        if (strcmp(client_origin, ALLOWED_ORIGINS[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

void handle_cors_request(const char *method, const char *origin_header) {
    printf("Incoming Request: Method=%s, Origin=%s\n", method, origin_header ? origin_header : "(None)");

    if (!origin_header) {
        printf("Standard same-origin or non-browser request. Proceeding normally.\n\n");
        return;
    }

    if (!is_origin_allowed(origin_header)) {
        printf("CORS POLICY REJECTION: Origin '%s' is not in whitelist!\n\n", origin_header);
        return;
    }

    /* Origin is authorized */
    if (strcmp(method, "OPTIONS") == 0) {
        printf("--- Sending CORS Preflight Response ---\n");
        printf("HTTP/1.1 204 No Content\r\n");
        printf("Access-Control-Allow-Origin: %s\r\n", origin_header);
        printf("Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS\r\n");
        printf("Access-Control-Allow-Headers: Authorization, Content-Type, X-Client-ID\r\n");
        printf("Access-Control-Allow-Credentials: true\r\n");
        printf("Access-Control-Max-Age: 86400\r\n");
        printf("Vary: Origin\r\n\r\n");
    } else {
        printf("--- Sending Actual CORS Response Headers ---\n");
        printf("Access-Control-Allow-Origin: %s\r\n", origin_header);
        printf("Access-Control-Allow-Credentials: true\r\n");
        printf("Vary: Origin\r\n\r\n");
    }
}

int main(void) {
    /* Scenario 1: Authorized Origin Preflight */
    handle_cors_request("OPTIONS", "proto-tls://dashboard.corp.com");

    /* Scenario 2: Unauthorized Hacker Origin */
    handle_cors_request("OPTIONS", "proto-tls://malicious-site.attacker.com");

    /* Scenario 3: Authorized Origin Actual PUT */
    handle_cors_request("PUT", "proto-tls://dashboard.corp.com");

    return EXIT_SUCCESS;
}
```

---

## 5. The Critical Vulnerability: Wildcard Origin with Credentials

A widespread security vulnerability in enterprise APIs is misconfiguring CORS to allow all origins while enabling credentials:

```text
# VULNERABLE CONFIGURATION
Access-Control-Allow-Origin: *
Access-Control-Allow-Credentials: true
```

### The Browser Protection Rule
The W3C CORS specification formally bans this combination:
$$\text{If } \text{Allow-Credentials} == \text{true} \implies \text{Allow-Origin} \ne \text{"*"}$$
If a server returns both headers, modern web browsers **abort the transaction** and throw a fatal console security error:
```text
The value of the 'Access-Control-Allow-Origin' header in the response must not be the 
wildcard '*' when the request's credentials mode is 'include'.
```

### The Insecure Dynamic Echo Exploit
To bypass the browser's wildcard block, novice developers often write naive server logic:
```python
# CATASTROPHIC ANTI-PATTERN
origin = request.headers.get("Origin")
response.headers["Access-Control-Allow-Origin"] = origin  # Echos back whatever origin called it!
response.headers["Access-Control-Allow-Credentials"] = "true"
```
An attacker creates a malicious page `evil.com`. When a victim visits `evil.com`, JavaScript issues an authenticated `fetch("proto-tls://bank.com/api/balance", {credentials: "include"})`.
The server reads `Origin: evil.com`, blindly echos `Access-Control-Allow-Origin: evil.com`, and includes credentials! The attacker's script successfully exfiltrates the victim's private financial data.

### Remediation
Always validate the incoming `Origin` against a strict, static server-side whitelist array before echoing the origin header. Never reflect arbitrary origins.
---

## 6. Modern Sec-Fetch-* Metadata Headers (Fetch Metadata Request Headers)

To provide defense-in-depth against cross-site leaks (XS-Leaks) and CSRF attacks without relying solely on CORS preflights, modern W3C specifications introduce `Sec-Fetch-*` headers:

- **`Sec-Fetch-Site`**: Describes the relationship between the initiator and the target (`same-origin`, `same-site`, `cross-site`, `none`).
- **`Sec-Fetch-Mode`**: The mode of the request (`cors`, `no-cors`, `navigate`, `websocket`).
- **`Sec-Fetch-Dest`**: The technical destination of the response (`document`, `image`, `script`, `empty`).

### Server-Side Isolation Policy
A web server can deploy an automated Resource Isolation Policy rejecting unauthorized cross-site requests at the very entrance of the gateway before executing expensive business logic:

```python
# Modern Fetch Metadata Defense
if request.headers.get("Sec-Fetch-Site") == "cross-site":
    if request.headers.get("Sec-Fetch-Dest") not in ["image", "video"]:
        # Block unauthorized cross-site API attempts immediately
        return HttpResponse(status=403)
```
---

## 7. Cross-Origin Embedder & Opener Policies (COOP & COEP)

To mitigate hardware side-channel attacks like Spectre and Meltdown within browser shared memory (`SharedArrayBuffer`), modern standards mandate origin isolation via:

- **`Cross-Origin-Opener-Policy: same-origin` (COOP)**: Isolates the top-level browsing context into a dedicated operating system process.
- **`Cross-Origin-Embedder-Policy: require-corp` (COEP)**: Forbids loading cross-origin subresources unless they explicitly opt in with `Cross-Origin-Resource-Policy: cross-origin`.
---

## 8. Debugging CORS Failures in Browser Developer Tools

When diagnosing CORS failures, developers inspect the browser Network and Console tabs:
- **`Missing Allow Origin`**: Server returned 200 OK but lacked `Access-Control-Allow-Origin`.
- **`Method Not Allowed`**: Preflight OPTIONS returned 200 without matching `Access-Control-Allow-Methods`.
- **`Credentials Mode Mismatch`**: Server returned `Access-Control-Allow-Origin: *` when credentials were included.
