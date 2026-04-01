from __future__ import annotations

import shutil
import subprocess


def notify_mac(title: str, message: str, url: str | None = None) -> None:
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")

    notifier = shutil.which("terminal-notifier")
    if notifier and url:
        subprocess.run(
            [
                notifier,
                "-title",
                safe_title,
                "-message",
                safe_message,
                "-open",
                url,
            ],
            check=False,
        )
        return

    if url:
        script = (
            f'display dialog "{safe_message}" with title "{safe_title}" '
            'buttons {"打开页面"} default button 1 '
            'with icon note giving up after 20\n'
            f'do shell script "open \\"{url}\\""'
        )
        subprocess.run(["osascript", "-e", script], check=False)
        return

    script = f'display notification "{safe_message}" with title "{safe_title}"'
    subprocess.run(["osascript", "-e", script], check=False)
