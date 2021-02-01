import pytest
from .entfunc import *


GPU_IMAGE = os.environ.get('RANCHER_GPU_IMAGE',"jianghang8421/gpu-ml-example:tf")
GPU_MEM_NODE = os.environ.get('RANCHER_GPU_MEM_NODE', "gpu-mem")
GPU_COUNT_NODE = os.environ.get('RANCHER_GPU_COUNT_NODE', "gpu-count")

RANCHER_GPUSHARE_SCHEDULER_NAME = os.environ.get('RANCHER_GPUSHARE_SCHEDULER_NAME','rancher-gpushare-scheduler')
GPUSHARE_DEVICE_PLUGIN = os.environ.get('RANCHER_GPUSHARE_PLUGIN',"gpushare-device-plugin")
NVIDIA_GPU_PLUGIN = os.environ.get('RANCHER_NVIDIA_GPU_PLUGIN',"nvidia-gpu-device-plugin")
GPUSHARE_SCHD_PLUGIN = os.environ.get('RANCHER_GPUSHARE_SCHD_PLUGIN',"gpushare-schd-extender")
DISABLE_GPU_CLUSTER = os.environ.get('RANCHER_DISABLE_GPU_CLUSTER', True)
K3S_CLUSTER = os.environ.get('RANCHER_K3S_CLUSTER', False)
MONITORING_TEMPLATE_ID = "cattle-global-data:system-library-rancher-monitoring"
GPU_CATALOG = "cluster-gpu-management"
CLUSTER_MONITORING_APP = "cluster-monitoring"
MONITORING_OPERATOR_APP = "monitoring-operator"
extraAnswers = {'exporter-gpu-node.enabled': 'true'}
gpu_share_lable = {'gpu.cattle.io/type':'share'}
gpu_default_label = {'gpu.cattle.io/type':'default'}
namespace = {"client": None, "p_client": None, "ns": None, "cluster": None, "project": None, "system": None, "sys_project":None}

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

DEFAULT_GPU_TIMEOUT = 60

if_without_rancher = pytest.mark.skipif(not DISABLE_GPU_CLUSTER, reason='not DISABLE GPU CLUSTER')
if_k8s_cluster =  pytest.mark.skipif(K3S_CLUSTER, reason='k8s test case')
if_k3s_cluster = pytest.mark.skipif(not K3S_CLUSTER, reason='k3s test case')


@if_k8s_cluster
def test_cluster_enable_gpu():
    p_client = namespace["system"]
    client = namespace['client']
    cluster = namespace['cluster']
    client.update(cluster, name=cluster.name, enableGPUManagement=True)

    time.sleep(3)
    gpu_plugin = p_client.list_workload(name=GPUSHARE_DEVICE_PLUGIN).data
    assert len(gpu_plugin) == 1
    gpu_wl = wait_for_wl_to_active(p_client, gpu_plugin[0])
    assert gpu_wl.state == "active"

    nvidia_plugin = p_client.list_workload(name=NVIDIA_GPU_PLUGIN).data
    assert len(nvidia_plugin) == 1
    nvidia_wl = wait_for_wl_to_active(p_client, nvidia_plugin[0])
    assert nvidia_wl.state == "active"

    schd_plugin = p_client.list_workload(name=GPUSHARE_SCHD_PLUGIN).data
    assert len(schd_plugin) == 1
    schd_wl = wait_for_wl_to_active(p_client, schd_plugin[0])
    assert schd_wl.state == "active"

    app = wait_for_app_to_active(p_client, GPU_CATALOG)
    assert app.state == "active"
    assert 'schedulerextender.schedulerName' in app.answers.keys()
    assert app.answers['schedulerextender.schedulerName'] == RANCHER_GPUSHARE_SCHEDULER_NAME

    configmaps = p_client.list_configMap(name='gpushare-scheduler-config', namespaceId='cattle-gpumanagement').data
    assert len(configmaps) == 1
    configmap = configmaps[0]
    config = yaml.load(configmap.data['config.yaml'])
    assert config['schedulerName'] == RANCHER_GPUSHARE_SCHEDULER_NAME


