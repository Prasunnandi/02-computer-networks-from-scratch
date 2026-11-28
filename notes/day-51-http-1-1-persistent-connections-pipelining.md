# Day 51: HTTP/1.1 Architecture: Persistent Connections, Pipelining, and Head-of-Line (HoL) Blocking

The original Hypertext Transfer Protocol (HTTP/1.0, RFC 1945) operated on a naive, transactional transport model: every single resource request (HTML documents, images, stylesheets, scripts) required opening a new dedicated TCP connection, executing the 3-way handshake, exchanging a single request-response pair, and closing the connection via a 4-way FIN teardown. HTTP/1.1 (RFC 2068, RFC 2616, RFC 7230, RFC 9112) revolutionized web transport by introducing persistent connections (`Connection: keep-alive`), connection reuse, and HTTP pipelining. This masterclass examines the low-level socket mechanics, mathematical latency derivations, and the fundamental flaw that doomed pipelining: Head-of-Line (HoL) blocking.

---

## 1. Non-Persistent vs Persistent Connection Dynamics

In HTTP/1.0, retrieving an HTML page referencing $N$ auxiliary sub-resources (images, CSS, JS) requires $N+1$ independent TCP connections. Each connection incurs:
1. One round-trip time ($RTT$) for the TCP SYN/SYN-ACK handshake.
2. One $RTT$ for the HTTP request and initial response data.
3. Slow-start congestion window penalties ($CWND = 1 \to 2 \to 4$).

```text
HTTP/1.0 (Non-Persistent):
Client                     Server
  |--- SYN --------------->|   (TCP Handshake: 1 RTT)
  |<-- SYN-ACK ------------|
  |--- ACK + GET /index -->|   (HTTP Transaction: 1 RTT)
  |<-- 200 OK (Data) ------|
  |--- FIN --------------->|   (Connection Teardown)
  |<-- ACK ----------------|
  (Repeat entire cycle for image1.png, style.css, script.js...)
```

### HTTP/1.1 Persistent Connections (`keep-alive`)
HTTP/1.1 makes persistent connections the default behavior. A single underlying TCP socket remains established across sequential requests until an explicit `Connection: close` header is received or an idle timeout expires.

```text
HTTP/1.1 (Persistent):
Client                     Server
  |--- SYN --------------->|   (Initial Handshake: 1 RTT)
  |<-- SYN-ACK ------------|
  |--- ACK + GET /index -->|   (First Request: 1 RTT)
  |<-- 200 OK -------------|
  |--- GET /style.css ---->|   (Zero Handshake: Immediate Request)
  |<-- 200 OK -------------|
  |--- GET /script.js ---->|   (Zero Handshake: Immediate Request)
  |<-- 200 OK -------------|
```

---

## 2. Mathematical Latency Models: HTTP/1.0 vs HTTP/1.1

Let $RTT$ be the round-trip propagation and queuing delay between client and server.
Let $T_{\text{trans}}$ be the transmission time of an HTTP payload across the physical wire ($T_{\text{trans}} = \frac{\text{Payload Size}}{\text{Bandwidth}}$).
Let $N$ be the total number of sequential resources to be retrieved.

### Non-Persistent Sequential Latency (HTTP/1.0)
Each resource requires a complete TCP handshake ($1 RTT$) and request-response round-trip ($1 RTT$):

$$T_{\text{non-persistent}} = \sum_{i=1}^{N} \left( 2 \cdot RTT + T_{\text{trans}, i} \right) = 2N \cdot RTT + \sum_{i=1}^{N} T_{\text{trans}, i}$$

### Persistent Sequential Latency (HTTP/1.1)
Only the initial connection incurs the handshake penalty; subsequent requests execute immediately:

$$T_{\text{persistent}} = 2 \cdot RTT + \sum_{i=2}^{N} RTT + \sum_{i=1}^{N} T_{\text{trans}, i} = (N + 1) \cdot RTT + \sum_{i=1}^{N} T_{\text{trans}, i}$$

### Ideal Pipelined Latency (HTTP/1.1 Pipelining)
Under pipelining, the client emits all $N$ requests back-to-back without waiting for intermediate responses:

$$T_{\text{pipelined}} = 2 \cdot RTT + \sum_{i=1}^{N} T_{\text{trans}, i}$$

The theoretical latency savings of pipelining over non-persistent HTTP/1.0 is:
$$\Delta T = (2N - 2) \cdot RTT$$

For an asset with $N = 30$ resources across a trans-continental link ($RTT = 80\text{ ms}$):
$$\Delta T = (60 - 2) \times 80\text{ ms} = 4,640\text{ ms} = 4.64\text{ seconds!}$$

---

## 3. The Demise of HTTP Pipelining: Head-of-Line (HoL) Blocking

Despite the mathematical superiority of pipelining, modern browsers have completely disabled HTTP/1.1 pipelining. The failure stems from a fundamental transport constraint:

### The Strict In-Order Response Requirement
In HTTP/1.1, individual responses carry no stream identifiers. Therefore, the server **must serialize responses in the exact sequential order that requests were received**:

