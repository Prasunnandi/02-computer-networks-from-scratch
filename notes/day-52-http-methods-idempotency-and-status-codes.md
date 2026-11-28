# Day 52: HTTP Methods, Idempotency, Safety, and Status Code Semantics

The architecture of the World Wide Web relies on the Representational State Transfer (REST) paradigm formalized in RFC 7231 and RFC 9110. HTTP is not merely an RPC transport; it is an object-oriented application protocol where standardized **Methods** define semantic actions, **Idempotency** guarantees fault-tolerant retry safety, and **Status Codes** establish an unambiguous contract between distributed systems. This masterclass examines the formal mathematics of safe and idempotent operations, status classification hierarchies, and cacheability semantics.

---

## 1. Formal Mathematical Definitions: Safety vs Idempotency

In distributed computing, client network failures (dropped packets, connection timeouts) require automated retry logic. Whether a client can safely resend an HTTP request without causing unintended side effects depends strictly on two mathematical properties: **Safety** and **Idempotency**.

### Definition of Safety
An HTTP method is **Safe** if it represents a read-only retrieval that does not alter the resource state on the origin server.
Let $S$ represent the state of the server. Let $f_m(S)$ denote the execution of HTTP method $m$:

$$\text{Method } m \text{ is Safe} \iff \forall S, \quad f_m(S) = S$$

Safe methods are inherently idempotent and unconditionally cacheable.
- **Safe Methods**: `GET`, `HEAD`, `OPTIONS`, `TRACE`

### Definition of Idempotency
An HTTP method is **Idempotent** if executing the method multiple consecutive times produces the identical server state as executing it exactly once.

$$\text{Method } m \text{ is Idempotent} \iff \forall S, \quad f_m(f_m(S)) = f_m(S)$$

By mathematical induction, for any $N \ge 1$ executions:
$$f_m^N(S) = f_m(S)$$

- **Idempotent Methods**: `GET`, `HEAD`, `PUT`, `DELETE`, `OPTIONS`, `TRACE`
- **Non-Idempotent Methods**: `POST`, `PATCH`, `CONNECT`

### Matrix of Semantic Method Guarantees

| Method | Safe? | Idempotent? | Request Body Allowed? | Primary Semantic Purpose |
| :--- | :---: | :---: | :---: | :--- |
| **`GET`** | **YES** | **YES** | No (Ignored) | Retrieve resource representation |
| **`HEAD`** | **YES** | **YES** | No | Retrieve identical headers without body |
| **`PUT`** | NO | **YES** | **YES** | Complete resource replacement / creation |
| **`DELETE`**| NO | **YES** | Optional | Remove designated resource |
| **`POST`** | NO | NO | **YES** | Process subordinate entity / state mutation |
| **`PATCH`**| NO | NO | **YES** | Partial resource delta mutation |
| **`OPTIONS`**| **YES**| **YES** | Optional | Query communication options / CORS preflight |

---

## 2. PUT vs POST vs PATCH: The Core Architectural Distinction

A common anti-pattern in distributed systems is conflating `PUT`, `POST`, and `PATCH`.

```text
Target Resource: /users/42
Current Database Record: { "id": 42, "name": "Alice", "role": "engineer", "city": "NYC" }

--- Execution of PUT ---
Request: PUT /users/42
Body:    { "name": "Alice Cooper" }
Result:  Database replaces entire record! "role" and "city" are WIPED (set to null)!
         Executing 10 times leaves the exact same record: Idempotent!

--- Execution of PATCH ---
Request: PATCH /users/42
Body:    { "city": "SF" }
Result:  Database updates ONLY the city field. "name" and "role" are preserved!

--- Execution of POST ---
Request: POST /users/42/transactions
Body:    { "amount": 100 }
Result:  Appends a new financial debit. Executing 3 times debits $300: NON-IDEMPOTENT!
```

---

## 3. HTTP Status Code Taxonomies & Semantics

HTTP status codes are 3-digit unsigned integers categorized into five architectural classes:

```text
Status Code Classes:
  1xx (Informational): Request received, continuing process (e.g., 100 Continue, 101 Switching Protocols)
  2xx (Successful):    Action received, understood, and accepted (e.g., 200 OK, 201 Created, 204 No Content)
  3xx (Redirection):   Further action needed to complete request (e.g., 301 Moved, 302 Found, 304 Not Modified)
  4xx (Client Error):  Request contains bad syntax or cannot be fulfilled (e.g., 400 Bad Request, 404 Not Found)
  5xx (Server Error):  Server failed to fulfill apparently valid request (e.g., 500 Internal, 502 Bad Gateway)
```

### Critical Architectural Distinctions
- **`301 Moved Permanently` vs `302 Found` vs `307 Temporary Redirect` vs `308 Permanent Redirect`**:
  - Legacy browsers incorrectly converted `301` and `302` `POST` requests into `GET` requests upon redirecting.
  - RFC 7231 introduced `307` and `308` to strictly guarantee that the **HTTP method and request body remain unaltered** across the redirection hop.
- **`204 No Content`**: Indicates successful completion where the server deliberately emits zero response body bytes (essential for REST `DELETE` operations and save actions).
- **`401 Unauthorized` vs `403 Forbidden`**:
  - `401` means *unauthenticated*: the client lacks credentials and must authenticate via `WWW-Authenticate`.
  - `403` means *unauthorized*: the client's identity is known, but they possess insufficient permissions; re-authenticating will not alter the verdict.

