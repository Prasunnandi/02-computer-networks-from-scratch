"""
Day 51: HTTP/1.1 Persistent Connection & Pipelining Simulator
100% pure Python standard library implementation of HTTP/1.1 persistent connections,
keep-alive timeout management, request pipelining, and Head-of-Line (HoL) blocking analysis.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional, Tuple


@dataclass
class HTTPRequest:
    request_id: int
    method: str
    path: str
    headers: Dict[str, str] = field(default_factory=dict)
    processing_time_sec: float = 0.01  # Simulated server execution latency


@dataclass
class HTTPResponse:
    request_id: int
    status_code: int
    headers: Dict[str, str]
    body: str
    completion_timestamp: float


class HTTP11Connection:
    """Simulates an HTTP/1.1 persistent TCP socket handling sequential and pipelined flows."""

    def __init__(self, keep_alive_timeout: float = 5.0, max_requests: int = 100):
        self.keep_alive_timeout = keep_alive_timeout
        self.max_requests = max_requests
        self.is_open = True
        self.requests_served = 0
        self.last_activity = time.time()
        # Simulated socket buffer for pipelining
        self.pipelined_queue: List[HTTPRequest] = []

    def send_request_sequential(self, req: HTTPRequest, current_time: float) -> Optional[HTTPResponse]:
        """Executes standard persistent HTTP/1.1 sequential request."""
        if not self.is_open:
            return None
        if (current_time - self.last_activity) > self.keep_alive_timeout:
            self.is_open = False
            return None

        self.requests_served += 1
        self.last_activity = current_time + req.processing_time_sec

        headers = {"Content-Type": "text/plain", "Connection": "keep-alive"}
        if self.requests_served >= self.max_requests or req.headers.get("Connection") == "close":
            self.is_open = False
            headers["Connection"] = "close"

        return HTTPResponse(
            request_id=req.request_id,
            status_code=200,
            headers=headers,
            body=f"Response for {req.path}",
            completion_timestamp=self.last_activity
        )

    def enqueue_pipelined_request(self, req: HTTPRequest):
        """Buffers pipelined requests emitted back-to-back without waiting for responses."""
        if self.is_open:
            self.pipelined_queue.append(req)

    def process_pipelined_stream(self, start_time: float) -> List[HTTPResponse]:
        """
        Processes pipelined requests in strict FIFO order, demonstrating
        Application-Layer Head-of-Line (HoL) blocking.
        """
        responses: List[HTTPResponse] = []
        clock = start_time

        for req in self.pipelined_queue:
            # Server must complete and transmit in exact sequential order
            clock += req.processing_time_sec
            resp = HTTPResponse(
                request_id=req.request_id,
                status_code=200,
                headers={"Connection": "keep-alive"},
                body=f"Data for {req.path}",
                completion_timestamp=clock
            )
            responses.append(resp)

        self.pipelined_queue.clear()
        self.last_activity = clock
        return responses


def main():
    print("=== Day 51: HTTP/1.1 Persistent Connection & Pipelining Simulator ===")

    now = 1000.0
    conn = HTTP11Connection(keep_alive_timeout=5.0, max_requests=10)

    # Test 1: Sequential persistent connection reuse
    req1 = HTTPRequest(request_id=1, method="GET", path="/index.html")
    resp1 = conn.send_request_sequential(req1, now)
    assert resp1 is not None
    assert resp1.status_code == 200
    assert resp1.headers["Connection"] == "keep-alive"
    assert conn.is_open is True
    print(f"[*] Test 1 Passed: First request completed on persistent connection (Socket Open)")

    # Test 2: Second request reusing identical connection at t+2s
    req2 = HTTPRequest(request_id=2, method="GET", path="/style.css")
    resp2 = conn.send_request_sequential(req2, now + 2.0)
    assert resp2 is not None
    assert conn.requests_served == 2
    print(f"[*] Test 2 Passed: Second request reused socket at t+2s without new TCP handshake")

    # Test 3: Idle timeout closes connection
    req3 = HTTPRequest(request_id=3, method="GET", path="/script.js")
    resp3 = conn.send_request_sequential(req3, now + 10.0)  # Exceeds 5.0s timeout
    assert resp3 is None
    assert conn.is_open is False
    print("[*] Test 3 Passed: Idle timeout successfully terminated persistent socket")

    # Test 4: Head-of-Line (HoL) Blocking in Pipelining
    pipe_conn = HTTP11Connection()
    # Request A is a slow database query taking 2.0 seconds
    slow_req = HTTPRequest(request_id=101, method="GET", path="/slow-report.pdf", processing_time_sec=2.0)
    # Request B and C are fast static assets taking only 0.01 seconds
    fast_req1 = HTTPRequest(request_id=102, method="GET", path="/logo.png", processing_time_sec=0.01)
    fast_req2 = HTTPRequest(request_id=103, method="GET", path="/app.js", processing_time_sec=0.01)

    pipe_conn.enqueue_pipelined_request(slow_req)
    pipe_conn.enqueue_pipelined_request(fast_req1)
    pipe_conn.enqueue_pipelined_request(fast_req2)

    responses = pipe_conn.process_pipelined_stream(start_time=now)
    assert len(responses) == 3
    # Fast requests are blocked behind the slow request:
    assert responses[0].completion_timestamp == now + 2.0
    assert responses[1].completion_timestamp == now + 2.01
    assert responses[2].completion_timestamp == now + 2.02
    print(f"[*] Test 4 Passed: HoL blocking demonstrated: Fast asset (/logo.png) stalled until t={responses[1].completion_timestamp}s")

    print("All HTTP/1.1 Persistent Connection assertions passed successfully!")


if __name__ == "__main__":
    main()
