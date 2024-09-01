from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple, Literal
from aiutilities import AIUtilities, LLMConfig
import json
from anthropic.types import ToolUseBlock
from story_generation import generate_adventure
import logging
import time
from prompt import system_prompt

SYSTEM_PROMPT = system_prompt
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameState(BaseModel):
    battlemap: Dict[Tuple[int, int], str]
    player_pos: Tuple[int, int] = Field(default=(2, 2))
    last_action: str = ""
    log: List[str] = Field(default_factory=list)
    conversation_history: List[str] = Field(default_factory=list)
    change_type: Literal['same_map', 'new_map'] = 'same_map'
    adventure: Optional[Dict] = None

ai_utilities = AIUtilities()

def generate_initial_state(adventure: Dict) -> Tuple[Optional[GameState], int, int, int, int, float]:
    logger.info("Generating initial game state based on adventure setup")
    start_time = time.time()
    
    prompt = [
        {"role": "system", "content": "You are an AI dungeon master tasked with creating an initial game state based on an adventure setup."},
        {"role": "user", "content": f"Generate an initial game state for this adventure:\n{json.dumps(adventure, indent=2)}\n\nProvide a 6x6 battlemap, player position, and initial description."}
    ]

    json_schema = {
        "type": "object",
        "properties": {
            "battlemap": {
                "type": "object",
                "description": "A 6x6 grid representing the initial game map. Keys are coordinate tuples '(x, y)', values are emoji representations.",
                "patternProperties": {
                    "^\\([0-5], [0-5]\\)$": {"type": "string"}
                }
            },
            "player_pos": {
                "type": "array",
                "items": {"type": "integer", "minimum": 0, "maximum": 5},
                "minItems": 2,
                "maxItems": 2,
                "description": "The initial player position as [x, y] coordinates."
            },
            "initial_description": {
                "type": "string",
                "description": "A brief description of the initial game state and the player's surroundings."
            }
        },
        "required": ["battlemap", "player_pos", "initial_description"]
    }

    llm_config = LLMConfig(client="anthropic", model="claude-3-5-sonnet-20240620", json_schema=json_schema)

    try:
        result = ai_utilities.run_ai_tool_completion(prompt, llm_config=llm_config)
        
        if isinstance(result, str):
            initial_state = json.loads(result)
        elif isinstance(result, dict):
            initial_state = result
        elif hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                if isinstance(content_item, ToolUseBlock):
                    initial_state = content_item.input
                    break
            else:
                raise ValueError("No ToolUseBlock found in the response")
        else:
            raise ValueError(f"Unexpected response format: {type(result)}")

        # Convert string tuple keys to actual tuples
        battlemap = {eval(k): v for k, v in initial_state["battlemap"].items()}
        
        end_time = time.time()
        response_time = end_time - start_time
        
        game_state = GameState(
            battlemap=battlemap,
            player_pos=tuple(initial_state["player_pos"]),
            log=[initial_state["initial_description"]],
            adventure=adventure
        )
        
        return game_state, result.usage.input_tokens, result.usage.output_tokens, result.usage.cache_creation_input_tokens, result.usage.cache_read_input_tokens, response_time
    except Exception as e:
        logger.error(f"Error generating initial state: {str(e)}")
        return None, 0, 0, 0, 0, 0

