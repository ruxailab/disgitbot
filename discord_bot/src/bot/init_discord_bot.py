"""
Discord Bot Initialization

Entry point for the Discord bot using modular architecture.
"""

from .bot import create_bot

def main():
    """Main entry point for the Discord bot."""
    bot_instance = create_bot()
    bot_instance.run()

# For backward compatibility
if __name__ == "__main__":
    main()
