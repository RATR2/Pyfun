import os
import sys
import requests
import hashlib
import base64
import customtkinter as ctk
import threading
import psutil
import time #github omg
import re
from PVconfig import SERVER_IP, SERVER_PORT, LEADERBOARD_ENDPOINT, REPO_OWNER, REPO_NAME, FILE_PATH, BANNED_WORDS, KNOWN_CHEAT_PROCESSES

LOCAL_SCRIPT_PATH = os.path.abspath(__file__)

def get_remote_script_content():
    """
    Fetch the latest version of the script from GitHub.
    Returns:
        str: Content of the remote file.
    """
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    print(f"Fetching from URL: {url}")  # Debug statement to check URL
    response = requests.get(url)
    print(f"Response status code: {response.status_code}")  # Debug to see response code
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to fetch the remote file: HTTP {response.status_code}")
        return None

def update_script():
    """
    Checks for updates and replaces the local script with the latest version.
    """
    remote_content = get_remote_script_content()
    if remote_content is None:
        print("No update found.")
        return
    
    with open(LOCAL_SCRIPT_PATH, "r") as file:
        local_content = file.read()
    
    if local_content != remote_content:
        # Update the local script file
        with open(LOCAL_SCRIPT_PATH, "w") as file:
            file.write(remote_content)
        print("Script updated successfully.")
        # Restart the script
        os.execv(sys.executable, ["python"] + sys.argv)
    else:
        print("Script is already up to date.")

class ClickerGame(ctk.CTk):
    def __init__(self, username):
        super().__init__()

        # GUI window properties
        self.title("Clicker Game")
        self.geometry("400x300")

        # Store the username
        self.username = username

        # Initial score and encoded score
        self._score = 0
        self._encoded_score = self.encode_score(self._score)  # Initialize _encoded_score

        # Countdown timer
        self.timer_duration = 25  # Set the timer duration to 25 seconds
        self.remaining_time = self.timer_duration  # Time left in the countdown

        # UI elements
        self.score_label = ctk.CTkLabel(self, text="Score: 0", font=("Arial", 24))
        self.score_label.pack(pady=20)

        self.click_button = ctk.CTkButton(self, text="Click Me!", command=self.increment_score)
        self.click_button.pack(pady=20)

        self.timer_label = ctk.CTkLabel(self, text=f"Time Remaining: {self.remaining_time}s", font=("Arial", 14))
        self.timer_label.pack(pady=10)

        self.leaderboard_button = ctk.CTkButton(self, text="View Leaderboard", command=self.show_leaderboard)
        self.leaderboard_button.pack(pady=10)

        # Start anti-cheat monitoring with after()
        self.after(5000, self.anti_cheat_monitor)  # Check every 5 seconds
        
        # Start automatic score update
        self.after(10000, self.send_score_to_server)  # Send score every 10 seconds

        # Start the countdown
        self.start_countdown()

    def encode_score(self, score):
        # Example encoding function (you can customize it as needed)
        return base64.b64encode(str(score).encode()).decode()

    def start_countdown(self):
        # Disables the click button and starts the countdown
        self.click_button.configure(state="disabled")
        self.remaining_time = self.timer_duration
        self.update_timer()

    def update_timer(self):
        # Updates the timer label and re-enables the button when time is up
        if self.remaining_time > 0:
            self.timer_label.configure(text=f"Time Remaining: {self.remaining_time}s")
            self.remaining_time -= 1
            self.after(1000, self.update_timer)  # Update timer every second
        else:
            self.timer_label.configure(text="You can click now!")
            self.click_button.configure(state="normal")  # Re-enable the button

    def increment_score(self):
        self._score += 1
        self._encoded_score = self.encode_score(self._score)  # Update the encoded score
        self.update_score_display()
        self.start_countdown()

    def update_score_display(self):
        self.score_label.configure(text=f"Score: {self._score}")

    def send_score_to_server(self):
        try:
            data = {
                'username': self.username,  # Send username along with the score
                'score': self._score,
                'encoded_score': self._encoded_score
            }
            response = requests.post(LEADERBOARD_ENDPOINT, json=data, timeout=5, verify=False)
            if response.status_code == 200:
                print("Score updated successfully on the server.")
            else:
                print(f"Failed to update score: HTTP {response.status_code}")
        except Exception as e:#git
            print(f"Error while sending score to the server: {e}")

        # Schedule the next score update
        self.after(10000, self.send_score_to_server)  # Repeat every 10 seconds

    def show_leaderboard(self):
        leaderboard_text = "Leaderboard data not available."
        leaderboard_text = self.fetch_leaderboard_data()
        self.display_leaderboard_window(leaderboard_text)

    def fetch_leaderboard_data(self):
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5, verify=False)
            if response.status_code == 200:
                leaderboard_data = response.json()
                return "\n".join(
                    [f"{i+1}. {entry['username']}: {entry['score']}" for i, entry in enumerate(leaderboard_data)]
                )
            else:
                print(f"Leaderboard fetch failed with status code: {response.status_code}")
                return "Failed to load leaderboard."
        except Exception as e:
            print(f"Exception occurred while fetching leaderboard: {e}")  # Print the error message
            return f"Error: {str(e)}"


    def fetch_leaderboard_data(self):
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5, verify=False)
            if response.status_code == 200:
                leaderboard_data = response.json()
                return "\n".join(
                    [f"{i + 1}. {entry['username']}: {entry['score']}" for i, entry in enumerate(leaderboard_data)]
                )
            else:
                print(f"Leaderboard fetch failed with status code: {response.status_code}")
                return "Failed to load leaderboard."
        except Exception as e:
            print(f"Exception occurred while fetching leaderboard: {e}")  # Print the error message
            return f"Error: {str(e)}"
    def display_leaderboard_window(self, leaderboard_text):
        leaderboard_window = ctk.CTkToplevel(self)
        leaderboard_window.title("Leaderboard")
        leaderboard_label = ctk.CTkLabel(leaderboard_window, text=leaderboard_text)
        leaderboard_label.pack(pady=10, padx=10)

    def anti_cheat_monitor(self):
        for process in psutil.process_iter(attrs=['name']):
            process_name = process.info['name']
            if any(cheat_tool.lower() in process_name.lower() for cheat_tool in KNOWN_CHEAT_PROCESSES):
                self.handle_cheat_detected(process_name)
                return

        # Schedule the next anti-cheat check
        self.after(5000, self.anti_cheat_monitor)  # Repeat check every 5 seconds

    def handle_cheat_detected(self, cheat_name):
        # Notify the user that a cheat tool was detected and display cooldown message
        self.timer_label.configure(text="Cooldown: Cheats Detected")  # Update the timer label
        self.click_button.configure(state="disabled")  # Disable the click button
        
        # Start a cooldown period
        self.start_cooldown()

    def start_cooldown(self):
        self.remaining_time = 10  # Set cooldown duration (10 seconds for example)
        self.update_timer()  # Start the cooldown timer

