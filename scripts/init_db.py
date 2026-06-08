# Initialize DB (creates data directory + todos table)
import os
from skills.todo import TodoSkill

os.makedirs("data", exist_ok=True)
TodoSkill(db_path="data/assistant.db")
print("Initialized data/assistant.db with todos table")
