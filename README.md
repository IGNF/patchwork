# patchwork
Patchwork est un outil permettant d'enrichir un fichier lidar à haute densité avec des points d'un fichier à basse densité dans les secteurs où le premier fichier n'a pas de point mais où le second en possède.

## Fonctionnement
Les données en entrée sont:  
- un fichier lidar que l'ont souhaite enrichir  
- un fichier lidar contenant des points supplémentaires  
  
En sortie il y a :  
- Un fichier, copie du premier en entrée, enrichi des points voulu  
  
Les deux fichiers d'entrée sont découpés en tuiles carrées, généralement d'1m². Si une tuile du fichier à enrichir ne contient aucun point ayant le classement qui nous intéresse, on prend les points de la tuile de même emplacement du fichier de points supplémentaire.

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

