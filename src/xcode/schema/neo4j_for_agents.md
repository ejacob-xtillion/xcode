# Neo4j Knowledge Graph Schema (for agents)

Use this schema to write Cypher queries against the codebase knowledge graph built by xgraph.

## Node labels

| Label | Meaning |
|-------|---------|
| Project | Root project (id: `project:{project_name}`) |
| Folder | Directory |
| File | Source file (has `path`) |
| Class | Class definition |
| Callable | Function or method |
| Test | Test function or method |
| Module | Imported module |
| Variable | Variable |
| Namespace, Interface, Constructor, Property, Struct, Record, Enum | C#-specific |

## Relationship types

- **DECLARED_IN** – element declared in File/Class (e.g. Callable → File)
- **IMPORTS** – File imports Module
- **INHERITS_FROM** – Class → Class
- **USES** – Callable/Test uses another Callable/Class/Variable
- **TESTS** – Test exercises a Callable
- **INCLUDED_IN** – File/Folder in Project/Folder

## Node properties

Nodes are merged on `id`. Common properties: `id`, `name`, `type`, `path`, `line_number`, `description` (if descriptions enabled).

## Project scoping

When multiple repos share one Neo4j DB, scope queries by project:

```cypher
MATCH (p:Project {name: $projectName})
RETURN p
```

Then traverse from `p` via INCLUDED_IN, DECLARED_IN, etc.

## Example Cypher queries

### Callables that use a given name (e.g. "payment")

```cypher
MATCH (c:Callable)-[:USES]->(target)
WHERE target.name CONTAINS 'payment'
RETURN c.name, c.path, c.line_number
```

### Tests that cover a callable

```cypher
MATCH (t:Test)-[:TESTS]->(c:Callable {name: 'process_payment'})
RETURN t.name, t.path
```

### File and its callables

```cypher
MATCH (f:File {path: 'src/payments/client.py'})<-[:DECLARED_IN]-(c:Callable)
RETURN c.name, c.line_number
```

### Class and its methods; inheritance

```cypher
MATCH (c:Class)-[:INHERITS_FROM*0..]->(base:Class)
WHERE c.name = 'PaymentClient'
RETURN c, base
```
