import random
import asyncio
from telethon import events

# List of words for scrambling
wordlist = [
    "python", "telethon", "discord", "scramble", "game", "programming", "developer",
    "apple", "banana", "orange", "cherry", "grape", "melon", "mango", "lemon",
    "pear", "kiwi", "table", "chair", "book", "pencil", "paper", "clock", "shoes",
    "car", "boat", "phone"
]

# Store user games (track active games)
active_games = {}

# Store player scores
player_scores = {}

# Store players who participated in the current game session
active_players_in_game = {}

async def start_word_scramble(event):
    """Start the Word Scramble game."""
    user_id = event.sender_id
    chat_id = event.chat_id  # Store chat ID for group context

    # Check if the user is already playing a game
    if user_id in active_games:
        await event.respond("❌ You are already playing a game. Type /stop to end the current game.")
        return

    # Mark user as playing a game
    active_games[user_id] = chat_id

    # Start the game loop
    await play_game(event)

async def play_game(event):
    """Play the Word Scramble game in a group."""
    chat_id = event.chat_id  # The group chat ID
    active_players = []  # Track active players in this game

    # Add all members of the group to the active players list
    participants = await event.client.get_participants(chat_id)
    for participant in participants:
        active_players.append(participant.id)
        # Initialize scores for new players
        if participant.id not in player_scores:
            player_scores[participant.id] = 0

    # Loop through the word list
    for word in wordlist:
        # Check if the game is stopped before starting the next word
        if event.sender_id not in active_games:
            await event.respond(f"❌ The game has been stopped.")
            return  # Stop the game entirely if it's been stopped

        scrambled_word = ''.join(random.sample(word, len(word)))
        
        # Send the scrambled word to the group and notify users about the time limit
        await event.respond(f"🧩 Word Scramble\n\nUnscramble this word: {scrambled_word}\nYou have 30 seconds to guess!")

        # Track guesses
        guesses = {}
        start_time = asyncio.get_event_loop().time()

        # Create a task for the timer (the 30-second wait)
        timer_task = asyncio.create_task(asyncio.sleep(30))

        # Define a check for valid guesses from players in the group
        def check_message(guess_event):
            return guess_event.chat_id == chat_id and guess_event.text.strip().lower() != "/stop" and guess_event.sender_id in active_players

        # Register the event handler to listen for guesses
        @event.client.on(events.NewMessage(func=check_message))
        async def handle_guess(guess_event):
            nonlocal guesses

            if guess_event.text.strip().lower() == word.lower():
                # If a correct guess is made, store it and send confirmation to the group
                if guess_event.sender_id not in guesses:  # Prevent duplicate guesses
                    guesses[guess_event.sender_id] = guess_event.text.strip()
                    await event.respond(f"✅ {guess_event.sender.username} guessed the word correctly: {word}!")

                    # Increase the player's score
                    player_scores[guess_event.sender_id] += 1  # Award 1 point for correct guess

                    # Add the player to the active session list
                    active_players_in_game[guess_event.sender_id] = True

                    # Cancel the timer task to stop waiting
                    timer_task.cancel()

                    return  # Break the loop and go to the next word

        # Register the /stop command to stop the game at any time
        @event.client.on(events.NewMessage(pattern='/stop'))
        async def stop_game(event):
            if event.chat_id == chat_id and event.sender_id in active_players:
                # Stop the game for this user
                if event.sender_id in active_games:
                    active_games.pop(event.sender_id, None)
                    await event.respond(f"❌ The game has been stopped by {event.sender.username}.")
                    # Clean up the event handler
                    event.client.remove_event_handler(stop_game)  # Unregister the /stop handler
                    # Cancel the timer if it's still running
                    timer_task.cancel()

                    # Exit the game loop
                    return

        # Wait for either the timer to expire or a correct guess
        try:
            await timer_task
            if len(guesses) == 0:  # If no one guessed correctly
                await event.respond(f"❌ Time's up! The correct word was: {word}")
        except asyncio.CancelledError:
            # Timer was cancelled, either due to a correct guess or manual interruption
            pass

        # Remove the event handler after the time limit or after a correct guess
        event.client.remove_event_handler(handle_guess)

        # Continue with the next word if the game is still active
        if event.sender_id not in active_games:
            await event.respond(f"❌ The game has been stopped.")
            return  # Break the loop if the game is stopped

    # Once the game is over, remove the user from active games
    active_games.pop(event.sender_id, None)

    # Display final scores (only for active players in the game)
    await event.respond("The game is over! Thanks for playing! 🎮")

    # Prepare the final scores
    final_scores = {player_id: player_scores[player_id] for player_id in active_players_in_game}

    # Sort the final scores (highest to lowest)
    sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

    # Generate the leaderboard with player names and profile links
    leaderboard = "🏅 Final Scores:\n"
    for idx, (player_id, score) in enumerate(sorted_scores):
        participant = await event.client.get_entity(player_id)
        first_name = participant.first_name or "Anonymous"
        profile_link = f"tg://user?id={player_id}"
        leaderboard += f"{idx + 1}. [**{first_name}**]({profile_link}): {score}\n"

    await event.respond(leaderboard)

    # Clean up active players in game
    active_players_in_game.clear()
