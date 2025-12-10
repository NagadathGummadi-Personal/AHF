#!/usr/bin/env python3
"""
Generate Dart Code from JSON Schema.

This script generates Dart model classes and form builders from
the exported JSON schemas with UI metadata.

Usage:
    python scripts/generate_flutter.py

Output:
    frontend/lib/generated/models/*.dart
    frontend/lib/generated/forms/*.dart
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent


def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def to_pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return ''.join(x.title() for x in snake_str.split('_'))


def json_type_to_dart(json_type: str, format_hint: Optional[str] = None) -> str:
    """Convert JSON schema type to Dart type."""
    type_map = {
        "string": "String",
        "integer": "int",
        "number": "double",
        "boolean": "bool",
        "array": "List<dynamic>",
        "object": "Map<String, dynamic>",
    }
    return type_map.get(json_type, "dynamic")


def get_dart_type(prop: Dict[str, Any], prop_name: str, definitions: Dict[str, Any]) -> str:
    """
    Get Dart type for a JSON schema property.
    """
    # Handle non-dict types
    if not isinstance(prop, dict):
        return "dynamic"
    
    # Handle $ref
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        return ref_name
    
    # Handle anyOf (nullable types)
    if "anyOf" in prop:
        types = [t for t in prop["anyOf"] if isinstance(t, dict) and t.get("type") != "null"]
        if types:
            return get_dart_type(types[0], prop_name, definitions)
        return "dynamic"
    
    # Handle enum
    if "enum" in prop:
        # Check if this is a known enum
        return "String"  # Default to String for enums
    
    json_type = prop.get("type", "string")
    
    # Handle arrays
    if json_type == "array":
        items = prop.get("items", {})
        if items and isinstance(items, dict):
            item_type = get_dart_type(items, prop_name, definitions)
            return f"List<{item_type}>"
        return "List<dynamic>"
    
    # Handle objects with properties (nested models)
    if json_type == "object" and "properties" in prop:
        return "Map<String, dynamic>"
    
    # Handle additionalProperties (Dict)
    if json_type == "object" and "additionalProperties" in prop:
        additional = prop["additionalProperties"]
        if isinstance(additional, dict):
            value_type = get_dart_type(additional, prop_name, definitions)
            return f"Map<String, {value_type}>"
        elif additional is True:
            return "Map<String, dynamic>"
        return "Map<String, dynamic>"
    
    return json_type_to_dart(json_type, prop.get("format"))


def generate_enum_class(name: str, enum_data: Dict[str, Any]) -> str:
    """Generate Dart enum class."""
    values = enum_data.get("values", [])
    labels = enum_data.get("labels", {})
    
    lines = [f"enum {name} {{"]
    
    for value in values:
        dart_name = to_camel_case(value.replace("-", "_"))
        lines.append(f"  {dart_name}('{value}'),")
    
    lines.append("  ;")
    lines.append("")
    lines.append("  final String value;")
    lines.append(f"  const {name}(this.value);")
    lines.append("")
    lines.append(f"  static {name} fromString(String? value) {{")
    lines.append("    if (value == null) return values.first;")
    lines.append("    return values.firstWhere(")
    lines.append("      (e) => e.value == value,")
    lines.append("      orElse: () => values.first,")
    lines.append("    );")
    lines.append("  }")
    lines.append("")
    lines.append("  String get label {")
    lines.append("    switch (this) {")
    
    for value in values:
        dart_name = to_camel_case(value.replace("-", "_"))
        label = labels.get(value, value)
        lines.append(f"      case {name}.{dart_name}:")
        lines.append(f"        return '{label}';")
    
    lines.append("    }")
    lines.append("  }")
    lines.append("}")
    
    return "\n".join(lines)


def generate_model_class(
    name: str,
    schema: Dict[str, Any],
    definitions: Dict[str, Any]
) -> str:
    """Generate Dart model class from JSON schema."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    
    lines = [f"class {name} {{"]
    
    # Generate fields
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        dart_type = get_dart_type(prop, prop_name, definitions)
        
        # Check if nullable
        is_nullable = prop_name not in required or "anyOf" in prop
        nullable_suffix = "?" if is_nullable else ""
        
        # Add documentation from UI metadata
        ui = prop.get("ui", {})
        if ui.get("display_name"):
            lines.append(f"  /// {ui['display_name']}")
        if ui.get("help_text"):
            lines.append(f"  /// {ui['help_text']}")
        
        lines.append(f"  final {dart_type}{nullable_suffix} {dart_name};")
    
    lines.append("")
    
    # Generate constructor
    lines.append(f"  const {name}({{")
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        is_required = prop_name in required and "anyOf" not in prop
        prefix = "required " if is_required else ""
        lines.append(f"    {prefix}this.{dart_name},")
    lines.append("  });")
    lines.append("")
    
    # Generate fromJson
    lines.append(f"  factory {name}.fromJson(Map<String, dynamic> json) {{")
    lines.append(f"    return {name}(")
    
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        dart_type = get_dart_type(prop, prop_name, definitions)
        
        # Handle different types
        json_type = prop.get("type", "string")
        
        if dart_type.startswith("List<"):
            item_type = dart_type[5:-1]
            if item_type in ["String", "int", "double", "bool", "dynamic"]:
                lines.append(f"      {dart_name}: (json['{prop_name}'] as List?)?.cast<{item_type}>(),")
            else:
                lines.append(f"      {dart_name}: (json['{prop_name}'] as List?)")
                lines.append(f"          ?.map((e) => {item_type}.fromJson(e as Map<String, dynamic>))")
                lines.append(f"          .toList(),")
        elif dart_type.startswith("Map<String,"):
            lines.append(f"      {dart_name}: json['{prop_name}'] != null")
            lines.append(f"          ? Map<String, dynamic>.from(json['{prop_name}'])")
            lines.append(f"          : null,")
        elif dart_type == "int":
            lines.append(f"      {dart_name}: json['{prop_name}'] as int?,")
        elif dart_type == "double":
            lines.append(f"      {dart_name}: (json['{prop_name}'] as num?)?.toDouble(),")
        elif dart_type == "bool":
            lines.append(f"      {dart_name}: json['{prop_name}'] as bool?,")
        elif dart_type == "String":
            lines.append(f"      {dart_name}: json['{prop_name}'] as String?,")
        else:
            # Assume it's a nested model
            lines.append(f"      {dart_name}: json['{prop_name}'] != null")
            lines.append(f"          ? {dart_type}.fromJson(json['{prop_name}'] as Map<String, dynamic>)")
            lines.append(f"          : null,")
    
    lines.append("    );")
    lines.append("  }")
    lines.append("")
    
    # Generate toJson
    lines.append("  Map<String, dynamic> toJson() {")
    lines.append("    return {")
    
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        dart_type = get_dart_type(prop, prop_name, definitions)
        
        if dart_type.startswith("List<"):
            item_type = dart_type[5:-1]
            if item_type in ["String", "int", "double", "bool", "dynamic"]:
                lines.append(f"      if ({dart_name} != null) '{prop_name}': {dart_name},")
            else:
                lines.append(f"      if ({dart_name} != null) '{prop_name}': {dart_name}!.map((e) => e.toJson()).toList(),")
        elif dart_type not in ["String", "int", "double", "bool", "dynamic"] and not dart_type.startswith("Map"):
            lines.append(f"      if ({dart_name} != null) '{prop_name}': {dart_name}!.toJson(),")
        else:
            lines.append(f"      if ({dart_name} != null) '{prop_name}': {dart_name},")
    
    lines.append("    };")
    lines.append("  }")
    lines.append("")
    
    # Generate copyWith
    lines.append(f"  {name} copyWith({{")
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        dart_type = get_dart_type(prop, prop_name, definitions)
        lines.append(f"    {dart_type}? {dart_name},")
    lines.append("  }}) {")
    lines.append(f"    return {name}(")
    for prop_name, prop in properties.items():
        dart_name = to_camel_case(prop_name)
        lines.append(f"      {dart_name}: {dart_name} ?? this.{dart_name},")
    lines.append("    );")
    lines.append("  }")
    lines.append("")
    
    # Generate default factory
    lines.append(f"  factory {name}.empty() {{")
    lines.append(f"    return const {name}();")
    lines.append("  }")
    
    lines.append("}")
    
    return "\n".join(lines)


