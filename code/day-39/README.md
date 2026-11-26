# Day 39: DNSSEC Cryptographic Trust Chain Validator

## 1. What Are We Building & Why Does It Matter?
DNS was originally designed without authentication: any attacker capable of spoofing UDP packets could inject fake IP addresses into recursive caches.
**DNSSEC (Domain Name System Security Extensions)** solves this by adding public-key cryptography to DNS:
1. **RRSIG (Resource Record Signature)**: Every record set (RRset) is digitally signed by a private key.
2. **DNSKEY**: Nameservers publish their public keys:
   - **ZSK (Zone Signing Key)**: Signs individual domain records.
   - **KSK (Key Signing Key)**: Signs the ZSK to prove key authenticity.
3. **DS (Delegation Signer)**: The parent zone (e.g. `.com`) publishes a cryptographic hash of the child zone's KSK, establishing a continuous **Chain of Trust** up to the Root Trust Anchor.

In this lab, we build a **DNSSEC Chain Validator** in pure Python using standard library cryptographic hashing (`hashlib`) to verify signatures and detect record tampering.

---

## 2. Python Concepts for Beginners

### A. Cryptographic Hashes with `hashlib`
A cryptographic hash function converts arbitrary data into a fixed-length hexadecimal fingerprint:
```python
import hashlib
data = b"example.com. IN A 93.184.216.34"
digest = hashlib.sha256(data).hexdigest()  # 64-char hex string
```

### B. Timing-Attack Safe Comparison (`hmac.compare_digest`)
When comparing cryptographic signatures or hashes, using standard `==` can leak information through timing variations. Python provides `hmac.compare_digest(a, b)` for constant-time comparison.

### C. Class Properties for Bitflags
In DNSKEY records, flag `257` represents a KSK, while `256` represents a ZSK:
```python
@property
def is_ksk(self) -> bool:
    return self.flags == 257
```

---

## 3. Step-by-Step Code Walkthrough

1. **`DNSKEY` & `DSRecord` Dataclasses**: Represent public keys and parent delegation records.
2. **`compute_ds_digest()`**: Takes a child's public key and computes the SHA-256 fingerprint stored by the parent zone.
3. **`verify_rrsig()`**: Validates that an incoming record matches its attached cryptographic signature.
4. **`main()` Function**:
   - Initializes Root Trust Anchor.
   - Validates `.com` KSK against the parent DS record.
   - Validates the signature for `example.com A 93.184.216.34`.
   - Tests tampering detection: alters the IP to `6.6.6.6` and asserts that verification fails.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-39/dnssec_trust_chain_sim.py
```

Expected output:
```text
====================================================
DAY 39: DNSSEC CRYPTOGRAPHIC TRUST CHAIN VALIDATOR
====================================================
1. Root Trust Anchor KSK Initialized:
   Root DS Digest: e7b204...
2. Chain Link Validated: Root DS matches .com KSK digest!
3. Record Authenticity Validated: RRSIG for 'example.com. IN A 93.184.216.34' is cryptographically VALID!
4. Security Tamper Test: Spoofed record correctly REJECTED (BOGUS)!

[VERIFIED] DNSSEC Trust Chain Validator passed all cryptographic checks!
```

---

## 5. Common Python Errors & Troubleshooting

- **`TypeError: Unicode-objects must be encoded before hashing`**: `hashlib.sha256()` requires raw `bytes`, not Python strings. Always call `.encode('utf-8')`.
- **DNSSEC "Bogus" State**: In DNSSEC, if signature verification fails, the resolver flags the domain as `BOGUS` and returns `SERVFAIL` to the user rather than delivering forged data.

---

## 6. Beginner Exercises & Challenges

1. **Signature Inception & Expiration**: Add a check that verifies the current time is between `sig_inception` and `sig_expiration`.
2. **Key Tag Computation**: Implement the RFC 4034 Key Tag algorithm (16-bit checksum over the RDATA of the DNSKEY).
3. **NSEC Simulation**: Research and implement a mock `NSEC` record proving that a domain name does *not* exist without leaking the entire zone.
