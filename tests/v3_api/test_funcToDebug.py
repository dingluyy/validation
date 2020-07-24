import pytest
from .entfunc import *
from netaddr import *

CATTLE_TEST_URL = "https://35.229.215.12:8443/"
RANCHER_API_URL = 'https://35.229.215.12:8443/v3'
token = os.environ.get(ADMIN_TOKEN, "token-5pnx8:kc5df4wp5nq74v5f6phbvbjq4w5b7p5x9bswtnmrthshxtf2mlwmgg")
headers = {"cookie": "R_SESS=" + token}

list = []
def test_funcToDebug_macvlan_ipv6():
    client, cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('ipv6')
    cidr = '172.20.16.0/24'
    gateway = '172.20.16.1'
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway)
    cmd = 'apply -f ' + yaml
    subnet = execute_kubectl_cmd(cmd, False, True)
    print(subnet)
    os.remove(yaml)

    annotations = get_workload_macvlan('172.20.16.16', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, "busybox:musl", annotations)

    time.sleep(2)
    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]
    pod = wait_for_pod_to_running(p_client, pod)
    print(pod)
    annotations = pod['annotations']['k8s.v1.cni.cncf.io/networks-status']
    print(annotations)
    annotations.replace("\n", "")
    annotations = json.loads(annotations)
    ips = []
    for annotation in annotations:
        print("annotation for", annotation)
        a = annotation["name"]
        print(a)
        if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
            ips = annotation["ips"]
    print(ips)
    ipv6 = v4_to_v6(ips[0])
    print('ips[1]', ips[1])
    assert ipv6 == ips[1]
    client.delete(project)


def test_funcToDebug_base():
    client, cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    projects = client.list_project(name="test-29550", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, token)

    haha = p_client.list_secret()
    print(haha.data)


def test_funcToDebug_assert():
    client, cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, token)

    workloads = p_client.list_workload(name='nginx-ingress-controller').data
    workload = workloads[0]
    print(workload)


def test_funcToDebug_gpu_quota():
    client, cluster = get_admin_client_and_cluster_byUrlToken('https://18.217.60.191:8445/v3', 'token-5qq6x:hbb7nhcgpbcndfn22w2lw6dh5wq5qk8b2vx8fs74n87k9vsfgdxqpc')
    projects = client.list_project(name="test-random-875357-1599030874", clusterId=cluster.id).data
    assert len(projects) == 1

    project = projects[0]

    p = client.reload(project)
    p_annotations = p.annotations
    print(p.annotations)

def test_funcToDebug_wl_redeploy():
    list_url = 'https://34.122.194.246:8445'+'/k8s/clusters/c-dder/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets?limit=50&labelSelector=project%20in%20(%2C)'
    print(list_url)


def test_sort_time():
    result = []
    for artifact in list:
        tags = artifact['tags']
        for tag in tags:
            name = tag['name']
            time = tag['push_time']
            result.append(name)
    print(sorted(result))
