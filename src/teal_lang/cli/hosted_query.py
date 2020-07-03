"""GraphQL interface to Teal Cloud"""

import logging
import os
from types import SimpleNamespace

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .. import config
from . import interface as ui

LOG = logging.getLogger(__name__)

CLIENT = None


def _init(endpoint: str):
    global CLIENT

    if not endpoint:
        raise ValueError(endpoint)

    try:
        HASURA_SECRET = os.environ["HASURA_ADMIN_SECRET"]
    except KeyError:
        ui.exit_fail("HASURA_ADMIN_SECRET is not set")

    transport = RequestsHTTPTransport(
        url=endpoint,
        # TODO - change to x-hasura-access-key
        headers={"x-hasura-admin-secret": HASURA_SECRET},
        verify=True,  # The SSL cert
        retries=3,
    )
    CLIENT = Client(transport=transport, fetch_schema_from_transport=True,)
    LOG.info("Connected to Teal Cloud: %s", endpoint)


def _query(s: str, **kwargs) -> dict:
    if not CLIENT:
        cfg = config.get_last_loaded()
        _init(cfg.endpoint)
    LOG.info("Query args: %s", kwargs)
    return CLIENT.execute(gql(s), variable_values=kwargs)


## Pythonic queries:


def new_package(
    instance_id: int, python_hash: str, teal_hash: str, config_hash: str
) -> SimpleNamespace:
    qry = """
mutation NewPackage($id: Int!, $ch: String!, $ph: String!, $th: String!) {
  new_package(instance_id: $id, config_hash: $ch, python_hash: $ph, teal_hash: $th) {
    package {
      id
      new_python
      new_config
      new_teal
      python_url
      teal_url
      config_url
    }
  }
}
"""
    data = _query(qry, id=instance_id, ph=python_hash, th=teal_hash, ch=config_hash)
    return SimpleNamespace(**data["new_package"]["package"])


def get_instance(project_id: int, instance_name: str) -> SimpleNamespace:
    qry = """
query GetInstance($name: String!, $pid: Int!) {
  instance(limit: 1, where: {project_id: {_eq: $pid}, name: {_eq: $name}}) {
    id
    ready
  }
}
"""
    data = _query(qry, pid=project_id, name=instance_name)
    return SimpleNamespace(**data["instance"][0])


def new_deployment(instance_id: int, package_id: int) -> SimpleNamespace:
    qry = """
mutation NewDeployment($package_id: Int!, $iid: Int!) {
  insert_deployment_one(object: {package_id: $package_id, instance_id: $iid}) {
    id
  }
}
"""
    data = _query(qry, package_id=package_id, iid=instance_id)
    return SimpleNamespace(**data["insert_deployment_one"])


def switch(instance_id: int, new_deployment_id: int) -> SimpleNamespace:
    qry = """
mutation DeployIt($iid: Int!, $did: Int!) {
  switch_deployment(instance_id: $iid, new_deployment_id: $did) {
    ok
  }
}
    """
    data = _query(qry, did=new_deployment_id, iid=instance_id)
    return SimpleNamespace(**data["switch_deployment"])


def destroy(instance_id: int) -> SimpleNamespace:
    qry = """
mutation DeployIt($id: Int!) {
  switch_deployment(instance_id: $id) {
    ok
  }
}
    """
    data = _query(qry, id=instance_id)
    return SimpleNamespace(**data["switch_deployment"])


def status(deployment_id: int) -> SimpleNamespace:
    qry = """
query DeploymentStatus($id: Int!) {
  deployment_by_pk(id: $id) {
    active
    started_deploy
    deployed_at
    started_at
  }
}
    """
    data = _query(qry, id=deployment_id)
    return SimpleNamespace(**data["deployment_by_pk"])


def list_projects() -> list:
    qry = """
query ListProjects {
  project {
    id
    name
  }
}
    """
    data = _query(qry)
    return [SimpleNamespace(**p) for p in data["project"]]


def is_instance_ready(instance_id: int) -> bool:
    qry = """
query IsInstanceReady($id: Int!) {
  instance_by_pk(id: $id) {
    ready
  }
}
    """
    data = _query(qry, id=instance_id)
    return data["instance_by_pk"]["ready"]