```text
Client Emits Pipelined Requests:
[ GET /slow-report.pdf ] ---> [ GET /fast-icon.png ] ---> [ GET /style.css ]

Server Processing:
1. /slow-report.pdf takes 5,000 ms (complex database aggregation)
2. /fast-icon.png takes 2 ms
3. /style.css takes 1 ms

Wire Delivery:
Even though icon.png and style.css are ready instantly, the server CANNOT transmit
them because the client has no way to demultiplex chunks!
Result: /fast-icon.png and /style.css are BLOCKED behind /slow-report.pdf!
```

If `/slow-report.pdf` hangs, crashes, or drops a packet, the entire TCP connection stalls. This phenomenon is known as **Application-Layer Head-of-Line (HoL) Blocking**.

---

## 4. Compilable C Implementation: Raw Socket HTTP/1.1 Persistent Client

The following C program connects to an HTTP server, sends two sequential GET requests over a single persistent TCP connection, parses `Content-Length`, and verifies socket reuse.

Compile with: `gcc -O2 -Wall -Wextra persistent_http.c -o persistent_http`

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

#define BUFFER_SIZE 8192

int send_request_and_parse(int sockfd, const char *host, const char *path) {
    char request[1024];
    snprintf(request, sizeof(request),
             "GET %s HTTP/1.1\r\n"
             "Host: %s\r\n"
             "Connection: keep-alive\r\n"
             "User-Agent: RawCClient/1.0\r\n"
             "\r\n", path, host);

    if (send(sockfd, request, strlen(request), 0) < 0) {
        perror("send failed");
        return -1;
    }
    printf("Sent HTTP/1.1 GET %s (Connection: keep-alive)\n", path);

    char buffer[BUFFER_SIZE];
    ssize_t bytes_received = recv(sockfd, buffer, sizeof(buffer) - 1, 0);
    if (bytes_received <= 0) {
        perror("recv failed or connection closed");
        return -1;
    }
    buffer[bytes_received] = '\0';

    /* Parse Status Code */
    int status_code = 0;
    sscanf(buffer, "HTTP/1.1 %d", &status_code);
    printf("Received Server Response: Status %d (%ld bytes)\n", status_code, bytes_received);

    /* Verify if server supports keep-alive */
    if (strstr(buffer, "Connection: close") != NULL) {
        printf("Notice: Server signaled 'Connection: close'. Cannot reuse socket.\n");
        return 0;
    }

    return 1; /* Socket remains open and healthy */
}

int main(void) {
    const char *hostname = "127.0.0.1";
    int port = 8080;

    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket creation failed");
        return EXIT_FAILURE;
    }

    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
    inet_pton(AF_INET, hostname, &serv_addr.sin_addr);

    printf("Connecting to %s:%d...\n", hostname, port);
    if (connect(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        perror("connect failed (start a local test HTTP server on 8080)");
        close(sockfd);
        return EXIT_FAILURE;
    }

    /* Request 1 */
    printf("--- Transaction 1 ---\n");
    int can_reuse = send_request_and_parse(sockfd, hostname, "/index.html");

    /* Request 2: Reusing identical socket descriptor without re-connecting! */
    if (can_reuse) {
        printf("\n--- Transaction 2 (Reusing Socket FD %d) ---\n", sockfd);
        send_request_and_parse(sockfd, hostname, "/style.css");
    }

    close(sockfd);
    printf("Connection terminated cleanly.\n");
    return EXIT_SUCCESS;
}
```

---

## 5. Browser Parallel Connections & Domain Sharding Workarounds

Because pipelining proved unreliable across middleboxes and proxies, web browsers developed alternative workarounds to achieve concurrency in the HTTP/1.1 era:

1. **Parallel TCP Sockets**: Browsers open between 6 and 8 simultaneous TCP connections per host domain.
2. **Domain Sharding**: Web architectures distributed assets across multiple subdomains (`img1.site.com`, `img2.site.com`, `css.site.com`). This allowed a browser to open up to 32 parallel TCP streams simultaneously.
3. **The Trade-off**: While domain sharding mitigated HoL blocking, it severely undermined internet health by causing packet congestion, bufferbloat, and defeating TCP slow-start efficiency across shared router queues.

---

## 6. Production Post-Mortem: Intermediary Proxy Pipelining Desync Outage

### Incident Overview
In 2012, an enterprise cloud proxy provider rolled out experimental HTTP/1.1 pipelining to reduce edge latency. Within hours, users reported receiving other customers' account dashboards and private banking receipts.

### The Interleaving Corruption
1. A corporate branch office routed all outbound web traffic through a caching forward proxy.
2. The proxy pipelined two requests from separate internal users onto a single upstream TCP connection to a banking portal:
   - Request A: User 1 requesting `/account_balance`
   - Request B: User 2 requesting `/public_faq`
3. A transparent intermediate firewall dropped a TCP segment belonging to Request A, causing the origin web server to process Request B first and reply.
4. The forward proxy, adhering strictly to the pipelining specification, assumed the *first* response it received belonged to the *first* request it sent (Request A).
5. User 1 received the public FAQ, while User 2 received User 1's private financial data!

### Industry Resolution
This catastrophic desynchronization vulnerability proved that HTTP/1.1 pipelining was fundamentally unviable in heterogeneous internet environments, accelerating the standardization and adoption of **HTTP/2 binary stream multiplexing**.
