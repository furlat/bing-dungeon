from fasthtml.common import *
from core import GameState, update_battlemap_with_ai
from typing import Dict, Tuple, List
from markupsafe import Markup
from collections import deque
import time
import asyncio
import json

app, rt = fast_app()

# Initialize the game state
initial_battlemap = {
    (0, 0): '🏰', (1, 0): '🌳', (2, 0): '🌳', (3, 0): '🌳', (4, 0): '🌳', (5, 0): '🏠',
    (0, 1): '🌳', (1, 1): '🌾', (2, 1): '🌾', (3, 1): '🌾', (4, 1): '🌾', (5, 1): '🌳',
    (0, 2): '🌳', (1, 2): '🌾', (2, 2): '🏠', (3, 2): '🌾', (4, 2): '🌾', (5, 2): '🌳',
    (0, 3): '🌳', (1, 3): '🌾', (2, 3): '🌾', (3, 3): '🏛️', (4, 3): '🌾', (5, 3): '🌳',
    (0, 4): '🌳', (1, 4): '🌾', (2, 4): '🌾', (3, 4): '🌾', (4, 4): '🌾', (5, 4): '🌳',
    (0, 5): '🏠', (1, 5): '🌳', (2, 5): '🌳', (3, 5): '🌳', (4, 5): '🌳', (5, 5): '🏰'
}
game_state = GameState(battlemap=initial_battlemap, player_pos=(2, 2))
state_history = deque([game_state], maxlen=10)
current_state_index = 0

def render_map(battlemap: Dict[Tuple[int, int], str], player_pos: Tuple[int, int], highlight_diff=False, previous_map=None):
    map_str = ""
    for y in range(6):
        for x in range(6):
            if (x, y) == player_pos:
                map_str += '<span class="player">🤺</span>'
            else:
                char = battlemap.get((x, y), ' ')
                if highlight_diff and previous_map and char != previous_map.get((x, y), ' '):
                    map_str += f'<span class="highlight">{char}</span>'
                else:
                    map_str += char
        map_str += '\n'
    return Pre(Markup(map_str), cls="game-map")

def render_log(log: List[str]):
    return Div(*(P(log_entry) for log_entry in log), id="log-container")

def render_usage_widget(input_tokens, output_tokens, response_time):
    return Div(
        H4("AI Usage Statistics"),
        P(f"Input tokens: {input_tokens}"),
        P(f"Output tokens: {output_tokens}"),
        P(f"Total tokens: {input_tokens + output_tokens}"),
        P(f"Response time: {response_time:.2f} seconds"),
        cls="usage-widget"
    )

@rt("/")
def get():
    return Titled("Virtual Tabletop Game",
        H1("Welcome to Virtual Tabletop"),
        P("Experience tabletop gaming in a digital environment!"),
        A("Enter Game Room", href="/game", cls="button")
    )

@rt("/game")
def get():
    global game_state, current_state_index
    current_state = state_history[current_state_index]
    previous_state = state_history[current_state_index - 1] if current_state_index > 0 else None
    
    return Titled("",
        H1("Game Room"),
        Div(
            Div(
                H3("Current Map"),
                render_map(current_state.battlemap, current_state.player_pos),
                cls="map-container"
            ),
            Div(
                H3("Previous Map"),
                render_map(previous_state.battlemap, previous_state.player_pos) if previous_state else P("No previous state"),
                cls="map-container"
            ),
            Div(render_log(current_state.log), cls="log-container"),
            cls="game-area"
        ),
        Div(
            Button("Highlight Diff", hx_post="/highlight_diff", hx_target=".game-area", hx_swap="innerHTML"),
            Button("Go Back", hx_post="/go_back", hx_target=".game-area", hx_swap="innerHTML"),
            Button("Go Forward", hx_post="/go_forward", hx_target=".game-area", hx_swap="innerHTML"),
            Button("Restart", hx_post="/restart", hx_target="body", hx_swap="innerHTML"),
            cls="control-buttons"
        ),
        Form(
            Input(type="text", name="action", placeholder="Type your action", autofocus=True),
            Button("Submit", type="submit"),
            hx_post="/action",
            hx_target=".game-area",
            hx_swap="innerHTML",
            _="on htmx:afterRequest set value of input[name='action'] to ''"
        ),
        P("Last action: ", Span(current_state.last_action, id="last-action"))
    )

