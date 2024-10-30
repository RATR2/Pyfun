import os
import sys
import requests
import hashlib
import base64
import customtkinter as ctk
import threading
import psutil
import time
from PVconfig import SERVER_IP, SERVER_PORT, LEADERBOARD_ENDPOINT

# GitHub repository information for the updater
REPO_OWNER = "RATR2"
REPO_NAME = "Pyfun"
FILE_PATH = "./"  # Path in the repo to the script file
LOCAL_SCRIPT_PATH = os.path.abspath(__file__)
# Anti-cheat configuration
KNOWN_CHEAT_PROCESSES = ["Cheat Engine", "WeMod"]

def get_remote_script_content():
    """
    Fetch the latest version of the script from GitHub.
    Returns:
        str: Content of the remote file.
    """
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{FILE_PATH}"
    response = requests.get(url)
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

        # UI elements
        self.score_label = ctk.CTkLabel(self, text="Score: 0", font=("Arial", 24))
        self.score_label.pack(pady=20)

        self.click_button = ctk.CTkButton(self, text="Click Me!", command=self.increment_score)
        self.click_button.pack(pady=20)

        self.leaderboard_button = ctk.CTkButton(self, text="View Leaderboard", command=self.show_leaderboard)
        self.leaderboard_button.pack(pady=10)

        # Start anti-cheat thread
        self.anti_cheat_thread = threading.Thread(target=self.anti_cheat_monitor, daemon=True)
        self.anti_cheat_thread.start()

    def increment_score(self):
        # Increase the score and update obfuscated score
        self._score += 1
        self._encoded_score = encode_score(self._score)
        self.update_score_display()

    def update_score_display(self):
        # Update score label in the UI
        self.score_label.configure(text=f"Score: {self._score}")

    def show_leaderboard(self):
        # Fetch and display leaderboard from server
        try:
            response = requests.get(LEADERBOARD_ENDPOINT, timeout=5)
            if response.status_code == 200:
                leaderboard_data = response.json()
                leaderboard_text = "\n".join(
                    [f"{i+1}. {entry['name']}: {entry['score']}" for i, entry in enumerate(leaderboard_data)]
                )
            else:
                leaderboard_text = "Failed to load leaderboard."
        except Exception as e:
            leaderboard_text = f"Error: {str(e)}"

        # Display leaderboard in new window
        leaderboard_window = ctk.CTkToplevel(self)
        leaderboard_window.title("Leaderboard")
        leaderboard_label = ctk.CTkLabel(leaderboard_window, text=leaderboard_text)
        leaderboard_label.pack(pady=10, padx=10)

    def anti_cheat_monitor(self):
        # Background process that continuously checks for known cheat programs
        while True:
            for process in psutil.process_iter(attrs=['name']):
                process_name = process.info['name']
                if any(cheat_tool.lower() in process_name.lower() for cheat_tool in KNOWN_CHEAT_PROCESSES):
                    self.show_cheat_detected_warning(process_name)
                    return
            time.sleep(5)  # Check every 5 seconds

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
