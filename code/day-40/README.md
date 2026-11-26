# Day 40: Encrypted DNS: DoT Framing & DoH HTTP/2 Codec

## 1. What Are We Building & Why Does It Matter?
Traditional DNS queries travel in plain text across the Internet over UDP port 53. This allows local Wi-Fi eavesdroppers, Internet Service Providers (ISPs), and repressive nation-state firewalls to spy on every website you visit or redirect queries to censorship portals.
To protect user privacy and confidentiality, the IETF developed two modern encrypted transport standards:
1. **DNS-over-TLS (DoT - RFC 7858)**: Encapsulates DNS queries inside a secure TLS tunnel over dedicated port 853. Because TCP is a stream, each DNS message is framed by prepending a 2-byte big-endian length prefix.
2. **DNS-over-HTTPS (DoH - RFC 8484)**: Transports DNS queries inside HTTP/2 or HTTP/3 sessions over standard HTTPS port 443 using the MIME type `application/dns-message`. Because it blends into regular HTTPS web traffic, it cannot be selectively blocked by port inspection.

In this lab, we build an **Encrypted DNS Codec** in pure Python that frames DoT streams and formats DoH HTTP requests.

---

## 2. Python Concepts for Beginners

### A. Stream Framing (Length Prefixes)
In TCP/TLS streams, multiple messages can arrive merged together or split across packets. Prepending a 2-byte length allows the receiver to buffer bytes until the complete message arrives:
```python
import struct
data = b"hello"
framed = struct.pack("!H", len(data)) + data  # [0x00, 0x05, 'h', 'e', 'l', 'l', 'o']
```

### B. Base64url Encoding without Padding
RFC 8484 specifies that DoH GET queries use URL-safe Base64 (`base64.urlsafe_b64encode`) with trailing `=` padding stripped:
```python
import base64
encoded = base64.urlsafe_b64encode(raw_bytes).decode('ascii').rstrip('=')
```

### C. Restoring Base64 Padding
When decoding base64 in Python, missing padding causes an `binascii.Error`. We restore padding using modulo arithmetic:
```python
padded = encoded + '=' * ((4 - len(encoded) % 4) % 4)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`frame_dot_message()`**: Takes raw DNS wire bytes and prepends the 16-bit length prefix (`!H`).
2. **`unframe_dot_stream()`**: Inspects a stream buffer; if at least 2 bytes are present, reads the length and extracts the full message.
3. **`encode_doh_get_url()`**: Formats an RFC 8484 compliant HTTPS URL with base64url query parameter.
4. **`decode_doh_get_param()`**: Recovers the binary wire bytes from a URL query parameter.
5. **`build_doh_post_headers()`**: Returns HTTP headers with MIME type `application/dns-message`.
6. **`main()` Function**: Validates DoT framing and DoH encoding with 100% round-trip fidelity.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-40/doh_dot_client_sim.py
```

Expected output:
```text
====================================================
DAY 40: ENCRYPTED DNS (DoT & DoH CODEC)
====================================================
1. DNS-over-TLS (DoT):
   Original Size: 12B -> Framed Size: 14B
   [PASS] DoT stream framing & unframing verified with 100% fidelity.

2. DNS-over-HTTPS (DoH) GET Request:
   URL: mock://doh.internal.resolver/resolve?dns=q80BAAABAAAAAAAA
   [PASS] DoH GET base64url roundtrip verified without padding.

3. DNS-over-HTTPS (DoH) POST Headers:
   Headers: {'Content-Type': 'application/dns-message', 'Accept': 'application/dns-message', 'Content-Length': '12'}
   [PASS] DoH POST binary MIME type verified (application/dns-message).

[VERIFIED] Encrypted DNS Codec passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`binascii.Error: Incorrect padding`**: Occurs if base64url string lacks required padding when passed to `urlsafe_b64decode()`. Our helper automatically restores padding.
- **DoT Stream Fragmentation**: If network packets arrive partially, `unframe_dot_stream()` returns `b""` and `0` bytes consumed until more data arrives.

---

## 6. Beginner Exercises & Challenges

1. **Stream Accumulator**: Write a buffer loop that handles receiving a fragmented DoT stream where only 1 byte arrives in the first chunk and the rest in the second.
2. **DoH POST Payload Builder**: Write a function that packages the binary DNS query into a mock HTTP POST request body.
3. **Oblivious DoH (ODoH)**: Research RFC 9230 (Oblivious DoH) and diagram how proxy relays separate client IP addresses from query contents.
