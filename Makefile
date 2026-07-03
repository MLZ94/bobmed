# BobMed — Pipeline de publication d'un quiz
#
# Usage : make validate F=Quiz_UE7.3_2024-2025_S1.html
#         make insert   F=Quiz_UE7.3_2024-2025_S1.html
#         make publish  F=Quiz_UE7.3_2024-2025_S1.html
#
# Chaque cible dépend de la précédente : insert ne tourne que si validate passe,
# publish ne tourne que si insert réussit.
#
# Variable F : chemin vers le quiz HTML (sans le .snippet.html — déduit auto).

.PHONY: validate insert test publish check-f

# Vérification que F est défini
check-f:
ifndef F
	$(error "Variable F manquante. Exemple : make validate F=Quiz_UE7.3_2024-2025_S1.html")
endif

# ── Étape 1 : validation automatique ──────────────────────────────────────────
validate: check-f
	@echo "▶ Validation de $(F)…"
	python3 validate_quiz.py "$(F)"
	@echo "✓ Validation OK"

# ── Étape 2 : insertion dans le portail ───────────────────────────────────────
# Dépend de validate : bloqué si des erreurs existent.
SNIPPET = $(F:.html=.snippet.html)

insert: validate
	@echo "▶ Insertion du snippet dans le portail…"
	@if [ ! -f "$(SNIPPET)" ]; then \
		echo "✗ Fichier snippet introuvable : $(SNIPPET)"; \
		exit 1; \
	fi
	python3 insert_snippet.py "$(SNIPPET)"
	@echo "✓ Portail mis à jour"

# ── Étape 3 : vérification du portail (dry-run de l'insertion) ────────────────
# Utile pour prévisualiser sans toucher au portail.
dry-run: check-f
	@echo "▶ Dry-run — aucune modification écrite"
	@if [ ! -f "$(SNIPPET)" ]; then echo "✗ Snippet introuvable : $(SNIPPET)"; exit 1; fi
	python3 insert_snippet.py --dry-run "$(SNIPPET)"

# ── Étape 4 : publication complète ────────────────────────────────────────────
# Enchaîne validate + insert, puis prépare le commit.
# Le git add/commit reste manuel pour garder le contrôle sur ce qui est stagé.
publish: insert
	@echo ""
	@echo "══════════════════════════════════════════════════"
	@echo "  Prêt à publier. Vérifier le diff avant commit :"
	@echo "    git diff"
	@echo "    git add $(F) $(SNIPPET) <portail modifié>"
	@echo "    git commit -m \"Ajouter $(notdir $(F))\""
	@echo "    git push -u origin main"
	@echo "══════════════════════════════════════════════════"

# ── Validation de tous les quiz existants ─────────────────────────────────────
validate-all:
	@echo "▶ Validation de tous les quiz HTML…"
	@python3 validate_quiz.py $$(find . -name "Quiz_*.html" | sort) ; \
	EXIT=$$? ; \
	echo "" ; \
	if [ $$EXIT -eq 0 ]; then echo "✓ Tous les quiz sont valides"; \
	else echo "✗ Des erreurs bloquantes ont été trouvées (voir ci-dessus)"; fi ; \
	exit $$EXIT

# ── Aide ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "BobMed — Commandes disponibles"
	@echo "────────────────────────────────────────────────────────────────"
	@echo "  make validate F=Quiz_XX.html    Valide un quiz (exit 1 si erreurs)"
	@echo "  make insert   F=Quiz_XX.html    Insère le snippet dans le portail"
	@echo "  make dry-run  F=Quiz_XX.html    Prévisualise l'insertion sans écrire"
	@echo "  make publish  F=Quiz_XX.html    Pipeline complet (validate → insert)"
	@echo "  make validate-all               Valide TOUS les quiz du dépôt"
	@echo ""
	@echo "  F = chemin vers le fichier HTML (le .snippet.html est déduit auto)"
	@echo ""
