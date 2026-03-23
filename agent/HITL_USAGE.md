# Human-In-The-Loop Agent Instructions
## Getting Started 
* Read important LangChain Documentation on [Human-In-The-Loop Agents](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
* Human-in-the-loop agent will trigger an interrupt event when a request is made requiring a tool specified in the interruptOn AgentConfig parameter.
* Config example:
```yaml
---
# Combined MCP test configuration
# Tests both stdio (Neo4j) and HTTP (GitHub) MCP servers

agents: 1
typeOfGraph: simple

# LLM configuration
LLMType: openai

MCPServers:
  github:
    formOfTransport: http
    url: "https://api.githubcopilot.com/mcp/"
    port: 443
    authType: bearer
    authEnvVar: "GITHUB_TOKEN"

AgentConfigs:
  github_agent:
    prompt: |
      You are GitHubAgent, an expert developer assistant with full access to GitHub via tool calls. Your responsibilities include understanding the user's requests related to repositories, issues, pull requests, and code; deciding when to call tools to read or modify GitHub data; using tools accurately with correct parameters; and summarizing results clearly and concisely for the user. Available tools (high level): - Repositories: search_repositories (find repositories by keywords and filters), create_repository (create a new repository under the configured account or organization), fork_repository (fork an existing repository), create_branch (create a new branch from a base branch or commit), list_commits (list commits in a repository or branch), push_files (add or update files in bulk from local content). - Files: get_file_contents (read files from a specific path and ref), create_or_update_file (create or update a single file in a repository). - Issues: search_issues (search issues and pull requests across repositories), list_issues (list issues in a repository with filters), create_issue (open a new issue), get_issue (fetch full details of a specific issue), update_issue (modify title, body, state, or labels), add_issue_comment (add a comment to an issue). - Code search: search_code (search for code snippets across repositories). - Users: search_users (search for GitHub users). - Pull requests: list_pull_requests (list pull requests in a repository with filters), create_pull_request (open a new pull request from a branch), get_pull_request (fetch full details of a pull request), get_pull_request_files (list files changed in a pull request), get_pull_request_status (get CI, mergeability, or status checks), get_pull_request_comments (list conversation comments on a pull request), get_pull_request_reviews (list review events on a pull request), create_pull_request_review (submit a review—approve, comment, or request changes), update_pull_request_branch (sync or merge the base branch into the pull request branch), merge_pull_request (merge a pull request). Safety and behavior: - Before destructive or irreversible actions (such as creating repositories, merging pull requests, or overwriting files), restate what you're about to do and wait for user confirmation unless the user explicitly requests it. - Prefer reading existing state (get_*, list_*, search_*) before writing. - If required information is missing (such as repo name, owner, branch, or file path), ask a brief clarification from the user. - When you complete a tool call, summarize what was changed and include links or identifiers (repository names, issue numbers, pull request numbers) in your response.
    type: hitl_agent
    mcpServers:
      - github
    ModelName: "gpt-4.1-mini"
    temperature: 0.2
    interruptOn: 
      - tool_name: "create_pull_request"
        allowed_decisions:
          - "approve"
          - "reject"
      - tool_name: "issue_write" # By default, all decisions allowed (approve, edit, reject)
      - tool_name: "update_pull_request" # By default, all decisions allowed (approve, edit, reject)
    descriptionPrefix: "Tool execution pending approval"
```
* This agent will cause an interrupt event on the following tool calls: `create_pull_request`, `issue_write`, and `update_pull_request`
* The tool `create_pull_request` will give users the option to either "approve" or "reject" the request- all other tools will have all three options available ("approve", "edit", "reject").

## Invocation
* Like all other agents, Human-In-The-Loop Agents can be invoked using the streaming or completion endpoints.
* The following is an example for the above config, requesting the agent to update a pull request, which will cause an interrupt event:
```bash
curl -X 'POST' \
  'http://localhost:8000/agents' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "Can you update the pull request 67 in Organization/Repo_Name to add test_reviewer as a reviewer?",
  "agent_name": "github_agent"
}'
```
* This will lead to the following response:
```bash
data: 
    {
        "role":"assistant",
        "type":"tool_call",
        "tool_call_id":"call_id",
        "tool":"update_pull_request",
        "args":
            {
                "owner":"organization",
                "repo":"repo_name",
                "pullNumber":67,
                "reviewers":["test_reviewer"]
            },
        "timestamp":"YYYY-MM-DDTHH:MM:SS+00:00"
    }

data: 
    {
        "role":"assistant",
        "type":"interrupt",
        "options":["approve","edit","reject"],
        "prompt":"Tool execution requires approval\n\nTool: update_pull_request\nArgs: {'owner': 'organization', 'repo': 'repo_name', 'pullNumber': 67, 'reviewers': ['test_reviewer']}","timestamp":"YYYY-MM-DDTHH:MM:SS+00:00"
    }

data: 
    {
        "type":"complete",
        "session_id":1,
        "status":"interrupted",
        "execution_time_ms":1947,
        "timestamp":"YYYY-MM-DDTHH:MM:SS+00:00"
    }
```

## On Interrupt: Resume Endpoint

### Format
```bash
    {
    "session_id": 0,
    "command": {
        "decisions": [
        {
            "type": "approve",
            "edited_action": 
                {
                "name": "string",
                "args": 
                    {
                    "additionalProp1": {}
                    }
                },
            "message": "string"
            }
        ]
    }
```
* **Required Parameters**:
    * **session_id**: from the stream endpoint, same session ID from the interrupt event
    * **command.decisions.type**: "approve", "edit" or "reject"
    * **command.decisions.edited_action**: only necessary if decision type = "edit"
        * **"name"**: tool name of interrupt event
        * **"args"**: dependant on interrupt event tool args (from response)- args to modify/edit in tool call
    * **command.decisions.message**: only necessary if decision type = "reject". An explanation on why the action was rejected

#### Approve
```bash
curl -X 'POST' \
  'http://localhost:8000/agents/resume' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": 1,
  "command": {
    "decisions": [
      {
        "type": "approve"
      }
    ]
  }
}'
```

#### Edit

```bash
curl -X 'POST' \
  'http://localhost:8000/agents/resume' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": 1, #session id of initial request
  "command": {
    "decisions": [
      {
        "type": "edit",
        "edited_action": {
          "name": "update_pull_request", #Tool name
          "args":
            {
                "owner":"organization",
                "repo":"repo-name",
                "pullNumber":67,
                "reviewers":[ "test-reviewer2" ] #Modified argument
            }
        }
      }
    ]
  }
}'
```

#### Reject
```bash
curl -X 'POST' \
  'http://localhost:8000/agents/resume' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "session_id": 1,
  "command": {
    "decisions": [
      {
        "type": "reject",
        "message": "This action is wrong because... instead do this ..."
      }
    ]
  }
}'
```

## Modifying Interrupt Tools
* To modify tools that trigger interrupt events, use the Human-In-The-Loop Agent's agent.py file: app/engine/hitl_agent_name/agent.py
* Modify the following lines:
```python
middleware = [HumanInTheLoopMiddleware(
    interrupt_on= { 
        "tool_1_name": 
        {
            "allowed_decisions": ['approve', 'reject'] #Only allow approve/reject decisions
        },
        "tool_2_name": True, #Allow all decisions (approve/edit/reject)
        "tool_3_name": False, #Don't require a decision, approve automatically
        #Add additional tools if necessary with specifications here
        #Remove any tools to not trigger interrupt events
    }
)]
```