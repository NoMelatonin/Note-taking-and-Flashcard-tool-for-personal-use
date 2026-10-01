"""Contrast checks for the specified text and focus colour combinations."""


def luminance(colour):
    components = [int(colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in components]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast(first, second):
    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


if __name__ == "__main__":
    for name, foreground, background, minimum in (
        ("Main text", "#2E2E2E", "#FFFFFF", 4.5),
        ("Secondary sidebar text", "#666666", "#F6F6F6", 4.5),
        ("Selected text", "#2E2E2E", "#E7E7E7", 4.5),
        ("Editor selection", "#2E2E2E", "#EDE6FD", 4.5),
        ("Primary button", "#FFFFFF", "#555555", 4.5),
        ("Focus outline", "#737373", "#E7E7E7", 3.0),
    ):
        ratio = contrast(foreground, background)
        assert ratio >= minimum, f"{name}: {ratio:.2f} below {minimum}"
        print(f"{name}: {ratio:.2f}:1 (minimum {minimum}:1)")
