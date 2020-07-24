import pytest
from .entfunc import *

k8s_version = os.environ.get('RANCHER_K8S_VERSION', "v1.15.5-rancher1-1")
RANCHER_CLEANUP_CLUSTER = os.environ.get('RANCHER_CLEANUP_CLUSTER', "True")
NETWORK_PLUGIN = os.environ.get('NETWORK_PLUGIN', "canal")
GPU_IMAGE = os.environ.get('RANCHER_GPU_IMAGE',"jianghang8421/gpu-ml-example:tf")
MONITORING_TEMPLATE_ID = "cattle-global-data:system-library-rancher-monitoring"
CLUSTER_MONITORING_APP = "cluster-monitoring"
MONITORING_OPERATOR_APP = "monitoring-operator"
GPU_MONITORING_APP = "cluster-gpu-monitoring"
DEFAULT_GPU_IMEOUT = 60
GPU_MEM_NODE = "gpu-mem"
GPU_COUNT_NODE = "gpu-count"
GPUSHARE_PLUGIN = os.environ.get('RANCHER_GPUSHARE_PLUGIN',"gpushare-device-plugin")
NVIDIA_GPU_PLUGIN = os.environ.get('RANCHER_NVIDIA_GPU_PLUGIN',"nvidia-gpu-device-plugin")

rke_config = {
    "addonJobTimeout": 30,
    "ignoreDockerVersion": True,
    "sshAgentAuth": False,
    "type": "rancherKubernetesEngineConfig",
    "authentication": {
        "strategy": "x509",
        "type": "authnConfig"
    },
    "ingress": {
        "provider": "nginx",
        "type": "ingressConfig"
    },
    "monitoring": {
        "provider": "metrics-server",
        "type": "monitoringConfig"
    },
    "services": {
        "type": "rkeConfigServices",
        "kubeApi": {
            "alwaysPullImages": False,
            "podSecurityPolicy": False,
            "serviceNodePortRange": "30000-32767",
            "type": "kubeAPIService"
        },
        "etcd": {
            "creation": "12h",
            "extraArgs": {
                "heartbeat-interval": 500,
                "election-timeout": 5000
            },
            "retention": "72h",
            "snapshot": False,
            "type": "etcdService",
            "backupConfig": {
                "enabled": True,
                "intervalHours": 12,
                "retention": 6,
                "type": "backupConfig"
            }
        },
        "scheduler": {
            "extraArgs": {
                "policy-config-file": "/etc/gpushare/scheduler-policy-config.json"
            },
            "extraBinds": [
                "/etc/gpushare/scheduler-policy-config.json:/etc/gpushare/scheduler-policy-config.json"
            ]
        }
    }
}

docker_config = {
    "default-runtime": "nvidia",
    "runtimes": {
        "nvidia": {
            "path": "/usr/bin/nvidia-container-runtime",
            "runtimeArgs": []
        }
    }
}

share_resource_quota = {"limit": {"requestsGpuMemory": "4"}}

share_namespace_resource_quota = {"limit":{"requestsGpuMemory":"2"}}

default_resource_quota = {"limit":{"requestsGpuCount":"4"}}

default_namespace_resource_quota = {"limit":{"requestsGpuCount":"2"}}

C_MONITORING_ANSWERS = {
        "operator-init.enabled": "true",
        "exporter-node.enabled": "true",
        "exporter-gpu-node.enabled": "true",
        "exporter-node.ports.metrics.port": "9796",
        "exporter-kubelets.https": "true",
        "exporter-node.resources.limits.cpu": "200m",
        "exporter-node.resources.limits.memory": "200Mi",
        "operator.resources.limits.memory": "500Mi",
        "prometheus.retention": "12h",
        "grafana.persistence.enabled": "false",
        "prometheus.persistence.enabled": "false",
        "prometheus.persistence.storageClass": "default",
        "grafana.persistence.storageClass": "default",
        "grafana.persistence.size": "10Gi",
        "prometheus.persistence.size": "50Gi",
        "prometheus.resources.core.requests.cpu": "750m",
        "prometheus.resources.core.limits.cpu": "1000m",
        "prometheus.resources.core.requests.memory": "750Mi",
        "prometheus.resources.core.limits.memory": "1000Mi",
        "prometheus.persistent.useReleaseName": "true"
    }


