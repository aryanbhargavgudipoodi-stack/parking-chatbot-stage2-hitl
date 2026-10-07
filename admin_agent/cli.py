"""
Admin-facing CLI: lets the administrator approve/refuse reservation
requests by chatting in natural language with the LangChain tool-calling
agent (in addition to the REST API in admin_agent/api.py).

Usage:
    python -m admin_agent.cli

Try:
    list pending requests
    approve request <id> because a slot is available
    refuse request <id>, lot is full
"""
from admin_agent.agent import AdminAgent


def main():
    admin_agent = AdminAgent()
    executor = admin_agent.build_admin_chat_agent()

    print("Admin console — type 'exit' to quit. Try: 'list pending requests'")
    chat_history = []
    while True:
        try:
            user_input = input("Admin: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        result = executor.invoke({"input": user_input, "chat_history": chat_history})
        print(f"Agent: {result['output']}")
        chat_history.append(("human", user_input))
        chat_history.append(("ai", result["output"]))


if __name__ == "__main__":
    main()