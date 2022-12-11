class _GradeAmount:
    def __init__(self, amount):
        self.amount = amount

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.amount == other.amount

    def __repr__(self):
        return f"{self.__class__.__name__}(amount={self.amount!r})"


class Points(_GradeAmount):
    """Represents an absolute number of points."""

    def __str__(self):
        return f"{self.amount} points"


class Percentage(_GradeAmount):
    """Represents a percentage."""

    def __str__(self):
        return f"{self.amount * 100}%"
