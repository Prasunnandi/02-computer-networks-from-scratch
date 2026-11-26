# Day 31: DNS Hierarchy Walker & Referral Chaser

## 1. What Are We Building & Why Does It Matter?
When you type a web address into your browser, your computer does not know how to find it directly. There is no single server on Earth that holds every website's IP address. Instead, the global Domain Name System (DNS) is arranged like an inverted tree:
- **Root Servers (`.`)**: Know which servers manage top-level domains like `.com`, `.org`, and `.edu`.
- **Top-Level Domain (TLD) Servers**: Know which authoritative nameservers manage second-level domains like `example.com`.
- **Authoritative Nameservers**: Hold the actual IP addresses (A records) for hostnames.

In this lab, we build a **DNS Hierarchy Walker** in pure Python. It simulates iterative DNS resolution: asking the Root server, receiving a referral to the TLD, asking the TLD, and finally obtaining the authoritative IP address.

---

## 2. Python Concepts for Beginners

### A. Python Dictionaries for In-Memory Routing
A dictionary (`dict`) maps keys to values using curly braces `{}`. We use dictionaries to simulate nameserver directories:
```python
referrals = {
    ".com.": "192.5.6.30",
    ".org.": "199.19.56.1"
}
target_ip = referrals.get(".com.")  # Returns "192.5.6.30"
```

### B. Python `dataclasses`
Instead of writing boilerplate `__init__` methods, `@dataclass` automatically creates constructors:
```python
from dataclasses import dataclass

@dataclass
class DNSRecord:
    name: str
    record_type: str
    value: str
    ttl: int = 300
```

### C. While Loops and State Transitions
An iterative resolver repeats queries in a `while True:` loop, updating its `current_server_ip` whenever it receives a delegation referral, terminating only when it hits an answer or NXDOMAIN.

---

## 3. Step-by-Step Code Walkthrough

1. **`DNSRecord` Dataclass**: Represents an individual DNS Resource Record (e.g., domain name, record type `A`, IP address, and Time-To-Live).
2. **`NameserverZone` Class**: Simulates an individual DNS nameserver. Its `query()` method inspects its records; if found, it returns `ANSWER`. If a subzone delegation exists, it returns `REFERRAL` with the next IP address.
3. **`DNSHierarchySimulator` Class**: Bootstraps three levels of the Internet:
   - Root Server (`198.41.0.4`) pointing `.com.` to `192.5.6.30`.
   - TLD Server (`192.5.6.30`) pointing `example.com.` to `208.67.222.222`.
   - Authoritative Server (`208.67.222.222`) storing `93.184.216.34`.
4. **`resolve_iterative(target_domain)`**: Executes the hop-by-hop walking process, logging each step to stdout.
5. **`main()` Function**: Runs automated test cases resolving apex domains, subdomains, and invalid names.

---

## 4. How to Run & Expected Output

Run the script from your terminal:
```bash
python 02-computer-networks-from-scratch/code/day-31/dns_hierarchy_walker.py
```

Expected output:
```text
====================================================
DAY 31: DNS HIERARCHY WALKER & REFERRAL CHASER
====================================================
[*] Starting Iterative Resolution for: example.com. (Type: A)
  Step 1: Querying . at IP 198.41.0.4...
  [->] Referral Delegation to .com. at IP 192.5.6.30
  Step 2: Querying .com. at IP 192.5.6.30...
  [->] Referral Delegation to example.com. at IP 208.67.222.222
  Step 3: Querying example.com. at IP 208.67.222.222...
  [+] Final Answer Received from example.com.!
      -> example.com.  TTL=86400  IN A  93.184.216.34
  [PASS] Test 1: example.com resolved successfully.
...
[VERIFIED] DNS Hierarchy Walker passed all tests with 100% fidelity!
```

---

## 5. Common Python Errors & Troubleshooting

- **`KeyError: 'target_ns'`**: Occurs if a dictionary key lookup `dict['key']` fails. Always verify dictionary keys exist or use `dict.get('key')`.
- **Infinite Loop**: If a referral points back to the same server, a `while True:` loop never terminates. Production resolvers use a maximum hop limit (e.g., 16 hops).
- **Trailing Dot Confusion**: In DNS, a Fully Qualified Domain Name (FQDN) ends with a dot (`example.com.`). If forgotten, string matches may fail. Our code sanitizes names with `fqdn = domain if domain.endswith('.') else domain + '.'`.

---

## 6. Beginner Exercises & Challenges

1. **Add a Country Code TLD (ccTLD)**: Add a referral for `.uk.` to the root server and create an authoritative server for `bbc.co.uk.`.
2. **Hop Counter**: Add a `max_hops = 10` counter to `resolve_iterative()` that raises a `RuntimeError` if an infinite delegation loop is detected.
3. **Query Types**: Add support for querying `NS` or `MX` records by passing `qtype="NS"` into the resolver.\n