# Virtual Tabletop Adventure Game

Welcome to the Virtual Tabletop Adventure Game! This is an AI-powered text-based adventure game where you can create and explore unique adventures.

## Installation

1. Ensure you have Python 3.7+ installed on your system.

2. Clone this repository:
   ```bash
   git clone https://github.com/furlat/bing-dungeon.git
   cd bing-dungeon
   ```

3. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

4. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

5. Set up your Anthropic API key:
   - Create a file named `.env` in the project root directory
   - Add your Anthropic API key to the file:
     ```bash
     ANTHROPIC_API_KEY=your_api_key_here
     ```

## Running the Game

1. Start the game server:
   ```bash
   python main.py
   ```

2. Open your web browser and go to `http://localhost:5001`

## How to Play

1. **Generate an Adventure**:
   - On the home page, enter a theme or idea for your adventure in the text box.
   - Click "Generate Adventure" to create a unique adventure based on your input.
   - Review the generated adventure details, including the title, setting, objective, challenges, key locations, and NPCs.

2. **Start the Adventure**:
   - Click "Start Adventure" to begin playing.

3. **Gameplay**:
   - You'll see a description of your current situation and a 6x6 grid representing your environment.
   - Type your actions into the text box (e.g., "move north", "examine the statue", "talk to the merchant").
   - Click "Submit" or press Enter to perform your action.
   - The AI will process your action and update the game state, providing a description of what happens.

4. **Navigation**:
   - Your character is represented by a 🤺 emoji on the grid.
   - Other emojis represent different elements in the environment (e.g., 🌳 for trees, 🏠 for buildings).

5. **Continue Playing**:
   - Keep entering actions to progress through the adventure.
   - Try to achieve the main objective while overcoming challenges and interacting with NPCs.

6. **Start Over**:
   - Click the "Restart" button at any time to return to the home page and generate a new adventure.

Enjoy your unique, AI-generated adventure!