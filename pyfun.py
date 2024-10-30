import os
import sys
import requests
import hashlib
import base64
import customtkinter as ctk
import threading
import psutil
import time
from PVconfig import SERVER_IP, LEADERBOARD_ENDPOINT, REPO_OWNER, REPO_NAME, FILE_PATH

LOCAL_SCRIPT_PATH = os.path.abspath(__file__)
KNOWN_CHEAT_PROCESSES = ["Cheat Engine", "WeMod"]

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

# Encodes and obfuscates score
def encode_score(score):
    return base64.b64encode(hashlib.sha256(str(score).encode()).digest()).decode()

class ClickerGame(ctk.CTk):
    def __init__(self):
        super().__init__()

        # GUI window properties
        self.title("Clicker Game")
        self.geometry("400x300")

        # Initial score and encoded score
        self._score = 0
        self._encoded_score = encode_score(self._score)
        
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
        
        # Start the countdown
        self.start_countdown()

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
        # Increase the score and update obfuscated score
        self._score += 1
        self._encoded_score = encode_score(self._score)
        self.update_score_display()
        
        # Restart the countdown after a successful click
        self.start_countdown()

    def update_score_display(self):
        # Update score label in the UI
        self.score_label.configure(text=f"Score: {self._score}")

    def show_leaderboard(self):
        # Default message if leaderboard fetch fails
        leaderboard_text = "Leaderboard data not available."
    
        # Attempt to fetch leaderboard data
        leaderboard_text = self.fetch_leaderboard_data()
    
        # Display leaderboard in new window
        self.display_leaderboard_window(leaderboard_text)

    def fetch_leaderboard_data(self):
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5)
            if response.status_code == 200:
                leaderboard_data = response.json()
                return "\n".join(
                    [f"{i+1}. {entry['name']}: {entry['score']}" for i, entry in enumerate(leaderboard_data)]
                )
            else:
                print(f"Leaderboard fetch failed with status code: {response.status_code}")
                return "Failed to load leaderboard."
        except Exception as e:
            print(f"Exception occurred while fetching leaderboard: {e}")  # Print the error message
            return f"Error: {str(e)}"

    def display_leaderboard_window(self, leaderboard_text):
        # Helper function to create a window to display leaderboard
        leaderboard_window = ctk.CTkToplevel(self)
        leaderboard_window.title("Leaderboard")
        leaderboard_label = ctk.CTkLabel(leaderboard_window, text=leaderboard_text)
        leaderboard_label.pack(pady=10, padx=10)

        # Display leaderboard in new window
        leaderboard_window = ctk.CTkToplevel(self)
        leaderboard_window.title("Leaderboard")
        leaderboard_label = ctk.CTkLabel(leaderboard_window, text=leaderboard_text)
        leaderboard_label.pack(pady=10, padx=10)

    def anti_cheat_monitor(self):
        # Background process that continuously checks for known cheat programs
        for process in psutil.process_iter(attrs=['name']):
            process_name = process.info['name']
            if any(cheat_tool.lower() in process_name.lower() for cheat_tool in KNOWN_CHEAT_PROCESSES):
                self.show_cheat_detected_warning(process_name)
                return

        # Schedule the next anti-cheat check
        self.after(5000, self.anti_cheat_monitor)  # Repeat check every 5 seconds

    def show_cheat_detected_warning(self, cheat_name):
        # Notify the user that a cheat tool was detected
        warning_window = ctk.CTkToplevel(self)
        warning_window.title("Cheat Detected")
        warning_label = ctk.CTkLabel(warning_window, text=f"Cheat Detected: {cheat_name}\nGame will close.")
        warning_label.pack(pady=10, padx=10)
        
        # Exit game after warning
        self.after(3000, self.destroy)

if __name__ == "__main__":
    update_script()  # Check for updates before starting the game

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = ClickerGame()
    app.mainloop()