@if_k3s_cluster
def test_k3s_enable_gpu():
    system = namespace['system']
    cluster = namespace['cluster']
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    system_project = namespace['sys_project']
    ns = c_client.create_namespace(name=random_test_name('cattle-gpu-management'),
                                   projectId=system_project.id)
    answers = {"defaultImage": True, "image.defaultScheduler.version": "v1.18", "memoryunit": "GiB"}
    externalId = "catalog://?catalog=pandaria&template=rancher-gpu-management&version=0.0.3"

    system.create_app(answers=answers, externalId=externalId, name="rancher-gpu-management", projectId=system_project.id,
                      targetNamespace=ns.name)

    time.sleep(3)
    gpu_plugin = system.list_workload(name=GPUSHARE_DEVICE_PLUGIN).data
    assert len(gpu_plugin) == 1
    gpu_wl = wait_for_wl_to_active(system, gpu_plugin[0])
    assert gpu_wl.state == "active"

    nvidia_plugin = system.list_workload(name=NVIDIA_GPU_PLUGIN).data
    assert len(nvidia_plugin) == 1
    nvidia_wl = wait_for_wl_to_active(system, nvidia_plugin[0])
    assert nvidia_wl.state == "active"

    schd_plugin = system.list_workload(name=GPUSHARE_SCHD_PLUGIN).data
    assert len(schd_plugin) == 1
    schd_wl = wait_for_wl_to_active(system, schd_plugin[0])
    assert schd_wl.state == "active"

    app = wait_for_app_to_active(system, 'rancher-gpu-management')
    assert app.state == "active"

    configmaps = system.list_configMap(name='gpushare-scheduler-config',namespaceId=ns.name).data
    assert len(configmaps) == 1
    configmap = configmaps[0]
    config = yaml.load(configmap.data['config.yaml'])
    assert config['schedulerName'] == RANCHER_GPUSHARE_SCHEDULER_NAME


def test_add_share_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result


def test_delete_share_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    node, node_labels = get_node_label_byName(client, cluster, GPU_MEM_NODE)
    if  "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'share':
        result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
        assert result

    check_delete_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, 'gpu.cattle.io/type')


def test_modify_share_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    node, node_labels = get_node_label_byName(client, cluster, GPU_MEM_NODE)
    if "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'share':
        result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
        assert result

    modify_result = check_modify_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type", "default")
    assert modify_result

    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_add_default_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result


def test_delete_default_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    node, node_labels = get_node_label_byName(client, cluster, GPU_COUNT_NODE)
    if "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'default':
        result, node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
        assert result

    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_modify_default_gpu_label():
    client = namespace["client"]
    cluster = namespace["cluster"]
    node, node_labels = get_node_label_byName(client, cluster, GPU_COUNT_NODE)
    if "gpu.cattle.io/type" not in node_labels or node_labels['gpu.cattle.io/type'] != 'default':
        result, node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
        assert result

    modify_result = check_modify_gpu_label(client, node, NVIDIA_GPU_PLUGIN,
                                           GPUSHARE_DEVICE_PLUGIN, "gpu.cattle.io/type", "share")
    assert modify_result

    check_delete_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, "gpu.cattle.io/type")


def test_modify_gpu_label_other():
    client = namespace["client"]
    cluster = namespace["cluster"]
    add_result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert add_result

    modify_result = check_modify_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type", "other")
    assert modify_result

    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_gpu_mem_scheduler():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result
    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    assert workload.scheduling['scheduler'] == RANCHER_GPUSHARE_SCHEDULER_NAME

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_count_scheduler():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result
    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    assert workload.scheduling['scheduler'] == 'default-scheduler'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_mem_unused():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]

    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '1'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_mem_used2():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '3', '3')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '3'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '3'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_mem_overrun():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '10', '10')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '10'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '10'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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


def test_gpu_mem_count():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '1'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '1'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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
    check_delete_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, "gpu.cattle.io/type")


