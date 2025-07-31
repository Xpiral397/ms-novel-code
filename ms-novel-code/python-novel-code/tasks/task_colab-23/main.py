# main.py

class StringAnalyzer:
    """
    Class for analyzing string patterns.
    Method has_repeated_pattern returns True if the string can be formed
    by repeating a substring multiple times.
    """
    def has_repeated_pattern(self, s: str) -> bool:
        if len(s) < 2:
            return False
        doubled = (s + s)[1:-1]
        return s in doubled
