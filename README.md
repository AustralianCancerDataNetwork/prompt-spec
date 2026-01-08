# `prompt-spec`
*A lightweight, LinkML-aligned prompt and schema management toolkit for clinical NLP & LLM workflows.*

`prompt-spec` provides:

- **Structured prompt templates**  
- **LinkML → Pydantic** auto-generation for LLM output schemas  
- **Validation of few-shot examples** within prompts
- A **shared format** for prompt libraries across collaborating groups

This toolkit is intentionally minimal and designed for stability, reuse, and strong typing when integrating with LLM libraries such as **[pydantic-instructor](https://python.useinstructor.com/)**

---

# Project Structure

```text
prompt-spec/
├── cli.py                        ← Main command line interface
├── core/
│   └── prompt_template.py        ← Prompt class utilities
├── engines/
│   ├── __init__.py
│   └── instructor_engine.py      ← Wrapper function for integrating prompts with ontoGPT via Instructor interface
├── output_models/
│   └── condition_model.yaml      ← LinkML schema for defining model outputs - create new endpoint definitions here
├── generated_models/
│   └── (auto-generated pydantic models)
└── prompts/
    └── condition_prompt.yaml     ← This is where the actual prompt definitions exist
```

---

# Installation

`uv pip install -e .`

---

# Usage

## 1. Defining LinkML output models

Place all LinkML schemas inside `prompt-spec/output_models`

Example: *condition_model.yaml*

```yaml
name: ConditionList
id: https://example.org/condition_model
prefixes:
  linkml: https://w3id.org/linkml/
default_range: string

classes:
  Condition:
    attributes:
      label: string
      verbatim_name: string
      codable_name: string
      who_diagnosed: string
      is_negated: boolean

  ConditionList:
    attributes:
      conditions:
        multivalued: true
        range: Condition
```

## 2. Generate Pydantic models from LinkML

`prompt-spec build-models`

This reads all `*.yaml` schemas in `prompt-spec/output_models/` and generates Pydantic classes into `prompt-spec/generated_models/`.

After running this, you will have files such as:

* `prompt-spec/generated_models/ConditionList.py`

Alternatively, run for just one class update at a time: `prompt-spec generate-pydantic-from-linkml output_models/condition_model.yaml`

## 3. Populate prompt template

`prompt-spec create-empty-prompt condition_model prompts/condition_prompt.yaml`

This produces:

```yaml
output_model: condition_model
instruction: "<<< fill in your system prompt here >>>"
examples:
  example_1:
    input: "<<< sample input text here >>>"
    output:
      conditions: []
```

## 4. Validate a prompt against its template

`prompt-spec validate-prompt condition_prompt.yaml`

