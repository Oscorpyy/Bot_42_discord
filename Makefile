SCREEN_NAME = bot42

.PHONY: install run stop restart logs clean

install:
	uv sync

run:
	@screen -list | grep -q $(SCREEN_NAME) && echo "Le bot tourne déjà !" || \
	screen -dmS $(SCREEN_NAME) uv run main.py && echo "Bot lancé avec uv dans le screen '$(SCREEN_NAME)'."

stop:
	@screen -list | grep -q $(SCREEN_NAME) && screen -S $(SCREEN_NAME) -X quit && echo "Bot arrêté." || \
	echo "Le bot n'est pas en cours d'exécution."

restart: stop run

logs:
	screen -r $(SCREEN_NAME)

clean:
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} +
