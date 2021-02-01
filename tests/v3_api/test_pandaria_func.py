from .entfunc import *
import pytest

namespace = {"client": None, "cluster": None, "c_client": None, "project": None, "p_client": None, "ns": None, "system": None, "sys_project":None}
headers = {"cookie": "R_SESS=" + ADMIN_TOKEN}

'''
    check duplicate project name
'''
def test_add_duplicate_project_name():
    cluster = namespace["cluster"]
    project = namespace["project"]
    url = cluster["links"]["projects"]
    r = requests.post(url, json={
        "enableProjectMonitoring":False,
        "type":"project",
        "name":project.name,
        "clusterId":cluster.id,
        "labels":{}}, verify=False,headers=headers)
    assert r.status_code == 409
    assert r.json()["message"] == "duplicate project name"


def test_edit_duplicate_project_name():
    client = namespace["client"]
    cluster = namespace["cluster"]
    project = namespace["project"]

    p = create_project(client, cluster, random_test_name("test-edit-project"))
    url = p["links"]["update"]

    r = requests.put(url, json={
        "enableProjectMonitoring":False,
        "type":"project",
        "name":project.name,
        "clusterId":cluster.id,
        "labels":{}}, verify=False,headers=headers)
    assert r.status_code == 409
    assert r.json()["message"] == "duplicate project name"


@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    client, cluster = get_admin_client_and_cluster()
    create_kubeconfig(cluster)
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)

    p, ns = create_project_and_ns(
        ADMIN_TOKEN, cluster, random_test_name("test-pandaria"))
    p_client = get_project_client_for_token(p, ADMIN_TOKEN)

    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    sys_client = get_project_client_for_token(project, ADMIN_TOKEN)

    namespace["client"] = client
    namespace["cluster"] = cluster
    namespace["c_client"] = c_client

    namespace["project"] = p
    namespace["p_client"] = p_client

    namespace["system"] = sys_client
    namespace["sys_project"] = project

    def fin():
        client = namespace["client"]
        client.delete(namespace["project"])
    request.addfinalizer(fin)