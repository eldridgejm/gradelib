class GradingPipeline:
    def __init__(self):
        self.steps = {}

    def step(self, number):
        def decorator(func):
            self.steps[number] = func
            return func

        return decorator

    def grade(self):
        steps = [self.steps[k] for k in sorted(self.steps)]
        gb = steps[0]()
        for step in steps[1:]:
            res = step(gb)
            if res is not None:
                gb = res
        return gb
