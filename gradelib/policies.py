def forgive_lates(self, n, within=None):
    """Forgive the first n lates within a group of assignments.

    Parameters
    ----------
    n : int
        The number of lates to forgive.
    within : Sequence[str]
        A collection of assignments within which lates will be forgiven.
        If None, all assignments will be used. Default: None

    Notes
    -----
    By "first n", we mean with respect to the order specified by the `within`
    argument. As such, the `within` argument must be an ordered *sequence*.
    If not, a ValueError will be raised. For convenience, the result of
    :attr:`Gradebook.assignments` is an ordered sequence, and the order is guaranteed
    to be the same as the order of the underlying column names in the `points`
    table.

    If a late assignment is marked as dropped it will not be forgiven, as
    it is advantageous for the student to use the forgiveness elsewhere.

    Returns
    -------
    Gradebook
        The gradebook with the specified lates forgiven.

    Raises
    ------
    ValueError
        If `within` is empty, or if n is not a positive integer.
    TypeError
        If `within` is not an ordered sequence.

    """
    if n < 1:
        raise ValueError("Must forgive at least one late.")

    if within is None:
        within = self.assignments

    if not within:
        raise ValueError("Cannot pass an empty list of assignments.")

    new_late = self.late.copy()
    for pid in self.pids:
        forgiveness_remaining = n
        for assignment in within:
            is_late = self.late.loc[pid, assignment]
            is_dropped = self.dropped.loc[pid, assignment]
            if is_late and not is_dropped:
                new_late.loc[pid, assignment] = False
                forgiveness_remaining -= 1

            if forgiveness_remaining == 0:
                break

    return self._replace(late=new_late)

def _points_with_lates_replaced_by_zeros(self):
    replaced = self.points_marked.copy()
    replaced[self.late.values] = 0
    return replaced

def drop_lowest(self, n, within=None):
    """Drop the lowest n grades within a group of assignments.

    Parameters
    ----------
    n : int
        The number of grades to drop.
    within : Collection[str]
        A collection of assignments; the lowest among them will be dropped.
        If None, all assignments will be used. Default: None

    Notes
    -----
    If all assignments are worth the same number of points, dropping the
    assignment with the lowest score is most advantageous to the student.
    However, if the assignments are not worth the same number of points,
    the best strategy for the student is not necessarily to drop to
    assignment with the smallest score. In this case, the problem of
    determining the optimal set of assignments to drop in order to maximize
    the overall score is non-trivial.

    In this implementation, dropping assignments is performed via a
    brute-force algorithm: each possible combination of kept assignments is
    tested, and the one which yields the largest total_points /
    maximum_points_possible is used. The time complexity of this approach
    is combinatorial, and therefore it is not recommended beyond small
    problem sizes. For a better algorithm, see:
    http://cseweb.ucsd.edu/~dakane/droplowest.pdf

    If an assignment is marked as late, it will be considered a zero for
    the purposes of dropping. Therefore it is usually preferable to use
    :meth:`Gradebook.forgive_lates` before this method.

    If an assignment has already been marked as dropped, it won't be
    considered for dropping. This is useful, for instance, when a student's
    assignment is dropped due to an external circumstance.

    Returns
    -------
    Gradebook
        The gradebook with the specified assignments dropped.

    Raises
    ------
    ValueError
        If `within` is empty, or if n is not a positive integer.

    """
    # number of kept assignments
    if within is None:
        within = self.assignments

    if not within:
        raise ValueError("Cannot pass an empty list of assignments.")

    # convert to a list because Pandas likes lists, not Assignments objects
    within = list(within)

    # the combinations of assignments to drop
    combinations = list(itertools.combinations(within, n))

    # count lates as zeros
    points_with_lates_as_zeros = self._points_with_lates_replaced_by_zeros()[within]

    # a full table of maximum points available. this will allow us to have
    # different points available per person
    points_available = self.points_marked.copy()[within]
    points_available.iloc[:, :] = self.points_available[within].values

    # we will try each combination and compute the resulting score for each student
    scores = []
    for possibly_dropped in combinations:
        possibly_dropped = list(possibly_dropped)
        possibly_dropped_mask = self.dropped.copy()
        possibly_dropped_mask[possibly_dropped] = True

        earned = points_with_lates_as_zeros.copy()
        earned[possibly_dropped_mask] = 0

        out_of = points_available.copy()
        out_of[possibly_dropped_mask] = 0

        score = earned.sum(axis=1) / out_of.sum(axis=1)
        scores.append(score)

    # now we put the scores into a table and find the index of the best
    # score for each student
    all_scores = pd.concat(scores, axis=1)
    index_of_best_score = all_scores.idxmax(axis=1)

    # loop through the students and mark the assignments which should be
    # dropped
    new_dropped = self.dropped.copy()
    for pid in self.pids:
        best_combo_ix = index_of_best_score.loc[pid]
        tossed = list(combinations[best_combo_ix])
        new_dropped.loc[pid, tossed] = True

    return self._replace(dropped=new_dropped)


