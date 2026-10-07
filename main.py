from src.chatbot import ParkingChatbot


def main():
    bot = ParkingChatbot()
    print("Parking Assistant — type 'exit' to quit.")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        print(f"Bot: {bot.handle_message(user_input)}")


if __name__ == "__main__":
    main()