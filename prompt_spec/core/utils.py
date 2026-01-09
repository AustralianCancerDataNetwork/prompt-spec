from pathlib import Path
from linkml_runtime import SchemaView
from linkml.utils.datautils import infer_root_class
import importlib.util, json
from ruamel.yaml.scalarstring import LiteralScalarString

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_MODELS_DIR = BASE_DIR / "output_models"
GENERATED_MODELS_DIR = BASE_DIR / "generated_models"
PROMPTS_DIR = BASE_DIR / "prompts"

def load_output_field(output):
    """Convert YAML-loaded output field into a Python dict if needed."""
    if isinstance(output, str):
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            raise ValueError("Output block must contain valid JSON.")
    return output


def build_example_output(output_dict):
    """Convert structured example to pretty JSON in literal block form."""
    return LiteralScalarString(
        json.dumps(output_dict, indent=2)
    )

def dump_example_output(template: dict, output_path: Path):
    from ruamel.yaml import YAML
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 10000  # disable wrapping
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        yaml.dump(template, f)

def abbreviate_enum(enum):
    """Render enum as <<enum|a,b,c>>."""
    vals = list(enum.permissible_values.keys())
    return f"<<enum|{','.join(vals)}>>"

def is_local_class(sv: SchemaView, class_name: str) -> bool:
    """Return True if this class is defined in this schema file (not imported)."""
    return class_name in sv.schema.classes # type: ignore

def get_template_for_model(sv: SchemaView, model_name: str, model_cls, output_path: Path) -> dict:
    """Return a default prompt template structure for a given model."""
    empty_output = build_json_example(sv, model_cls.__name__)
    json_block = build_example_output(empty_output)

    template = {
        "name": f"{model_name}_extraction",
        "prompt_type": "few_shot",
        "system": LiteralScalarString(
            "Act as a medical data entry specialist.\n"
            "Extract all conditions ... etc."
        ),
        "instruction": "Extract all conditions mentioned in the text...",
        "output_model": model_name,
        "examples": [
            {
                "input": "<<example text>>",
                "output": json_block
            }
        ],
    }
    return template

def placeholder_for_slot(sv, slot):
    """Return a placeholder appropriate for the slot's type."""
    range_name = slot.range

    # Enumerations
    if range_name in sv.all_enums():
        enum = sv.get_enum(range_name)
        return abbreviate_enum(enum)
    # Primitive types
    if range_name in ("string", "str"):
        return "<<string>>"
    if range_name in ("integer", "int"):
        return "<<integer>>"
    if range_name in ("float", "double"):
        return "<<number>>"
    if range_name == "boolean":
        return "<<boolean>>"
    # Nested class
    if sv.get_class(range_name) and is_local_class(sv, range_name):
        return build_json_example(sv, range_name)
    # Fallback
    return "<<value>>"

def build_json_example(sv: SchemaView, class_name: str) -> dict:
    """Construct a *clean* schema-aware JSON-compatible dict with placeholders."""
    output = {}

    for slot_name in sv.class_slots(class_name):
        slot = sv.induced_slot(slot_name, class_name)
        ph = placeholder_for_slot(sv, slot)

        if slot.multivalued:
            output[slot_name] = [ph]
        else:
            output[slot_name] = ph

    return output

def load_pydantic_class(model_name: str, schema: str | Path | None = None):
    """
    Load a generated Pydantic class corresponding to the LinkML tree root.

    Steps:
    1. Load the LinkML schema (YAML).
    2. Infer the root class using LinkML's official mechanism.
    3. Load that class from the generated Pydantic module.
    4. Fall back to filename→CamelCase if needed.
    """
    schema_path: Path

    if schema is None:
        schema_path = OUTPUT_MODELS_DIR / f"{model_name}.yaml"
    else:
        schema_path = Path(schema)
    
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Schema not found: {schema_path}. Expected LinkML schema for '{model_name}'."
        )

    sv = SchemaView(schema_path)
    root_class_name = infer_root_class(sv)

    if not root_class_name:
        raise RuntimeError(
            f"Could not infer a root class for schema: {schema_path}. "
            "Ensure that at least one class has `tree_root: true` or is inferable."
        )

    module_path = GENERATED_MODELS_DIR / f"{model_name}.py"
    if not module_path.exists():
        raise FileNotFoundError(
            f"Pydantic model file not found: {module_path}. "
            f"Run `prompt-spec generate-pydantic-from-linkml for {model_name}` first."
        )

    spec = importlib.util.spec_from_file_location(model_name, module_path)
    module = importlib.util.module_from_spec(spec) # type: ignore
    spec.loader.exec_module(module) # type: ignore

    # Try to load the inferred class
    if hasattr(module, root_class_name):
        return getattr(module, root_class_name)

    # if we cannot find an inferred tree_root, assume class has same name as file but in CamelCase
    fallback_class = "".join(p.capitalize() for p in model_name.split("_"))
    if hasattr(module, fallback_class):
        return getattr(module, fallback_class)

    available = [k for k, v in module.__dict__.items() if isinstance(v, type)]
    raise AttributeError(
        f"Could not locate the inferred root class '{root_class_name}' "
        f"in generated module {module_path}.\n"
        f"Available classes: {available}"
    )
