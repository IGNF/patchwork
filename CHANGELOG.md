# CHANGELOG

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