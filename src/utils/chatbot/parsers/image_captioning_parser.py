from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser

class ImageCaptionResponse(BaseModel):
    description: str = Field(
        ...,
        description=(
            "A single, complete paragraph that fully describes the image. "
            "The description must include all visible content such as text, formulas, labels, diagrams, or symbols, "
            "and clearly explain how the image relates to the provided context."
        )
    )


image_captioning_parser = PydanticOutputParser(
    pydantic_object=ImageCaptionResponse
)