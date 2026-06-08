import os
import json
import openai
from skills.todo import TodoSkill

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # change as needed

openai.api_key = os.getenv("OPENAI_API_KEY")

class Agent:
    def __init__(self):
        self.todo = TodoSkill(db_path=os.getenv("DB_PATH", "data/assistant.db"))
        # basic system prompt asking the model to reply with a JSON action
        self.system_prompt = (
            "You are an assistant that outputs a single JSON object describing the action to take. "
            "Return JSON only. Schema:{\"action\": <string>, \"text\": <string|null>, \"todo_title\": <string|null>, \"todo_id\": <int|null>}. "
            "Actions supported: speak, todo_add, todo_list, todo_complete, noop. "
            "If you want to speak back to the user, use action 'speak' and set 'text'."
        )

    def _ask_llm(self, transcript: str):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User said: \"{transcript}\". Decide action."}
        ]
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=200,
            temperature=0.2,
        )
        return resp.choices[0].message.content

    def handle_text(self, text: str):
        # Ask LLM for JSON action
        raw = self._ask_llm(text)
        try:
            action = json.loads(raw)
        except Exception:
            # fallback: speak raw text as reply
            return {"text": "Sorry, I couldn't parse the plan. " + raw}

        act = action.get("action")
        if act == "todo_add":
            title = action.get("todo_title") or text
            todo = self.todo.add_todo(title)
            return {"text": f"Added todo: {title}"}
        elif act == "todo_list":
            todos = self.todo.list_todos()
            if not todos:
                return {"text": "Your todo list is empty."}
            lines = ["Your todos:"]
            for t in todos:
                lines.append(f"- [{t['id']}] {'\u2714' if t['completed'] else ' '} {t['title']}")
            return {"text": "\n".join(lines)}
        elif act == "todo_complete":
            todo_id = action.get("todo_id")
            if todo_id is None:
                return {"text": "I need a todo id to complete."}
            ok = self.todo.complete_todo(todo_id)
            return {"text": f"Marked todo {todo_id} complete." if ok else f"Couldn't find todo {todo_id}."}
        elif act == "speak":
            return {"text": action.get("text", "Okay.")}
        else:
            return {"text": action.get("text", "Okay.")}
