# CHANGELOG

- **Changement de comportement** :
    Le champ "DONOR_CLASS_TRANSLATION" décrit maintenant l'association entre les classes du fichier donneur et les classes correspondantes dans le fichier de sortie. Au lieu de choisir entre ajouter une colonne et modifier les classes entre le fichier de donneur et le fichier de sortie, on applique maintenant les 2 traitements :
        - Si "NEW_COLUMN" est non nul, on ajoute une dimension décrivant l'origine du fichier
        - Les classes des points issus du fichier donneur sont converties via le dictionnaire "DONOR_CLASS_TRANSLATION" au moment de l'ajout des points au fichier de sortie.

## 1.3.0
- Possibilité d'ignorer les points synthétiques du fichier donneur (paramètre DONOR_USE_SYNTHETIC_POINTS dans le fichier de config)

## 1.2.1
- Ajout de gdal dans l'image docker (fichiers manquant pour l'utiliser en ligne de commande)

## 1.2.0
- mise à jour de laspy pour le correctif de la fonction `append_points`
- Possibilité d'utiliser des points de montage pour rediriger les chemins donnés dans le shapefile vers un autre dossier
- [Breaking change] Utilisation d'un shapefile pour définir les fichiers donneurs à utiliser pour chaque zone
- génération de la carte d'indice même quand il n'y a pas de points à ajouter

## 1.1.1
- lint
- ajout de pre-commit hooks pour appliquer le lint au moment des commits
- patchwork crée lui-même les sous-dossiers dont chaque étape a besoin
- correctif pour la recherche de correspondance des las dans le csv de matching

## 1.1.0
- modification de chemin pour pouvoir passer dans la gpao
- coupure des chemins de fichiers en chemins de répertoires/nom de fichiers pour pouvoir les utiliser sur docker + store
- patchwork vérifie maintenant s'il y a un ficheir csv en entrée. Si c'est le cas, le fichier donneur utilisé est celui qui correspond au fichier receveur dans le fichier csv. S'il n'y a pas de fichier donneur correspondant, patchwork termine sans rien faire

## 1.0.0
version initiale :
- découpe et sélection des fichiers lidar
- ajout de points d'un fichier lidar donneur vers un fichier receveur
- ajout de l'intégration continue