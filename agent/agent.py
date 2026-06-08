import os
import json
import openai
from skills.todo import TodoSkill
from skills.device import DeviceSkill

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # change as needed

openai.api_key = os.getenv("OPENAI_API_KEY")

class Agent:
    def __init__(self):
        self.todo = TodoSkill(db_path=os.getenv("DB_PATH", "data/assistant.db"))
        self.device = DeviceSkill(db_path=os.getenv("DB_PATH", "data/assistant.db"))
        # enhanced system prompt asking the model to reply with a JSON action
        self.system_prompt = (
            "You are an assistant that outputs a single JSON object describing the action to take. "
            "Return JSON only. Schema: {\"action\": <string>, \"text\": <string|null>, \"todo_title\": <string|null>, \"todo_id\": <int|null>, \"device_action\": <string|null>, \"args\": <object|null>}. "
            "Actions supported: speak, todo_add, todo_list, todo_complete, device_control, noop. "
            "For device_control use device_action and args. Do not include any code or commentary, only JSON."
        )

    def _ask_llm(self, transcript: str):
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"User said: \"{transcript}\". Decide action."}
        ]
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=300,
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
                lines.append(f"- [{t['id']}] {'✔' if t['completed'] else ' '} {t['title']}")
            return {"text": "\n".join(lines)}
        elif act == "todo_complete":
            todo_id = action.get("todo_id")
            if todo_id is None:
                return {"text": "I need a todo id to complete."}
            ok = self.todo.complete_todo(todo_id)
            return {"text": f"Marked todo {todo_id} complete." if ok else f"Couldn't find todo {todo_id}."}
        elif act == "device_control":
            # forward to device skill for validation & planning
            plan = self.device.plan_action({"device_action": action.get("device_action"), "args": action.get("args")}, text)
            # if requires confirmation, tell client to ask user to confirm
            if plan.get("requires_confirmation"):
                return {"device_pending": True, "pending_id": plan.get("pending_id"), "message": plan.get("message")}
            else:
                # best-effort execute
                res = self.device.confirm_and_execute(plan.get("pending_id"))
                return {"text": res.get("message")}
        elif act == "speak":
            return {"text": action.get("text", "Okay.")}
        else:
            return {"text": action.get("text", "Okay.")}
