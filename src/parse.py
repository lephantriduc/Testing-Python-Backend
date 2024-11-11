import ast

def parse(code):
    tree = ast.parse(code)
    parsed_data = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            parsed_data.append({
                "type": "function",
                "name": node.name,
                "body": node.body
            })

        elif isinstance(node, ast.ClassDef):
            parsed_data.append({
                "type": "class",
                "name": node.name,
                "body": node.body
            })

        elif isinstance(node, ast.Expr):
            parsed_data.append({
                "type": "expr",
                "name": node.value,
                "body": node.value
            })

        elif isinstance(node, ast.Assign):
            parsed_data.append({
                "type": "assign",
                "targets": node.targets,
                "value": node.value
            })

    return parsed_data
