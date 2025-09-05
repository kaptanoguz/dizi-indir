# Dizibox Downloader

Tired of dealing with Dizibox's amateur protections? This tool just gets you the file directly. It's designed to cut through their simple layers of protection.

### The Security Layers It Handles

The obstacles they use are basic. Here's what this tool automates for you:

*   **Newbie Trap (`debugger;`):** The script isn't browser-based, so we dont even give a damn about this.
*   **Nested iframes:** Instead of manually clicking through multiple `iframe`s, the script passes the entire chain automatically.
*   **Referer Check:** It sends the correct referer header, bypassing the check, simple.
*   **AES Encryption:** They "encrypt" the final video with basic AES and thankfully provide the key. The script simply uses it to decrypt the file.

### What It Does

*   **Bypasses Protections:** Handles all the obstacles listed above in seconds. You just provide the link.
*   **Single or Season Download:** Give it a single episode link, or add `--sezon` to grab the entire season.
*   **Automatic Organization:** Finds the series name, season, and episode number on its own. Creates folders like `The-Series-Name Season-1` and names files neatly like `01. Episode - Episode Name.mp4`.
*   **Skips Duplicates:** It detects if you've already downloaded an episode and skips it to save time.

### Installation

You have Python. Just install these:

```bash
pip install requests beautifulsoup4 pycryptodome tqdm yt-dlp
```

### Usage

*   **Single Episode:**
    ```bash
    python dizibox.py "https://www.dizibox.net/series-name/season-1-episode-1"
    ```

*   **Full Season:**
    ```bash
    python dizibox.py "https://www.dizibox.net/series-name/season-1-episode-5" --sezon
    ```

That's it. Download and watch.
