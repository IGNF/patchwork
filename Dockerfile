FROM mambaorg/micromamba:latest
COPY environment.yml /environment.yml
# Using USER root seems to fix permission issues when building mamba environment with pip packages
USER root
RUN micromamba env create -n patchwork -f /environment.yml

WORKDIR /patchwork
COPY . /patchwork

ENV PATH=$PATH:/opt/conda/envs/patchwork/bin/
ENV PROJ_LIB=/opt/conda/envs/patchwork/share/proj/
