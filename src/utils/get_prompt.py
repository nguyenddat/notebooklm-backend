from langchain_core.prompts import ChatPromptTemplate

from utils.chatbot.parsers import summarize_history_parser, notebook_chat_parser, \
    image_captioning_parser, correct_section_structure_parser
from utils.chatbot.prompts import summarize_history_prompt, notebook_chat_prompt, \
    image_captioning_prompt, correct_section_structure_prompt

def get_prompt_by_task(task: str):
    if task == "summarize_history":
        prompt_template = summarize_history_prompt.propmt
        parser = summarize_history_parser.parser
    
    elif task == "notebook_chat":
        prompt_template = notebook_chat_prompt.prompt
        parser = notebook_chat_parser.parser
    
    elif task == "image_captioning":
        prompt_template = image_captioning_prompt.prompt
        parser = image_captioning_parser.parser
    
    elif task == "correct_section_structure":
        prompt_template = correct_section_structure_prompt.prompt
        parser = correct_section_structure_parser.parser
    
    else:
        raise ValueError(f"Unknown task: {task}")
    

    # Messages
    system_message = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template + "\n{format_instructions}"),
        ]
    ).partial(
        format_instructions=parser.get_format_instructions() if parser else ""
    )
    return system_message, parser