# homegalaxy-ansible

Rôles Ansible **marketplace** de la HomeBox (HomeGalaxy). Ce repo est la source
de vérité des recettes d'installation des apps vitrine ; chaque box le consomme
via un **clone local épinglé sur un SHA** déclaré par le catalogue Core
(`GET /api/v1/roles-repo`) — jamais une branche, jamais un tag, jamais `@main`.

## Structure

```
roles/
  adguard/          → containers : adguard
  home-assistant/   → containers : homeassistant
  jellyfin/         → containers : jellyfin
  minecraft/        → containers : minecraft    (slug catalogue : minecraft-server)
  nextcloud/        → containers : nextcloud
  ollama-stack/     → containers : ollama, openwebui  (slug catalogue : ollama-webui)
```

⚠️ Pour deux rôles, le nom de dossier ≠ slug catalogue (héritage conservé
volontairement) : la traduction slug→dossier vit dans le champ `local_path`
du catalogue Core, **jamais ici**.

Chaque rôle = `tasks/main.yml` (docker run + route Traefik) +
`templates/*.j2` + `meta/homegalaxy.yml` (contrat ci-dessous).

## Contrat containers cross-repo (ARCH-R6)

Chaque rôle déclare dans `meta/homegalaxy.yml` les préfixes des containers
qu'il démarre :

```yaml
container_prefixes:
  - adguard
```

- Les valeurs sont les préfixes **réels** des `--name {prefix}-{{ capsule_id }}`
  du rôle (`ollama-stack` en déclare deux : `ollama` et `openwebui`).
- **Vérifié intra-repo** par la CI (`.github/scripts/check_container_contract.py`) :
  un `--name` non déclaré ou un préfixe fantôme fait échouer le build.
- **Vérifié côté box** par le test d'intégrité backend : le mapping
  `ROLE_CONTAINER_PREFIXES` est comparé aux meta du clone épinglé, ET un grep
  `--name` indépendant tourne contre le clone (le meta peut mentir, le grep
  ne ment pas — les deux doivent passer).

## Consommation par la box

- La box maintient un clone dans `/ansible-marketplace`, convergé vers le SHA
  épinglé : `git fetch` → `git cat-file -e {sha}^{commit}` →
  `git checkout --detach {sha}`. Un SHA inconnu ou un réseau coupé laissent
  le clone **exactement dans son état précédent**.
- L'installation d'une app est 100 % locale sur le clone — le réseau n'est
  **jamais** dans le chemin critique d'une install. Clone absent ou incomplet →
  fallback automatique sur les rôles bundlés de la box.
- Le SHA épinglé vit **uniquement** dans le catalogue Core
  (`marketplace_roles_repo = {url, sha}`) — nulle part côté box, ni .env,
  ni constante.
- Deux box synchronisées sur le même SHA installent exactement la même recette.

## Procédure de bump SHA

1. Merger les changements de rôles ici (CI verte obligatoire).
2. Relever le SHA complet (40 hex) du commit cible.
3. **AVANT** de merger le bump côté catalogue : synchroniser un clone local sur
   ce SHA et faire tourner les tests d'intégrité backend contre lui
   (mapping ↔ meta + grep `--name`). Le drift cross-repo s'attrape au bump,
   jamais en prod.
4. Mettre à jour `marketplace_roles_repo.sha` dans le catalogue apphg (Core).

## Limite assumée MVP

Le contrat cross-repo n'est **jamais** vérifié par la CI du monorepo box : sur
son runner, ni `/ansible` ni `/ansible-marketplace` n'existent — le test
d'intégrité étendu y double-skip. Les deux seules vérifications automatisées
sont la CI de CE repo et les tests container au bump de SHA (procédure
ci-dessus, manuelle). L'automatisation cross-CI est un chantier post-MVP.

## Règle absolue : zéro secret

Les rôles ne portent **aucun** secret ni credential. Toute donnée d'instance
passe en **extravars** (`capsule_id`, `racine_slug`, ports alloués,
`ollama_model`, …). C'est ce qui permet à ce repo d'être public.
