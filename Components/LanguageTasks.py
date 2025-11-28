from pydantic import BaseModel,Field
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API")

if not api_key:
    raise ValueError("API key not found. Make sure it is defined in the .env file.")

class JSONResponse(BaseModel):
    """
    The response should strictly follow the following structure: -
     [
        {
        start: "Start time of the clip",
        content: "Highlight Text",
        end: "End Time for the highlighted clip"
        }
     ]
    """
    start: float = Field(description="Start time of the clip")
    content: str= Field(description="Highlight Text")
    end: float = Field(description="End time for the highlighted clip")

system = """

Based on the Transcription user provides with start and end, highlight the most interesting <1 minute segment. keep the time stamps for the clip to start and end.

Follow this Format and return in valid json 
[{{
start: "Start time of the clip",
content: "Highlight Text",
end: "End Time for the highlighted clip"
}}]

Return Proper JSON only

I WILL DO JSON['start'] AND IF IT DOESNT WORK THEN...

<TRANSCRIPTION>
{Transcription}

"""

# User = """
# Example
# """




def GetHighlight(Transcription):
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model="gpt-4o-2024-05-13",
        temperature=0.7,
        api_key = api_key
    )

    from langchain.prompts import ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system",system),
            ("user",Transcription)
        ]
    )
    chain = prompt |llm.with_structured_output(JSONResponse,method="function_calling")
    response = chain.invoke({"Transcription":Transcription})
    Start,End = int(response.start), int(response.end)
    # print(f"Start is {Start}")
    # print(f"End is {End}\n\n")
    if Start==End:
        Ask = input("Error - Get Highlights again (y/n) -> ").lower()
        if Ask == "y":
            Start, End = GetHighlight(Transcription)
        return Start, End
    return Start,End

if __name__ == "__main__":
    print(GetHighlight(User))