def test_modify_node_count_gpu_count():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    old_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"
    old_cons = old_workload.containers
    assert len(old_cons) == 1
    old_con = old_cons[0]
    assert old_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert old_con.resources.limits['rancher.io/gpu-mem'] == '1'

    modify_result = check_modify_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, NVIDIA_GPU_PLUGIN,
                                           "gpu.cattle.io/type", "default")
    assert modify_result

    new_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    new_workload = wait_for_wl_to_active(p_client, new_workload)
    assert new_workload.state == "active"
    new_cons = new_workload.containers
    assert len(new_cons) == 1
    new_con = new_cons[0]
    assert new_con.resources.requests['nvidia.com/gpu'] == '1'
    assert new_con.resources.limits['nvidia.com/gpu'] == '1'

    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"

    p_client.delete(old_workload)
    wait_for_wl_delete(p_client, old_workload)
    p_client.delete(new_workload)
    wait_for_wl_delete(p_client, new_workload)
    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_modify_node_count_gpu_mem():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    old_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"
    old_cons = old_workload.containers
    assert len(old_cons) == 1
    old_con = old_cons[0]
    assert old_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert old_con.resources.limits['rancher.io/gpu-mem'] == '1'

    modify_result = check_modify_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, NVIDIA_GPU_PLUGIN,
                                           "gpu.cattle.io/type", "default")
    assert modify_result

    new_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '2', '2')
    new_cons = new_workload.containers
    assert len(new_cons) == 1
    new_con = new_cons[0]
    assert new_con.resources.requests['rancher.io/gpu-mem'] == '2'
    assert new_con.resources.limits['rancher.io/gpu-mem'] == '2'
    start = time.time()
    wl = new_workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
            pods = p_client.list_pod(workloadId=new_workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient rancher.io/gpu-mem" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=new_workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]

    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"

    p_client.delete(old_workload)
    wait_for_wl_delete(p_client, old_workload)
    p_client.delete(new_workload)
    wait_for_wl_delete(p_client, new_workload)
    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_gpu_count_unused():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '2', '2')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '2'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '2'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_count_used2():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '1'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '1'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)


def test_gpu_count_overrun():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '6', '6')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '6'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '6'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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


def test_gpu_count_mem():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '2', '2')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '2'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '2'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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
    check_delete_gpu_label(client, node, NVIDIA_GPU_PLUGIN, "gpu.cattle.io/type")


def test_modify_node_mem_gpu_mem():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    old_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"
    old_cons = old_workload.containers
    assert len(old_cons) == 1
    old_con = old_cons[0]
    assert old_con.resources.requests['nvidia.com/gpu'] == '1'
    assert old_con.resources.limits['nvidia.com/gpu'] == '1'

    modify_result = check_modify_gpu_label(client, node, NVIDIA_GPU_PLUGIN, GPUSHARE_DEVICE_PLUGIN,
                                           "gpu.cattle.io/type", "share")
    assert modify_result

    new_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '2', '2')
    new_workload = wait_for_wl_to_active(p_client, new_workload)
    assert new_workload.state == "active"
    new_cons = new_workload.containers
    assert len(new_cons) == 1
    new_con = new_cons[0]
    assert new_con.resources.requests['rancher.io/gpu-mem'] == '2'
    assert new_con.resources.limits['rancher.io/gpu-mem'] == '2'

    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"

    p_client.delete(old_workload)
    wait_for_wl_delete(p_client, old_workload)
    p_client.delete(new_workload)
    wait_for_wl_delete(p_client, new_workload)
    check_delete_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, "gpu.cattle.io/type")


def test_modify_node_mem_gpu_count():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    result, node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    old_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"
    old_cons = old_workload.containers
    assert len(old_cons) == 1
    old_con = old_cons[0]
    assert old_con.resources.requests['nvidia.com/gpu'] == '1'
    assert old_con.resources.limits['nvidia.com/gpu'] == '1'

    modify_result = check_modify_gpu_label(client, node, NVIDIA_GPU_PLUGIN, GPUSHARE_DEVICE_PLUGIN,
                                           "gpu.cattle.io/type", "share")
    assert modify_result

    new_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '2', '2')
    new_cons = new_workload.containers
    assert len(new_cons) == 1
    new_con = new_cons[0]
    assert new_con.resources.requests['nvidia.com/gpu'] == '2'
    assert new_con.resources.limits['nvidia.com/gpu'] == '2'
    start = time.time()
    wl = new_workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
            pods = p_client.list_pod(workloadId=new_workload.id).data
            assert len(pods) == 1
            pod = pods[0]
            assert pod.transitioning == "error"
            assert "Insufficient nvidia.com/gpu" in pod.transitioningMessage
            break
        time.sleep(.5)
        workloads = p_client.list_workload(uuid=new_workload.uuid).data
        assert len(workloads) == 1
        wl = workloads[0]

    old_workload = wait_for_wl_to_active(p_client, old_workload)
    assert old_workload.state == "active"

    p_client.delete(old_workload)
    wait_for_wl_delete(p_client, old_workload)
    p_client.delete(new_workload)
    wait_for_wl_delete(p_client, new_workload)
    check_delete_gpu_label(client, node, GPUSHARE_DEVICE_PLUGIN, "gpu.cattle.io/type")


