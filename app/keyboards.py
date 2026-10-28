import json

def quality_keyboard() -> str:
    buttons = [
        [{"action": {"type": "text", "label": "1080p"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "720p"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "480p"}, "color": "primary"}],
        [{"action": {"type": "text", "label": "Отмена"}, "color": "secondary"}],
    ]
    return json.dumps({"one_time": True, "buttons": buttons}, ensure_ascii=False)

def main_keyboard() -> str:
    buttons = [
        [{"action": {"type": "text", "label": "ℹ️ Помощь"}, "color": "secondary"}],
        [{"action": {"type": "text", "label": "Отмена"}, "color": "secondary"}],
    ]
    return json.dumps({"one_time": False, "buttons": buttons}, ensure_ascii=False)
