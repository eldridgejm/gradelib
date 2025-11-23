# gradelib

A Python package for computing overall grades in courses. Designed for reproducible, error-free grading with support for common policies (drops, late penalties, exceptions) and tools for finding robust letter grade scales.

## Project Structure

```
src/gradelib/
├── core/                 # Core data structures (Gradebook, Student, Assignments)
├── io/                   # Input from Gradescope, Canvas, and scale files
├── policies/             # Grading policies (lates, drops, exceptions, attempts)
├── preprocessing.py      # Combine assignment parts/versions
├── scales.py             # Letter grade scales and mapping
├── statistics.py         # Ranking, GPA, distributions
├── plot.py               # Bokeh interactive visualizations
├── overview.py           # Jupyter notebook summaries
└── reports.py            # PDF report generation (LaTeX-based)
```

## Key Concepts

- **Gradebook**: Central class holding `points_earned` (DataFrame), `points_possible` (Series), `lateness` (DataFrame), `dropped` (boolean mask), `notes`, and `grading_groups`
- **GradingGroup**: Defines assignment weighting. Use `with_equal_weights()` or `with_proportional_weights()` factory methods
- **Policies**: Callable objects that modify gradebooks in-place (e.g., `lates.Deduct`, `drops.drop_most_favorable`, `exceptions.make_exceptions`)

## Development Commands

```bash
# Sync dependencies
uv sync

# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/test_scales.py

# Run linter
uv run ruff check src/

# Format code
uv run ruff format src/
```

## Code Conventions

- **Formatting**: Ruff (configured in pyproject.toml)
- **Type hints**: Used throughout
- **Docstrings**: NumPy style with Parameters/Returns/Raises sections
- **Python version**: 3.10+

## Testing

Tests are in `/tests/` using pytest. Each module has corresponding test files:
- `tests/test_core/` - Core data structure tests
- `tests/test_io/` - I/O parsing tests
- `tests/test_policies/` - Policy logic tests

## Common Patterns

- DataFrames for tabular grade data (students as index, assignments as columns)
- Policies modify Gradebook in-place
- Notes tracked via nested dicts: `{Student: {channel: [notes]}}`
- Factory methods for GradingGroup creation
- `Assignments` and `Students` implement Sequence protocol with `.starting_with()`, `.ending_with()`, `.find()` utilities

## Dependencies

Runtime: pandas, numpy, matplotlib, bokeh

## Documentation

Full docs at https://eldridgejm.github.io/gradelib/
