import os
import sys
import requests
import hashlib
import base64
import customtkinter as ctk
import threading
import psutil
import time
import signal
import re
import logging
from PVconfig import (
    SERVER_IP, SERVER_PORT, LEADERBOARD_ENDPOINT, 
    REPO_OWNER, REPO_NAME, FILE_PATH, 
    BANNED_WORDS, KNOWN_CHEAT_PROCESSES
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LOCAL_SCRIPT_PATH = os.path.abspath(__file__)
LAST_UPDATE_CHECK = time.time()
UPDATE_CHECK_INTERVAL = 3600  # Check for updates every hour

def get_remote_script_content():
    """Fetch the latest version of the script from GitHub."""
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    logging.info(f"Fetching from URL: {url}")
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch the remote file: {e}")
        return None

def update_script():
    """Check for updates and replace the local script with the latest version."""
    global LAST_UPDATE_CHECK

    current_time = time.time()
    if current_time - LAST_UPDATE_CHECK < UPDATE_CHECK_INTERVAL:
        logging.info("Skipping update check, within interval.")
        return

    remote_content = get_remote_script_content()
    if remote_content is None:
        return
    
    with open(LOCAL_SCRIPT_PATH, "r") as file:
        local_content = file.read()

    if local_content != remote_content:
        with open(LOCAL_SCRIPT_PATH, "w") as file:
            file.write(remote_content)
        logging.info("Script updated successfully.")
        os.execv(sys.executable, ["python"] + sys.argv)
    else:
        logging.info("Script is already up to date.")

class ClickerGame(ctk.CTk):
    def __init__(self, username):
        super().__init__()
        self.title("Clicker Game")
        self.geometry("400x300")
        self.username = username
        self.auth_key = None  # Store the auth key
        self._score = 0
        self._encoded_score = self.encode_score(self._score)
        self.timer_duration = 60
        self.remaining_time = self.timer_duration
        self.upgrade_cost = 5
        signal.signal(signal.SIGINT, self.handle_exit)
        signal.signal(signal.SIGTERM, self.handle_exit)

        self.score_label = ctk.CTkLabel(self, text="Score: 0", font=("Arial", 24))
        self.score_label.pack(pady=20)
        self.click_button = ctk.CTkButton(self, text="Click Me!", command=self.increment_score)
        self.click_button.pack(pady=20)
        self.timer_label = ctk.CTkLabel(self, text=f"Time Remaining: {self.remaining_time}s", font=("Arial", 14))
        self.timer_label.pack(pady=10)
        self.leaderboard_button = ctk.CTkButton(self, text="View Leaderboard", command=self.show_leaderboard)
        self.leaderboard_button.pack(pady=10)
        self.upgrade_button = ctk.CTkButton(self, text="Upgrade (Cost: 5)", command=self.upgrade_timer)
        self.upgrade_button.pack(pady=10)

        self.after(5000, self.anti_cheat_monitor)
        self.after(10000, self.send_score_to_server)
        self.start_countdown()

        # Create user on the server and get the auth key
        self.create_user()

    def encode_score(self, score):
        return base64.b64encode(str(score).encode()).decode()

    def start_countdown(self):
        self.click_button.configure(state="disabled")
        self.remaining_time = self.timer_duration
        self.update_timer()

    def update_timer(self):
        if self.remaining_time > 0:
            self.timer_label.configure(text=f"Time Remaining: {self.remaining_time}s")
            self.remaining_time -= 1
            self.after(1000, self.update_timer)
        else:
            self.timer_label.configure(text="You can click now!")
            self.click_button.configure(state="normal")

    def increment_score(self):
        self._score += 1
        self._encoded_score = self.encode_score(self._score)
        self.update_score_display()
        self.start_countdown()

    def update_score_display(self):
        self.score_label.configure(text=f"Score: {self._score}")

    def create_user(self):
        """Create a new user and retrieve the auth key from the server."""
        try:
            data = {
                'username': self.username,
                'score': self._score
            }
            response = requests.post(LEADERBOARD_ENDPOINT, json=data, timeout=5, verify=False)
            response.raise_for_status()  # Raise an error for bad responses
            result = response.json()
            self.auth_key = result.get('auth_key')  # Get the auth key from the server
            logging.info(f"User created successfully with auth key: {self.auth_key}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error while creating user: {e}")

    def send_score_to_server(self):
        try:
            data = {
                'username': self.username,
                'score': self._score,
                'auth_key': self.auth_key  # Include the auth key
            }
            response = requests.post(LEADERBOARD_ENDPOINT, json=data, timeout=5, verify=False)
            response.raise_for_status()
            logging.info("Score updated successfully on the server.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error while sending score to the server: {e}")

        self.after(10000, self.send_score_to_server)

    def show_leaderboard(self):
        leaderboard_text = self.fetch_leaderboard_data()
        self.display_leaderboard_window(leaderboard_text)

    def fetch_leaderboard_data(self):
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5, verify=False)
            response.raise_for_status()
            leaderboard_data = response.json()
            return "\n".join(
                [f"{i + 1}. {entry['username']}: {entry['score']}" for i, entry in enumerate(leaderboard_data)]
            )
        except requests.exceptions.RequestException as e:
            logging.error(f"Exception occurred while fetching leaderboard: {e}")
            return "Error fetching leaderboard."

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

        self.after(5000, self.anti_cheat_monitor)

    def handle_cheat_detected(self, cheat_name):
        self.timer_label.configure(text="Cooldown: Cheats Detected")
        self.click_button.configure(state="disabled")
        self.start_cooldown()

    def start_cooldown(self):
        self.remaining_time = 10
        self.update_timer()

    def upgrade_timer(self):
        if self._score >= self.upgrade_cost and self.timer_duration > 5:
            self._score -= self.upgrade_cost
            self.timer_duration -= 2
            self._encoded_score = self.encode_score(self._score)
            self.update_score_display()
            self.upgrade_cost += 5
            self.upgrade_button.configure(text=f"Upgrade (Cost: {self.upgrade_cost})")

            if self.timer_duration == 5:
                self.upgrade_button.configure(text="Maxed", state="disabled")
        else:
            logging.info("Not enough score to upgrade or timer duration is maxed.")

    def handle_exit(self, signum, frame):
        self.remove_user_from_server()
        self.quit()

    def remove_user_from_server(self):
        try:
            response = requests.delete(f"{LEADERBOARD_ENDPOINT}/{self.username}", timeout=5, verify=False)
            response.raise_for_status()
            logging.info(f"User {self.username} removed from the server.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error while removing user from the server: {e}")

def ask_for_username():
    update_script()
    username_window = ctk.CTk()
    username_window.title("Enter Username")
    username_window.geometry("300x200")

    def submit_username():
        username = username_entry.get()
        if username:
            if not is_username_valid(username):
                logging.warning("Username is invalid.")
                username_entry.delete(0, ctk.END)
                return
            username_window.destroy()
            app = ClickerGame(username)
            app.mainloop()
        else:
            logging.warning("Username cannot be empty.")

    username_entry = ctk.CTkEntry(username_window)
    username_entry.pack(pady=20)
    submit_button = ctk.CTkButton(username_window, text="Submit", command=submit_username)
    submit_button.pack(pady=10)

    username_window.mainloop()

def is_username_valid(username):
    return len(username) > 0 and not any(banned_word in username for banned_word in BANNED_WORDS)

if __name__ == "__main__":
    ask_for_username()