from .entfunc import *
import pytest

namespace = {"client": None, "p_client": None, "ns": None, "cluster": None, "project": None, "system": None, "sys_project":None, "c_client": None, "clusteralertgroup": None, "projectalertgroup": None}
MONITORING_TEMPLATE_ID = "cattle-global-data:system-library-rancher-monitoring"


def test_node_disk_reads_completed_total():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 3000,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum by (device, instance, node) (irate(node_disk_reads_completed_total[5m]))",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_reads_completed_total",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_disk_read_bytes_total():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 50,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum by (device, instance, node) (irate(node_disk_read_bytes_total[5m])) / 1024 / 1024",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_read_bytes_total",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_disk_read_time_rate():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 100,
        "type": "metricRule",
        "duration": "10s",
        "expression": "rate(node_disk_read_time_seconds_total[5m]) / rate(node_disk_reads_completed_total[5m])",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_read_time_rate",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_disk_avail_bytes():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "greater-than",
        "thresholdValue": 15,
        "type": "metricRule",
        "duration": "10s",
        "expression": "node_filesystem_avail_bytes/node_filesystem_size_bytes * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_avail_bytes",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_disk_writes_completed_total():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 3000,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum by (device, instance, node) (irate(node_disk_writes_completed_total[5m]))",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_writes_completed_total",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_disk_written_bytes_total():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 50,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum by (device, instance, node) (irate(node_disk_written_bytes_total[5m])) / 1024 / 1024",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_disk_written_bytes_total",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_load_machine_cpu_cores():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "greater-than",
        "thresholdValue": 20,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum(node_load1) by (node)  / sum(machine_cpu_cores) by (node) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_load_machine_cpu_cores",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_filesystem_free_bytes():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "has-value",
        "type": "metricRule",
        "duration": "10s",
        "expression": "predict_linear(node_filesystem_free_bytes{mountpoint!~\"^/etc/(?:resolv.conf|hosts|hostname)$\"}[6h], 3600 * 24) < 0",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_filesystem_free_bytes",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_memory_available_rate():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 80,
        "type": "metricRule",
        "duration": "10s",
        "expression": "(1 - sum(node_memory_MemAvailable_bytes) by (instance) / sum(node_memory_MemTotal_bytes) by (instance)) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_memory_available_rate",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_etcd_debugging_mvcc_db_total_size():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 524288000,
        "type": "metricRule",
        "duration": "10s",
        "expression": "sum(etcd_debugging_mvcc_db_total_size_in_bytes)",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="etcd_debugging_mvcc_db_total_size",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_process_fds_rate():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 85,
        "type": "metricRule",
        "duration": "10s",
        "expression": "(process_open_fds / process_max_fds) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="process_fds_rate",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_etcd_server_leader_changes_seen_total():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 3,
        "type": "metricRule",
        "duration": "10s",
        "expression": "increase(etcd_server_leader_changes_seen_total[1h])",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="etcd_server_leader_changes_seen_total",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_etcd_debugging_snap_save_total_duration():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "has-value",
        "type": "metricRule",
        "duration": "10s",
        "expression": "histogram_quantile(0.99, sum(rate(etcd_debugging_snap_save_total_duration_seconds_bucket[5m])) by (instance, le))",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="etcd_debugging_snap_save_total_duration",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_etcd_disk_backend_commit_duration():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 1,
        "type": "metricRule",
        "duration": "10s",
        "expression": "histogram_quantile(0.99, sum(rate(etcd_disk_backend_commit_duration_seconds_bucket[5m])) by (instance, le))",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="etcd_disk_backend_commit_duration",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_etcd_disk_wal_fsync_duration():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 1,
        "type": "metricRule",
        "duration": "10s",
        "expression": "histogram_quantile(0.99, sum(rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])) by (instance, le))",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="etcd_disk_wal_fsync_duration",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_node_filesystem_files_use_rate():
    client = namespace["client"]
    cluster = namespace["cluster"]
    clusteralertgroup = namespace["clusteralertgroup"]
    metricRule={
        "comparison": "less-than",
        "thresholdValue": 85,
        "type": "metricRule",
        "duration": "10s",
        "expression": "(1 - node_filesystem_files_free/node_filesystem_files) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }

    clusterAlertRule = client.create_clusterAlertRule(name="node_filesystem_files_use_rate",
                                   clusterId=cluster.id, groupId=clusteralertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_project_memory():
    client = namespace["client"]
    project = namespace["project"]
    projectalertgroup = namespace["projectalertgroup"]
    metricRule={
        "comparison": "has-value",
        "type": "metricRule",
        "duration": "10s",
        "expression": "(sum(container_memory_working_set_bytes) by (pod_name, container_name) / sum(label_join(label_join(kube_pod_container_resource_limits_memory_bytes,\"pod_name\", \"\", \"pod\"),\"container_name\", \"\", \"container\")) by (pod_name, container_name)) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }
    clusterAlertRule = client.create_projectAlertRule(name="project_memory",
                                                      projectId=project.id, groupId=projectalertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


def test_project_cpu():
    client = namespace["client"]
    project = namespace["project"]
    projectalertgroup = namespace["projectalertgroup"]
    metricRule={
        "comparison": "has-value",
        "type": "metricRule",
        "duration": "10s",
        "expression": "(sum(container_cpu_usage_seconds_total) by (pod_name, container_name) / sum(label_join(label_join(kube_pod_container_resource_limits_cpu_cores,\"pod_name\", \"\", \"pod\"),\"container_name\", \"\", \"container\")) by (pod_name, container_name)) * 100",
        "onlyReadThresholdValue": False,
        "unit": None,
        "commonRule": None,
        "description": "Common Rules"
    }
    clusterAlertRule = client.create_projectAlertRule(name="project_cpu",
                                                      projectId=project.id, groupId=projectalertgroup.id, metricRule=metricRule,)
    assert clusterAlertRule.state == "active"


@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    client, cluster = get_admin_client_and_cluster()
    create_kubeconfig(cluster)
    p, ns = create_project_and_ns(
        ADMIN_TOKEN, cluster, random_test_name("test-metricRule"))
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    sys_client = get_project_client_for_token(project, ADMIN_TOKEN)

    namespace["client"] = client
    namespace["cluster"] = cluster
    namespace["project"] = p
    namespace["system"] = sys_client
    namespace["sys_project"] = project
    namespace["c_client"] = c_client

    monitoring_template = client.list_template(
        id=MONITORING_TEMPLATE_ID).data[0]

    MONITORING_VERSION = monitoring_template.defaultVersion
    C_MONITORING_ANSWERS = {
        "operator-init.enabled": "true",
        "exporter-kube-state.enabled": "true",
        "exporter-kubelets.enabled": "true",
        "exporter-kubernetes.enabled": "true",
        "exporter-fluentd.enabled": "true",
        "exporter-node.enabled": "true",
        "exporter-gpu-node.enabled": "false",
        "exporter-node.ports.metrics.port": "9796",
        "exporter-kubelets.https": "true",
        "exporter-node.resources.limits.cpu": "100m",
        "exporter-node.resources.limits.memory": "200Mi",
        "operator.resources.limits.memory": "500Mi",
        "prometheus.retention": "12h",
        "grafana.persistence.enabled": "false",
        "prometheus.persistence.enabled": "false",
        "prometheus.persistence.storageClass": "default",
        "grafana.persistence.storageClass": "default",
        "grafana.persistence.size": "10Gi",
        "prometheus.persistence.size": "50Gi",
        "prometheus.resources.core.requests.cpu": "50m",
        "prometheus.resources.core.limits.cpu": "1000m",
        "prometheus.resources.core.requests.memory": "750Mi",
        "prometheus.resources.core.limits.memory": "1000Mi",
        "prometheus.persistent.useReleaseName": "true"
    }

    if cluster["enableClusterMonitoring"] is False:
        client.action(cluster, "enableMonitoring", answers=C_MONITORING_ANSWERS, version=MONITORING_VERSION)
        wait_for_monitor_app_to_active(sys_client, "cluster-monitoring")
        wait_for_monitor_app_to_active(sys_client, "monitoring-operator")

    dingtalkConfig = {
        "type":"dingtalkConfig",
        "url":"https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb"}
    notifier = client.create_notifier(name=random_test_name("cluster-metricRule"), clusterId=cluster.id, dingtalkConfig=dingtalkConfig)

    recipients = [{"notifierType":"dingtalk","notifierId": notifier.id,"recipient":""}]
    clusteralertgroup = client.create_clusterAlertGroup(name=random_test_name("cluster-group"), clusterId=cluster.id, recipients=recipients)
    assert clusteralertgroup.state == "active"
    wait_for_monitor_app_to_active(sys_client, "cluster-alerting")
    namespace["clusteralertgroup"] = clusteralertgroup
    projectalertgroup = client.create_projectAlertGroup(name=random_test_name("project-metricRule"), projectId=p.id, recipients=recipients)
    assert projectalertgroup.state == "active"
    namespace["projectalertgroup"] = projectalertgroup

    def fin():
        client = namespace["client"]
        #client.delete(namespace["project"])
        #client.delete(namespace["clusteralertgroup"])
        #client.delete(namespace["projectalertgroup"])
    request.addfinalizer(fin)


def wait_for_monitor_app_to_active(client, app,
                           timeout=DEFAULT_MULTI_CLUSTER_APP_TIMEOUT):
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