from openai import OpenAI
import json, yaml
from pathlib import Path
import os

from .utils import load_pydantic_class

def draft_prompt_with_openai(model_name: str, output_path: Path):
    """
    Uses OpenAI to generate a populated prompt template based on the
    Pydantic model structure.
    """

    # Load the Pydantic class
    model_cls = load_pydantic_class(model_name)

    # Convert model schema to JSON schema for LLM context
    schema = model_cls.model_json_schema()

    try:
        os.environ["OPENAI_API_KEY"]
    except KeyError:
        raise EnvironmentError("OPENAI_API_KEY not set in environment variables.")
    
    client = OpenAI()  # requires OPENAI_API_KEY env var

    system_msg = (
        "You are helping to create a structured clinical NLP extraction prompt.\n"
        "Given a Pydantic model schema, generate:\n"
        "1. A clear system instruction targeted at LLMs.\n"
        "2. One example input text for the task.\n"
        "3. One example JSON output that conforms strictly to the provided schema.\n"
    )

    user_msg = (
        "Here is the model schema for the NLP output:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Please generate a prompt template with:\n"
        "• system_instruction\n"
        "• example_input\n"
        "• example_output (must validate against the schema)\n"
        "Return in JSON with keys: instruction, input, output."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]
    )

    message = response.choices[0].message["content"] # type: ignore
    try:
        draft = json.loads(message)
    except json.JSONDecodeError:
        raise ValueError("OpenAI returned non-JSON output; re-run the draft-prompt command.")

    # Build YAML template
    template = {
        "output_model": model_name,
        "instruction": draft["instruction"],
        "examples": {
            "example_1": {
                "input": draft["input"],
                "output": draft["output"]
            }
        }
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(template, sort_keys=False))

    print(f"✓ Draft prompt created using OpenAI at {output_path}")
