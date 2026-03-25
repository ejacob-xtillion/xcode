# Changelog

All notable changes to xCode will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository cleanup and documentation organization
- CONTRIBUTING.md with development guidelines
- CHANGELOG.md for version tracking
- Organized documentation into docs/ directory

### Changed
- Moved technical documentation to docs/ directory
- Updated README.md with cleaner structure and better organization
- Enhanced .gitignore to prevent temporary files

### Removed
- Temporary analysis JSON files from root directory

## [0.1.0] - 2024-03-24

### Added
- Tool retry middleware for robust agent execution
- Automatic retry logic for failed tool calls with exponential backoff
- Comprehensive functional and regression test reports
- Verification loop with automatic test discovery and generation
- CLI flags for verification control (--no-verify, --no-test-generation, --max-fix-attempts)
- Test discovery service using Neo4j graph queries
- Test generation service for untested callables
- Modified file tracking during agent execution
- Agent prompt enhancements for mandatory verification requirements

### Changed
- Enhanced agent system prompt with tool retry documentation
- Updated environment configuration with retry settings
- Improved orchestrator to track and verify file modifications

### Fixed
- Test mocks and removed unused methods
- Docker environment variable loading for both CLI and agent services
- CLI task classification error handling

## [0.0.1] - Initial Release

### Added
- CLI tool with Click interface
- FastAPI + LangGraph AI agent
- Neo4j knowledge graph integration
- MCP tools for Neo4j and filesystem operations
- Docker Compose orchestration
- Local LLM support (Ollama)
- Interactive mode
- Clean architecture with domain/service/repository layers
- Comprehensive test suite
- Rich terminal UI with progress indicators

[Unreleased]: https://github.com/yourusername/xcode/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/xcode/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/yourusername/xcode/releases/tag/v0.0.1
