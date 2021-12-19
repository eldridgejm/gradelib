from typing import Callable


StringPredicate = Callable[[str], bool]


class Predicate:

    def __init__(self, func):
        self.func = func

    @classmethod
    def new(cls, func):
        return cls(func)

    def __call__(self, x):
        return self.func(x)

    def __and__(self, other):
        def new_func(x):
            return self(x) and other(x)

        return self.__class__(new_func)

    def __or__(self, other):
        def new_func(x):
            return self(x) or other(x)

        return self.__class__(new_func)

    def __or__(self, other):
        def new_func(x):
            return self(x) or other(x)

        return self.__class__(new_func)

    def __invert__(self):
        def new_func(x):
            return not self(x)

        return self.__class__(new_func)


def starting_with(prefix: str) -> Predicate:
    @Predicate.new
    def predicate(s):
        return s.startswith(prefix)
    return predicate


def ending_with(suffix: str) -> Predicate:
    @Predicate.new
    def predicate(s):
        return s.endswith(suffix)
    return predicate


def containing(substring: str) -> Predicate:
    @Predicate.new
    def predicate(s):
        return substring in s
    return predicate
