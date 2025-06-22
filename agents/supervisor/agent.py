import os
import json
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv()

model = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

prompt_template = """
You are an expert at processing meeting transcripts. Your task is to analyze the following transcript and identify any specific, actionable commands or tasks that were mentioned.

**Instructions:**
1.  Read the entire transcript carefully.
2.  Identify all explicit requests or action items. These could be things like assigning a task, scheduling a meeting, creating a document, or sending a message.
3.  For each identified action, formulate a clear and concise command that a worker agent can execute.
4.  If the same command is repeated, only include it once.
5.  Return your findings as a JSON array of strings, where each string is a self-contained command.
6.  If no actionable commands are found, return an empty JSON array `[]`.

MAKE SURE TO ONLY RETURN THE JSON ARRAY OF STRINGS REPRESENTING THE COMMANDS AND NOTHING ELSE.

**Example:**

**Transcript:**
"Okay team, great standup. For the new login flow, can you add Sara as a reviewer on the auth PR? Also, let's schedule a follow-up for tomorrow at 3 PM to review the designs. And please, someone send a reminder to the #eng channel about the code freeze."

**Your Response:**
[
    "add Sara as a reviewer on the auth PR",
    "schedule a meeting for tomorrow at 3 PM to review the designs",
    "send a reminder to the #eng channel about the code freeze"
]

**Transcript to Analyze:**
{transcript}

**Your Response:**
"""

def workflow(state: dict):
    """
    This function processes the meeting transcript to extract actionable commands.
    """
    print("---EXTRACTING COMMANDS FROM TRANSCRIPT---")
    transcript_text = "\n".join(state["transcript"])

    # If the transcript is empty, there's nothing to do.
    if not transcript_text.strip():
        return {"messages": []}

    prompt = prompt_template.format(transcript=transcript_text)
    
    response = model.invoke(prompt)
    
    try:
        # The model should return a JSON array of strings.
        commands = json.loads(response.content)
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from model response.")
        print(f"Response content: {response.content}")
        return {"messages": []}

    # We convert each command into a HumanMessage.
    # The main graph will then process each of these messages.
    new_messages = [HumanMessage(content=cmd) for cmd in commands]
    
    print(f"Extracted {len(new_messages)} commands.")
    
    # We will return these messages to be processed one by one.
    # For now, let's just add them to the state. The graph needs to be updated to handle this.
    return {"messages": new_messages}


