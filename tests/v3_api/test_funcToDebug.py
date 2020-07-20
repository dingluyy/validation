import pytest
from .entfunc import *

CATTLE_TEST_URL = "https://35.188.66.242:8443/"
RANCHER_API_URL = CATTLE_TEST_URL + '/v3'
token = os.environ.get(ADMIN_TOKEN, "token-7gvkp:6ncnbk468d7r7427jsqhmkgdx2zvsmn245grwwp8lblbkgqt9tbm4r")

def test_funcToDebug_validate_wl():
    client, cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)

    workload = create_job_wl(p_client, ns, "nginx")
    print(workload)
    validate_workload(p_client, workload, 'job', ns.name)
