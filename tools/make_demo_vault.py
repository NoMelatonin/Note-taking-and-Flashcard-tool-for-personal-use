"""Create an isolated example inside work/; never overwrite an existing demo."""

from pathlib import Path
import struct
import zlib


def create_demo_vault(destination: Path | None = None) -> Path:
    root = Path(__file__).resolve().parents[1]
    destination = destination or root / "work" / "demo-vault"
    destination = destination.resolve()
    if not destination.is_relative_to(root / "work"):
        raise ValueError("Demo vaults must be inside this repository's ignored work/.")
    if destination.exists():
        return destination  # A user's experiments in the demo are preserved.
    (destination / "Ideas" / "Small steps").mkdir(parents=True)
    (destination / "Reading").mkdir()
    (destination / "assets").mkdir()
    (destination / "Welcome.md").write_text("""# A little room for your thoughts

Welcome to **Bluebell**. Your notes are ordinary Markdown files.

## Make yourself at home

- Choose a folder on the left.
- Create a note with **New note**.
  - Give ideas space to grow.
- [x] Open a local vault
- [ ] Write your first thought

1. Write in **Edit**.
2. Settle into **Read**.

> Small thoughts are worth keeping.

Try [[Ideas/First thought|your first thought]], or a [relative link](Reading/Book.md).

| A quiet habit | A little benefit |
| --- | --- |
| Write freely | Find clarity |
| Link your notes | Follow a thread |

Use `inline code`, *italics* and ~~a change of mind~~.

```python
thought = "Start small"
print(thought)
```

---

![A soft blue landscape](assets/landscape.png)

An external [Qt documentation link](https://doc.qt.io/) opens only when clicked.
""", encoding="utf-8")
    (destination / "Ideas" / "First thought.md").write_text("# First thought\n\nA small beginning. Back to [[Welcome]].\n", encoding="utf-8")
    (destination / "Ideas" / "Small steps" / "Grüße.md").write_text("# Grüße\n\nSpaces and Unicode names work here.\n", encoding="utf-8")
    (destination / "Reading" / "Book.md").write_text("# Book notes\n\nWhat stayed with you?\n\n[Home](../Welcome.md)\n", encoding="utf-8")
    (destination / "preserve.txt").write_text("This non-Markdown file stays untouched.\n", encoding="utf-8")
    width, height = 440, 110
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            colour = (212, 232, 245) if y < 65 + 14 * ((x // 40) % 2) else (137, 174, 197)
            rows.extend(colour)
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    image = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b"")
    (destination / "assets" / "landscape.png").write_bytes(image)
    return destination


if __name__ == "__main__":
    print(create_demo_vault())
