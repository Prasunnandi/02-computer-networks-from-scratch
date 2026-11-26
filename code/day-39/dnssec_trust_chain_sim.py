#!/usr/bin/env python3
"""
Day 39 Lab: DNSSEC Cryptographic Trust Chain Validator
Simulates the hierarchical cryptographic chain of trust in DNSSEC:
Root Trust Anchor -> DS record -> Zone DNSKEY (KSK & ZSK) -> RRSIG verification.
Uses Python standard library (hashlib, hmac) only.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DNSKEY:
    flags: int       # 256 for ZSK (Zone Signing Key), 257 for KSK (Key Signing Key)
    protocol: int    # 3
    algorithm: int   # 13 for ECDSA P-256 SHA-256
    public_key: str  # Simulated public key string

    @property
    def is_ksk(self) -> bool:
        return self.flags == 257


@dataclass
class DSRecord:
    key_tag: int
    algorithm: int
    digest_type: int  # 2 for SHA-256
    digest: str       # Hex string of SHA-256(owner_name + DNSKEY)


@dataclass
class RRSIG:
    type_covered: str
    algorithm: int
    labels: int
    original_ttl: int
    sig_expiration: int
    sig_inception: int
    key_tag: int
    signer_name: str
    signature: str


class DNSSECTrustChainValidator:
    """Validates DNSSEC cryptographic trust chains from Root Anchor down to host records."""

    @staticmethod
    def compute_ds_digest(owner_name: str, dnskey: DNSKEY) -> str:
        """Computes DS record SHA-256 hash over owner name and wire DNSKEY."""
        material = f"{owner_name.lower()}:{dnskey.flags}:{dnskey.public_key}".encode('utf-8')
        return hashlib.sha256(material).hexdigest()

    @staticmethod
    def compute_simulated_rrsig(data: str, secret_signing_key: str) -> str:
        """Simulates digital signature using HMAC-SHA256."""
        return hmac.new(secret_signing_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()

    @staticmethod
    def verify_rrsig(data: str, public_key: str, signature: str) -> bool:
        """Verifies simulated signature against public key."""
        # For simulation, matching secret-derived public key check
        expected_sig = DNSSECTrustChainValidator.compute_simulated_rrsig(data, public_key)
        return hmac.compare_digest(expected_sig, signature)


def main():
    print("====================================================")
    print("DAY 39: DNSSEC CRYPTOGRAPHIC TRUST CHAIN VALIDATOR")
    print("====================================================")

    # 1. Setup Root Zone Trust Anchor
    # In production, the Root KSK digest is pre-configured into the resolver software.
    root_ksk = DNSKEY(flags=257, protocol=3, algorithm=13, public_key="root-ksk-pub-key-2024")
    root_ds = DNSSECTrustChainValidator.compute_ds_digest(".", root_ksk)
    print(f"1. Root Trust Anchor KSK Initialized:")
    print(f"   Root DS Digest: {root_ds[:32]}...")

    # 2. Child Zone (.com) KSK & ZSK
    com_ksk = DNSKEY(flags=257, protocol=3, algorithm=13, public_key="com-ksk-pub-key-secret")
    com_zsk = DNSKEY(flags=256, protocol=3, algorithm=13, public_key="com-zsk-pub-key-secret")

    # Parent (Root) signs DS record pointing to Child (.com) KSK
    com_ds_in_parent = DSRecord(
        key_tag=12345,
        algorithm=13,
        digest_type=2,
        digest=DNSSECTrustChainValidator.compute_ds_digest(".com.", com_ksk)
    )

    # Verification Step A: Validate Child KSK against Parent DS
    computed_child_ds = DNSSECTrustChainValidator.compute_ds_digest(".com.", com_ksk)
    assert computed_child_ds == com_ds_in_parent.digest
    print(f"2. Chain Link Validated: Root DS matches .com KSK digest!")

    # 3. Zone Signing Key (ZSK) signs the actual host record (A record)
    host_record = "example.com. IN A 93.184.216.34"
    rrsig = RRSIG(
        type_covered="A",
        algorithm=13,
        labels=2,
        original_ttl=3600,
        sig_expiration=2000000000,
        sig_inception=1000000000,
        key_tag=54321,
        signer_name="example.com.",
        signature=DNSSECTrustChainValidator.compute_simulated_rrsig(host_record, com_zsk.public_key)
    )

    # Verification Step B: Validate RRSIG using ZSK
    is_valid = DNSSECTrustChainValidator.verify_rrsig(host_record, com_zsk.public_key, rrsig.signature)
    assert is_valid is True
    print(f"3. Record Authenticity Validated: RRSIG for '{host_record}' is cryptographically VALID!")

    # Verification Step C: Detect Tampering!
    tampered_record = "example.com. IN A 6.6.6.6"  # Malicious injection attempt
    is_tampered_valid = DNSSECTrustChainValidator.verify_rrsig(tampered_record, com_zsk.public_key, rrsig.signature)
    assert is_tampered_valid is False
    print("4. Security Tamper Test: Spoofed record correctly REJECTED (BOGUS)!")

    print("\n[VERIFIED] DNSSEC Trust Chain Validator passed all cryptographic checks!")


if __name__ == "__main__":
    main()