---

## 4. Compilable C Implementation: HTTP Request Line & Header Parser

Compile with: `gcc -O2 -Wall -Wextra http_parser.c -o http_parser`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    METHOD_UNKNOWN = 0,
    METHOD_GET,
    METHOD_HEAD,
    METHOD_POST,
    METHOD_PUT,
    METHOD_DELETE,
    METHOD_PATCH,
    METHOD_OPTIONS
} http_method_t;

typedef struct {
    http_method_t method;
    char path[256];
    char version[16];
    int is_safe;
    int is_idempotent;
} parsed_request_t;

parsed_request_t parse_http_request_line(const char *raw_request) {
    parsed_request_t req;
    memset(&req, 0, sizeof(req));

    char method_str[16];
    if (sscanf(raw_request, "%15s %255s %15s", method_str, req.path, req.version) != 3) {
        req.method = METHOD_UNKNOWN;
        return req;
    }

    if (strcmp(method_str, "GET") == 0) {
        req.method = METHOD_GET;
        req.is_safe = 1;
        req.is_idempotent = 1;
    } else if (strcmp(method_str, "HEAD") == 0) {
        req.method = METHOD_HEAD;
        req.is_safe = 1;
        req.is_idempotent = 1;
    } else if (strcmp(method_str, "POST") == 0) {
        req.method = METHOD_POST;
        req.is_safe = 0;
        req.is_idempotent = 0;
    } else if (strcmp(method_str, "PUT") == 0) {
        req.method = METHOD_PUT;
        req.is_safe = 0;
        req.is_idempotent = 1;
    } else if (strcmp(method_str, "DELETE") == 0) {
        req.method = METHOD_DELETE;
        req.is_safe = 0;
        req.is_idempotent = 1;
    } else if (strcmp(method_str, "PATCH") == 0) {
        req.method = METHOD_PATCH;
        req.is_safe = 0;
        req.is_idempotent = 0;
    } else if (strcmp(method_str, "OPTIONS") == 0) {
        req.method = METHOD_OPTIONS;
        req.is_safe = 1;
        req.is_idempotent = 1;
    }

    return req;
}

int main(void) {
    const char *test_lines[] = {
        "GET /api/v1/users HTTP/1.1",
        "POST /api/v1/orders HTTP/1.1",
        "PUT /api/v1/users/42 HTTP/1.1",
        "DELETE /api/v1/sessions/abc HTTP/1.1"
    };

    for (size_t i = 0; i < 4; i++) {
        parsed_request_t r = parse_http_request_line(test_lines[i]);
        printf("Request: %s\n", test_lines[i]);
        printf("  -> Path: %s | Protocol: %s\n", r.path, r.version);
        printf("  -> Safe: %s | Idempotent: %s\n\n",
               r.is_safe ? "YES" : "NO",
               r.is_idempotent ? "YES" : "NO");
    }

    return EXIT_SUCCESS;
}
```

---

## 5. Production Post-Mortem: The Google Web Accelerator GET Deletion Catastrophe

### Incident Overview
In 2005, Google launched the *Google Web Accelerator*, a client-side proxy extension designed to reduce page load latency. To accelerate navigation, the software crawled HTML documents in the background and aggressively prefetched all hyperlinks (`<a href="...">`) embedded on web pages using standard `GET` requests.

### The Architectural Failure
Thousands of contemporary web applications (vBulletin forums, custom administrative portals, CMS platforms) violated HTTP specification semantics by implementing state-mutating actions via hyperlinks:
```html
<!-- Catastrophic design pattern: Mutating state via GET -->
<a href="/admin/delete_user.php?id=102">Delete User</a>
<a href="/forum/thread.php?action=destroy&id=55">Delete Thread</a>
```

### The Destruction
1. Administrative users with the accelerator installed browsed their web applications.
2. The accelerator scanned the HTML, extracted all `href` links, and issued background HTTP `GET` requests to prefetch content.
3. The server executed the deletion scripts, assuming the administrator clicked the buttons.
4. Entire message boards, user registries, and database tables were wiped within seconds.

### The Architectural Lesson
The HTTP specification defines `GET` as **Safe**. Caches, search engine spiders, web prefetchers, and browser accelerators are legally entitled under RFC 9110 to invoke `GET` requests at will without warning. Any action that mutates server state must strictly be gated behind non-safe methods (`POST`, `PUT`, `DELETE`).
---

## 6. Safe Method Caching & Conditional Revalidation Rules

According to RFC 9110, caches are permitted to store responses to safe methods (`GET`, `HEAD`) by default unless prohibited by explicit `Cache-Control` directives.

### Automatic Invalidation of Cache on Unsafe Methods
When a non-safe HTTP method (`POST`, `PUT`, `DELETE`, `PATCH`) succeeds on a resource URI:
1. The client cache and all intermediate proxy caches **must invalidate** any stored representations of the target URI:
```text
POST /api/v1/users/42 -> Triggers Invalidation of cached GET /api/v1/users/42
```
2. Furthermore, if the response includes a `Location` or `Content-Location` header, the cache must also invalidate the secondary target URI referenced by those headers.
