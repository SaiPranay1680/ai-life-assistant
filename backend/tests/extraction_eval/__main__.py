"""Allow `python -m tests.extraction_eval` to run the evaluation runner."""

from .runner import main

raise SystemExit(main())
