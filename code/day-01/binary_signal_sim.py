"""
Day 01 Lab: Binary Signal Simulator & Base Conversion
Demonstrates manual base conversion and Shannon Channel Capacity.
"""
import math
from binary_hex_converter import int_to_binary_manual, int_to_hex_manual, main as converter_main

def shannon_channel_capacity(bandwidth_hz: float, snr_linear: float) -> float:
    """
    Computes Shannon-Hartley theorem: C = B * log2(1 + S/N)
    """
    return bandwidth_hz * math.log2(1.0 + snr_linear)

if __name__ == "__main__":
    converter_main()
    print("\n--- Shannon Channel Capacity Proof ---")
    bw = 3000.0 # 3 kHz telephone line
    snr = 1000.0 # 30 dB SNR
    cap = shannon_channel_capacity(bw, snr)
    print(f"Bandwidth: {bw} Hz, SNR: {snr} -> Max Theoretical Capacity: {cap:.2f} bps")
