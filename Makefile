.PHONY: run reset-memory run-fresh

run: 
	python -m chainlit run src/interfaces/chainlit_app.py

reset-memory:
	rm -f src/ai_companion/modules/memory/short_term/memory.db

run-fresh: reset-memory run
