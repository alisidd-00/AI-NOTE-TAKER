import openai
import os
from dotenv import load_dotenv
load_dotenv()

# ================================================================================================================================#

# OpenAI Credentials
api_key = os.getenv('OPENAI_KEY')
openai.organization = os.getenv('OPENAI_ORGANIZATION')
openai.api_key = api_key

#======================================================================================================================================#

# Prompts

summary_prompt = """Generate a concise summary of the key points discussed in the meeting. Focus on unique topics without repeating any point. Avoid using numbering or listing."""
action_prompt = """Suggest actionable items based on the meeting. Focus on unique topics without repeating any point. Avoid using numbering."""
keywords_prompt= """Generate 10 keywords summarizing the key topics discussed. Provide only single words or short phrases that capture the essence of each topic, without numbering or detailed explanations."""
#======================================================================================================================================#

# Function for Summarization, Action Items, Notes and Outline of meeting

def get_chatbot_response(prompt_type, prompt_content):
    """
    Generates a response from a chatbot model based on the specified prompt type and content.

    This function maps a given prompt type to a predefined prompt template and then uses
    OpenAI's ChatCompletion to generate a chatbot response. The response is tailored to the
    type of information requested (e.g., summary, action items, outline, notes, keywords).

    Parameters:
    - prompt_type (str): The type of prompt for which a response is sought. Valid types include
      'summary', 'action', 'outline', 'notes', and 'keywords'.
    - prompt_content (str): The content to be processed by the chatbot for generating a response.

    Returns:
    - str: The content of the chatbot's response.

    Note: Requires OpenAI API access and appropriate API keys set up in the environment.
    """
    prompt_map = {
        "summary": summary_prompt,
        "action": action_prompt,
        "keywords":keywords_prompt
    }

    input_prompt = "You are a helpful assistant that provides {}.\n".format(
        prompt_map.get(prompt_type, "information"))
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": input_prompt},
                {"role": "user", "content": prompt_content}
            ],
            temperature=0.2,
            max_tokens=700,
            top_p=0.1,
            frequency_penalty=0.0,
            presence_penalty=0.1
        )

        chatbot_reply = response['choices'][0]['message']['content']
    except openai.Error as e:
        chatbot_reply = f"An error occurred: {str(e)}"
        
    return chatbot_reply
#======================================================================================================================================#