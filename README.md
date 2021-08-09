# Pyttern

Simple ans stupid pattern matching for Python

## Usage

With the decorator `@pyttern`, you can do pattern matching easily with:

```python
@pyttern
def pat(a, b): {
  (1, 2): a,
  (3, 4): b,
  (_1, 5): _1 * 5,
  _ : 100,
}

pat(1, 2) => 1
pat(3, 4) => 4
pat(10, 5) => 50
pat(0, 0) => 100
```

For a more complex example, check out: [Tick](tests/tick.py)
