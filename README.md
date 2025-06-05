# patchwork
Patchwork est un outil permettant d'enrichir un fichier lidar à haute densité avec des points d'un ou plusieurs fichiers à basse densité dans les secteurs où le premier fichier n'a pas de point mais où le second en possède.

## Fonctionnement
Les données en entrée sont:
- un fichier lidar que l'ont souhaite enrichir
- un fichier shapefile, décrivant les fichiers qui serviront à enrichir le fichier lidar et les zones d'application potentielles (détails dans [Définition du fichier shapefile](#définition-du-fichier-shapefile))

En sortie il y a :
- Un fichier, copie du premier en entrée, enrichi des points des fichiers basse densité dans les zones identifiées.

Les deux fichiers d'entrée sont découpés en mailles carrées, part défaut d'1m². Si une tuile du fichier à enrichir ne contient aucun point ayant le classement qui nous intéresse, on prend les points de la tuile de même emplacement du fichier de points supplémentaire.

L'appartenance à une tuile est décidée par un arrondi par défaut, c'est-à-dire que tous les éléments de [n, n+1[ (ouvert en n+1) font partie de la même tuile.

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
## Utilisation

Le script d'ajout de points peut être lancé via :
```bash
python main.py \
    filepath.RECIPIENT_DIRECTORY=[dossier parent du fichier receveur] \
    filepath.RECIPIENT_NAME=[nom du fichier receveur] \
    filepath.SHP_DIRECTORY=[dossier parent du shapefile] \
    filepath.SHP_NAME=[nom du fichier shapefile] \
    filepath.OUTPUT_DIR=[dossier de sortie] \
    filepath.OUTPUT_NAME=[nom du fichier de sortie] \
    [autres options]
```
Les différentes options sont modifiables soit dans le fichier `configs/configs_patchwork.yaml`, soit en ligne de commande comme indiqué juste au-dessus.
Voir le fichier [config_patchwork.yaml](configs/configs_patchwork.yaml) pour le détail des options


## Définition du fichier shapefile

TODO