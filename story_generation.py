import json
from aiutilities import AIUtilities, LLMConfig
from anthropic.types import ToolUseBlock, TextBlock
import logging
import asyncio
from concurrent.futures import TimeoutError

ai_utilities = AIUtilities()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_adventure(user_input: str):
    logger.info(f"Starting adventure generation for input: {user_input}")
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
        logger.info("Sending request to AI")
        result = await asyncio.wait_for(
            asyncio.to_thread(ai_utilities.run_ai_tool_completion, prompt, llm_config=llm_config),
            timeout=60  # 60 seconds timeout
        )
        logger.info(f"AI response received. Type: {type(result)}")
        
        if isinstance(result, str):
            logger.error(f"Unexpected string result: {result}")
            return None, 0, 0, 0, 0
        
        if hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                if isinstance(content_item, ToolUseBlock):
                    adventure = content_item.input
                    break
                elif isinstance(content_item, TextBlock):
                    adventure = json.loads(content_item.text)
                    break
            else:
                raise ValueError("No valid content found in the response")
        else:
            raise ValueError(f"Unexpected response format: {type(result)}")
        
        # Validate the adventure structure
        required_keys = ["title", "setting", "objective", "challenges", "key_locations", "npcs"]
        for key in required_keys:
            if key not in adventure:
                raise ValueError(f"Missing required key in adventure: {key}")
        
        logger.info("Adventure generated successfully")
        return adventure, result.usage.input_tokens, result.usage.output_tokens, result.usage.cache_creation_input_tokens, result.usage.cache_read_input_tokens
    except TimeoutError:
        logger.error("Adventure generation timed out")
        return None, 0, 0, 0, 0
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        logger.error(f"Raw response: {result}")
        return None, 0, 0, 0, 0
    except Exception as e:
        logger.error(f"Error generating adventure: {str(e)}")
        logger.error(f"Raw response: {result}")
        return None, 0, 0, 0, 0