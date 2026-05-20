import os
import random
import string
import time
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import concurrent.futures
from tkinter import ttk

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NEGATIVE_AVAILABILITY_PATTERN = re.compile(
    r'\b(is not avail\w*|are not avail\w*|not avail\w*|already taken|is taken|taken|unavailable)\b',
    re.IGNORECASE,
)
POSITIVE_AVAILABILITY_PATTERN = re.compile(
    r'\b(seems to be available|is available|available)\b',
    re.IGNORECASE,
)
HTML_DIV_RESPONSE_PATTERN = re.compile(
    r'<div[^>]+id=["\'](?:yres|nres)["\'][^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)

thread_local = threading.local()

class color:
    VIOLET, CYAN, DARK_CYAN, BLUE, GREEN, YELLOW, RED, WHITE, BLACK, GRAY, MAGENTA, BOLD, DIM, NORMAL, UNDERLINED, STOP = '\033[95m', '\033[96m', '\033[36m', '\033[94m', '\033[92m', '\033[93m', '\033[91m', '\033[37m', '\033[30m','\033[38;2;88;88;88m', '\033[35m', '\033[1m', '\033[2m', '\033[22m', '\033[4m', '\033[0m'

def create_requests_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=100,
        pool_maxsize=100,
        pool_block=True,
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6420.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    return session


def get_session():
    if not hasattr(thread_local, 'session'):
        thread_local.session = create_requests_session()
    return thread_local.session


def parse_availability_response(response):
    if not response:
        return None

    normalized = ' '.join(response.split())
    if NEGATIVE_AVAILABILITY_PATTERN.search(normalized):
        return False
    if POSITIVE_AVAILABILITY_PATTERN.search(normalized):
        return True
    if 'avail' in normalized and not NEGATIVE_AVAILABILITY_PATTERN.search(normalized):
        return True
    return None


def extract_response_text(html_text):
    match = HTML_DIV_RESPONSE_PATTERN.search(html_text or '')
    if match:
        raw_text = match.group(1)
        raw_text = re.sub(r'<[^>]+>', '', raw_text)
        return raw_text.strip()
    return (html_text or '').strip()


def check_username_availability(username):
    try:
        session = get_session()
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                page = session.post(
                    'https://www.gamertagavailability.com/checkuser.php',
                    data={'Gamertag': username, 'Language': 'English'},
                    timeout=20,
                    verify=False,
                )
                break
            except requests.exceptions.Timeout:
                if attempt == max_retries:
                    raise
                time.sleep(0.5 * attempt)

        if page.status_code != 200:
            return None, f"HTTP {page.status_code} received from availability service."

        response = extract_response_text(page.text)
        print(f"Debug: {username} -> '{response}'")

        parsed = parse_availability_response(response)
        if parsed is False:
            return False, response
        if parsed is True:
            return True, response

        return None, f'Unexpected response: {response[:200]}'
    except requests.exceptions.SSLError as ssl_error:
        return None, f"SSL error while checking availability: {ssl_error}"
    except requests.exceptions.RequestException as request_error:
        return None, f"Request error while checking availability: {request_error}"
    except Exception as e:
        return None, f"Error occurred while checking availability for {username}: {e}"

def is_valid_username(username):
    if not username or len(username) > 12 or not username[0].isalpha() or not username[-1].isalnum() or '  ' in username:
        return False
    for char in username:
        if not (char.isalnum() or char == ' '):
            return False
    return True

def generate_username(length):
    fragments = ["xim", "xen", "xio", "vex", "zen", "rax", "lyn", "kai", "tor", "nova", "ter", "fdo", "vki", "gko", "dwe", "fjv", "fkf", "ovk"]
    name = ""
    while len(name) < length:
        remaining = length - len(name)
        if remaining >= 3 and random.random() < 0.7:
            valid_fragments = [fragment for fragment in fragments if len(fragment) <= remaining]
            if valid_fragments:
                fragment = random.choice(valid_fragments)
                name += fragment
                continue
        name += random.choice(string.ascii_lowercase)
    name = name[:length]
    if not name[0].isalpha():
        name = random.choice(string.ascii_lowercase) + name[1:]
    return name

def generate_username_with_numbers(length):
    if length <= 3:
        return generate_username(length)
    digit = random.choice(string.digits)
    name = generate_username(length - 1)
    insert_pos = random.randrange(1, len(name))
    return name[:insert_pos] + digit + name[insert_pos:]

def clear_existing_usernames(length):
    folder_name = "Claimable"
    file_path = os.path.join(folder_name, f"{length}L.txt")
    if os.path.exists(file_path):
        with open(file_path, "w"):
            pass
        print(f"[ {color.GREEN}+{color.STOP} ] Existing {length}L usernames cleared.")
    else:
        print(f"[ {color.YELLOW}!{color.STOP} ] No existing {length}L usernames found.")

def save_valid_username_to_file(username, length):
    if username:
        folder_name = "Claimable"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        file_path = os.path.join(folder_name, f"{length}L.txt")
        
        # Add the new valid username to the file
        with open(file_path, "a") as file:
            if os.path.getsize(file_path) > 0:  # Check if file is not empty
                file.write('\n')  # Add newline only if the file is not empty
            file.write(username)

class GamertagCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gamertag Checker")
        self.root.geometry("720x620")
        self.root.configure(bg="#120003")
        self.file_lock = threading.Lock()
        
        # Plasma red/black theme
        self.bg_color = "#120003"
        self.entry_bg = "#1f0007"
        self.fg_color = "#ffb3b3"
        self.button_bg = "#a80000"
        self.button_fg = "#ffffff"

        title_label = tk.Label(root, text="GAMERTAG CHECKER", bg=self.bg_color, fg="#ff5050", font=("Arial", 20, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(12, 10))

        # Own list option
        self.own_list_var = tk.BooleanVar()
        cb = tk.Checkbutton(root, text="Use your own list of usernames", variable=self.own_list_var, command=self.toggle_own_list, bg=self.bg_color, fg=self.fg_color, selectcolor="#330000", activebackground="#220001", activeforeground="#ffdddd", highlightthickness=0)
        cb.grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=5)

        # Length input
        length_label = tk.Label(root, text="Username length (3-12):", bg=self.bg_color, fg=self.fg_color)
        length_label.grid(row=2, column=0, sticky='w', padx=10, pady=5)
        self.length_var = tk.IntVar(value=3)
        length_spinbox = tk.Spinbox(root, from_=3, to=12, textvariable=self.length_var, bg=self.entry_bg, fg=self.fg_color, insertbackground="#ff5555", relief='flat', highlightthickness=1, highlightbackground="#440000")
        length_spinbox.grid(row=2, column=1, sticky='w', padx=10, pady=5)

        # Discord webhook input
        webhook_label = tk.Label(root, text="Discord Webhook URL (optional):", bg=self.bg_color, fg=self.fg_color)
        webhook_label.grid(row=7, column=0, sticky='w', padx=10, pady=5)
        self.webhook_var = tk.StringVar(value="https://discordapp.com/api/webhooks/1502558522246955059/hbjBPQkzngpgqy2nR4lfuzW-3lIu62n4u5iY3v8rLc2pcUYFYT3hF29nWc0ihJIaQPYa")
        self.webhook_entry = tk.Entry(root, textvariable=self.webhook_var, width=30, bg=self.entry_bg, fg=self.fg_color, insertbackground="#ff5555", relief='flat', highlightthickness=1, highlightbackground="#440000")
        self.webhook_entry.grid(row=7, column=1, columnspan=3, sticky='w', padx=10, pady=5)
        
        # File path input (hidden initially)
        self.file_label = tk.Label(root, text="File path:", bg=self.bg_color, fg=self.fg_color)
        self.file_entry = tk.Entry(root, width=50, bg=self.entry_bg, fg=self.fg_color, insertbackground="#ff5555", relief='flat', highlightthickness=1, highlightbackground="#440000")
        self.browse_button = tk.Button(root, text="Browse", command=self.browse_file, bg=self.button_bg, fg=self.button_fg, activebackground="#770000", activeforeground="#ffffff", bd=0)
        self.clear_button = tk.Button(root, text="Clear existing", command=self.clear_existing, bg=self.button_bg, fg=self.button_fg, activebackground="#770000", activeforeground="#ffffff", bd=0)

        # Generate options (shown when not own list)
        self.num_label = tk.Label(root, text="Number of usernames to generate:", bg=self.bg_color, fg=self.fg_color)
        self.num_var = tk.IntVar(value=10)
        self.num_entry = tk.Spinbox(root, from_=1, to=1000, textvariable=self.num_var, bg=self.entry_bg, fg=self.fg_color, insertbackground="#ff5555", relief='flat', highlightthickness=1, highlightbackground="#440000")
        self.numbers_var = tk.BooleanVar()
        self.numbers_check = tk.Checkbutton(root, text="Include numbers", variable=self.numbers_var, bg=self.bg_color, fg=self.fg_color, selectcolor="#330000", activebackground="#220001", activeforeground="#ffdddd", highlightthickness=0)

        # Output area
        output_label = tk.Label(root, text="Output:", bg=self.bg_color, fg=self.fg_color)
        output_label.grid(row=5, column=0, sticky='w', padx=10, pady=5)
        self.output_text = scrolledtext.ScrolledText(root, width=90, height=15, bg="#120005", fg="#ff8a8a", insertbackground="#ff8a8a", relief='flat', bd=0)
        self.output_text.grid(row=6, column=0, columnspan=4, padx=10, pady=5)

        # Start button
        self.start_button = tk.Button(root, text="Start Checking", command=self.start_checking, bg=self.button_bg, fg=self.button_fg, font=("Arial", 12, "bold"), padx=10, pady=10, activebackground="#880000", bd=0)
        self.start_button.grid(row=8, column=0, columnspan=2, pady=10)

        # Stop button
        self.stop_button = tk.Button(root, text="Stop Checking", command=self.stop_checking, bg="#cc1111", fg="#ffffff", font=("Arial", 12, "bold"), padx=10, pady=10, state='disabled', activebackground="#990000", bd=0)
        self.stop_button.grid(row=8, column=2, columnspan=2, pady=10)

        watermark_label = tk.Label(root, text="made by sou1w4ves", bg=self.bg_color, fg="#8b1a1a", font=("Arial", 8, "italic"))
        watermark_label.grid(row=9, column=0, sticky='w', padx=10, pady=(0, 6))

        self.toggle_own_list()

    def toggle_own_list(self):
        if self.own_list_var.get():
            self.file_label.grid(row=3, column=0, sticky='w', padx=10, pady=5)
            self.file_entry.grid(row=3, column=1, sticky='w', padx=10, pady=5)
            self.browse_button.grid(row=3, column=2, padx=5, pady=5)
            self.clear_button.grid(row=4, column=0, columnspan=2, pady=5)
            self.num_label.grid_remove()
            self.num_entry.grid_remove()
            self.numbers_check.grid_remove()
        else:
            self.file_label.grid_remove()
            self.file_entry.grid_remove()
            self.browse_button.grid_remove()
            self.clear_button.grid_remove()
            self.num_label.grid(row=3, column=0, sticky='w', padx=10, pady=5)
            self.num_entry.grid(row=3, column=1, sticky='w', padx=10, pady=5)
            self.numbers_check.grid(row=4, column=0, columnspan=2, sticky='w', padx=10, pady=5)

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select file", filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)

    def clear_existing(self):
        length = self.length_var.get()
        clear_existing_usernames(length)
        self.output_text.insert(tk.END, f"Cleared existing {length}L usernames.\n")

    def update_output(self, text):
        self.root.after(0, lambda: self.output_text.insert(tk.END, text))

    def start_checking(self):
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.output_text.delete(1.0, tk.END)
        self.cancel_event = threading.Event()
        threading.Thread(target=self.run_checks).start()

    def stop_checking(self):
        if hasattr(self, 'cancel_event'):
            self.cancel_event.set()
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.update_output("Checking stopped by user.\n")

    def send_to_discord(self, username):
        """Send available gamertag to Discord webhook"""
        webhook_url = self.webhook_var.get().strip()
        if not webhook_url:
            return
        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = {
                    "content": f"✅ **Available Gamertag Found!**\n`{username}`"
                }
                response = requests.post(webhook_url, json=data, timeout=10)
                if response.status_code == 204:
                    self.update_output(f"Sent to Discord: {username}\n")
                    return
                elif response.status_code == 429:
                    retry_after = response.json().get('retry_after', 1)
                    self.update_output(f"Rate limited, retrying in {retry_after:.2f}s...\n")
                    time.sleep(retry_after)
                    continue
                else:
                    self.update_output(f"Failed to send to Discord: {response.status_code} - {response.text}\n")
                    return
            except Exception as e:
                self.update_output(f"Failed to send to Discord: {e}\n")
                return
        self.update_output(f"Gave up sending to Discord after {max_retries} retries.\n")

    def run_checks(self):
        try:
            folder_name = "Claimable"
            if not os.path.exists(folder_name):
                os.makedirs(folder_name)
                self.update_output("'Claimable' folder created.\n")

            length = self.length_var.get()
            if self.own_list_var.get():
                file_path = self.file_entry.get().strip()
                if not os.path.isfile(file_path):
                    messagebox.showerror("Error", "Invalid file path.")
                    self.start_button.config(state='normal')
                    return
                with open(file_path, "r") as file:
                    usernames = [username.strip() for username in file.readlines() if username.strip()]
                usernames = list(dict.fromkeys(usernames))
                # Filter to selected length and valid usernames
                usernames = [u for u in usernames if len(u) == length and is_valid_username(u)]
            else:
                num_usernames = self.num_var.get()
                use_numbers = self.numbers_var.get()
                usernames = []
                username_set = set()
                while len(usernames) < num_usernames:
                    if use_numbers:
                        new_username = generate_username_with_numbers(length)
                    else:
                        new_username = generate_username(length)
                    if is_valid_username(new_username) and new_username not in username_set:
                        username_set.add(new_username)
                        usernames.append(new_username)

            max_workers = min(80, max(1, len(usernames)))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_username = {executor.submit(check_username_availability, username): username for username in usernames}
                for future in concurrent.futures.as_completed(future_to_username):
                    if self.cancel_event.is_set():
                        self.update_output("Checking cancelled.\n")
                        break
                    username = future_to_username[future]
                    try:
                        availability, response = future.result()
                        if availability is True:
                            self.update_output(f"✅ Gamertag '{username}' seems to be available!\n")
                            with self.file_lock:
                                save_valid_username_to_file(username, length)
                            self.send_to_discord(username)
                        elif availability is False:
                            self.update_output(f"❌ Gamertag '{username}' is not available!\n")
                        else:
                            self.update_output(f"⚠️ Could not determine availability for '{username}': {response}\n")
                    except Exception as exc:
                        self.update_output(f"⚠️ Error checking {username}: {exc}\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))

def main():
    root = tk.Tk()
    app = GamertagCheckerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()