# Contributing

Small bug fixes, clear examples, and reproducible bug reports are welcome.

1. Follow the [README setup](README.md#install).
2. Make a focused change under `src/doclink/`.
3. Add a regression test under `tests/` when changing checker behavior.
4. Run `python -m unittest discover -s tests -v` and `doclink .`.
5. Explain the observed problem, the change, and your test results in your PR.

For a bug report, include your Python version, operating system, the command
you ran, a minimal Markdown example, and expected versus actual output.
Remove private URLs and credentials before sharing output.

Useful starter improvements include per-link line numbers, explicit HTML
anchor support, and more heading-renderer compatibility fixtures. Discuss
larger features before implementing them. Keep offline checks deterministic
and web tests independent of public services.
