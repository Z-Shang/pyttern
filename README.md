# Pyttern

Simple ans stupid pattern matching for Python

## Usage
With the decorator `@pyttern`, you can do pattern matching easily with:
```python
@pyttern
def pat(a, b): {
  (1, 2): a,
  (3, 4): b
}

pat(1, 2) => 1
pat(3, 4) => 4
```

