import gradelib.predicates


def test_starting_with():
    predicate = gradelib.predicates.starting_with('foo')

    assert not predicate('testing')
    assert predicate('foobar')

def test_and():
    predicate = (
        gradelib.predicates.starting_with('foo')
        &
        gradelib.predicates.ending_with('bar')
    )

    assert not predicate('testing')
    assert not predicate('foobaz')
    assert not predicate('this bar')
    assert predicate('foo this bar')

def test_or():
    predicate = (
        gradelib.predicates.starting_with('foo')
        |
        gradelib.predicates.ending_with('bar')
    )

    assert not predicate('testing')
    assert predicate('foobaz')
    assert predicate('this bar')
    assert not predicate('bar this')

def test_not():
    predicate = (
        gradelib.predicates.starting_with('foo')
        &
        ~gradelib.predicates.containing('bar')
    )

    assert predicate('foo this')
    assert not predicate('foo bar this')
