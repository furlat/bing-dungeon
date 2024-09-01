from fasthtml.common import *
from core import GameState, update_battlemap_with_ai, generate_initial_state
from story_generation import generate_adventure
from typing import Dict, Tuple, List
from markupsafe import Markup
from collections import deque
import time
import asyncio
import json
import logging

app, rt = fast_app()

game_state = None
state_history = deque(maxlen=50)
current_adventure = None

logger = logging.getLogger(__name__)

def render_map(battlemap: Dict[Tuple[int, int], str], player_pos: Tuple[int, int]):
    map_str = ""
    for y in range(6):
        for x in range(6):
            if (x, y) == player_pos:
                map_str += '<span class="player">🤺</span>'
            else:
                map_str += battlemap.get((x, y), ' ')
        map_str += '\n'
    return Pre(Markup(map_str), cls="game-map")

def render_step(state: GameState, action: str, reaction: str, input_tokens: int, output_tokens: int, response_time: float, cache_creation_tokens: int, cache_read_tokens: int):
    return Div(
        H3(f"Step {len(state_history)}"),
        Div(
            H4("World State"),
            Div(
                Div(
                    render_map(state.battlemap, state.player_pos),
                    cls="world-state"
                ),
                Div(
                    H4("Statistics"),
                    P(f"Input tokens: {input_tokens}"),
                    P(f"Output tokens: {output_tokens}"),
                    P(f"Total tokens: {input_tokens + output_tokens}"),
                    P(f"Cache creation tokens: {cache_creation_tokens}"),
                    P(f"Cache read tokens: {cache_read_tokens}"),
                    P(f"Response time: {response_time:.2f} seconds"),
                    cls="statistics"
                ),
                cls="world-and-stats"
            )
        ),
        Div(
            H4("Action"),
            P(action),
            cls="action"
        ),
        Div(
            H4("Reaction"),
            P(reaction),
            cls="reaction"
        ),
        cls="game-step"
    )

@rt("/")
def get():
    return Titled("Bing Dungeon - AI-Powered Emoji Adventure",
                  #add dragon emoji and other emojis
        H1("🐉 🐉 🐉 Welcome to Bing Dungeon 🐉 🐉 🐉"),
        Div(
            H2("About Bing Dungeon"),
            P("Bing Dungeon is an innovative text-based adventure game that uses advanced AI to create dynamic, personalized stories. Each adventure is uniquely generated based on your input, offering endless possibilities for exploration and storytelling."),
            P("Key features:"),
            Ul(
                Li("AI-generated adventures tailored to your preferences"),
                Li("Dynamic world that responds to your actions"),
                Li("Emoji-based visual representation of the game world"),
                Li("Engaging narratives with challenges, NPCs, and key locations")
            ),
            cls="about-section"
        ),
        H2("Start Your Adventure"),
        P("Enter a theme or concept for your adventure, and let the AI create a unique world for you to meme!"),
        Form(
            Input(type="text", name="adventure_prompt", placeholder="e.g., 'Space pirates', 'Medieval fantasy', 'Cyberpunk detective'", autofocus=True),
            Button("Generate Adventure", type="submit", hx_indicator="#loading"),
            hx_post="/generate_adventure",
            hx_target="#adventure-details",
            hx_swap="innerHTML"
        ),
        Div(id="adventure-details"),
        Div(id="loading", cls="htmx-indicator", _="Loading...")
    )

