#!/usr/bin/env python3
"""Contrat containers intra-repo (story 9.4.3b — gate Murat 4, ARCH-R6).

Pour chaque rôle sous roles/ :
- extrait les préfixes réels des `--name {prefix}-{{ capsule_id }}` de tasks/main.yml ;
- les compare à `container_prefixes` déclaré dans meta/homegalaxy.yml.

Toute divergence (préfixe réel non déclaré OU préfixe déclaré fantôme) fait
échouer la CI : le contrat ne peut pas drifter DANS le repo. Le drift
cross-repo (mapping backend ↔ meta du clone épinglé) est attrapé côté box
au bump de SHA — cf. README.
"""

import pathlib
import re
import sys

import yaml

ROLES_DIR = pathlib.Path(__file__).resolve().parents[2] / "roles"
NAME_RE = re.compile(r"--name\s+([a-z0-9]+)-\{\{\s*capsule_id\s*\}\}")


def main() -> int:
    """Vérifie chaque rôle ; retourne 0 si le contrat est cohérent, 1 sinon."""
    errors: list[str] = []
    roles = sorted(p for p in ROLES_DIR.iterdir() if p.is_dir())
    if not roles:
        print("❌ Aucun rôle sous roles/ — arborescence corrompue ?")
        return 1

    for role in roles:
        tasks_path = role / "tasks" / "main.yml"
        meta_path = role / "meta" / "homegalaxy.yml"

        if not tasks_path.exists():
            errors.append(f"{role.name}: tasks/main.yml manquant")
            continue

        found = set(NAME_RE.findall(tasks_path.read_text(encoding="utf-8")))
        if not found:
            errors.append(
                f"{role.name}: aucun `--name {{prefix}}-{{{{ capsule_id }}}}` "
                "trouvé dans tasks/main.yml"
            )
            continue

        if not meta_path.exists():
            errors.append(f"{role.name}: meta/homegalaxy.yml manquant (contrat ARCH-R6)")
            continue

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        declared = set(meta.get("container_prefixes") or [])
        if found != declared:
            errors.append(
                f"{role.name}: --name réels {sorted(found)} ≠ "
                f"meta déclarés {sorted(declared)}"
            )
        else:
            print(f"✅ {role.name}: {sorted(found)}")

    if errors:
        print("\n".join(f"❌ {e}" for e in errors))
        return 1
    print(f"Contrat containers cohérent sur {len(roles)} rôles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