def test_both_mem_count():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    mem_result, mem_node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert mem_result
    count_result, count_node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert count_result

    count_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '2', '2')
    count_workload = wait_for_wl_to_active(p_client, count_workload)
    assert count_workload.state == "active"
    count_cons = count_workload.containers
    assert len(count_cons) == 1
    count_con = count_cons[0]
    assert count_con.resources.requests['nvidia.com/gpu'] == '2'
    assert count_con.resources.limits['nvidia.com/gpu'] == '2'

    count_result = False
    count_pods = p_client.list_pod(workloadId=count_workload.id).data
    for count_pod in count_pods:
        count_pod = wait_for_pod_to_running(p_client, count_pod, DEFAULT_GPU_TIMEOUT)
        assert count_pod.state == "running"
        if count_pod.nodeId == count_node.id:
            count_result = True
            break
    assert count_result

    mem_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    mem_workload = wait_for_wl_to_active(p_client, mem_workload)
    assert mem_workload.state == "active"
    mem_cons = mem_workload.containers
    assert len(mem_cons) == 1
    mem_con = mem_cons[0]
    assert mem_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert mem_con.resources.limits['rancher.io/gpu-mem'] == '1'

    mem_result = False
    mem_pods = p_client.list_pod(workloadId=mem_workload.id).data
    for mem_pod in mem_pods:
        mem_pod = wait_for_pod_to_running(p_client, mem_pod, DEFAULT_GPU_TIMEOUT)
        assert mem_pod.state == "running"
        if mem_pod.nodeId == mem_node.id:
            mem_result = True
            break
    assert mem_result

    p_client.delete(count_workload)
    wait_for_wl_delete(p_client, count_workload)
    p_client.delete(mem_workload)
    wait_for_wl_delete(p_client, mem_workload)


def test_both_mem_count_overrun():
    client = namespace["client"]
    cluster = namespace["cluster"]
    ns = namespace["ns"]
    p_client = namespace["p_client"]
    mem_result, mem_node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert mem_result
    count_result, count_node = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN,
                                                   gpu_default_label)
    assert count_result

    count_workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '10', '10')
    count_cons = count_workload.containers
    assert len(count_cons) == 1
    count_con = count_cons[0]
    assert count_con.resources.requests['nvidia.com/gpu'] == '10'
    assert count_con.resources.limits['nvidia.com/gpu'] == '10'

    start = time.time()
    count_wl = count_workload
    while count_wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
            count_pods = p_client.list_pod(workloadId=count_workload.id).data
            assert len(count_pods) == 1
            count_pod = count_pods[0]
            assert count_pod.transitioning == "error"
            assert "Insufficient nvidia.com/gpu" in count_pod.transitioningMessage
            break
        time.sleep(.5)
        count_workloads = p_client.list_workload(uuid=count_workload.uuid).data
        assert len(count_workloads) == 1
        count_wl = count_workloads[0]

    mem_workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    mem_cons = mem_workload.containers
    assert len(mem_cons) == 1
    mem_con = mem_cons[0]
    assert mem_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert mem_con.resources.limits['rancher.io/gpu-mem'] == '1'

    start = time.time()
    mem_wl = mem_workload
    while mem_wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
            mem_pods = p_client.list_pod(workloadId=mem_workload.id).data
            assert len(mem_pods) == 1
            mem_pod = mem_pods[0]
            assert mem_pod.transitioning == "error"
            assert "Insufficient nvidia.com/gpu" in mem_pod.transitioningMessage
            break
        time.sleep(.5)
        mem_workloads = p_client.list_workload(uuid=mem_workload.uuid).data
        assert len(mem_workloads) == 1
        mem_wl = mem_workloads[0]

    p_client.delete(count_workload)
    wait_for_wl_delete(p_client, count_workload)
    p_client.delete(mem_workload)
    wait_for_wl_delete(p_client, mem_workload)


def test_add_gpu_mem_quota_default_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    ns = c_client.wait_success(ns)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]
    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == share_namespace_resource_quota["limit"]["requestsGpuMemory"]

    client.delete(project)


