.PHONY: test serve init verify ingest benchmark clean

test:
	python -m unittest discover tests -v

serve:
	python gauntlet.py serve --host 0.0.0.0 --port 8080 --dir database

init:
	python gauntlet.py init --dir database

verify:
	python gauntlet.py verify --dir database

ingest:
	python gauntlet.py ingest datasets/demo_events.jsonl --dir database

benchmark:
	python gauntlet.py benchmark --dir database

clean:
	rm -rf database/ __pycache__ gauntlet/**/__pycache__
