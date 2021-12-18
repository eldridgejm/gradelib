class Student:
    def __init__(self, name, pid):
        self.name = name
        self.pid = pid

    def __repr__(self):
        return f"Student({self.name!r}, {self.pid!r})"

    def __hash__(self):
        return hash(self.pid)

    def __eq__(self, other):
        if isinstance(other, Student):
            return (self.name == other.name) and (self.pid == other.pid)

        elif isinstance(other, (list, tuple)):
            if len(other) != 2:
                return False

            other = self.__class__(other[0], other[1])
            return self == other

        raise TypeError(
            f"Cannot compare type {self.__class__.__name__} to type {other.__class__.__name__}"
        )
