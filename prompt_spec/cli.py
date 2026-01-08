import typer, subprocess, yaml
from pathlib import Path
from linkml_runtime import SchemaView
from pydantic import ValidationError

from .core.utils import load_pydantic_class, OUTPUT_MODELS_DIR, PROMPTS_DIR, GENERATED_MODELS_DIR, get_template_for_model, dump_example_output, load_output_field

app = typer.Typer(help="prompt-spec command line tools")

@app.command("generate-pydantic-from-linkml")
def generate_pydantic_from_linkml(schema_path: Path):
    """
    Generate a single Pydantic model from a LinkML schema using the linkml-gen-pydantic command.
    """
    GENERATED_MODELS_DIR.mkdir(exist_ok=True)
    module_name = schema_path.stem

    # linkml command
    cmd = [
        "gen-pydantic",
        str(schema_path)
    ]

    typer.echo(f"Generating Pydantic model from {schema_path.name} ...")

    output_file = GENERATED_MODELS_DIR / f"{module_name}.py"
    with open(output_file, "w") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, check=True)

    typer.echo(f"✓ Generated Pydantic models for {module_name}")

@app.command("build-models")
def build_models():
    """
    Generate Pydantic classes from all LinkML schemas in output_models/.
    """
    schemas = list(OUTPUT_MODELS_DIR.glob("*.yaml"))
    if not schemas:
        typer.echo("No LinkML schema files found in output_models/")
        raise typer.Exit(code=1)

    for schema in schemas:
        generate_pydantic_from_linkml(schema)

    typer.echo("🎉 Finished generating all Pydantic models.")


@app.command("create-empty-prompt")
def create_empty_prompt(model_name: str, output_path: Path):
    """Create an empty YAML prompt template for a given output model."""

    model_cls = load_pydantic_class(model_name)
    schema_path = OUTPUT_MODELS_DIR / f"{model_name}.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(f"No LinkML schema found at {schema_path}")

    sv = SchemaView(schema_path)

    template = get_template_for_model(sv, model_name, model_cls, output_path)

    if output_path.exists():
        print(f"⚠ File already exists: {output_path}")

        choice = typer.prompt(
            "Choose action: [c]ancel, [o]verwrite, [v]ersioned copy",
            default="c"
        ).lower()

        if choice.startswith("c"):
            print("✘ Cancelled.")
            raise typer.Exit()

        elif choice.startswith("v"):
            base = output_path.stem
            suffix = output_path.suffix
            parent = output_path.parent

            version = 2
            new_path = parent / f"{base}_v{version}{suffix}"
            while new_path.exists():
                version += 1
                new_path = parent / f"{base}_v{version}{suffix}"

            print(f"↪ Saving versioned file as {new_path}")
            output_path = new_path
    dump_example_output(template, output_path)
    print(f"✓ Empty prompt created at {output_path}")


@app.command("validate-prompt")
def validate_prompt(
    prompt_file: str = typer.Argument(..., help="YAML prompt file to validate"),
):
    """
    Validate a prompt YAML file against its linked Pydantic output model.
    """
    prompt_path = PROMPTS_DIR / prompt_file
    if not prompt_path.exists():
        typer.echo(f"❌ Prompt file not found: {prompt_file}")
        raise typer.Exit(code=1)

    typer.echo(f"Validating prompt: {prompt_file}")

    with open(prompt_path) as f:
        data = yaml.safe_load(f)

    model_name = data.get("output_model")
    examples = data.get("examples", {})

    if not model_name:
        typer.echo("❌ Prompt YAML must contain an 'output_model' field.")
        raise typer.Exit(code=1)

    try:
        model_class = load_pydantic_class(model_name)
    except Exception as e:
        typer.echo(f"❌ Could not import generated model '{model_name}': {e}")
        raise typer.Exit(code=1)

    # Validate examples
    errors = False
    for example in examples:
        example_text = example['input']
        example_output = load_output_field(example['output'])
        try:
            model_class.model_validate(example_output)
        except ValidationError as e:
            typer.echo(f"\n❌ Validation error in example:\n  \"{example_text[:80]}...\"\n{str(e)}")
            errors = True
    if errors:
        typer.echo("\n❌ Prompt validation failed.")
        raise typer.Exit(code=1)
    else:
        typer.echo("✅ Prompt validated successfully.")

def main():
    app()

if __name__ == "__main__":
    main()