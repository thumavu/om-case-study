#!/usr/bin/env python3

import json
import sys
from pathlib import Path


INDENT = "  "
SKIP_KEYS = {"id", "output"}
ALLOWED_UPDATE_PATHS = {"tags.GitCommitHash"}
OUTPUT_DIR_NAME = "generated-tf"


class RawExpression(str):
    pass


def to_hcl(value, level=0):
    padding = INDENT * level
    next_padding = INDENT * (level + 1)

    if isinstance(value, RawExpression):
        return str(value)

    if isinstance(value, dict):
        if not value:
            return "{}"

        lines = ["{"]
        for key, nested_value in value.items():
            if nested_value is None:
                continue
            lines.append(f"{next_padding}{key} = {to_hcl(nested_value, level + 1)}")
        lines.append(f"{padding}}}")
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return "[]"

        if all(not isinstance(item, (dict, list)) for item in value):
            return json.dumps(value)

        lines = ["["]
        for item in value:
            lines.append(f"{next_padding}{to_hcl(item, level + 1)},")
        lines.append(f"{padding}]")
        return "\n".join(lines)

    if isinstance(value, str):
        return json.dumps(value)
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "null"

    return str(value)


def walk_planned_modules(module):
    resources = list(module.get("resources", []))

    for child_module in module.get("child_modules", []):
        resources.extend(walk_planned_modules(child_module))

    return resources


def walk_config_modules(module):
    resources = list(module.get("resources", []))

    for module_call in module.get("module_calls", {}).values():
        child_module = module_call.get("module")
        if isinstance(child_module, dict):
            resources.extend(walk_config_modules(child_module))

    return resources


def expression_value(expression):
    if not isinstance(expression, dict):
        return None

    if "constant_value" in expression:
        return expression["constant_value"]

    references = expression.get("references", [])
    if references:
        return RawExpression(references[0])

    return None


def resource_values(resource):
    if isinstance(resource.get("values"), dict):
        return resource["values"]

    after = resource.get("change", {}).get("after")
    if isinstance(after, dict):
        return after

    expressions = resource.get("expressions", {})
    values = {}

    if "for_each_expression" in resource:
        values["for_each"] = expression_value(resource["for_each_expression"])

    for key, expression in expressions.items():
        if isinstance(expression, list):
            values[key] = []
            for item in expression:
                block = {}
                for nested_key, nested_expression in item.items():
                    block[nested_key] = expression_value(nested_expression)
                values[key].append(block)
        else:
            values[key] = expression_value(expression)

    return values


def find_resources(plan):
    planned_root = plan.get("planned_values", {}).get("root_module")
    if isinstance(planned_root, dict):
        resources = walk_planned_modules(planned_root)
        if resources:
            return resources

    resources = []
    for resource in plan.get("resource_changes", []):
        after = resource.get("change", {}).get("after")
        if isinstance(after, dict):
            resources.append(resource)
    if resources:
        return resources

    config_root = plan.get("configuration", {}).get("root_module")
    if isinstance(config_root, dict):
        resources = walk_config_modules(config_root)
        if resources:
            return resources

    return []


def find_changed_paths(before, after, prefix=""):
    if before == after:
        return set()

    if isinstance(before, dict) and isinstance(after, dict):
        changed_paths = set()

        for key in set(before) | set(after):
            child_prefix = f"{prefix}.{key}" if prefix else key

            if key not in before or key not in after:
                changed_paths.add(child_prefix)
                continue

            changed_paths.update(
                find_changed_paths(before[key], after[key], child_prefix)
            )

        return changed_paths

    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return {prefix or "<root>"}

        changed_paths = set()
        for index, (before_item, after_item) in enumerate(zip(before, after)):
            child_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            changed_paths.update(
                find_changed_paths(before_item, after_item, child_prefix)
            )

        return changed_paths

    return {prefix or "<root>"}


def validate_allowed_actions(plan):
    invalid_changes = []

    for resource in plan.get("resource_changes", []):
        actions = resource.get("change", {}).get("actions", [])
        if not actions:
            continue

        if actions == ["create"]:
            continue

        if actions == ["update"]:
            before = resource.get("change", {}).get("before") or {}
            after = resource.get("change", {}).get("after") or {}
            changed_paths = find_changed_paths(before, after)
            disallowed_paths = sorted(
                path for path in changed_paths if path not in ALLOWED_UPDATE_PATHS
            )

            if not disallowed_paths:
                continue

            invalid_changes.append(
                f'{resource.get("address", "unknown")}: modifies {", ".join(disallowed_paths)}. '
                "Action required: revert every change except tags.GitCommitHash."
            )
            continue

        actions_text = ", ".join(actions)
        invalid_changes.append(
            f'{resource.get("address", "unknown")}: action {actions_text} is not allowed. '
            "Action required: regenerate the plan so this resource is only created, "
            "or updated only for tags.GitCommitHash."
        )

    if invalid_changes:
        details = "\n".join(invalid_changes)
        raise ValueError(
            "The plan may only create resources or update tags.GitCommitHash.\n"
            f"Blocked changes:\n{details}"
        )


def render_resource(resource):
    block_type = "data" if resource.get("mode") == "data" else "resource"
    body = resource_values(resource)

    lines = [f'{block_type} "{resource["type"]}" "{resource["name"]}" {{']

    for key, value in body.items():
        if key in SKIP_KEYS or value is None:
            continue
        lines.append(f"{INDENT}{key} = {to_hcl(value, 1)}")

    lines.append("}")
    return "\n".join(lines)


def convert_file(input_path, output_path):
    with input_path.open("r", encoding="utf-8") as file:
        plan = json.load(file)

    validate_allowed_actions(plan)

    resources = find_resources(plan)
    if not resources:
        raise ValueError("No resources found in the JSON file.")

    output = "\n\n".join(render_resource(resource) for resource in resources) + "\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        file.write(output)


def main():
    if len(sys.argv) not in {2, 3}:
        print("Usage: python script.py <input.json> [output.tf]")
        return 1

    input_path = Path(sys.argv[1])
    default_output_path = input_path.parent / OUTPUT_DIR_NAME / input_path.with_suffix(".tf").name
    output_path = Path(sys.argv[2]) if len(sys.argv) == 3 else default_output_path

    try:
        convert_file(input_path, output_path)
    except FileNotFoundError:
        print(f"File not found: {input_path}")
        return 1
    except json.JSONDecodeError:
        print(f"Invalid JSON file: {input_path}")
        return 1
    except ValueError as error:
        print(error)
        return 1

    print(f"Created {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