def update_battlemap_with_ai(game_state: GameState, user_action: str) -> Tuple[GameState, int, int, int, int]:
    logger.info(f"Updating battlemap with AI for action: {user_action}")
    
    if game_state is None:
        logger.error("Game state is None. Cannot update battlemap.")
        return None, 0, 0, 0, 0

    # Prepare the input for the AI
    battlemap_str = "\n".join([f"{k}: {v}" for k, v in game_state.battlemap.items()])
    
    conversation_history = "\n".join(game_state.conversation_history[-5:])  # Include last 5 interactions
    
    adventure_context = json.dumps(game_state.adventure)
    
    extra_system_prompt = f"""You are an AI dungeon master for a text-based adventure game. Your task is to update the game state based on the player's actions and the current adventure context.

Current adventure context:
{adventure_context}

Use this context to inform your responses and guide the player through the adventure. Incorporate elements from the adventure into the game world and narrative.

"""
    system_prompt_final = SYSTEM_PROMPT + extra_system_prompt
    prompt = [
        {"role": "system", "content": system_prompt_final},
        {"role": "user", "content": f"Current battlemap:\n{battlemap_str}\nPlayer position: {game_state.player_pos}\nRecent conversation:\n{conversation_history}\nUser action: {user_action}\n\nUpdate the battlemap and provide a brief description of what happened."}
    ]

    # Define the expected output schema
    json_schema = {
        "type": "object",
        "properties": {
            "change_type": {
                "type": "string",
                "enum": ["same_map", "new_map"],
                "description": "Indicates whether the action results in the same map layout or a completely new map. Use 'same_map' for actions that don't significantly change the environment, and 'new_map' for actions that lead to a new area or drastically alter the current one."
            },
            "battlemap": {
                "type": "object",
                "description": "Represents the 6x6 game grid. Each key is a coordinate tuple '(x, y)' where x and y range from 0 to 5. The value is an emoji representing the terrain or object at that location. This should reflect all changes made by the player's action, including environmental changes, item pickups, or NPC movements. Never include player emojis in this map.",
                "patternProperties": {
                    "^\\([0-5], [0-5]\\)$": {
                        "type": "string",
                        "description": "An emoji representing the terrain or object at this coordinate. Must be one of the emojis defined in the legend (e.g., 🏰, 🌳, 🌾, 🏠, etc.). Never use player emojis (🤺, 🚶, 🤴) here."
                    }
                }
            },
            "player_pos": {
                "type": "array",
                "description": "The player's new position after the action. This should be updated if the player moves, but remain the same if the action doesn't involve movement. The position is represented as [x, y] coordinates.",
                "items": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5
                },
                "minItems": 2,
                "maxItems": 2
            },
            "description": {
                "type": "string",
                "description": "A brief, engaging narrative description of what happened as a result of the player's action. This should include details about the environment, any changes to the battlemap, interactions with NPCs or objects, and the outcome of the player's action. The description should be written in second person ('You...') and should be 2-3 sentences long."
            }
        },
        "required": ["change_type", "battlemap", "player_pos", "description"]
    }

    # Set up the LLMConfig for Anthropic
    llm_config=LLMConfig(client="anthropic", model="claude-3-5-sonnet-20240620", json_schema=json_schema)

    # Make the API call
    try:
        result = ai_utilities.run_ai_tool_completion(prompt, llm_config=llm_config)
        logger.info(f"AI response received: {result}")
        
        # Parse the result
        if isinstance(result, str):
            response = json.loads(result)
        elif isinstance(result, dict):
            response = result
        elif hasattr(result, 'content') and isinstance(result.content, list):
            for content_item in result.content:
                if isinstance(content_item, ToolUseBlock):
                    response = content_item.input
                    break
            else:
                raise ValueError("No ToolUseBlock found in the response")
        else:
            raise ValueError("Unexpected response format")
        
        # Convert string tuple keys to actual tuples
        updated_battlemap = {eval(k): v for k, v in response["battlemap"].items()}
        
        # Remove any player emoji from the battlemap
        for k, v in updated_battlemap.items():
            if v in ['🤺', '🚶', '🤴']:
                updated_battlemap[k] = '🌾'  # Replace with grass or appropriate terrain
        
        # Create a new GameState from the updated state
        new_state = GameState(
            battlemap=updated_battlemap,
            player_pos=tuple(response["player_pos"]),
            last_action=user_action,
            log=game_state.log + [f"AI response: {response['description']}"],
            conversation_history=game_state.conversation_history + [f"User action: {user_action}", f"AI response: {response['description']}"],
            change_type=response["change_type"],
            adventure=game_state.adventure
        )
        
        logger.info(f"New game state created: {new_state}")
        return new_state, result.usage.input_tokens, result.usage.output_tokens, result.usage.cache_creation_input_tokens, result.usage.cache_read_input_tokens
    except Exception as e:
        logger.error(f"Error updating game state: {str(e)}")
        return None, 0, 0, 0, 0