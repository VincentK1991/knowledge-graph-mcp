#!/usr/bin/env python3
"""
Schema Manager Utility

A command-line utility to manage knowledge graph schemas:
- List available schemas
- Validate schema files
- Convert between YAML and Python formats
- Generate schema summaries
- Merge multiple schemas
"""

import argparse
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from knowledge_graph_mcp.resources.schema_loader import YAMLSchemaLoader


def list_schemas(loader: YAMLSchemaLoader):
    """List all available schema files."""
    schemas = loader.get_available_schemas()
    if not schemas:
        print("No schema files found.")
        return

    print("Available schemas:")
    for schema_name in schemas:
        try:
            metadata = loader.get_schema_metadata(schema_name)
            print(f"  • {schema_name}")
            print(f"    Name: {metadata.name}")
            print(f"    Version: {metadata.version}")
            print(f"    Description: {metadata.description}")
            print(f"    Categories: {', '.join(metadata.categories)}")
            print()
        except Exception as e:
            print(f"  • {schema_name} (Error loading: {e})")


def validate_schema(loader: YAMLSchemaLoader, schema_name: str):
    """Validate a schema file."""
    try:
        loader.load_schema(schema_name)
        entity_types = loader.get_entity_types(schema_name)
        relationships = loader.get_relationships(schema_name)

        print(f"✅ Schema '{schema_name}' is valid!")
        print(f"   Entity types: {len(entity_types)}")
        print(f"   Relationships: {len(relationships)}")

        # Check for common issues
        warnings = []

        # Check for entities referenced in relationships but not defined
        defined_entities = set(entity_types.keys())
        referenced_entities = set()

        for rel in relationships:
            referenced_entities.add(rel.get('from', ''))
            referenced_entities.add(rel.get('to', ''))

        undefined_entities = referenced_entities - defined_entities - {''}
        if undefined_entities:
            warnings.append(f"Undefined entities referenced in relationships: {', '.join(undefined_entities)}")

        # Check for duplicate relationship definitions
        rel_signatures = []
        for rel in relationships:
            signature = (rel.get('from'), rel.get('to'), rel.get('type'))
            if signature in rel_signatures:
                warnings.append(f"Duplicate relationship: {signature}")
            rel_signatures.append(signature)

        if warnings:
            print("\n⚠️  Warnings:")
            for warning in warnings:
                print(f"   {warning}")

    except Exception as e:
        print(f"❌ Schema '{schema_name}' is invalid: {e}")


def show_summary(loader: YAMLSchemaLoader, schema_name: str):
    """Show a summary of a schema."""
    try:
        summary = loader.create_schema_summary(schema_name)
        metadata = summary['metadata']
        stats = summary['statistics']

        print(f"Schema Summary: {metadata['name']}")
        print(f"Version: {metadata['version']}")
        print(f"Description: {metadata['description']}")
        print()

        print("Statistics:")
        print(f"  Entity Types: {stats['total_entity_types']}")
        print(f"  Relationships: {stats['total_relationships']}")
        print(f"  Unique Relationship Types: {stats['unique_relationship_types']}")
        print(f"  Categories: {stats['categories_count']}")
        print()

        print("Entity Categories:")
        for category, entities in summary['entity_categories'].items():
            print(f"  {category}: {len(entities)} entities")
            for entity in sorted(entities):
                print(f"    • {entity}")
        print()

        print("Relationship Types:")
        for rel_type in summary['relationship_types']:
            print(f"  • {rel_type}")

    except Exception as e:
        print(f"❌ Error generating summary for '{schema_name}': {e}")


def convert_to_python(loader: YAMLSchemaLoader, schema_name: str, output_file: str):
    """Convert a YAML schema to Python class format."""
    try:
        python_code = loader.export_to_python_class(schema_name)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(python_code)
            print(f"✅ Python class written to {output_file}")
        else:
            print(python_code)

    except Exception as e:
        print(f"❌ Error converting schema '{schema_name}' to Python: {e}")


def merge_schemas(loader: YAMLSchemaLoader, schema_names: list, output_file: str):
    """Merge multiple schemas into one."""
    try:
        merged = loader.merge_schemas(*schema_names)

        # Convert back to YAML format
        import yaml
        yaml_content = yaml.dump(merged, default_flow_style=False, sort_keys=False)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(yaml_content)
            print(f"✅ Merged schema written to {output_file}")
        else:
            print(yaml_content)

    except Exception as e:
        print(f"❌ Error merging schemas {schema_names}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage knowledge graph schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python schema_manager.py list
  python schema_manager.py validate software_engineering
  python schema_manager.py summary medical_domain
  python schema_manager.py convert software_engineering --output schema.py
  python schema_manager.py merge software_engineering medical_domain --output combined.yaml
        """
    )

    parser.add_argument(
        "--schemas-dir",
        help="Directory containing schema files (default: ../schemas)"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    subparsers.add_parser('list', help='List all available schemas')

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a schema file')
    validate_parser.add_argument('schema_name', help='Name of the schema to validate')

    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show schema summary')
    summary_parser.add_argument('schema_name', help='Name of the schema to summarize')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert YAML schema to Python')
    convert_parser.add_argument('schema_name', help='Name of the schema to convert')
    convert_parser.add_argument('--output', '-o', help='Output file (default: stdout)')

    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple schemas')
    merge_parser.add_argument('schema_names', nargs='+', help='Names of schemas to merge')
    merge_parser.add_argument('--output', '-o', required=True, help='Output file for merged schema')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize the schema loader
    schemas_dir = args.schemas_dir
    if schemas_dir is None:
        # Default to schemas directory relative to this script
        schemas_dir = Path(__file__).parent.parent / "schemas"

    loader = YAMLSchemaLoader(schemas_dir)

    # Execute the requested command
    if args.command == 'list':
        list_schemas(loader)
    elif args.command == 'validate':
        validate_schema(loader, args.schema_name)
    elif args.command == 'summary':
        show_summary(loader, args.schema_name)
    elif args.command == 'convert':
        convert_to_python(loader, args.schema_name, args.output)
    elif args.command == 'merge':
        merge_schemas(loader, args.schema_names, args.output)


if __name__ == '__main__':
    main()