@rt("/generate_adventure", methods=['POST'])
async def generate_adventure_endpoint(adventure_prompt: str):
    start_time = time.time()
    try:
        logger.info(f"Starting adventure generation for prompt: {adventure_prompt}")
        result = await generate_adventure(adventure_prompt)
        logger.info(f"Adventure generation completed. Result type: {type(result)}")
        
        if result[0] is None:
            logger.error("Adventure generation failed: result[0] is None")
            return P("Failed to generate adventure. Please try again.")
        
        adventure, adv_input_tokens, adv_output_tokens, adv_cache_creation_tokens, adv_cache_read_tokens = result
        logger.info(f"Adventure unpacked. Title: {adventure.get('title', 'No title')}")
    except Exception as e:
        logger.error(f"Error in generate_adventure: {str(e)}", exc_info=True)
        return P(f"An error occurred while generating the adventure: {str(e)}")

    try:
        global current_adventure
        current_adventure = adventure
        
        logger.info("Creating adventure_div")
        end_time = time.time()
        generation_time = end_time - start_time
        
        adventure_div = Div(
            H2(adventure['title']),
            H3("Setting"),
            P(adventure['setting']),
            H3("Objective"),
            P(adventure['objective']),
            H3("Challenges"),
            Ul(*[Li(challenge) for challenge in adventure['challenges']]),
            H3("Key Locations"),
            Ul(*[Li(location) for location in adventure['key_locations']]),
            H3("NPCs"),
            Ul(*[Li(f"{npc['name']}: {npc['description']}") for npc in adventure['npcs']]),
            Div(
                H4("Adventure Generation Statistics"),
                P(f"Input tokens: {adv_input_tokens}"),
                P(f"Output tokens: {adv_output_tokens}"),
                P(f"Total tokens: {adv_input_tokens + adv_output_tokens}"),
                P(f"Cache creation tokens: {adv_cache_creation_tokens}"),
                P(f"Cache read tokens: {adv_cache_read_tokens}"),
                P(f"Generation time: {generation_time:.2f} seconds"),
                cls="statistics"
            ),
            id="adventure-details"
        )
        
        logger.info("Adventure_div created successfully")
        logger.info(f"Total time for adventure generation: {generation_time:.2f} seconds")
        
        return adventure_div + Div(
            Button("Generate Initial Game State", 
                   hx_post="/generate_initial_state", 
                   hx_target="#game-state", 
                   hx_indicator="#loading"),
            Div(id="game-state"),
            id="game-state-container"
        )
    except Exception as e:
        logger.error(f"Error while creating adventure_div: {str(e)}", exc_info=True)
        return P(f"An error occurred while processing the generated adventure: {str(e)}")

@rt("/generate_initial_state", methods=['POST'])
async def generate_initial_state_endpoint():
    global game_state, current_adventure
    
    logger.info("Starting initial game state generation")
    
    if not current_adventure:
        logger.error("No adventure has been generated")
        return P("No adventure has been generated. Please generate an adventure first.")
    
    try:
        logger.info("Calling generate_initial_state function")
        result = await asyncio.to_thread(generate_initial_state, current_adventure)
        logger.info(f"generate_initial_state completed. Result type: {type(result)}")
        
        if result[0] is None:
            logger.error("Initial state generation failed: result[0] is None")
            return P("Failed to generate initial game state. Please try again.")
        
        game_state, init_input_tokens, init_output_tokens, init_cache_creation_tokens, init_cache_read_tokens, init_response_time = result
        logger.info("Initial game state unpacked successfully")
    except Exception as e:
        logger.error(f"Error in generate_initial_state: {str(e)}", exc_info=True)
        return P(f"An error occurred while generating the initial game state: {str(e)}")

    if game_state:
        state_history.clear()
        state_history.append(game_state)
        
        logger.info("Returning initial game state information")
        return Div(
            H4("Initial Game State Generated"),
            P("The initial game state has been created successfully."),
            Div(
                H4("Generation Statistics"),
                P(f"Input tokens: {init_input_tokens}"),
                P(f"Output tokens: {init_output_tokens}"),
                P(f"Total tokens: {init_input_tokens + init_output_tokens}"),
                P(f"Cache creation tokens: {init_cache_creation_tokens}"),
                P(f"Cache read tokens: {init_cache_read_tokens}"),
                P(f"Response time: {init_response_time:.2f} seconds"),
                cls="statistics"
            ),
            A("Start Adventure", href="/game", cls="button"),
            id="game-state"
        )
    else:
        logger.error("Game state is None after generation")
        return P("Failed to generate initial game state. Please try again.")

