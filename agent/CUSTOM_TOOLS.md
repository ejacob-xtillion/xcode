# Adding Custom Tools to Your Agent

This guide explains how to add custom tools directly to your agent without using MCP servers. Custom tools are Python functions that your agent can call to perform specific actions or retrieve information.

## When to Use Custom Tools vs MCP Servers

### Use Custom Tools When:
- Tools are specific to this single agent
- You need simple, stateless utilities (calculators, formatters, validators)
- You want rapid prototyping without server setup
- Tools don't need to be shared across multiple agents
- You prefer direct Python integration

### Use MCP Servers When:
- Tools need to be shared across multiple agents
- You have complex integrations (databases, external APIs, services)
- You want standardized tool discovery and protocol
- Tools require separate lifecycle management
- You need language-agnostic tool definitions

## Overview

Tools in this repository use LangChain's `@tool` decorator. The agent uses the tool's docstring to understand when and how to use it, so clear documentation is critical.

### Where to edit in this repo

- Add or change local tools in `app/engine/custom_tools.py` (extend `get_all_tools()`).
- Agents load custom tools automatically via `app/templates/agent_templates/simple_agent/agent.py.j2` (the generated `app/engine/<agent_name>/agent.py` already pulls them in).
- If you generated an output app (e.g., `output/combined_mcp_app*/`), mirror tool edits in its `app/engine/custom_tools.py` if you want the baked artifact to include them.

### Built-in Hello World example

We ship a minimal custom tool that requires no MCP server configuration. It lives at `app/engine/custom_tools.py`:

```python
from langchain.tools import tool
from app.core.logger import get_logger

logger = get_logger()

@tool
def get_hello_world() -> str:
    """
    Return a friendly hello-world message.

    Use this when the user asks for a basic greeting or to confirm custom tools
    are available without calling an MCP server.
    """
    message = "Hello from the custom tool!"
    logger.info("custom_tool_hello_requested", message=message)
    return message


def get_all_tools() -> list:
    """Return all custom tools defined in this module."""
    return [get_hello_world]
```

To add more local tools, extend the same module and include them in `get_all_tools()`.

### Key Concepts

- **Tool Definition**: A Python function decorated with `@tool`
- **Docstring**: The tool's description that helps the LLM decide when to use it
- **Tool Registration**: Adding the tool to the list passed to `create_agent()`
- **Type Safety**: Using type hints for parameters and return values

## Quick Start: Adding a Simple Tool

Custom tools are defined on a per-agent basis and must be activated for each agent. Preferably, the custom tool is included in the configuration file that generates the repository.

### Step 1: Create a Tools Module

Create a new file in your agent's directory:

```bash
# If your agent is named "bartender"
touch app/engine/bartender/tools.py
```

### Step 2: Define Your Tool

Add your tool function to `app/engine/<agent_name>/tools.py`:

```python
from langchain.tools import tool
from app.core.logger import get_logger

logger = get_logger()

@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 15.0) -> str:
    """
    Calculate the tip amount for a restaurant bill.
    
    Use this tool when the user asks about tipping or calculating gratuity.
    
    Args:
        bill_amount: The total bill amount in dollars
        tip_percentage: The tip percentage (default: 15.0)
    
    Returns:
        A formatted string with the tip amount and total
    """
    try:
        if bill_amount < 0:
            return "Error: Bill amount cannot be negative"
        
        if tip_percentage < 0 or tip_percentage > 100:
            return "Error: Tip percentage must be between 0 and 100"
        
        tip = bill_amount * (tip_percentage / 100)
        total = bill_amount + tip
        
        logger.info("tip_calculated", bill=bill_amount, tip_pct=tip_percentage, tip=tip)
        
        return f"Tip: ${tip:.2f}\nTotal: ${total:.2f}"
    
    except Exception as e:
        logger.error("calculate_tip_failed", error=str(e))
        return f"Error: Failed to calculate tip: {str(e)}"

def get_all_tools() -> list:
    """Get all available tools for this agent."""
    return [calculate_tip]
```

### Step 3: Import and Use Tools in Your Agent

Update your agent file (`app/engine/<agent_name>/agent.py`). This file may already include a few custom tools if they were specified in the configuration file used to generate this repository.

```python
from app.engine.<agent_name>.tools import get_all_tools
from app.engine.mcp_tools import get_tool_discovery

async def create_agent_instance(
    settings: AppSettings,
    headers: Optional[Dict[str, str]] = None,
    request: Optional[object] = None
) -> CompiledStateGraph:
    """Create and return an agent instance."""
    
    # Get MCP tools (if any)
    discovery = get_tool_discovery()
    mcp_tools_by_server = await discovery.discover_all_tools(headers=headers, request=request)
    mcp_tools = [tool for server_tools in mcp_tools_by_server.values() for tool in server_tools]
    
    # Get custom tools
    custom_tools = get_all_tools()
    
    # Combine all tools
    all_tools = mcp_tools + custom_tools
    
    logger.info(
        "agent_tools_loaded",
        agent_name="<agent_name>",
        mcp_tool_count=len(mcp_tools),
        custom_tool_count=len(custom_tools),
        total_tools=len(all_tools),
    )
    
    # Initialize LLM
    llm = init_chat_model(...)
    
    # Create agent with all tools
    agent = create_agent(
        model=llm,
        tools=all_tools,  # Pass combined tools
        state_modifier="Your system prompt"
    )
    
    return agent
```

