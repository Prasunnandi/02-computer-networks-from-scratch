#!/usr/bin/env python3
"""
Day 38 Lab: DNS Cache Poisoning & Kaminsky Vulnerability Simulator
Demonstrates the mathematics behind the classic 2008 Dan Kaminsky attack:
explaining how predictable transaction IDs and static UDP source ports allow
an attacker to poison recursive caches via random subdomain baiting, and
how RFC 5452 UDP source port randomization defeats it.
Uses Python standard library only.
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, Tuple, Optional


class KaminskyAttackSimulator:
    """Simulates cache poisoning attack complexity with and without source port randomization."""

    TOTAL_TXIDS = 65536         # 16-bit Transaction ID space (2^16)
    STATIC_PORTS = 1            # Legacy UDP: fixed port 53
    RANDOM_PORTS = 60000        # RFC 5452: ephemeral port pool (~60,000 available ports)

    @staticmethod
    def calculate_attack_probability(num_spoofed_packets: int, use_port_randomization: bool) -> float:
        """
        Calculates probability of attacker successfully guessing the correct
        (TxID, SourcePort) pair for a single pending recursive query.
        Formula: P = 1 - (1 - 1/N)^k where N is entropy search space.
        """
        if use_port_randomization:
            entropy_space = KaminskyAttackSimulator.TOTAL_TXIDS * KaminskyAttackSimulator.RANDOM_PORTS  # ~3.93 x 10^9
        else:
            entropy_space = KaminskyAttackSimulator.TOTAL_TXIDS * KaminskyAttackSimulator.STATIC_PORTS   # 65,536

        if num_spoofed_packets >= entropy_space:
            return 1.0

        # Approximation: P ≈ k / N
        prob = num_spoofed_packets / entropy_space
        return min(1.0, prob)

    @staticmethod
    def simulate_attack_run(use_port_randomization: bool, max_guesses_per_probe: int = 100, attempts: int = 20) -> Tuple[int, bool]:
        """
        Simulates an attacker firing random subdomain bait queries (e.g. sub1.example.com, sub2.example.com)
        and blasting forged responses with random TxIDs and ports.
        """
        victim_txid = random.randint(0, 65535)
        victim_port = random.randint(1024, 65535) if use_port_randomization else 53

        for probe_num in range(1, attempts + 1):
            # Target regenerates for each query attempt
            target_txid = random.randint(0, 65535)
            target_port = random.randint(1024, 65535) if use_port_randomization else 53

            # Attacker blasts max_guesses_per_probe forged packets
            for _ in range(max_guesses_per_probe):
                guess_txid = random.randint(0, 65535)
                guess_port = random.randint(1024, 65535) if use_port_randomization else 53

                if guess_txid == target_txid and guess_port == target_port:
                    return probe_num, True  # Poisoned successfully!

        return attempts, False


def main():
    print("====================================================")
    print("DAY 38: DNS CACHE POISONING & KAMINSKY BUG SIMULATOR")
    print("====================================================")

    # 1. Mathematical Entropy Comparison
    legacy_entropy = KaminskyAttackSimulator.TOTAL_TXIDS * KaminskyAttackSimulator.STATIC_PORTS
    modern_entropy = KaminskyAttackSimulator.TOTAL_TXIDS * KaminskyAttackSimulator.RANDOM_PORTS

    print(f"1. Entropy Comparison:")
    print(f"   Legacy DNS (Fixed Port 53) Search Space : {legacy_entropy:,} states (~16 bits)")
    print(f"   RFC 5452 (Port Randomization) Space     : {modern_entropy:,} states (~32 bits)")

    # 2. Probability with 1,000 forged packets per query
    p_legacy = KaminskyAttackSimulator.calculate_attack_probability(1000, use_port_randomization=False)
    p_modern = KaminskyAttackSimulator.calculate_attack_probability(1000, use_port_randomization=True)

    print(f"\n2. Poisoning Probability per Probe (1,000 forged responses):")
    print(f"   Legacy (No Port Randomization) : {p_legacy * 100:.2f}%")
    print(f"   Modern (RFC 5452 Hardened)     : {p_modern * 100:.6f}%")

    assert p_legacy > 0.01  # > 1.5% chance per attempt!
    assert p_modern < 0.00001  # Virtually impossible without billions of packets

    # 3. Simulate Kaminsky Attack Simulation
    print(f"\n3. Running Simulated Attack against Modern Resolver (20 probes, 500 guesses/probe)...")
    probes, poisoned = KaminskyAttackSimulator.simulate_attack_run(use_port_randomization=True, max_guesses_per_probe=500, attempts=20)
    print(f"   Result: Poisoned={poisoned} after {probes} probes.")
    assert poisoned is False, "Modern port-randomized resolver should resist small-scale spoofing!"
    print("   [PASS] Port randomization successfully thwarted cache poisoning attempt.")

    print("\n[VERIFIED] Kaminsky Attack Simulator passed all mathematical assertions!")


if __name__ == "__main__":
    main()
