<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/letta-ai/letta/refs/heads/main/assets/Letta-logo-RGB_GreyonTransparent_cropped_small.png">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/letta-ai/letta/refs/heads/main/assets/Letta-logo-RGB_OffBlackonTransparent_cropped_small.png">
    <img alt="Memos logo" src="https://raw.githubusercontent.com/letta-ai/letta/refs/heads/main/assets/Letta-logo-RGB_GreyonOffBlack_cropped_small.png" width="500">
  </picture>
</p>

# Memos (Fork of Letta)

> **A fork of Letta with unified provider management**

Memos is a modified version of [Letta](https://github.com/letta-ai/letta) that unifies the provider system for better flexibility.

## What Memos Changes

Compared to the original Letta, Memos includes the following modifications:

- **Unified Provider System**: All providers are created through the API and stored in the database
- **Custom Provider Names**: Use your own names for providers
- **Hard Delete**: Providers are truly deleted from the database

## Documentation

See the `docs/` folder for detailed documentation:

- **[LETTA_ARCHITECTURE_DEEP_DIVE.md](docs/LETTA_ARCHITECTURE_DEEP_DIVE.md)** - Complete analysis of Letta's architecture and implementation
- **[KETTA_PROVIDER_UNIFICATION_PLAN.md](docs/KETTA_PROVIDER_UNIFICATION_PLAN.md)** - The plan for unifying the provider system

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/kosmoli/memos.git
cd memos

# Install dependencies
pip install -e .

# Or use uv (recommended)
uv pip install -e .
```

### Running the Server

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the server
python -m letta.server.rest_api.server
```

The server will start on `http://localhost:8283`.

## Compatibility with Letta

Memos aims to maintain API compatibility with Letta where possible, so existing Letta clients should work with Memos. However, there are behavioral differences:

1. **Provider Management**: All providers must be created via API (no auto-sync from environment)
2. **Provider Handles**: Handles use the provider's actual name (no `openai-proxy` prefix)
3. **Provider Deletion**: Deletion is permanent (hard delete)

## Development

### Branch Strategy

- `main` - Tracks upstream Letta changes
- `memos` - Our modifications and improvements

### Syncing with Upstream

```bash
# Add Letta as upstream (if not already added)
git remote add letta https://github.com/letta-ai/letta.git

# Fetch upstream changes
git fetch letta main

# Review changes
git log HEAD..letta/main --oneline

# Cherry-pick specific fixes
git cherry-pick <commit-hash>
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest tests/
```

## Contributing

Memos is an open source project. Contributions are welcome!

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Acknowledgments

- **[Letta](https://github.com/letta-ai/letta)** - The original project
- **[Klui](https://github.com/kosmoli/klui)** - The frontend UI for Memos

## License

This project is licensed under the same license as Letta (see [LICENSE](LICENSE)).

---

**Note**: This is a fork of Letta. For the original project, visit https://github.com/letta-ai/letta
