import json
from aiutilities import AIUtilities, LLMConfig
from anthropic.types import ToolUseBlock

ai_utilities = AIUtilities()

def generate_adventure(user_input: str):
    prompt = [
        {"role": "system", "content": "You are a creative storyteller tasked with generating a random adventure based on user input."},
        {"role": "user", "content": f"Generate a random adventure based on this input: {user_input}"}
    ]

    json_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "The title of the adventure"},
            "setting": {"type": "string", "description": "A brief description of the adventure's setting"},
            "objective": {"type": "string", "description": "The main objective or goal of the adventure"},
            "challenges": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of challenges or obstacles the player might face"
            },
            "key_locations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "A list of important locations in the adventure"
            },
            "npcs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["name", "description"]
                },
                "description": "A list of important NPCs in the adventure"
            }
        },
        "required": ["title", "setting", "objective", "challenges", "key_locations", "npcs"]
    }

    llm_config = LLMConfig(client="anthropic", model="claude-3-5-sonnet-20240620", json_schema=json_schema)

    try:
        result = ai_utilities.run_ai_tool_completion(prompt, llm_config=llm_config)
        
        if isinstance(result, str):
            adventure = json.loads(result)
        elif isinstance(result, dict):
            adventure = result
        elif hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                if isinstance(content_item, ToolUseBlock):
                    adventure = content_item.input
                    break
            else:
                raise ValueError("No ToolUseBlock found in the response")
        else:
            raise ValueError(f"Unexpected response format: {type(result)}")
        
        # Validate the adventure structure
        required_keys = ["title", "setting", "objective", "challenges", "key_locations", "npcs"]
        for key in required_keys:
            if key not in adventure:
                raise ValueError(f"Missing required key in adventure: {key}")
        
        return adventure, result.usage.input_tokens, result.usage.output_tokens
    except Exception as e:
        print(f"Error generating adventure: {str(e)}")
        return None, 0, 0