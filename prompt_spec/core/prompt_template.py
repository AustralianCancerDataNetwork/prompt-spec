from pydantic import BaseModel
from typing import Optional, Type, List
from enum import Enum

class PromptExample(BaseModel):
    input: str
    output: BaseModel

class PromptType(str, Enum):
    zero_shot = "zero_shot"
    few_shot = "few_shot"
    instruction_following = "instruction_following"
    extraction = "extraction"
    classification = "classification"

class PromptTemplate(BaseModel):
    system: Optional[str] = None
    instruction: str
    output_model: Type[BaseModel]
    examples: List[PromptExample] = []

    def render(self, user_input: str) -> str:
        # build few-shot block
        examples_block = "\n\n".join([
            f"Input:\n{ex.input}\nOutput:\n{ex.output.model_dump_json(indent=2)}"
            for ex in self.examples
        ]) if self.examples else ""

        # assemble full prompt
        return (
            (self.system + "\n\n") if self.system else "" +
            self.instruction.strip() +
            ("\n\nExamples:\n" + examples_block if examples_block else "") +
            "\n\nUser Input:\n" + user_input
        )

PromptExample.model_rebuild()
PromptTemplate.model_rebuild()
