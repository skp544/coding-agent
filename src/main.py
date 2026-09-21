from runtime import AgentTurnResult, resume_turn, start_turn, format_interrupt
from config.config import get_work_dir
from models import select_provider
from memory.memory import thread_config, make_checkpointer
from agent import build_agent
from prompts import build_system_prompt, build_greeting
from typing import Any
import uuid


def _ask_yes_or_no(name: str) -> bool:
    while True:
        answer = input(f"Allow {str(name)}? (y/n): ").strip().lower()

        if answer in ["y", "yes"]:
            return True
        if answer in ["n", "no"]:
            return False
        print("Please answer with 'y' or 'n'. ", flush=True)


def _prompt_decision(pending: dict[str, Any]) -> list[dict]:
    print("\n----human in the loop-------", flush=True)
    print(format_interrupt(pending), flush=True)

    requests = pending.get("action_requests") or []
    decisions: list[dict] = []

    for action in requests:
        name = action.get("name", "tool")
        approved = _ask_yes_or_no(name)
        if approved:
            decisions.append({"type": "approve"})
        else:
            decisions.append(
                {
                    "type": "reject",
                    "message": (
                        f"User declined {str(name)}. Do not immediately retry the same."
                        "Explain what failed or ask the user"
                    ),
                }
            )

    print("------------------------------------------\n", flush=True)
    return decisions


def _drain(agent, result: AgentTurnResult, config: dict) -> AgentTurnResult:
    while result.pending_interrupt is not None:
        decision = _prompt_decision(result.pending_interrupt)
        result = resume_turn(agent, decision, config)

    return result


def chat() -> None:
    work_dir = get_work_dir()
    work_dir.mkdir(exist_ok=True, parents=True)

    provider = select_provider()
    checkpointer = make_checkpointer()
    agent = build_agent(checkpointer=checkpointer)

    config = thread_config(str(uuid.uuid4()))

    print(build_greeting())
    print(f"Provider: {provider.name} . {provider.model}")
    print(f"Working directory: {work_dir}")
    print("Type 'exit', 'quit', 'stop', 'bye' or 'q' to exit the conversation.\n")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() in ("exit", "quit", "stop", "bye", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        try:
            result = _drain(agent, start_turn(agent, user_input, config), config)
        except RuntimeError as e:
            print(f"LLM: {e}\n")
            continue

        except Exception as e:
            print(f"LLM: {type(e).__name__}: {e}\n")
            continue

        print(f"LLM: {result.text or '(no text)'}\n")

        if result.structured:
            print(
                f"Summary = {result.structured.status}\n"
                f"{result.structured.summary}"
                f"Files touched= {result.structured.files_touched}"
            )
        print("\n")


if __name__ == "__main__":
    chat()