@rt("/game")
def get():
    global game_state
    if not game_state or not game_state.adventure:
        return RedirectResponse(url='/')
    
    return Titled("The Bing Dungeon",
        H1(game_state.adventure['title']),
        Div(
            Div(*(render_step(state, state.last_action, state.log[-1] if state.log else "", 0, 0, 0, 0, 0) 
                  for state in reversed(state_history)), 
                id="game-history", 
                cls="game-history"),
            Form(
                Input(type="text", name="action", placeholder="Type your action", autofocus=True),
                Button("Submit", type="submit", hx_indicator="#action-loading"),
                hx_post="/action",
                hx_target="#game-history",
                hx_swap="afterbegin",
                _="on htmx:afterRequest call scrollToTop()"
            ),
            Div(id="action-loading", cls="htmx-indicator", _="Processing action..."),
            cls="game-area"
        ),
        Div(
            Button("Restart", hx_post="/restart", hx_target="body", hx_swap="innerHTML"),
            cls="control-buttons"
        ),
        Script("""
            document.body.addEventListener('htmx:afterSwap', function(evt) {
                if (evt.detail.target.id === 'game-history') {
                    evt.detail.target.scrollTop = 0;
                }
            });

            function scrollToTop() {
                document.getElementById('game-history').scrollTop = 0;
            }
        """)
    )

@rt("/action", methods=['POST'])
async def post(action: str):
    global game_state, state_history
    action = action.lower().strip()
    if action == '':
        return "Action cannot be empty"
    
    if game_state is None:
        return "Game has not been initialized. Please start a new game."

    # Update the game state using the AI
    start_time = time.time()
    result = await asyncio.to_thread(update_battlemap_with_ai, game_state, action)
    new_state, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens = result if result[0] is not None else (None, 0, 0, 0, 0)
    end_time = time.time()
    
    # Calculate response time
    response_time = end_time - start_time
    
    if new_state is None:
        return "Failed to update game state. Please try again or start a new game."

    # Update the game state and history
    game_state = new_state
    state_history.append(game_state)
    
    # Render the new step
    return render_step(game_state, action, game_state.log[-1], input_tokens, output_tokens, response_time, cache_creation_tokens, cache_read_tokens)

@rt("/restart", methods=['POST'])
def post():
    global game_state, state_history
    game_state = None
    state_history.clear()
    return RedirectResponse(url='/', status_code=303)

app.hdrs += (
    Style("""
        .game-map {
            font-family: monospace;
            line-height: 1.5;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            font-size: 27.6px;  /* Increased by 15% from 24px */
            margin: 0;
            white-space: pre;
        }
        .player {
            color: blue;
        }
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 0;
        }
        .control-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        form {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        input[type="text"] {
            flex-grow: 1;
            padding: 10px;
            font-size: 16px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
        }
        .game-area {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 20px;
        }
        .game-history {
            display: flex;
            flex-direction: column;
            gap: 20px;
            margin-bottom: 20px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .game-step {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 10px;
        }
        .world-and-stats {
            display: flex;
            justify-content: flex-start;
            align-items: stretch;  /* Changed from flex-start to stretch */
        }
        .world-state {
            flex: 0 0 auto;
            margin-right: 20px;
        }
        .statistics {
            flex: 0 0 300px;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;  /* Changed from center to flex-start */
        }
        .statistics h4 {
            margin-top: 0;
            margin-bottom: 10px;  /* Added margin-bottom */
        }
        .statistics p {
            margin: 5px 0;  /* Reduced margin for paragraphs */
        }
        .action, .reaction {
            margin-bottom: 10px;
        }
        
        .htmx-indicator {
            display: none;
        }
        .htmx-request .htmx-indicator {
            display: inline;
        }
        .htmx-request.htmx-indicator {
            display: inline;
        }
        
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100px;
            font-size: 18px;
            font-weight: bold;
        }
        
        .about-section {
            margin-bottom: 20px;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        h1 {
            color: #2c3e50;
            text-align: center;
        }
        
        h2 {
            color: #34495e;
        }
        
        .about-section {
            background-color: #f9f9f9;
            border-radius: 5px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        button[type="submit"] {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        
        button[type="submit"]:hover {
            background-color: #2980b9;
        }
    """),
)

serve()