**Note:** Use `get_tool_discovery()` instead of creating `GlobalToolDiscovery` directly so you reuse the shared, cached instance and avoid redundant MCP connections.

### Step 4: Test Your Tool

Start your application and test via the API:

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "bartender",
    "query": "Calculate a 20% tip on a $50 bill"
  }'
```

## Tool Patterns

### Pattern 1: Simple Utility Tool

Stateless functions that perform calculations or transformations:

```python
@tool
def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format a number as currency.
    
    Args:
        amount: The amount to format
        currency: Currency code (USD, EUR, GBP, etc.)
    
    Returns:
        Formatted currency string
    """
    try:
        symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
        symbol = symbols.get(currency, currency)
        return f"{symbol}{amount:,.2f}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Pattern 2: Tool with External API

Tools that make HTTP requests:

```python
import httpx

@tool
async def fetch_exchange_rate(from_currency: str, to_currency: str) -> str:
    """
    Get the current exchange rate between two currencies.
    
    Args:
        from_currency: Source currency code (e.g., USD)
        to_currency: Target currency code (e.g., EUR)
    
    Returns:
        Current exchange rate as a string
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            )
            response.raise_for_status()
            data = response.json()
            rate = data["rates"].get(to_currency)
            
            if not rate:
                return f"Error: Exchange rate not found for {to_currency}"
            
            logger.info("exchange_rate_fetched", from_curr=from_currency, to_curr=to_currency, rate=rate)
            return f"1 {from_currency} = {rate} {to_currency}"
    
    except httpx.HTTPError as e:
        logger.error("exchange_rate_failed", error=str(e))
        return f"Error: Failed to fetch exchange rate: {str(e)}"
```

## Best Practices

### 1. Write Clear Docstrings

The docstring is how the LLM understands your tool:

```python
@tool
def good_tool(param: str) -> str:
    """
    Clear, action-oriented description of what the tool does.
    
    Explain when the agent should use this tool. Include any important
    constraints, supported formats, or edge cases.
    
    Args:
        param: Detailed description of the parameter
    
    Returns:
        Detailed description of the return value
    """
    pass
```

### 2. Use Type Hints

Always include type hints:

```python
@tool
def typed_tool(text: str, count: int) -> str:  # Good
    pass
```

### 3. Handle Errors Gracefully

Wrap tool logic in try-except blocks:

```python
@tool
def safe_tool(param: str) -> str:
    """Tool with proper error handling."""
    try:
        result = risky_operation(param)
        return str(result)
    except SpecificError as e:
        return f"Error: Specific issue: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected failure: {str(e)}"
```

### 4. Log Tool Usage

Use structured logging:

```python
from app.core.logger import get_logger

logger = get_logger()

@tool
def logged_tool(param: str) -> str:
    """Tool with proper logging."""
    try:
        logger.info("tool_called", param=param)
        result = perform_operation(param)
        logger.info("tool_succeeded", result=result)
        return str(result)
    except Exception as e:
        logger.error("tool_failed", error=str(e), exc_info=True)
        return f"Error: {str(e)}"
```

### 5. Keep Tools Focused

Each tool should do one thing well:

```python
# Good - focused tools
@tool
def fetch_data(url: str) -> str:
    """Fetch data from a URL."""
    pass

@tool
def parse_data(data: str) -> dict:
    """Parse fetched data."""
    pass

# Bad - tool does too much
@tool
def fetch_and_parse_and_analyze(url: str) -> str:
    """Fetches, parses, and analyzes data."""  # Too complex!
    pass
```
### Integration Testing

Test through the API:

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "bartender",
    "query": "Calculate a 15% tip on a $75 bill"
  }'
```

### Manual Testing

1. Start the server: `docker-compose up`
2. Send requests that trigger your tool
3. Check logs to verify tool was called
4. Verify the response is correct

## Troubleshooting

### Tool Not Being Called

1. Check the docstring - is it clear when to use the tool?
2. Verify the tool is in `get_all_tools()` return list
3. Check logs to see if agent considered the tool
4. Make the docstring more explicit

### Tool Returns Errors

1. Add detailed error handling
2. Validate inputs before processing
3. Check logs for full traceback
4. Test the function directly in Python

### Agent Misuses Tool

1. Improve docstring with clearer instructions
2. Add examples in the docstring
3. Validate inputs and return helpful errors
4. Consider splitting into multiple focused tools

## Additional Resources

- [LangChain Tools Documentation](https://python.langchain.com/docs/how_to/custom_tools/)
- [Pydantic Models](https://docs.pydantic.dev/latest/)
- [Structured Logging with structlog](https://www.structlog.org/)