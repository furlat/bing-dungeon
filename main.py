from fasthtml.common import *
from core import GameState, update_battlemap_with_ai, generate_initial_state
from story_generation import generate_adventure
from typing import Dict, Tuple, List
from markupsafe import Markup
from collections import deque
import time
import asyncio
import json

app, rt = fast_app()

game_state = None
state_history = deque(maxlen=50)

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

def render_step(state: GameState, action: str, reaction: str, input_tokens: int, output_tokens: int, response_time: float):
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
    return Titled("Virtual Tabletop Game",
        H1("Welcome to Virtual Tabletop"),
        P("Experience tabletop gaming in a digital environment!"),
        Form(
            Input(type="text", name="adventure_prompt", placeholder="Enter a theme for your adventure", autofocus=True),
            Button("Generate Adventure", type="submit", hx_indicator="#loading"),
            hx_post="/generate_adventure",
            hx_target="#adventure-details",
            hx_swap="innerHTML"
        ),
        Div(id="adventure-details"),
        Div(id="loading", cls="htmx-indicator", _="Loading...")
    )

@rt("/generate_adventure", methods=['POST'])
async def post(adventure_prompt: str):
    start_time = time.time()
    result = await asyncio.to_thread(generate_adventure, adventure_prompt)
    adventure, adv_input_tokens, adv_output_tokens = result if result[0] is not None else (None, 0, 0)
    
    if adventure:
        global game_state
        result = await asyncio.to_thread(generate_initial_state, adventure)
        game_state, init_input_tokens, init_output_tokens, init_response_time = result if result[0] is not None else (None, 0, 0, 0)
        end_time = time.time()
        total_response_time = end_time - start_time
        
        if game_state:
            state_history.clear()
            state_history.append(game_state)
            
            total_input_tokens = adv_input_tokens + init_input_tokens
            total_output_tokens = adv_output_tokens + init_output_tokens
            
            return Div(
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
                    H4("Generation Statistics"),
                    P(f"Total input tokens: {total_input_tokens}"),
                    P(f"Total output tokens: {total_output_tokens}"),
                    P(f"Total tokens: {total_input_tokens + total_output_tokens}"),
                    P(f"Total response time: {total_response_time:.2f} seconds"),
                    cls="statistics"
                ),
                A("Start Adventure", href="/game", cls="button"),
                Script("window.scrollTo(0, document.body.scrollHeight);")
            )
        else:
            return P("Failed to generate initial game state. Please try again.")
    else:
        return P("Failed to generate adventure. Please try again.")

@rt("/game")
def get():
    global game_state
    if not game_state or not game_state.adventure:
        return RedirectResponse(url='/')
    
    return Titled("The Bing Dungeon",
        H1(game_state.adventure['title']),
        Div(
            Div(*(render_step(state, state.last_action, state.log[-1] if state.log else "", 0, 0, 0) 
                  for state in reversed(state_history)), 
                id="game-history", 
                cls="game-history"),
            Form(
                Input(type="text", name="action", placeholder="Type your action", autofocus=True),
                Button("Submit", type="submit", hx_indicator="#action-loading"),
                hx_post="/action",
                hx_target="#game-history",
                hx_swap="afterbegin",
                _="on htmx:afterRequest set value of input[name='action'] to ''"
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
    new_state, input_tokens, output_tokens = result if result[0] is not None else (None, 0, 0)
    end_time = time.time()
    
    # Calculate response time
    response_time = end_time - start_time
    
    if new_state is None:
        return "Failed to update game state. Please try again or start a new game."

    # Update the game state and history
    game_state = new_state
    state_history.append(game_state)
    
    # Render the new step
    return render_step(game_state, action, game_state.log[-1], input_tokens, output_tokens, response_time)

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
            align-items: flex-start;
        }
        .world-state {
            flex: 0 0 auto;
            margin-right: 20px;
        }
        .statistics {
            flex: 0 0 200px;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            align-self: stretch;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .statistics h4 {
            margin-top: 0;
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
    """),
)

serve()