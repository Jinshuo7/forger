# Require the Codex CLI for the marketplace install test

The marketplace install test requires the Codex CLI and deliberately fails rather than skips when the CLI is absent, because skipping would allow the plugin's install path to remain silently untested. Any future CI environment must install Codex before running the suite.