def test_add_gpu_mem_quota_spec_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    quota = {"limit": {"requestsGpuMemory": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuMemory == share_resource_quota["limit"]["requestsGpuMemory"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuMemory == \
           share_namespace_resource_quota["limit"]["requestsGpuMemory"]
    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuMemory == quota["limit"]["requestsGpuMemory"]

    client.delete(project)


def test_edit_gpu_mem_quota_spec_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    quota = {"limit": {"requestsGpuMemory": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    ns1 = p_client.update(ns,
                resourceQuota={"limit": {"requestsGpuMemory": "2"}})
    assert ns1.resourceQuota.limit.requestsGpuMemory == "2"

    client.delete(project)


def test_delete_gpu_mem_quota():
    resourceQuota = {"limit": {"requestsCpu": "1200m", "requestsGpuMemory": "20"}}
    namespaceDefaultResourceQuota = {"limit": {"requestsCpu": "200m", "requestsGpuMemory": "10"}}
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_count'),
                                    clusterId=cluster.id,
                                    resourceQuota=resourceQuota,
                                    namespaceDefaultResourceQuota=namespaceDefaultResourceQuota)
    project = client.wait_success(project)
    quota = {"limit": {"requestsCpu": "300m", "requestsGpuMemory": "5"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)
    assert ns.resourceQuota['limit']['requestsCpu'] == '300m'
    assert ns.resourceQuota['limit']['requestsGpuMemory'] == '5'

    resourceQuota = {"limit": {"requestsCpu": "1000m", "requestsGpuMemory": None}}
    namespaceDefaultResourceQuota = {"limit": {"requestsCpu": "400m", "requestsGpuMemory": None}}
    client.update(project,resourceQuota=resourceQuota, namespaceDefaultResourceQuota=namespaceDefaultResourceQuota)
    project = client.reload(project)
    assert 'requestsGpuMemory' not in project.resourceQuota['limit']
    ns = c_client.reload(ns)
    assert 'requestsGpuMemory' not in ns.resourceQuota['limit']

    client.delete(project)


def test_gpu_mem_with_quota_overrun():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '4', '4')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '4'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '4'

    time.sleep(3)
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]
    assert wl.transitioning == "error"
    assert "exceeded quota" in wl.transitioningMessage

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_mem_with_quota_part():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '1'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '1'

    time.sleep(1)
    p = client.reload(project)
    ns1= c_client.reload(ns)
    assert json.loads(p.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == '1'
    assert json.loads(ns1.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == '1'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_mem_with_quota_all():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_quota'),
                                    clusterId=cluster.id,
                                    resourceQuota=share_resource_quota,
                                    namespaceDefaultResourceQuota=share_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '2', '2')
    workload = wait_for_wl_to_active(p_client, workload)
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '2'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '2'

    time.sleep(1)
    p = client.reload(project)
    ns1= c_client.reload(ns)
    assert json.loads(p.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == '2'
    assert json.loads(ns1.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuMemory"] == '2'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_mem_quota_overrun_gpu():
    client = namespace["client"]
    cluster = namespace["cluster"]
    result, _ = check_add_gpu_label(client, cluster, GPU_MEM_NODE, GPUSHARE_DEVICE_PLUGIN, gpu_share_lable)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota={"limit": {"requestsGpuMemory": "30"}},
                                    namespaceDefaultResourceQuota={"limit": {"requestsGpuMemory": "15"}})
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'rancher.io/gpu-mem', '10', '10')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['rancher.io/gpu-mem'] == '10'
    assert wl_con.resources.limits['rancher.io/gpu-mem'] == '10'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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


def test_add_gpu_count_quota_default_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]
    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == default_namespace_resource_quota["limit"]["requestsGpuCount"]

    client.delete(project)


def test_add_gpu_count_quota_spec_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    quota = {"limit": {"requestsGpuCount": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)

    assert project.resourceQuota is not None
    assert project.resourceQuota.limit.requestsGpuCount == default_resource_quota["limit"]["requestsGpuCount"]
    assert project.namespaceDefaultResourceQuota is not None
    assert project.namespaceDefaultResourceQuota.limit.requestsGpuCount == \
           default_namespace_resource_quota["limit"]["requestsGpuCount"]
    assert ns is not None
    assert ns.resourceQuota is not None
    assert ns.resourceQuota.limit.requestsGpuCount == quota["limit"]["requestsGpuCount"]

    client.delete(project)


def test_edit_gpu_count_quota_spec_ns():
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    quota = {"limit": {"requestsGpuCount": "1"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-mem'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)
    ns1 = p_client.update(ns,
                          resourceQuota={"limit": {"requestsGpuCount": "2"}})
    assert ns1.resourceQuota.limit.requestsGpuCount == "2"

    client.delete(project)


def test_delete_gpu_count_quota():
    resourceQuota = {"limit": {"requestsCpu": "1200m", "requestsGpuCount": "200"}}
    namespaceDefaultResourceQuota = {"limit": {"requestsCpu": "200m", "requestsGpuCount": "60"}}
    client = namespace["client"]
    cluster = namespace["cluster"]
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name=random_test_name('gpu_count'),
                                    clusterId=cluster.id,
                                    resourceQuota=resourceQuota,
                                    namespaceDefaultResourceQuota=namespaceDefaultResourceQuota)
    project = client.wait_success(project)
    quota = {"limit": {"requestsCpu": "300m", "requestsGpuCount": "50"}}
    ns = c_client.create_namespace(name=random_test_name('gpu-count'),
                                   projectId=project.id,
                                   resourceQuota=quota)
    ns = c_client.wait_success(ns)
    assert ns.resourceQuota['limit']['requestsCpu'] == '300m'
    assert ns.resourceQuota['limit']['requestsGpuCount'] == '50'

    resourceQuota = {"limit": {"requestsCpu": "1000m", "requestsGpuCount": None}}
    namespaceDefaultResourceQuota = {"limit": {"requestsCpu": "400m", "requestsGpuCount": None}}
    client.update(project,resourceQuota=resourceQuota, namespaceDefaultResourceQuota=namespaceDefaultResourceQuota)
    project = client.reload(project)
    assert 'requestsGpuCount' not in project.resourceQuota['limit']
    ns = c_client.reload(ns)
    assert 'requestsGpuCount' not in ns.resourceQuota['limit']

    client.delete(project)


def test_gpu_count_with_quota_overrun():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '3', '3')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '3'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '3'

    time.sleep(3)
    workloads = p_client.list_workload(uuid=workload.uuid).data
    assert len(workloads) == 1
    wl = workloads[0]
    assert wl.transitioning == "error"
    assert "exceeded quota" in wl.transitioningMessage

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_count_with_quota_part():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '1', '1')
    workload = wait_for_wl_to_active(p_client, workload)
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '1'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '1'

    time.sleep(1)
    p = client.reload(project)
    ns1 = c_client.reload(ns)
    assert json.loads(p.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == '1'
    assert json.loads(ns1.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == '1'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_count_with_quota_all():
    client = namespace["client"]
    cluster = namespace["cluster"]

    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota=default_resource_quota,
                                    namespaceDefaultResourceQuota=default_namespace_resource_quota)
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '2', '2')
    workload = wait_for_wl_to_active(p_client, workload)
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '2'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '2'

    time.sleep(1)
    p = client.reload(project)
    ns1 = c_client.reload(ns)
    assert json.loads(p.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == '2'
    assert json.loads(ns1.annotations["field.cattle.io/resourceQuotaUsage"])["requestsGpuCount"] == '2'

    p_client.delete(workload)
    wait_for_wl_delete(p_client, workload)
    client.delete(project)


def test_gpu_count_quota_overrun_gpu():
    client = namespace["client"]
    cluster = namespace["cluster"]
    result, _ = check_add_gpu_label(client, cluster, GPU_COUNT_NODE, NVIDIA_GPU_PLUGIN, gpu_default_label)
    assert result

    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    project = client.create_project(name='test-' + random_str(),
                                    clusterId=cluster.id,
                                    resourceQuota={"limit": {"requestsGpuCount": "30"}},
                                    namespaceDefaultResourceQuota={"limit": {"requestsGpuCount": "15"}})
    project = client.wait_success(project)
    ns = create_ns(c_client, cluster, project)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workload = create_gpu_workload(p_client, ns, 'nvidia.com/gpu', '10', '10')
    wl_cons = workload.containers
    assert len(wl_cons) == 1
    wl_con = wl_cons[0]
    assert wl_con.resources.requests['nvidia.com/gpu'] == '10'
    assert wl_con.resources.limits['nvidia.com/gpu'] == '10'

    start = time.time()
    wl = workload
    while wl.state != "active":
        if time.time() - start > DEFAULT_GPU_TIMEOUT:
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


def test_enable_gpu_monitor():
    client, cluster = get_admin_client_and_cluster()

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring",
                      answers=C_MONITORING_ANSWERS,
                      extraAnswers=extraAnswers,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)

    workloads = p_client.list_workload(name="gpu-dcgm-exporter").data
    assert len(workloads) == 1
    gpu_monitor_wl = workloads[0]
    assert gpu_monitor_wl.workloadLabels['io.cattle.field/appId'] == CLUSTER_MONITORING_APP


def test_add_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
    assert result


def test_delete_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    nodes = client.list_node(name=GPU_MEM_NODE).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    if "gpumonitoring.cattle.io" not in node_labels or node_labels['gpumonitoring.cattle.io'] != True:
        result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
        assert result

    check_delete_gpu_label(client, node, "gpu-dcgm-exporter", "gpumonitoring.cattle.io")


def test_modify_gpu_monitor_label():
    client, cluster = get_admin_client_and_cluster()
    label = {'gpumonitoring.cattle.io': 'true'}
    result, node = check_add_gpu_label(client, cluster, GPU_MEM_NODE, "gpu-dcgm-exporter", label, "gpumonitoring.cattle.io")
    assert result

    node, node_labels = get_node_label_byId(client, node)
    node_labels['gpumonitoring.cattle.io'] = "false"

    client.update(node, labels=node_labels)

    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    workloads = p_client.list_workload(name="gpu-dcgm-exporter").data
    assert len(workloads) == 1
    workload = workloads[0]

    pods = wait_for_pod_delete(p_client, workload)
    assert len(pods) == 0

    result_node, result_labels = get_node_label_byId(client, node)
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
                      extraAnswers=extraAnswers,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)

    cluster = client.reload(cluster)
    client.action(cluster, "disableMonitoring")
    start = time.time()
    while True:
        if time.time() - start > 30:
            raise AssertionError(
                "Timed out waiting for disabling project monitoring")
        app1 = p_client.list_app(name=CLUSTER_MONITORING_APP)
        app2 = p_client.list_app(name=MONITORING_OPERATOR_APP)

        if len(app1.data) == 0 and len(app2.data) == 0:
            break


def test_disable_gpu_monitor():
    client, cluster = get_admin_client_and_cluster()

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring",
                      answers=C_MONITORING_ANSWERS,
                      extraAnswers=extraAnswers,
                      version=MONITORING_VERSION)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    wait_for_monitor_app_to_active(p_client, MONITORING_OPERATOR_APP)
    wait_for_monitor_app_to_active(p_client, CLUSTER_MONITORING_APP)

    answers = C_MONITORING_ANSWERS
    answers['exporter-gpu-node.enabled'] = 'false'
    fextraAnswers = {'exporter-gpu-node.enabled': 'false'}
    cluster = client.reload(cluster)
    client.action(cluster, "editMonitoring", answers=answers,extraAnswers=fextraAnswers)
    workloads = wait_for_wl_delete(p_client, 'gpu-dcgm-exporter')
    assert len(workloads) == 0


@if_without_rancher
@if_k8s_cluster
def test_cluster_disable_gpu():
    client = namespace['client']
    cluster = namespace['cluster']
    system = namespace['system']
    client.update(cluster, name=cluster.name, enableGPUManagement=False)

    wait_for_wl_delete(system, GPUSHARE_DEVICE_PLUGIN)
    wait_for_wl_delete(system, NVIDIA_GPU_PLUGIN)
    wait_for_wl_delete(system, GPUSHARE_SCHD_PLUGIN)

    apps = system.list_app(name=GPU_CATALOG).data
    start = time.time()
    while len(apps) != 0:
        if time.time() - start > DEFAULT_TIMEOUT:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        apps = system.list_app(name=GPU_CATALOG).data


@if_without_rancher
@if_k3s_cluster
def test_k3s_disable_gpu():
    system = namespace['system']
    system_project = namespace['sys_project']

    apps = system.list_app(projectId=system_project.id, name='rancher-gpu-management').data
    assert len(apps) == 1
    app = apps[0]
    system.delete(app)

    wait_for_wl_delete(system, GPUSHARE_DEVICE_PLUGIN)
    wait_for_wl_delete(system, NVIDIA_GPU_PLUGIN)
    wait_for_wl_delete(system, GPUSHARE_SCHD_PLUGIN)

    apps = system.list_app(name='rancher-gpu-management').data
    start = time.time()
    while len(apps) != 0:
        if time.time() - start > DEFAULT_TIMEOUT:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        apps = system.list_app(name='rancher-gpu-management').data


@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    client, cluster = get_admin_client_and_cluster()
    create_kubeconfig(cluster)
    p, ns = create_project_and_ns(
        ADMIN_TOKEN, cluster, random_test_name("test-gpu"))
    p_client = get_project_client_for_token(p, ADMIN_TOKEN)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    sys_client = get_project_client_for_token(project, ADMIN_TOKEN)

    namespace["client"] = client
    namespace["p_client"] = p_client
    namespace["ns"] = ns
    namespace["cluster"] = cluster
    namespace["project"] = p
    namespace["system"] = sys_client
    namespace["sys_project"] = project

    def fin():
        client = namespace["client"]
        client.delete(namespace["project"])
    request.addfinalizer(fin)


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


def check_add_gpu_label(client, cluster, node_name, wl, label, key="gpu.cattle.io/type", deleteFlag=False):
    '''
    :param client:
    :param cluster:
    :param wl: gpushare-device-plugin / nvidia-gpu-device-plugin
    :param label
    :return:
    '''
    p_client = namespace["system"]
    result = False

    node, node_labels = get_node_label_byName(client, cluster, node_name)
    labels = dict(node_labels, **label)
    client.update(node,labels = labels)

    workloads = p_client.list_workload(name=wl).data
    assert len(workloads) == 1
    workload = workloads[0]
    pods = p_client.list_pod(workloadId=workload.id).data
    for pod in pods:
        pod = wait_for_pod_to_running(p_client, pod, DEFAULT_GPU_TIMEOUT)
        assert pod.state == "running"
        if pod.nodeId == node.id:
            result = True
            break

    node, node_labels = get_node_label_byId(client, node)
    assert node_labels[key] == label[key]

    if deleteFlag:
        del node_labels[key]
        client.update(node, labels=node_labels)

    return result, node


def check_delete_gpu_label(client, node, wl, key):
    p_client = namespace["system"]

    node, node_labels = get_node_label_byId(client, node)
    del node_labels[key]
    client.update(node,labels=node_labels)

    workloads = p_client.list_workload(name=wl).data
    assert len(workloads) == 1
    workload = workloads[0]
    pods = wait_for_podOfNode_delete(p_client, workload, node)
    assert len(pods) == 0

    _, node_labels = get_node_label_byId(client, node)
    assert key not in node_labels.keys()


def check_modify_gpu_label(client, node, old_wl, new_wl, key, value):
    p_client = namespace["system"]
    result = False

    node, node_labels = get_node_label_byId(client, node)
    node_labels[key] = value
    client.update(node, labels = node_labels)

    old_workloads = p_client.list_workload(name=old_wl).data
    assert len(old_workloads) == 1
    old_workload = old_workloads[0]
    old_pods = wait_for_podOfNode_delete(p_client, old_workload, node)
    assert len(old_pods) == 0

    new_workloads = p_client.list_workload(name=new_wl).data
    assert len(new_workloads) == 1
    new_workload = new_workloads[0]
    new_pods = p_client.list_pod(workloadId=new_workload.id).data
    if value in ("share", "default"):
        for new_pod in new_pods:
            wait_for_pod_to_running(p_client,new_pod)
            if new_pod.nodeId == node.id:
                result = True
                break
    else:
        for new_pod in new_pods:
            assert new_pod.nodeId != node.id
        result = True

    node, node_labels = get_node_label_byId(client, node)
    assert node_labels['gpu.cattle.io/type'] == value

    return result


def get_node_label_byName(client, cluster, node_name):
    nodes = client.list_node(name=node_name, clusterId=cluster.id).data
    assert len(nodes) > 0
    node = nodes[0]
    node_labels = node.labels.__dict__
    return node, node_labels


def get_node_label_byId(client, node):
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


def create_gpu_workload(p_client, ns, gpu_key, requests, limits):
    name = random_test_name("gpu")
    con = [{"name": name,
            "image": GPU_IMAGE,
            "resources": {"requests": {gpu_key: requests}, "limits": {gpu_key: limits}}}]
    if gpu_key == "rancher.io/gpu-mem":
        scheduling = {"node": {}, "scheduler": RANCHER_GPUSHARE_SCHEDULER_NAME}
        workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        deploymentConfig={},
                                        scheduling=scheduling)
        return workload
    else:
        workload = p_client.create_workload(name=name,
                                            containers=con,
                                            namespaceId=ns.id,
                                            deploymentConfig={})
        return workload


def wait_for_podOfNode_delete(client, workload, node, timeout=DEFAULT_GPU_TIMEOUT):
    pods = client.list_pod(workloadId=workload.id, nodeId=node.id).data
    start = time.time()
    while len(pods) != 0:
        if time.time() - start > timeout:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        pods = client.list_pod(workloadId=workload.id, nodeId=node.id).data
    return pods