def generate_ui_schema_class(name: str, schema: Dict[str, Any]) -> str:
    """Generate Dart class with UI schema metadata."""
    properties = schema.get("properties", {})
    
    lines = [f"class {name}UISchema {{"]
    lines.append(f"  static const String modelName = '{name}';")
    lines.append("")
    lines.append("  static const Map<String, Map<String, dynamic>> fields = {")
    
    for prop_name, prop in properties.items():
        ui = prop.get("ui", {})
        if ui:
            lines.append(f"    '{prop_name}': {{")
            for key, value in ui.items():
                if isinstance(value, str):
                    lines.append(f"      '{key}': '{value}',")
                elif isinstance(value, bool):
                    lines.append(f"      '{key}': {str(value).lower()},")
                elif isinstance(value, (int, float)):
                    lines.append(f"      '{key}': {value},")
                elif isinstance(value, list):
                    json_list = json.dumps(value)
                    lines.append(f"      '{key}': {json_list},")
            lines.append("    },")
    
    lines.append("  };")
    lines.append("")
    
    # Generate getter methods
    lines.append("  static Map<String, dynamic>? getFieldUI(String fieldName) {")
    lines.append("    return fields[fieldName];")
    lines.append("  }")
    lines.append("")
    lines.append("  static String? getDisplayName(String fieldName) {")
    lines.append("    return fields[fieldName]?['display_name'] as String?;")
    lines.append("  }")
    lines.append("")
    lines.append("  static String? getWidgetType(String fieldName) {")
    lines.append("    return fields[fieldName]?['widget_type'] as String?;")
    lines.append("  }")
    lines.append("")
    lines.append("  static String? getGroup(String fieldName) {")
    lines.append("    return fields[fieldName]?['group'] as String?;")
    lines.append("  }")
    lines.append("")
    lines.append("  static bool isVisible(String fieldName, Map<String, dynamic> formData) {")
    lines.append("    final visibleWhen = fields[fieldName]?['visible_when'] as String?;")
    lines.append("    if (visibleWhen == null) return true;")
    lines.append("    return evaluateCondition(visibleWhen, formData);")
    lines.append("  }")
    lines.append("")
    lines.append("  static bool evaluateCondition(String condition, Map<String, dynamic> data) {")
    lines.append("    // Simple condition evaluator")
    lines.append("    // Supports: field == value, field != value, field == true/false")
    lines.append("    // And compound conditions with &&")
    lines.append("    final parts = condition.split('&&').map((p) => p.trim()).toList();")
    lines.append("    for (final part in parts) {")
    lines.append("      if (!_evaluateSingleCondition(part, data)) return false;")
    lines.append("    }")
    lines.append("    return true;")
    lines.append("  }")
    lines.append("")
    lines.append("  static bool _evaluateSingleCondition(String condition, Map<String, dynamic> data) {")
    lines.append("    // Parse condition like 'enabled == true' or 'mode == \\'auto\\''")
    lines.append("    final eqMatch = RegExp(r\"(\\w+)\\s*==\\s*(.+)\").firstMatch(condition);")
    lines.append("    if (eqMatch != null) {")
    lines.append("      final field = eqMatch.group(1)!;")
    lines.append("      var value = eqMatch.group(2)!.trim();")
    lines.append("      // Remove quotes")
    lines.append("      if (value.startsWith(\"'\") && value.endsWith(\"'\")) {")
    lines.append("        value = value.substring(1, value.length - 1);")
    lines.append("      }")
    lines.append("      final fieldValue = data[field];")
    lines.append("      if (value == 'true') return fieldValue == true;")
    lines.append("      if (value == 'false') return fieldValue == false;")
    lines.append("      return fieldValue?.toString() == value;")
    lines.append("    }")
    lines.append("    final neqMatch = RegExp(r\"(\\w+)\\s*!=\\s*(.+)\").firstMatch(condition);")
    lines.append("    if (neqMatch != null) {")
    lines.append("      final field = neqMatch.group(1)!;")
    lines.append("      var value = neqMatch.group(2)!.trim();")
    lines.append("      if (value.startsWith(\"'\") && value.endsWith(\"'\")) {")
    lines.append("        value = value.substring(1, value.length - 1);")
    lines.append("      }")
    lines.append("      final fieldValue = data[field];")
    lines.append("      if (value == 'true') return fieldValue != true;")
    lines.append("      if (value == 'false') return fieldValue != false;")
    lines.append("      return fieldValue?.toString() != value;")
    lines.append("    }")
    lines.append("    return true;")
    lines.append("  }")
    lines.append("")
    lines.append("  /// Get fields grouped by their 'group' property")
    lines.append("  static Map<String, List<String>> getGroupedFields() {")
    lines.append("    final groups = <String, List<String>>{};")
    lines.append("    for (final entry in fields.entries) {")
    lines.append("      final group = entry.value['group'] as String? ?? 'default';")
    lines.append("      groups.putIfAbsent(group, () => []).add(entry.key);")
    lines.append("    }")
    lines.append("    // Sort fields within each group by order")
    lines.append("    for (final group in groups.keys) {")
    lines.append("      groups[group]!.sort((a, b) {")
    lines.append("        final orderA = fields[a]?['order'] as int? ?? 0;")
    lines.append("        final orderB = fields[b]?['order'] as int? ?? 0;")
    lines.append("        return orderA.compareTo(orderB);")
    lines.append("      });")
    lines.append("    }")
    lines.append("    return groups;")
    lines.append("  }")
    lines.append("}")
    
    return "\n".join(lines)