@pytest.mark.skip
def test_cluster_enable_gpu():
    cluster = validate_gpu_cluster(k8s_version, plugin="canal", nodeport="32666",
                                   node_count=1, node_roles=[["etcd", "worker", "controlplane"]])
    validate_cluster_support_gpu(cluster, ADMIN_TOKEN)


def test_add_share_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type':'share'}
    result, node = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label, "gpu.cattle.io/type")
    assert result


def test_delete_share_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    nodes = client.list_node(name=GPU_MEM_NODE).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    if  "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'share':
        result, node = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label, "gpu.cattle.io/type")
        assert result

    check_delete_gpu_label(client, node, GPUSHARE_PLUGIN, "gpu.cattle.io/type")


def test_modify_share_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    add_result, node = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert add_result

    modify_result = check_modify_gpu_label(client, node, GPUSHARE_PLUGIN, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type", "default")
    assert modify_result


def test_add_default_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label, "gpu.cattle.io/type")
    assert result


def test_delete_default_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    nodes = client.list_node(name=GPU_COUNT_NODE).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    if "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'default':
        result, node = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
        assert result

    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_modify_default_gpu_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    add_result, node = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert add_result

    modify_result = check_modify_gpu_label(client, node, NVIDIA_GPU_PLUGIN,
                                           GPUSHARE_PLUGIN, "gpu.cattle.io/type", "share")
    assert modify_result


def test_gpu_mem_unused():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "1"}, "limits": {"rancher.io/gpu-mem": "1"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]


def test_gpu_mem_used2():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "3"}, "limits": {"rancher.io/gpu-mem": "3"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]


def test_gpu_mem_overrun():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "10"}, "limits": {"rancher.io/gpu-mem": "10"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    start = time.time()
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]

    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_IMEOUT:
            pods = p_client.list_pod(workloadId=workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient rancher.io/gpu-mem" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]

    projects = client.list_project(clusterId=cluster.id).data
    assert len(projects) >= 1
    for project in projects:
        if "p_gpu" in project.name:
            client.delete(project)


def test_gpu_mem_count():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, node = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "1"}, "limits": {"nvidia.com/gpu": "1"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=namespace.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    start = time.time()
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_IMEOUT:
            pods = p_client.list_pod(workloadId=workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient nvidia.com/gpu" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]
    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    check_delete_gpu_label(client, node, GPUSHARE_PLUGIN, "gpu.cattle.io/type")


def test_gpu_count_unused():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "2"}, "limits": {"nvidia.com/gpu": "2"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]


def test_gpu_count_used2():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "1"}, "limits": {"nvidia.com/gpu": "1"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=namespace.id,
                                        deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]


