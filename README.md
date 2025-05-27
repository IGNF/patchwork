# patchwork
Patchwork est un outil permettant d'enrichir un fichier lidar à haute densité avec des points d'un fichier à basse densité dans les secteurs où le premier fichier n'a pas de point mais où le second en possède.

## Fonctionnement
Les données en entrée sont:
- un fichier lidar que l'ont souhaite enrichir
- un fichier lidar contenant des points supplémentaires

En sortie il y a :
- Un fichier, copie du premier en entrée, enrichi des points voulus

Les deux fichiers d'entrée sont découpés en tuiles carrées, généralement d'1m². Si une tuile du fichier à enrichir ne contient aucun point ayant le classement qui nous intéresse, on prend les points de la tuile de même emplacement du fichier de points supplémentaire.

L'appartenance à une tuile est décidée par un arrondi par défaut, c'est-à-dire que tous les éléments de [n, n+1[ (ouvert en n+1) font parti de la même tuile.

## Installation
pré-requis: installer anaconda
Cloner le dépôt
```
git clone https://github.com/IGNF/patchwork.git
```

```
conda env create -f environment.yml
conda activate patchwork
```
## utilisation

Le script d'ajout de points peut être lancé via :
```
python main.py filepath.DONOR_FILE=[chemin fichier donneur] filepath.RECIPIENT_FILE=[chemin fichier receveur] filepath.OUTPUT_FILE=[chemin fichier de sortie] [autres options]
```
Les différentes options, modifiables soit dans le fichier `configs/configs_patchwork.yaml`, soit en ligne de commande comme indiqué juste au-dessus :

filepath.DONOR_DIRECTORY : Le répertoire du fichier qui peut donner des points à ajouter
filepath.DONOR_NAME : Le nom du fichier qui peut donner des points à ajouter
filepath.RECIPIENT_DIRECTORY : Le répertoire du fichier qui va obtenir des points en plus
filepath.RECIPIENT_NAME : Le nom du fichier qui va obtenir des points en plus
filepath.OUTPUT_DIR : Le répertoire du fichier en sortie
filepath.OUTPUT_NAME : Le nom du fichier en sortie
filepath.OUTPUT_INDICES_MAP_DIR : Le répertoire de sortie du fichier d'indice
filepath.OUTPUT_INDICES_MAP_NAME : Le nom de sortie du fichier d'indice

DONOR_CLASS_LIST : Défaut [2, 22]. La liste des classes des points du fichier donneur qui peuvent être ajoutés.
RECIPIENT_CLASS_LIST : Défaut [2, 3, 9, 17]. La liste des classes des points du fichier receveur qui, s'ils sont absents dans une cellule, justifirons de prendre les points du fichier donneur de la même cellule
TILE_SIZE : Défaut 1000. Taille du côté de l'emprise carrée représentée par les fichiers lidar d'entrée
PATCH_SIZE : Défaut 1. taille en mètre du côté d'une cellule (doit être un diviseur de TILE_SIZE, soit pour 1000 : 0.25, 0.5, 2, 4, 5, 10, 25...)