def generate_enums_file(enums: Dict[str, Any]) -> str:
    """Generate Dart file with all enums."""
    lines = [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by scripts/generate_flutter.py",
        "",
        "// ignore_for_file: constant_identifier_names",
        "",
    ]
    
    for name, data in enums.items():
        lines.append(generate_enum_class(name, data))
        lines.append("")
    
    return "\n".join(lines)


def generate_models_file(
    category: str,
    schemas: Dict[str, Any],
    definitions: Dict[str, Any]
) -> str:
    """Generate Dart file with model classes."""
    lines = [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by scripts/generate_flutter.py",
        "",
        "// ignore_for_file: unnecessary_this",
        "",
    ]
    
    for name, schema in schemas.items():
        lines.append(generate_model_class(name, schema, definitions))
        lines.append("")
    
    return "\n".join(lines)


def generate_ui_schemas_file(
    category: str,
    schemas: Dict[str, Any]
) -> str:
    """Generate Dart file with UI schema metadata."""
    lines = [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by scripts/generate_flutter.py",
        "",
    ]
    
    for name, schema in schemas.items():
        lines.append(generate_ui_schema_class(name, schema))
        lines.append("")
    
    return "\n".join(lines)


def generate_exports_file(schemas: Dict[str, Any]) -> str:
    """Generate barrel file exporting all generated code."""
    lines = [
        "// GENERATED CODE - DO NOT MODIFY BY HAND",
        "// Generated by scripts/generate_flutter.py",
        "",
        "// Enums",
        "export 'enums.g.dart';",
        "",
        "// Models",
        "export 'models/config_models.g.dart';",
        "export 'models/parameter_models.g.dart';",
        "export 'models/tool_models.g.dart';",
        "",
        "// UI Schemas",
        "export 'ui_schemas/config_ui_schemas.g.dart';",
        "export 'ui_schemas/parameter_ui_schemas.g.dart';",
        "export 'ui_schemas/tool_ui_schemas.g.dart';",
    ]
    
    return "\n".join(lines)


