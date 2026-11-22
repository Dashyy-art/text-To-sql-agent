# Commandes du projet. Toutes se lancent depuis la racine.
# Aucun compte cloud ni clé : la base DuckDB est livrée dans data/.
RUN = uv run

.PHONY: install lint test serve ask ask-precis eval eval-dev experiments

install:      ## Installe l'environnement et le contrôle avant commit
	uv sync
	uv run pre-commit install

lint:         ## Vérifie le style
	uv run ruff check .
	uv run ruff format --check .

test:         ## Tests unitaires, dont les attaques contre la base (sans réseau ni secret)
	uv run pytest -q

serve:        ## Lance le serveur MCP (stdio), pour un client MCP (ex. MCP Inspector)
	$(RUN) climate-sql-mcp

ask:          ## Pose une question : make ask Q="Quelle a été l'année la plus chaude ?"
	$(RUN) climate-sql-agent "$(Q)"

ask-precis:   ## Même chose avec le mode réflexion : plus juste (57 % contre 45 %), environ 5 fois plus lent
	$(RUN) climate-sql-agent --think "$(Q)"

eval-dev:     ## Évalue sur les 10 questions de développement
	$(RUN) climate-sql-eval --split dev --label dev

eval:         ## Évaluation officielle : 40 questions de test, 3 passages
	$(RUN) climate-sql-eval --split test --runs 3 --label reference

experiments:  ## Évaluation officielle + expériences (environ 1 h 15)
	./scripts/experiences.sh
