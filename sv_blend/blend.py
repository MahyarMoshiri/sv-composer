from .spaces import new_space

def blend(a: dict, b: dict) -> dict:
    # safe union (stub)
    g = new_space()
    return {"blend": {**a, **b}, "graph_nodes": len(g)}
