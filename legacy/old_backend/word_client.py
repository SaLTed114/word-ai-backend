import json
import os

import requests
import win32com.client

# from dotenv import load_dotenv

# load_dotenv()  # 加载 .env 文件

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def get_word_text():
    """获取当前活动Word文档的全部文本或选中文本"""
    try:
        word = win32com.client.GetActiveObject("Word.Application")
        doc = word.ActiveDocument
        # 获取选中文本，如果没有选中则获取全部文本
        if (
            word.Selection.Type != 0
        ):  # wdSelectionIP (0) means insertion point, not selected text
            text = word.Selection.Range.Text
            # Store the selection range to potentially update it later
            selection_range = word.Selection.Range
            return text, selection_range
        else:
            text = doc.Content.Text
            return text, doc.Content  # Use Content range for entire document
    except Exception as e:
        print(f"Error getting text from Word: {e}")
        return None, None


def update_word_text(range_to_update, new_text):
    """更新Word文档中的指定范围"""
    try:
        range_to_update.Text = new_text
        print("Word document updated.")
    except Exception as e:
        print(f"Error updating Word document: {e}")


def call_backend_api(endpoint, text):
    """调用后端API"""
    try:
        url = f"{BACKEND_URL}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        payload = {"text": text}
        print(f"Sending text to backend: {url}")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print("Backend response received.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling backend API: {e}")
        return None


if __name__ == "__main__":
    # Example Usage:
    # You would ideally add UI (like tkinter or a simple web server)
    # to trigger these actions. This is a command-line example.

    # 1. Get text from Word
    word_text, current_range = get_word_text()

    if word_text:
        print("\n--- Original Text from Word ---")
        print(word_text[:200] + "..." if len(word_text) > 200 else word_text)
        print("-------------------------------\n")

        # 2. Choose an action (in a real app, this would be a button click)
        action = input("Choose action (grammar, vocab, style): ").lower()

        if action == "grammar":
            result = call_backend_api("grammar", word_text)
            if result and result.get("corrected_text"):
                print("\n--- Grammar Correction Result ---")
                print(result["corrected_text"])
                print("-------------------------------\n")
                # Optionally update Word with the corrected text
                update = input("Update Word with corrected text? (yes/no): ").lower()
                if update == "yes":
                    update_word_text(current_range, result["corrected_text"])

        elif action == "vocab":
            result = call_backend_api("vocabulary", word_text)
            if result and result.get("suggestions"):
                print("\n--- Vocabulary Suggestions ---")
                for suggestion in result["suggestions"]:
                    print(
                        f"'{suggestion['original']}' -> '{suggestion['suggestion']}' (Context: {suggestion['context']})"
                    )
                print("------------------------------\n")
                # For vocab, replacing is more complex (need to find/replace accurately)
                # This example doesn't automatically replace. A real app would need
                # more sophisticated logic or user interaction to apply suggestions.

        elif action == "style":
            style_prompt = input("Enter style instruction (e.g., formal, concise): ")
            result = call_backend_api(
                "style", {"text": word_text, "style_instruction": style_prompt}
            )  # Pass style instruction
            if result and result.get("adjusted_text"):
                print("\n--- Style Adjustment Result ---")
                print(result["adjusted_text"])
                print("-------------------------------\n")
                update = input("Update Word with adjusted text? (yes/no): ").lower()
                if update == "yes":
                    update_word_text(current_range, result["adjusted_text"])

        else:
            print("Invalid action.")
    else:
        print("Could not get text from Word. Make sure Word is open with a document.")
