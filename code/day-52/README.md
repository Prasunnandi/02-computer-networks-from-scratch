# Day 52: HTTP Method Semantics & Idempotency Lab Tutorial

Welcome to Day 52 of Computer Networks from Scratch. Today, you will build an HTTP method evaluation and REST state mutation engine, formalizing the mathematical properties of Safety and Idempotency under RFC 7231 and RFC 9110.

---

## 1. What Are We Building & Why Does It Matter?

In distributed network systems, packet drops and connection timeouts are inevitable. When a client does not receive an HTTP response, it must decide: *Is it safe to automatically retransmit the request?*

The answer depends strictly on the HTTP Method:
- **Safety**: $f(S) = S$. The method performs read-only operations and does not alter server state (`GET`, `HEAD`, `OPTIONS`).
- **Idempotency**: $f(f(S)) = f(S)$. Executing the method multiple times produces the identical server state as executing it once (`GET`, `PUT`, `DELETE`).
- **Non-Idempotent**: Executing the request multiple times creates duplicate side effects (e.g. charging a credit card twice with `POST`).

In this lab, you implement this validation logic and automated retry safety checks.

---

## 2. Python Concepts for Beginners

### A. Python Enumerations (`enum.Enum`)
Restricting methods to the standardized RFC 7231 set:
```python
import enum

class HTTPMethod(enum.Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
```

### B. Python Sets for Group Classification
Fast $O(1)$ membership checking for semantic attributes:
```python
SAFE_METHODS = {HTTPMethod.GET, HTTPMethod.HEAD, HTTPMethod.OPTIONS}
if method in SAFE_METHODS:
    print("Method is safe to execute without state changes")
```

### C. Dictionary Copying (`dict()`)
Ensure state mutations do not share references with the input caller object:
```python
self.database[key] = dict(new_data)
```

---

## 3. Step-by-Step Code Walkthrough

1. **`HTTPMethod` Enum**: Defines the 7 standard HTTP methods.
2. **`ResourceStore` Class**:
   - `get()`: Safe read-only lookup.
   - `put()`: Idempotent full entity replacement.
   - `delete()`: Idempotent entity removal.
   - `post()`: Non-idempotent list append.
3. **`HTTPMethodEngine` Class**:
   - `is_safe()` & `is_idempotent()`: Evaluates methods against formal RFC sets.
   - `execute_with_retries()`: Enforces network safety. If a method is non-idempotent (`POST`) and `attempts > 1`, the engine raises a security alert and rejects execution.
4. **`main()` Test Suite**: Validates mathematical classifications, PUT multi-execution idempotency, DELETE idempotency, and automated retry suppression for POST.

---

## 4. How to Run & Expected Output

Run the script from your terminal using Python 3:
```bash
python code/day-52/http_method_idempotency_matrix.py
```

Expected output:
```text
=== Day 52: HTTP Method Semantics & Idempotent Mutation Engine ===
[*] Test 1 Passed: Safety and Idempotency mathematical classifications verified
[*] Test 2 Passed: PUT executed 5 times maintains identical state: {'name': 'Alice', 'role': 'Senior Engineer'}
[*] Test 3 Passed: DELETE executed 3 times leaves resource deleted
[*] Test 4 Passed: Non-idempotent POST retries rejected: SECURITY ALERT: Automated retries forbidden for non-idempotent method!
[*] Test 5 Passed: Single POST mutation executed cleanly: {'items': [{'item': 'Laptop'}]}
All HTTP Method Semantics assertions passed successfully!
```

---

## 5. Common Python Errors & Troubleshooting

- **Conflating PUT and PATCH**: Remember that `PUT` replaces the entire resource entity, whereas `PATCH` applies partial delta mutations.
- **Reference Mutation Bugs**: Always store copies of dictionaries (`dict(payload)`) to prevent callers from mutating database records after insertion.

---

## 6. Beginner Exercises & Challenges

1. **Implement PATCH Delta Mutations**: Add a `patch()` method to `ResourceStore` that updates only specified keys without wiping unspecified fields.
2. **Add Idempotency-Key Header Support**: Implement payment gateway style idempotency keys where unique tokens allow `POST` requests to be safely retried.
3. **Simulate Network Failure Simulation**: Add a simulated random network drop parameter that triggers retries only when network errors occur.