def main():
    """Main entry point."""
    input_file = PROJECT_ROOT / "frontend" / "lib" / "generated" / "tool_schemas.json"
    output_dir = PROJECT_ROOT / "frontend" / "lib" / "generated"
    
    print("Generating Dart code from JSON schemas...")
    print("-" * 50)
    
    # Load schemas
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    enums = data.get("enums", {})
    schemas = data.get("schemas", {})
    definitions = data.get("definitions", {})
    
    # Create output directories
    (output_dir / "models").mkdir(parents=True, exist_ok=True)
    (output_dir / "ui_schemas").mkdir(parents=True, exist_ok=True)
    
    # Generate enums
    enums_content = generate_enums_file(enums)
    enums_file = output_dir / "enums.g.dart"
    with open(enums_file, 'w', encoding='utf-8') as f:
        f.write(enums_content)
    print(f"  Generated: {enums_file.name}")
    
    # Generate models for each category
    for category, category_schemas in schemas.items():
        # Generate model classes
        models_content = generate_models_file(category, category_schemas, definitions)
        models_file = output_dir / "models" / f"{category}_models.g.dart"
        with open(models_file, 'w', encoding='utf-8') as f:
            f.write(models_content)
        print(f"  Generated: models/{models_file.name}")
        
        # Generate UI schema classes
        ui_content = generate_ui_schemas_file(category, category_schemas)
        ui_file = output_dir / "ui_schemas" / f"{category}_ui_schemas.g.dart"
        with open(ui_file, 'w', encoding='utf-8') as f:
            f.write(ui_content)
        print(f"  Generated: ui_schemas/{ui_file.name}")
    
    # Generate exports file
    exports_content = generate_exports_file(schemas)
    exports_file = output_dir / "generated.dart"
    with open(exports_file, 'w', encoding='utf-8') as f:
        f.write(exports_content)
    print(f"  Generated: {exports_file.name}")
    
    print("-" * 50)
    print("Done!")


if __name__ == "__main__":
    main()