def ask_for_username():
    update_script()
    username_window = ctk.CTk()
    username_window.title("Enter Username")
    username_window.geometry("300x200")

    def submit_username():
        username = username_entry.get()
        if username:
            if not is_username_valid(username):
                print("Username is invalid. Please use only allowed characters and avoid inappropriate words.")
                username_entry.delete(0, ctk.END)  # Clear the entry field
            elif check_username_exists(username):
                print("Username already exists. Please choose a different one.")
                username_entry.delete(0, ctk.END)  # Clear the entry field
            else:
                username_window.destroy()  # Close the username window
                start_game(username)  # Start the game with the valid username

    def is_username_valid(username):
        # Check for inappropriate words
        if any(banned_word in username.lower() for banned_word in BANNED_WORDS):
            return False
        
        # Allow only alphanumeric characters and specified symbols
        return bool(re.match(r"^[a-zA-Z0-9$%()_\-]*$", username))  # Modify the regex pattern as needed

    def check_username_exists(username):
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5, verify=False)
            if response.status_code == 200:
                leaderboard_data = response.json()
                existing_usernames = [entry['username'] for entry in leaderboard_data]
                return username in existing_usernames
            else:
                print(f"Failed to fetch leaderboard for username check: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"Error while checking username: {e}")
            return False

    username_label = ctk.CTkLabel(username_window, text="Enter Username:")
    username_label.pack(pady=10)

    username_entry = ctk.CTkEntry(username_window)
    username_entry.pack(pady=10)

    submit_button = ctk.CTkButton(username_window, text="Submit", command=submit_username)
    submit_button.pack(pady=10)

    username_window.mainloop()

def start_game(username):
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ClickerGame(username)
    app.mainloop()
if __name__ == "__main__":
    ask_for_username()