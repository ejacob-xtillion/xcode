from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables not defined in model
    )

    # API Configuration
    api_version: str = Field(default="1.0.0")
    api_port: int = Field(default=8000)
    environment: str = Field(default="dev")

    # CORS Configuration
    cors_allowed_origins: list[str] = Field(default=[])

    # Logging Configuration
    log_level: str = Field(default="INFO")

    # JWT Configuration
    jwt_enabled: bool = Field(default=False, description="Enable JWT authentication")
    jwt_issuer: Optional[str] = Field(default=None, description="JWT issuer URL (e.g., https://your-auth.com/)")
    jwt_audience: Optional[str] = Field(default=None, description="JWT audience (your API identifier)")
    jwt_algorithms: list[str] = Field(default=["RS256"], description="Allowed JWT algorithms")
    jwt_jwks_url: Optional[str] = Field(default=None, description="JWKS URL for JWT signature verification (if not provided, defaults to {issuer}/.well-known/jwks.json)")


    # LLM Configuration
    llm_api_key: Optional[str] = Field(default=None, description="LLM API key (not required for Bedrock)")
    llm_model: str = Field(default="gpt-4.1-mini")
    llm_base_url: Optional[str] = Field(default=None)
    llm_temperature: float = Field(default=0.0)
    llm_timeout: int = Field(default=600, description="LLM API timeout in seconds (default: 10 minutes)")
    llm_max_retries: int = Field(default=3, description="Maximum number of retries for LLM API calls")
    llm_request_timeout: int = Field(default=600, description="HTTP request timeout for LLM API calls in seconds")
   
    # AWS Bedrock Configuration
    aws_region: Optional[str] = Field(default=None, description="AWS region for Bedrock (required when LLMType=bedrock)")
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS access key ID (required when LLMType=bedrock)")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS secret access key (required when LLMType=bedrock)")
    aws_session_token: Optional[str] = Field(default=None, description="AWS session token (required when LLMType=bedrock)")

    # LangSmith Configuration
    langsmith_tracing: bool = Field(default=False)
    langsmith_endpoint: Optional[str] = Field(default="https://api.smith.langchain.com")
    langsmith_api_key: Optional[str] = Field(default=None)
    langsmith_project: Optional[str] = Field(default=None)

    # Database Configuration
    database_url: Optional[str] = Field(default=None)
    postgres_host: Optional[str] = Field(default=None)
    postgres_port: int = Field(default=5432)
    postgres_user: Optional[str] = Field(default=None)
    postgres_password: Optional[str] = Field(default=None)
    postgres_db: Optional[str] = Field(default=None)

    # OpenTelemetry Configuration
    otel_enabled: bool = Field(default=True)
    otel_service_name: str = Field(default="la-factoria-api")
    otel_exporter_otlp_traces_endpoint: Optional[str] = Field(default=None)
    otel_exporter_otlp_metrics_endpoint: Optional[str] = Field(default=None)
    otel_export_console: bool = Field(default=False)
    otel_export_interval_millis: int = Field(default=60000)

    # Header Forwarding Configuration
    header_forwarding: Optional[list[str]] = Field(
        default=None,
        description="List of header names to forward to downstream services (e.g., ['X-Custom-Header', 'X-User-ID'])",
    )

    # MCP Server Configuration
    # Dictionary mapping server names to their configuration
    # Each server config includes: url, formOfTransport, port, authType, authEnvVar, tenantId
    mcp_servers: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            'neo4j': {
                'formOfTransport': 'stdio',
                'command': 'uvx',
                'args': ['mcp-neo4j-cypher', '--transport', 'stdio'],
                'env': {
                    'NEO4J_URI': 'bolt://localhost:7687',
                    'NEO4J_USERNAME': 'neo4j',
                    'NEO4J_PASSWORD': 'password'
                },
                'url': None,
                'port': None,
                'authType': 'jwt',
                'authEnvVar': 'MCP_NEO4J_JWT_TOKEN'
            },
            'filesystem': {
                'formOfTransport': 'stdio',
                'command': 'npx',
                'args': ['-y', '@modelcontextprotocol/server-filesystem', '/Users/elijahgjacob'],
                'env': None,
                'url': None,
                'port': None,
                'authType': 'jwt',
                'authEnvVar': 'MCP_FILESYSTEM_JWT_TOKEN'
            }
        },
        description="MCP server configurations (name -> {url, formOfTransport, port, authType, authEnvVar, tenantId})",
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        # Override Neo4j URI from environment if provided
        import os
        neo4j_uri = os.getenv('NEO4J_URI')
        if neo4j_uri and 'neo4j' in self.mcp_servers:
            self.mcp_servers['neo4j']['env']['NEO4J_URI'] = neo4j_uri
    mcp_tool_cache_ttl_seconds: int = Field(default=1800, description="MCP tool discovery cache TTL in seconds (default: 30 minutes)")

    # Shell tool (custom LangChain tool — runs inside the agent process/container)
    shell_tool_enabled: bool = Field(
        default=True,
        description="When false, run_shell_command is not registered with the agent",
    )
    shell_allowed_roots_csv: Optional[str] = Field(
        default=None,
        description="Comma-separated absolute paths; cwd must resolve under one of these. "
        "If unset, uses the filesystem MCP server's allowed directory (last arg).",
    )
    shell_command_timeout_seconds: int = Field(
        default=120,
        ge=1,
        le=3600,
        description="Max seconds for a single shell command",
    )
    shell_max_output_bytes: int = Field(
        default=65536,
        ge=1024,
        le=2_097_152,
        description="Truncate combined stdout+stderr beyond this many bytes",
    )
    shell_auto_install_requirements: bool = Field(
        default=True,
        description="If requirements.txt exists in cwd, run uv/pip install -r before pytest-like commands",
    )
    shell_skip_redundant_requirements_install: bool = Field(
        default=True,
        description="Skip repeat installs when requirements.txt + cwd + Python path unchanged (in-process cache)",
    )
    shell_pip_install_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=1800,
        description="Timeout for automatic requirements.txt install (uv pip or python -m pip)",
    )

    # Streaming Configuration
    stream_timeout: int = Field(default=1200, description="Streaming timeout in seconds (default: 20 minutes)")


    def get_shell_allowed_roots(self) -> list[str]:
        """Absolute directories under which run_shell_command may set cwd (after realpath)."""
        if self.shell_allowed_roots_csv and self.shell_allowed_roots_csv.strip():
            return [
                p.strip()
                for p in self.shell_allowed_roots_csv.split(",")
                if p.strip()
            ]
        fs = self.mcp_servers.get("filesystem") or {}
        args = fs.get("args") or []
        if args:
            # @modelcontextprotocol/server-filesystem: last arg is the allowed root
            return [str(args[-1])]
        return ["/Users/elijahgjacob"]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in ["dev", "development", "local"]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ["prod", "production"]

    @property
    def async_database_url(self) -> Optional[str]:
        if not self.database_url:
            return None

        url = self.database_url
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def get_env(self, key: str) -> Optional[str]:
        """Get environment variable value from os.environ or .env file.
        """
        import os
        # First check os.environ (for runtime environment variables)
        value = os.environ.get(key)
        if value:
            return value
        
        # If not found, try loading from .env file using dotenv
        # This handles cases where variables are in .env but not in os.environ
        try:
            from dotenv import dotenv_values
            # Try .env file in current working directory (where the app runs from)
            env_file = Path(".env")
            if env_file.exists():
                env_vars = dotenv_values(env_file)
                return env_vars.get(key)
            
        except Exception:
            # File read errors, etc. - fail silently and return None
            pass
        
        return None


_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings
