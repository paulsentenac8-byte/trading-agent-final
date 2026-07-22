# Trading Agent — Zip complet v2 (Alpaca + interface adaptée)

## ✅ Ce zip est maintenant complet

`interface_debutant.py` est inclus en entier et a été adapté pour utiliser
Alpaca à la place d'IBKR. Tu n'as plus aucun fichier à ajouter toi-même.

---

## Ce qui a changé par rapport à ton repo actuel

### Nouveaux fichiers
- `src/alpaca_broker.py` — connecteur Alpaca, fonctionne depuis Render
  (contrairement à IBKR qui exige un logiciel local TWS allumé sur ton PC)
- `src/storage.py` — base SQLite pour l'historique des analyses et
  l'apprentissage (utilisé par l'onglet "Historique & learning" de
  l'interface)
- `submit_alpaca_orders.py` — script qui envoie les ordres validés à Alpaca
- `dashboard_pro.py` — interface premium sombre alternative, avec graphiques
  (courbe d'équité, répartition des positions). Optionnelle, en complément
  de `interface_debutant.py`.

### Fichiers modifiés
- **`interface_debutant.py`** — les boutons "Aperçu broker" et "Envoyer au
  broker démo" appellent maintenant `submit_alpaca_orders.py` au lieu de
  `submit_ibkr_orders.py`. Rien d'autre n'a changé dans cette interface.
- **`main.py`** — ajout d'un appel à `store_pipeline_run()` à la fin du
  pipeline, pour que l'historique et l'apprentissage se remplissent
  automatiquement à chaque analyse.
- `config.json`, `config.example.json` — `broker.mode` passe à `"alpaca"`
- `src/config.py` — ajout des champs de configuration Alpaca
- `src/risk.py`, `src/pretrade.py`, `src/signals.py` — alignés sur les
  versions montrées (utilisant `scalars.py` pour plus de robustesse)
- `doctor.py`, `start.py` — bug corrigé (référençaient un fichier
  `lancer_assistant.py` qui n'a jamais existé)
- `requirements.txt` — retire `ib-insync`, ajoute `plotly`

### Fichiers inchangés
`README.md`, `render.yaml`, `app_state.json`, `DEPLOY_WEB_PUBLIC.md`,
`GITHUB_RENDER_CLIC_PAR_CLIC.md`, `submit_ibkr_orders.py` (gardé pour
référence), `.streamlit/config.toml`, et tous les autres fichiers de `src/`.

---

## Étapes pour déployer

### 1. Crée ton compte Alpaca (gratuit)
Sur https://alpaca.markets, section **Paper Trading** → génère une clé API
(API Key ID + Secret Key).

### 2. Remplace tout sur ton repo GitHub
Supprime tous les fichiers de ton repo GitHub actuel, puis upload
l'intégralité du contenu de ce zip (en respectant les dossiers `src/` et
`.streamlit/`).

### 3. Ajoute tes clés dans Render (jamais sur GitHub)
Render → ton service → **Environment** :
- `ALPACA_API_KEY` → ton API Key ID
- `ALPACA_API_SECRET` → ton Secret Key

### 4. Vérifie le déploiement
Ouvre l'URL de ton app Render. Tu devrais voir ton interface habituelle.

### 5. Premier test, sans risque
1. Lance une analyse
2. Approuve les ordres voulus dans l'onglet de validation
3. "Aperçu broker" (dry-run, ne contacte pas Alpaca)
4. "Envoyer au broker démo" (envoie réellement, mais au compte paper —
   argent fictif, zéro risque tant que paper_only=true)

### 6. (Optionnel) Dashboard premium
Render → Settings → Start Command :
```
streamlit run dashboard_pro.py --server.port $PORT --server.address 0.0.0.0
```

---

## Garde-fous toujours actifs
- `paper_only: true` par défaut
- Kill switch, stress tests, meta-risk overlay : inchangés
- Aucune clé API écrite dans un fichier versionné