def test_gpu_count_overrun():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "6"}, "limits": {"nvidia.com/gpu": "6"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    start = time.time()
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]

    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_IMEOUT:
            pods = p_client.list_pod(workloadId=workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient nvidia.com/gpu" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]

    projects = client.list_project(clusterId=cluster.id).data
    assert len(projects) >= 1
    for project in projects:
        if "p_gpu" in project.name:
            client.delete(project)


def test_gpu_count_mem():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, node = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    project, namespace = create_project_and_ns(ADMIN_TOKEN, cluster, random_test_name("p_gpu"), random_test_name("gpu"))
    p_client = get_project_client_for_token(project,ADMIN_TOKEN)
    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "2"}, "limits": {"rancher.io/gpu-mem": "2"}}}]
    workload = p_client.create_workload(name=name,
                             containers=con,
                             namespaceId=namespace.id,
                             deploymentConfig={})
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    start = time.time()
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_IMEOUT:
            pods = p_client.list_pod(workloadId=workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient rancher.io/gpu-mem" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]
    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_add_gpu_mem_quota_default_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    client.delete(project)


def test_add_gpu_mem_quota_spec_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    quota = {"limit":{"requestsGpuMemory":"1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == quota["limit"]["requestsGpuMemory"]

    client.delete(project)


def test_edit_gpu_mem_quota_spec_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    quota = {"limit": {"requestsGpuMemory": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == quota["limit"]["requestsGpuMemory"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    ns1 = p_client.update(ns,
                resourceQuota={"limit": {"requestsGpuMemory": "2"}})

    assert ns1.resourceQuota.limit.requestsGpuMemory == "2"

    client.delete(project)


def test_gpu_mem_with_quota():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                 clusterId=cluster.id,
                                 resourceQuota=share_resource_quota,
                                 namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "2"}, "limits": {"rancher.io/gpu-mem": "2"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_mem_with_quota_overrun():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]


    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "4"}, "limits": {"rancher.io/gpu-mem": "4"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    time.sleep(5)
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]

    assert wl.transitioning == "error"
    assert "exceeded quota" in wl.transitioningMessage

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_add_gpu_count_quota_default_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]

    client.delete(project)


def test_add_gpu_count_quota_spec_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    quota = {"limit": {"requestsGpuCount": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == quota["limit"]["requestsGpuCount"]

    client.delete(project)


def test_edit_gpu_count_quota_spec_ns():
    client, cluster = get_admin_client_and_cluster()
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    quota = {"limit": {"requestsGpuCount": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == quota["limit"]["requestsGpuCount"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    ns1 = p_client.update(ns,
                          resourceQuota={"limit": {"requestsGpuCount": "2"}})

    assert ns1.resourceQuota.limit.requestsGpuCount == "2"

    client.delete(project)


def test_gpu_count_with_quota():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "1"}, "limits": {"nvidia.com/gpu": "1"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_count_with_quota_overrun():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]


    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "3"}, "limits": {"nvidia.com/gpu": "3"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    time.sleep(5)
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]

    assert wl.transitioning == "error"
    assert "exceeded quota" in wl.transitioningMessage

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_enable_gpu_monitor():
    client, cluster = get_admin_client_and_cluster()

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring",
                      answers=C_MONITORING_ANSWERS,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)
    wait_for_app_to_active(p_client, GPU_MONITORING_APP)


def test_add_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    result, node = check_add_gpu_label(client, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
    assert result


def test_delete_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    nodes = client.list_node(name=GPU_MEM_NODE).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    if "gpumonitoring.cattle.io" not in node_labels or node_labels['gpumonitoring.cattle.io'] != True:
        result, node = check_add_gpu_label(client, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
        assert result

    check_delete_gpu_label(client, node, "gpu-dcgm-exporter", "gpumonitoring.cattle.io")


def test_modify_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    result, node = check_add_gpu_label(client, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
    assert result

    node, node_labels = get_node_label(client, node)
    node_labels['gpumonitoring.cattle.io'] = "false"

    client.update(node, labels=node_labels)

    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workloads = p_client.list_workload(name="gpu-dcgm-exporter").data
    assert len(workloads) == 1
    workload = workloads[0]

    pods = wait_for_pod_delete(p_client, workload)
    assert len(pods) == 0

    result_node, result_labels = get_node_label(client, node)
    assert result_labels["gpumonitoring.cattle.io"] == node_labels['gpumonitoring.cattle.io']

    del result_labels['gpumonitoring.cattle.io']
    client.update(result_node, labels=result_labels)


def test_disable_monitor():
    client, cluster = get_admin_client_and_cluster()

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring",
                      answers=C_MONITORING_ANSWERS,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)
    wait_for_app_to_active(p_client, GPU_MONITORING_APP)

    cluster = client.reload(cluster)
    client.action(cluster, "disableMonitoring")
    start = time.time()
    while True:
        if time.time() - start > 30:
            raise AssertionError(
                "Timed out waiting for disabling project monitoring")
        app1 = p_client.list_app(name=CLUSTER_MONITORING_APP)
        app2 = p_client.list_app(name=MONITORING_OPERATOR_APP)
        app3 = p_client.list_app(name=GPU_MONITORING_APP)

        if len(app1.data) == 0 and len(app2.data) == 0 and len(app3.data) == 0:
            break


def test_disable_gpu_monitor():
    client, cluster = get_admin_client_and_cluster()

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring",
                      answers=C_MONITORING_ANSWERS,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)
    wait_for_app_to_active(p_client, GPU_MONITORING_APP)

    answers = C_MONITORING_ANSWERS
    answers['exporter-gpu-node.enabled'] = 'false'
    cluster = client.reload(cluster)
    client.action(cluster, "editMonitoring", answers=answers)
    start = time.time()
    while True:
        if time.time() - start > 30:
            raise AssertionError(
                "Timed out waiting for disabling project monitoring")
        app3 = p_client.list_app(name=GPU_MONITORING_APP)

        if len(app3.data) == 0:
            break


@pytest.mark.skip
def test_cluster_disable_gpu():
    client, cluster = get_admin_client_and_cluster()
    client.update(cluster, enableGPUManagement=False)

    project = cluster.list_project(name="System")
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    wait_for_wl_delete(p_client, GPUSHARE_PLUGIN)
    wait_for_wl_delete(p_client, NVIDIA_GPU_PLUGIN)
    wait_for_wl_delete(p_client, "gpushare-schd-extender")

    apps = client.list_app(name="cluster-gpu-management").data
    start = time.time()
    while len(apps) != 0:
        if time.time() - start > DEFAULT_TIMEOUT:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        apps = client.list_app(name="cluster-gpu-management").data


def test_gpu_mem_with_quota_part():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "1"}, "limits": {"rancher.io/gpu-mem": "1"}}}]

    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    wait_for_wl_to_active(p_client, workload)

    p = client.reload(project)
    ns1= c_client.reload(ns)
    p_annotations = p.annotations
    assert json.loads(p_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]
    ns_annotations = ns1.annotations
    assert json.loads(ns_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    wait_for_project_delete(client, cluster, project)


def test_gpu_mem_with_quota_all():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'share'}
    result, _ = check_add_gpu_label(client, GPU_MEM_NODE, GPUSHARE_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"rancher.io/gpu-mem": "2"}, "limits": {"rancher.io/gpu-mem": "2"}}}]

    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == con[0]["resources"]["requests"]["rancher.io/gpu-mem"]
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    wait_for_wl_to_active(p_client, workload)

    p = client.reload(project)
    ns1= c_client.reload(ns)
    p_annotations = p.annotations
    assert json.loads(p_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]
    ns_annotations = ns1.annotations
    assert json.loads(ns_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == con[0]["resources"]["limits"]["rancher.io/gpu-mem"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    wait_for_project_delete(client, cluster, project)


def test_gpu_count_with_quota_part():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "1"}, "limits": {"nvidia.com/gpu": "1"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    wait_for_wl_to_active(p_client, workload)

    p = client.reload(project)
    ns1 = c_client.reload(ns)
    p_annotations = p.annotations
    assert json.loads(p_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == \
           con[0]["resources"]["limits"]["nvidia.com/gpu"]
    ns_annotations = ns1.annotations
    assert json.loads(ns_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == \
           con[0]["resources"]["limits"]["nvidia.com/gpu"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    wait_for_project_delete(client, cluster, project)


def test_gpu_count_with_quota_all():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpu.cattle.io/type': 'default'}
    result, _ = check_add_gpu_label(client, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]

    ns = create_ns(c_client, cluster, project)

    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    name = random_test_name("gpu")
    con = [{"name": "test1",
            "image": GPU_IMAGE,
            "resources": {"requests": {"nvidia.com/gpu": "2"}, "limits": {"nvidia.com/gpu": "2"}}}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={})

    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == con[0]["resources"]["requests"]["nvidia.com/gpu"]
    assert wl_con.resources.limits['nvidia.com/gpu'] == con[0]["resources"]["limits"]["nvidia.com/gpu"]

    wait_for_wl_to_active(p_client, workload)

    p = client.reload(project)
    ns1 = c_client.reload(ns)
    p_annotations = p.annotations
    assert json.loads(p_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == \
           con[0]["resources"]["limits"]["nvidia.com/gpu"]
    ns_annotations = ns1.annotations
    assert json.loads(ns_annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == \
           con[0]["resources"]["limits"]["nvidia.com/gpu"]

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)
    wait_for_project_delete(client, cluster, project)


def validate_gpu_cluster(k8s_version, plugin="canal", nodeport="32666", node_count=1, node_roles=[["etcd", "worker", "controlplane"]]):
    rke_config["kubernetesVersion"] = k8s_version
    rke_config["network"] = {"type": "networkConfig", "plugin": plugin}

    aws_nodes = \
        AmazonWebServices().create_multiple_nodes(
            node_count, random_test_name("testcustom"))

    client = get_admin_client()
    cluster = client.create_cluster(name=random_name(),
                                    driver="rancherKubernetesEngine",
                                    enableGPUManagement=True,
                                    gpuSchedulerNodePort=nodeport,
                                    rancherKubernetesEngineConfig=rke_config)

    assert cluster.state == "active"
    i = 0
    urlPrefix = "http://127.0.0.1:" + nodeport + "/gpushare-scheduler"
    gpushare_config = {
        "kind": "Policy",
        "apiVersion": "v1",
        "extenders": [
            {
                "urlPrefix": urlPrefix,
                "filterVerb": "filter",
                "bindVerb":   "bind",
                "enableHttps": False,
                "nodeCacheCapable": True,
                "managedResources": [
                    {
                        "name": "rancher.io/gpu-mem",
                        "ignoredByScheduler": False
                    }
                ],
                "ignorable": False
            }
        ]
    }

    for aws_node in aws_nodes:
        docker_run_cmd = get_custom_host_registration_cmd(client, cluster, node_roles[i], aws_node)

        dir_gpu_cmd = "sudo mkdir -p /etc/gpushare/"
        gpudir_run_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                          + aws_node.public_ip_address + " \' " + dir_gpu_cmd + " \'"
        aws_node.execute_command(gpudir_run_cmd)

        config_gpu_cmd = "sudo echo " + gpushare_config + " > /etc/gpushare/scheduler-policy-config.json"
        gpuconfig_run_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                             + aws_node.public_ip_address + " \' " + config_gpu_cmd + " \'"
        aws_node.execute_command(gpuconfig_run_cmd)

        config_docker_cmd = "sudo echo " + docker_config + " > /etc/docker/daemon.json"
        dockerconfig_run_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                                + aws_node.public_ip_address + " \' " + config_docker_cmd + " \'"
        aws_node.execute_command(dockerconfig_run_cmd)

        restart_docker_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                                + aws_node.public_ip_address + " \' sudo service docker restart \'"
        aws_node.execute_command(restart_docker_cmd)

        cluster_run_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                  + aws_node.public_ip_address + " \' " + docker_run_cmd + " \'"
        aws_node.execute_command(cluster_run_cmd)
        i += 1

    cluster = validate_cluster(client, cluster)

    return cluster


def validate_cluster_support_gpu(cluster,token):
    project = cluster.list_project(name="System")
    p_client = get_project_client_for_token(project, token)

    validate_wl_byName(p_client, GPUSHARE_PLUGIN,"cattle-gpumanagement","DaemonSet")
    validate_wl_byName(p_client, NVIDIA_GPU_PLUGIN,"cattle-gpumanagement","DaemonSet")
    validate_wl_byName(p_client,"gpushare-schd-extender","cattle-gpumanagement","Deployment")

    #execute_kubectl_cmd()

    apps = p_client.list_app(name="cluster-gpu-management")
    assert len(apps) == 1
    app = wait_for_app_to_active(p_client, apps[0])
    assert app.state == "active"


def wait_for_app_to_active(client, app, timeout=DEFAULT_TIMEOUT):
    apps = client.list_app(name=app).data
    assert len(apps) >= 1
    application = apps[0]

    start = time.time()
    apps = client.list_app(uuid=application.uuid).data
    assert len(apps) == 1
    app1 = apps[0]
    while app1.state != "active":
        if time.time() - start > timeout:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        apps = client.list_app(uuid=application.uuid).data
        assert len(apps) == 1
        app1 = apps[0]
    return app1


def check_add_gpu_label(client, node_name, wl, label, key="gpu.cattle.io/type", deleteFlag=False):
    '''
    :param client:
    :param cluster:
    :param wl: gpushare-device-plugin / nvidia-gpu-device-plugin
    :param label
    :return:
    '''
    nodes = client.list_node(name=node_name).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    labels = dict(node_labels, **label)
    client.update(node,labels = labels)

    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project=projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workloads = p_client.list_workload(name=wl).data
    assert len(workloads) == 1
    workload = workloads[0]

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]
    pod = wait_for_pod_to_running(p_client,pod)
    assert pod.state == "running"

    result = False
    if pod.nodeId == node.id:
        result = True

    node, node_labels = get_node_label(client, node)
    assert node_labels[key] == label[key]

    if deleteFlag:
        del node_labels[key]
        client.update(node, labels=node_labels)

    return result, node


def check_delete_gpu_label(client, node, wl, key):
    node, node_labels = get_node_label(client, node)
    del node_labels[key]
    client.update(node,labels=node_labels)

    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workloads = p_client.list_workload(name=wl).data
    assert len(workloads) == 1
    workload = workloads[0]

    pods = wait_for_pod_delete(p_client,workload)
    assert len(pods) == 0

    _, node_labels = get_node_label(client, node)
    assert key not in node_labels.keys()


def check_modify_gpu_label(client, node, old_wl, new_wl, key, value):
    node, node_labels = get_node_label(client, node)
    node_labels[key] = value
    client.update(node, labels = node_labels)

    projects = client.list_project(name="System").data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    old_workloads = p_client.list_workload(name=old_wl).data
    assert len(old_workloads) == 1
    old_workload = old_workloads[0]
    old_pods = wait_for_pod_delete(p_client, old_workload)
    assert len(old_pods) == 0

    new_workloads = p_client.list_workload(name=new_wl).data
    assert len(new_workloads) == 1
    new_workload = new_workloads[0]
    new_pods = p_client.list_pod(workloadId=new_workload.id).data
    assert len(new_pods) == 1
    new_pod = new_pods[0]
    wait_for_pod_to_running(p_client,new_pod)

    result = False
    if new_pod.nodeId == node.id:
        result = True

    node, node_labels = get_node_label(client, node)
    assert node_labels['gpu.cattle.io/type'] == value

    check_delete_gpu_label(client, node, new_wl, key)

    return result


def get_node_label(client, node):
    nodes = client.list_node(id=node.id).data
    assert len(nodes) == 1
    node = nodes[0]
    labels = node.labels.__dict__
    return node, labels


def validate_gpu_resoucequota_kubectl(namespace, quota_type):
    '''
    :param namespace:
    :param quota_type: requestsGpuMemory / requestsGpuCount
    :return:
    '''
    command = "get quota --namespace " + namespace['id']

    result = execute_kubectl_cmd(command, json_out=True)
    testdict = namespace['resourceQuota']

    response = result["items"]
    assert "spec" in response[0]
    quotadict = (response[0]["spec"])
    assert quotadict['hard'][quota_type] == testdict['limit'][quota_type]


def wait_for_monitor_app_to_active(client, app,
                           timeout=DEFAULT_MULTI_CLUSTER_APP_TIMEOUT):
    """
    First wait for app to come in deployment state, then wait for it get
    in active state. This is to avoid wrongly conclude that app is active
    as app goes to state installing > active > deploying > active
    @param client: Project client
    @param app_id: App id of deployed app.
    @param timeout: Max time allowed to wait for app to become active.
    @return: app object
    """
    apps = client.list_app(name=app).data
    assert len(apps) >= 1
    application = apps[0]
    app_id = application.id
    start = time.time()
    app_data = client.list_app(id=app_id).data
    while len(app_data) == 0:
        if time.time() - start > timeout / 10:
            raise AssertionError(
                "Timed out waiting for listing the app from API")
        time.sleep(.2)
        app_data = client.list_app(id=app_id).data

    application = app_data[0]
    while application.state != "deploying":
        if time.time() - start > timeout / 3:
            break
        time.sleep(.2)
        app_data = client.list_app(id=app_id).data
        application = app_data[0]
    while application.state != "active":
        if time.time() - start > timeout:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        app = client.list_app(id=app_id).data
        assert len(app) >= 1
        application = app[0]
    return application
