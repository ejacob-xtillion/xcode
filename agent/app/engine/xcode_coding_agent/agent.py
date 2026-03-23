"""
xcode_coding_agent agent implementation (LangChain v1.0)

This provides a template for using LangChain's create_agent with streaming events.
"""
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.graph.state import CompiledStateGraph
from typing import Dict, List, Optional
from app.core.settings import AppSettings
from langgraph.checkpoint.base import BaseCheckpointSaver
from app.core.logger import get_logger
from app.engine.xcode_coding_agent.prompt import SYSTEM_PROMPT

# Agent-specific imports

from app.engine.mcp_tools import get_tool_discovery
from app.engine.custom_tools import get_all_tools as get_custom_tools



logger = get_logger()

async def create_agent_instance(
    settings: AppSettings, 
    checkpointer: BaseCheckpointSaver,
    headers: Optional[Dict[str, str]] = None,
    request: Optional[object] = None,
    tools: Optional[List[BaseTool]] = None,
    agent_session_id: int | None = None,
) -> CompiledStateGraph:
    """
    Create and return a xcode_coding_agent agent instance.

    Args:
        settings: Application settings containing LLM configuration
        checkpointer: Checkpointer instance (InMemorySaver or AsyncPostgresSaver)
        headers: Optional pre-built headers to forward to MCP servers
        request: Optional FastAPI request object (for building per-server headers)
        tools: Optional pre-discovered tools list (if provided, skips discovery)
    Returns:
        Compiled LangGraph agent
    """
    # Tool handling based on agent type
    

    # Resolve custom tools once (filter by allow or deny)
    custom_tools = get_custom_tools()
    
    custom_tools = []
    

    # Use provided tools if available, otherwise discover tools
    if tools is None:
        discovery = get_tool_discovery()
        all_tools = {}
        
        # Only discover tools from agent's configured MCP servers
        
        for server_name in ["neo4j", "filesystem"]:
            server_tools = await discovery.discover_server_tools(server_name, headers=headers, request=request)
            all_tools[server_name] = server_tools
        
        
        all_tools["custom"] = custom_tools

        # Flatten tools from configured servers plus custom into a single list
        tools = [tool for server_tools in all_tools.values() for tool in server_tools]
        
        logger.info(
            "agent_tools_discovered",
            agent_name="xcode_coding_agent",
            server_count=len(all_tools),
            total_tools=len(tools),
            tool_names=[t.name for t in tools]
        )
    else:
        existing_names = {t.name for t in tools}
        for custom_tool in custom_tools:
            if custom_tool.name not in existing_names:
                tools.append(custom_tool)
        
        logger.info(
            "agent_tools_provided",
            agent_name="xcode_coding_agent",
            total_tools=len(tools),
            tool_names=[t.name for t in tools]
        )
    
    
    model_name = "gpt-5"
    

    # Build model identifier with provider prefix if needed
    llm_type = "openai".lower()
    
    # Providers that use {provider}:{model} format
    PROVIDER_PREFIXES = {
        "azure": "azure_openai",
        "google_genai": "google_genai",
    }
    
    if llm_type in PROVIDER_PREFIXES and not model_name.startswith(f"{PROVIDER_PREFIXES[llm_type]}:"):
        model_identifier = f"{PROVIDER_PREFIXES[llm_type]}:{model_name}"
    else:
        model_identifier = model_name

    # Handle special model requirements
    # GPT-5 models require temperature=1 (not 0.0)
    # Models starting with 'o' (o1, o3, o4) need explicit provider specification
    # Get temperature from config if provided
    
    config_temperature = None
    
    
    # Handle special model requirements
    if model_name.startswith("gpt-5"):
        # GPT-5 models require temperature=1
        temperature = 1.0
    elif config_temperature is not None:
        # Use config temperature if provided
        temperature = config_temperature
    else:
        # Fall back to settings default
        temperature = settings.llm_temperature
    
    model_provider = None
    if model_name.startswith("o"):
        # o-models (o1, o3, o4) need explicit provider for LangChain
        model_provider = "openai"

    init_params = {
        "model": model_identifier,
        "temperature": temperature,
        "timeout": settings.llm_timeout,
        "max_retries": settings.llm_max_retries,
        "request_timeout": settings.llm_request_timeout,
    }
    
    # Add reasoning_effort if provided (useful for GPT-5 models)
    
    
    # Handle provider-specific configuration
    if llm_type == "bedrock":
        if not settings.aws_region:
            raise ValueError("AWS region is required for Bedrock provider. Set AWS_REGION environment variable.")
        init_params["model_provider"] = "bedrock"
        init_params["region_name"] = settings.aws_region
        
        # Add AWS credentials if provided
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            init_params["access_key_id"] = settings.aws_access_key_id
            init_params["secret_access_key"] = settings.aws_secret_access_key
            if settings.aws_session_token:
                init_params["session_token"] = settings.aws_session_token
        elif settings.aws_access_key_id or settings.aws_secret_access_key:
            raise ValueError(
                "Both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided together, "
                "or neither to use IAM role-based authentication."
            )

    elif llm_type == "litellm" and settings.llm_base_url:
        init_params["model_provider"] = "openai"
        if settings.llm_api_key:
            init_params["api_key"] = settings.llm_api_key
    elif model_provider:
        init_params["model_provider"] = model_provider
        if settings.llm_api_key:
            init_params["api_key"] = settings.llm_api_key
    else:
        if settings.llm_api_key:
            init_params["api_key"] = settings.llm_api_key

    # Handle base_url (standard **kwargs parameter)
    # Required for azure and custom providers
    if llm_type == "bedrock":
        # Bedrock doesn't use base_url - region is handled via region_name parameter
        pass
    elif llm_type in {"azure", "custom"}:
        if not settings.llm_base_url:
            raise ValueError(f"{llm_type.title()} provider requires llm_base_url")
        init_params["base_url"] = settings.llm_base_url
    elif llm_type == "litellm":
        # LiteLLM proxy mode: requires LLM_BASE_URL, uses model_provider="openai" (set above)
        # Model names: "us.anthropic.claude-*" (Bedrock), "claude-*" (Anthropic), etc.
        if not settings.llm_base_url:
            raise ValueError("LiteLLM provider requires llm_base_url (LiteLLM proxy URL)")
        init_params["base_url"] = settings.llm_base_url
    elif settings.llm_base_url:
        # Optional base_url for other providers (custom endpoints)
        init_params["base_url"] = settings.llm_base_url

    # Create model using init_chat_model
    # Auto-detects provider for: openai (gpt-*, o1-*, o3-*), anthropic (claude-*), 
    # google_vertexai (gemini-*), and others based on model name prefixes
    model = init_chat_model(**init_params)
    
    
    middleware = ()
    
    # Create agent using LangChain's create_agent helper
    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=checkpointer,
        name="Xcode_coding_agent Agent",
        system_prompt=SYSTEM_PROMPT,
        middleware=middleware
    )

    return agent