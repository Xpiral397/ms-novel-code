# main.py
import time
class StringAnalyzer:
    """
    Fast implementation using the 'double-and-slice' trick.
    """
    def has_repeated_pattern(self, s: str) -> bool:
        if len(s) < 2:
            return False
        doubled = (s + s)[1:-1]
        return s in doubled

class StringAnalyzerSlow(StringAnalyzer):
    """
    Slow variant: same logic plus a 0.5s delay.
    """
    def has_repeated_pattern(self, s: str) -> bool:
        time.sleep(0.5)
        return super().has_repeated_pattern(s)

# === Test cases ===
