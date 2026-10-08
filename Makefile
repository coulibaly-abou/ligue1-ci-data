install:
	pip install -e ".[dev,modele]"
db:
	docker compose up -d
collect:
	python -m src.collecte.run
etl:
	python -m src.etl.run
train:
	python -m src.modele.entrainement
export:
	python -m src.restitution.export
figures:
	python -m src.restitution.figures
rapport: figures
	python -m src.restitution.rapport
app:
	streamlit run app/Accueil.py
pipeline: collect etl train export
test:
	pytest
lint:
	ruff check .
video:
	python -m src.restitution.video
