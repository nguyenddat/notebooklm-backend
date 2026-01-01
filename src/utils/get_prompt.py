from langchain_core.prompts import ChatPromptTemplate

from utils.chatbot.parsers import summarize_history_parser, notebook_chat_parser
from utils.chatbot.prompts import summarize_history_prompt, notebook_chat_prompt

def get_prompt_by_task(task: str):
    if task == "summarize_history":
        prompt_template = summarize_history_prompt.propmt
        parser = summarize_history_parser.parser
    
    elif task == "notebook_chat":
        prompt_template = notebook_chat_prompt.propmt
        parser = notebook_chat_parser.parser
    
    else:
        raise ValueError(f"Unknown task: {task}")
    
    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", prompt_template + """{format_instructions}"""),
            ("human", "{question}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    return prompt_template, parser
