import time

import hydra
from omegaconf import DictConfig

from patchwork import patchwork


@hydra.main(config_path="configs/", config_name="config_title_stitching.yaml", version_base="1.2")
def run(config: DictConfig):
    patchwork(config)


if __name__ == "__main__":
    begin = time.time()
    run()
    end = time.time()
    print(f"Time : {end - begin} s")
