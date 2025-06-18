FROM mambaorg/micromamba:latest AS mamba_pdal
COPY environment.yml /environment.yml
# Using USER root seems to fix permission issues when building mamba environment with pip packages
USER root

RUN apt update
RUN apt install -y git

RUN micromamba env create -n patchwork -f /environment.yml

# Start from raw debian image to lower the final image size
FROM debian:bullseye-slim

# install PDAL + mamba environment
COPY --from=mamba_pdal /opt/conda/envs/patchwork/bin/pdal /opt/conda/envs/patchwork/bin/pdal
COPY --from=mamba_pdal /opt/conda/envs/patchwork/bin/python /opt/conda/envs/patchwork/bin/python
COPY --from=mamba_pdal /opt/conda/envs/patchwork/lib/ /opt/conda/envs/patchwork/lib/
COPY --from=mamba_pdal /opt/conda/envs/patchwork/ssl /opt/conda/envs/patchwork/ssl
COPY --from=mamba_pdal /opt/conda/envs/patchwork/share/proj/proj.db /opt/conda/envs/patchwork/share/proj/proj.db

ENV PATH=$PATH:/opt/conda/envs/patchwork/bin/
ENV PROJ_LIB=/opt/conda/envs/patchwork/share/proj/

WORKDIR /patchwork
COPY . /patchwork