@rt("/action", methods=['POST'])
async def post(action: str):
    global game_state, state_history, current_state_index
    action = action.lower().strip()
    if action == '':
        action = game_state.last_action
    
    # Immediately update the log with the user's action
    game_state.log.append(f"User action: {action}")
    game_state.last_action = action
    
    # Return an initial response with the updated log
    initial_response = render_game_area(game_state, state_history[current_state_index - 1] if current_state_index > 0 else None)
    
    # Add a custom attribute to trigger the AI response
    initial_response.attrs['hx-trigger'] = 'load'
    initial_response.attrs['hx-get'] = '/get_ai_response'
    initial_response.attrs['hx-target'] = 'this'
    initial_response.attrs['hx-swap'] = 'outerHTML'
    
    return initial_response

@rt("/get_ai_response", methods=['GET'])
async def get():
    global game_state, state_history, current_state_index
    
    # Update the game state using the AI
    start_time = time.time()
    game_state, input_tokens, output_tokens = await asyncio.to_thread(update_battlemap_with_ai, game_state, game_state.last_action)
    end_time = time.time()
    
    # Calculate response time
    response_time = end_time - start_time
    
    state_history.append(game_state)
    current_state_index = len(state_history) - 1
    
    return render_game_area(game_state, state_history[current_state_index - 1] if current_state_index > 0 else None, input_tokens, output_tokens, response_time)

@rt("/highlight_diff", methods=['POST'])
def post():
    global game_state, current_state_index
    current_state = state_history[current_state_index]
    previous_state = state_history[current_state_index - 1] if current_state_index > 0 else None
    return render_game_area(current_state, previous_state, highlight_diff=True)

@rt("/go_back", methods=['POST'])
def post():
    global current_state_index
    if current_state_index > 0:
        current_state_index -= 1
    current_state = state_history[current_state_index]
    previous_state = state_history[current_state_index - 1] if current_state_index > 0 else None
    return render_game_area(current_state, previous_state)

@rt("/go_forward", methods=['POST'])
def post():
    global current_state_index
    if current_state_index < len(state_history) - 1:
        current_state_index += 1
    current_state = state_history[current_state_index]
    previous_state = state_history[current_state_index - 1] if current_state_index > 0 else None
    return render_game_area(current_state, previous_state)

@rt("/restart", methods=['POST'])
def post():
    global game_state, state_history, current_state_index
    game_state = GameState(battlemap=initial_battlemap, player_pos=(2, 2))
    state_history = deque([game_state], maxlen=10)
    current_state_index = 0
    return get()

def render_game_area(current_state, previous_state, input_tokens=0, output_tokens=0, response_time=0, highlight_diff=False):
    description_color = "blue" if current_state.change_type == "same_map" else "green"
    return Div(
        Div(
            H3("Current Map"),
            render_map(current_state.battlemap, current_state.player_pos, highlight_diff, previous_state.battlemap if previous_state else None),
            cls="map-container"
        ),
        Div(
            H3("Previous Map"),
            render_map(previous_state.battlemap, previous_state.player_pos) if previous_state else P("No previous state"),
            cls="map-container"
        ),
        Div(render_log(current_state.log), cls="log-container"),
        Div(
            P(f"Change type: {current_state.change_type}", style=f"color: {description_color}; font-weight: bold;"),
            cls="change-type-container"
        ),
        render_usage_widget(input_tokens, output_tokens, response_time) if input_tokens or output_tokens else "",
        cls="game-area"
    )

app.hdrs += (
    Style("""
        .game-map {
            font-family: monospace;
            line-height: 1.5;
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            font-size: 32px;
            margin: 0;
            white-space: pre;
        }
        .highlight {
            background-color: #90EE90;
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
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 20px;
        }
        .map-container {
            flex: 1 1 45%;
            min-width: 300px;
        }
        .log-container {
            flex: 1 1 100%;
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            height: 150px;
            overflow-y: auto;
        }
        .log-container p {
            margin: 5px 0;
        }
        #log-container {
            display: flex;
            flex-direction: column;
        }
        .usage-widget {
            background-color: #e0e0e0;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
        }
        .usage-widget h4 {
            margin-top: 0;
        }
        .change-type-container {
            background-color: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
        }
    """),
    Script("""
        document.body.addEventListener('htmx:afterSettle', function(event) {
            console.log('HTMX after settle event triggered');
            if (event.detail.elt && event.detail.elt.classList.contains('game-area')) {
                console.log('Game area updated, triggering AI response');
                htmx.trigger(event.detail.elt, 'load');
            }
        });
    """)
)

serve()