import json
import os
import requests

import hydra
from omegaconf import DictConfig
from gpao.builder import Builder, Project
from gpao_utils.store import Store
from gpao.job import Job

from patchwork import patchwork
from version import __version__

docker_run = "docker run --userns=host --rm "

TAGS = ["docker"]
LOCAL = "/home/MDaab/code/patchwork"


def build_url_api(hostname: str):
    return f"http://{hostname}:8080/api/"


def send_project(url_api: str, filename: str):
    """send a gpao project"""
    headers = {
        "Content-type": "application/json",
    }
    with open(filename, "rb") as data:
        response = requests.put(url_api + "project", headers=headers, data=data)
    return response


@hydra.main(config_path="configs/", config_name="configs_patchwork.yaml", version_base="1.2")
def run_gpao(config: DictConfig):
    # patchwork(config)
    _project_json = LOCAL
    url_gpao = config.gpao.URL_GPAO
    job_lidar_selecter = [lidar_selecter_job(config)]
    projet_list = [Project("lidar selecter", job_lidar_selecter)]

    builder = Builder(projet_list)
    builder.save_as_json(_project_json)

    url_api = url_gpao
    if not url_api.lower().startswith("http"):
        url_api = build_url_api(url_gpao)
    response = send_project(url_api, _project_json)

    if response.status_code != 200:
        print("erreur de requête : ", response.status_code)
    assert response.status_code == 200
    print("Projet GPAO mis en base (" + url_api + ")")


def lidar_selecter_job(config: DictConfig):
    store_lidarhd = Store(config.gpao.LOCAL_STORE, config.gpao.WIN_STORE, config.gpao.UNIX_STORE)
    job_name = "Sélection/découpe des fichiers lidar"
    donor_dir = config.filepath.DONOR_DIRECTORY
    recipient_dir = config.filepath.RECIPIENT_DIRECTORY

    shp_name = config.filepath.SHP_NAME
    shp_dir = config.filepath.SHP_DIRECTORY
    csv_name = config.filepath.CSV_NAME
    csv_dir = config.filepath.CSV_DIRECTORY

    version_patchwork = __version__

    command = f"{docker_run} " + \
    f"-v {store_lidarhd.to_unix(donor_dir)}:/donor_dir " + \
    f"-v {store_lidarhd.to_unix(recipient_dir)}:/recipient_dir " + \
    f"-v {store_lidarhd.to_unix(shp_dir)}:/shp_dir " + \
    f"-v {store_lidarhd.to_unix(csv_dir)}:/csv_dir " + \
    f"patchwork:v{version_patchwork} " + \
    "python lidar_selecter.py " + \
    "filepath.DONOR_DIRECTORY=/donor_dir " + \
    "filepath.RECIPIENT_DIRECTORY=/recipient_dir " + \
    "filepath.SHP_DIRECTORY=/shp_dir " + \
    f"filepath.SHP_NAME={shp_name} " + \
    "filepath.CSV_DIRECTORY=/csv_dir " + \
    f"filepath.CSV_NAME={csv_name} " + \
    "filepath.OUTPUT_DIRECTORY=/output_dir "

    Job(job_name, command, tags=TAGS)


if __name__ == "__main__":
    run_gpao()