import os
import json
from datetime import datetime

class SessionRepository:
    def __init__(self, data_dir="data/sessions"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_messages(self, session_id, messages):
        if not session_id.endswith(".json"):
            filename = f"{session_id}.json"
        else:
            filename = session_id
        
        path = os.path.join(self.data_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

    def load_messages_if_exists(self, filename):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_messages(self, filename):
        return self.load_messages_if_exists(filename) or []

    def list_history_files(self, limit=20):
        files = [f for f in os.listdir(self.data_dir) if f.endswith(".json")]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.data_dir, x)), reverse=True)
        return files[:limit]

    def list_session_previews(self, limit=20):
        previews = []
        for filename in self.list_history_files(limit):
            path = os.path.join(self.data_dir, filename)
            mtime = os.path.getmtime(path)
            dt = datetime.fromtimestamp(mtime)
            
            with open(path, "r", encoding="utf-8") as f:
                messages = json.load(f)
            
            title = "新对话"
            for msg in messages:
                if msg["role"] == "user":
                    content = msg["content"].strip()
                    # Skip titles that are just question marks or empty
                    if not content or set(content) == {"?"}:
                        continue
                    title = content[:15]
                    break
            
            previews.append({
                "session_id": filename.replace(".json", ""),
                "title": title,
                "updated_at": dt.strftime("%Y-%m-%d %H:%M"),
                "filename": filename
            })
        return previews

    def resolve_session_id(self, preferred_id):
        return preferred_id

    def delete_session(self, filename):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            os.remove(path)

    def rename_session(self, filename, new_title):
        # Implementation can be simple or mapping based
        return filename
