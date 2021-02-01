from .entfunc import *
import pytest

namespace = {"client": None, "p_client": None, "ns": None, "cluster": None, "project": None, "system": None, "sys_project":None, "c_client": None}


def test_sink_dingtalk_required():
    answners = {
        "sinktarget": "dingtalk",
        "sink.dingtalk.webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb",
        "sink.dingtalk.label": "",
        "sink.dingtalk.level": "",
        "sink.dingtalk.namespaces": "",
        "sink.dingtalk.kinds": "",
        "sink.dingtalk.msg_type": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=dingtalk:https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb&"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_dingtalk_text():
    answners = {
        "sinktarget": "dingtalk",
        "sink.dingtalk.webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb",
        "sink.dingtalk.label": "test-dingtalk-text",
        "sink.dingtalk.level": "Normal",
        "sink.dingtalk.namespaces": "cattle-system,kube-system",
        "sink.dingtalk.kinds": "Pod,Node",
        "sink.dingtalk.msg_type": "text"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=dingtalk:https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb&label=test-dingtalk-text&level=Normal&namespaces=cattle-system,kube-system&kinds=Pod,Node&msg_type=text"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_dingtalk_markdown():
    answners = {
        "sinktarget": "dingtalk",
        "sink.dingtalk.webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb",
        "sink.dingtalk.label": "test-dingtalk-markdown",
        "sink.dingtalk.level": "",
        "sink.dingtalk.namespaces": "default,kube-system",
        "sink.dingtalk.kinds": "Pod,Node",
        "sink.dingtalk.msg_type": "markdown",
        "sink.dingtalk.cluster_id": "c550367cdf1e84dfabab013b277cc6bc2",
        "sink.dingtalk.region": "cn-shenzhen"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=dingtalk:https://oapi.dingtalk.com/robot/send?access_token=4b4de1354b290410523dcdf3ab04a5b3775f799e8d54949e7952ec437ba2cfdb&label=test-dingtalk-markdown&namespaces=default,kube-system&kinds=Pod,Node&msg_type=markdown&cluster_id=c550367cdf1e84dfabab013b277cc6bc2&region=cn-shenzhen"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_sls_required():
    answners = {
        "sinktarget": "sls",
        "sink.sls.sls_endpoint": "https://sls.aliyuncs.com",
        "sink.sls.project": "my_sls_project",
        "sink.sls.logStore": "my_sls_project_logStore",
        "sink.sls.topic": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=sls:https://sls.aliyuncs.com?project=my_sls_project&logStore=my_sls_project_logStore"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_sls_all():
    answners = {
        "sinktarget": "sls",
        "sink.sls.sls_endpoint": "https://sls.aliyuncs.com",
        "sink.sls.project": "my_sls_project",
        "sink.sls.logStore": "my_sls_project_logStore",
        "sink.sls.topic": "k8s-cluster-dev"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=sls:https://sls.aliyuncs.com?project=my_sls_project&logStore=my_sls_project_logStore&topic=k8s-cluster-dev"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_elasticsearch_required():
    answners = {
        "sinktarget": "elasticsearch",
        "sink.elasticsearch.es_server_url": "?nodes=http://foo.com:9200&nodes=http://bar.com:9200",
        "sink.elasticsearch.index": "",
        "sink.elasticsearch.esUserName": "",
        "sink.elasticsearch.esUserSecret": "",
        "sink.elasticsearch.maxRetries": "",
        "sink.elasticsearch.healthCheck": "",
        "sink.elasticsearch.sniff": "",
        "sink.elasticsearch.startupHealthcheckTimeout": "",
        "sink.elasticsearch.ver": "",
        "sink.elasticsearch.bulkWorkers": "",
        "sink.elasticsearch.cluster_name": "",
        "sink.elasticsearch.pipeline": ""
    }

    sink_cmds,app  = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=elasticsearch:?nodes=http://foo.com:9200&nodes=http://bar.com:9200"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_elasticsearch_all():
    answners = {
        "sinktarget": "elasticsearch",
        "sink.elasticsearch.es_server_url": "nodes=http://foo.com:9200&nodes=http://bar.com:9200",
        "sink.elasticsearch.index": "",
        "sink.elasticsearch.esUserName": "",
        "sink.elasticsearch.esUserSecret": "",
        "sink.elasticsearch.maxRetries": "",
        "sink.elasticsearch.healthCheck": "",
        "sink.elasticsearch.sniff": "",
        "sink.elasticsearch.startupHealthcheckTimeout": "",
        "sink.elasticsearch.ver": "",
        "sink.elasticsearch.bulkWorkers": "",
        "sink.elasticsearch.cluster_name": "",
        "sink.elasticsearch.pipeline": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=sls:https://sls.aliyuncs.com?project=my_sls_project&logStore=my_sls_project_logStore&topic=k8s-cluster-dev"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_honeycomb_required():
    answners = {
        "sinktarget": "honeycomb",
        "sink.honeycomb.dataset": "",
        "sink.honeycomb.writekey": "mywritekey",
        "sink.honeycomb.apihost": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=honeycomb:?writekey=mywritekey"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_honeycomb_all():
    answners = {
        "sinktarget": "honeycomb",
        "sink.honeycomb.dataset": "mydataset",
        "sink.honeycomb.writekey": "mywritekey",
        "sink.honeycomb.apihost": "https://api.honeycomb.com"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=honeycomb:?dataset=mydataset&writekey=mywritekey&apihost=https://api.honeycomb.com"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_influxdb_required():
    answners = {
        "sinktarget": "influxdb",
        "sink.influxdb.influxdb_url": "http://monitoring-influxdb:80/",
        "sink.influxdb.user": "",
        "sink.influxdb.pw": "",
        "sink.influxdb.db": "",
        "sink.influxdb.insecuressl": "",
        "sink.influxdb.withfields": "",
        "sink.influxdb.cluster_name": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=influxdb:http://monitoring-influxdb:80/"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_influxdb_all():
    answners = {
        "sinktarget": "influxdb",
        "sink.influxdb.influxdb_url": "http://monitoring-influxdb:80/",
        "sink.influxdb.user": "admin",
        "sink.influxdb.pw": "Harbor12345",
        "sink.influxdb.db": "k8s",
        "sink.influxdb.insecuressl": False,
        "sink.influxdb.withfields": False,
        "sink.influxdb.cluster_name": "test-k8s"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=influxdb:http://monitoring-influxdb:80/?user=admin&pw=Harbor12345&db=k8s&cluster_name=test-k8s"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_kafka_required():
    answners = {
        "sinktarget": "kafka",
        "sink.kafka.brokers": "brokers=localhost:9092&brokers=localhost:9093",
        "sink.kafka.eventstopic": "",
        "sink.kafka.compression": "",
        "sink.kafka.user": "",
        "sink.kafka.password": "",
        "sink.kafka.cacert": "",
        "sink.kafka.cert": "",
        "sink.kafka.key": "",
        "sink.kafka.insecuressl": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = ""
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_kafka_all():
    answners = {
        "sinktarget": "kafka",
        "sink.kafka.brokers": "brokers=localhost:9092&brokers=localhost:9093",
        "sink.kafka.eventstopic": "",
        "sink.kafka.compression": "",
        "sink.kafka.user": "",
        "sink.kafka.password": "",
        "sink.kafka.cacert": "",
        "sink.kafka.cert": "",
        "sink.kafka.key": "",
        "sink.kafka.insecuressl": ""
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = ""
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_mysql():
    answners = {
        "sinktarget": "mysql",
        "sink.mysql.mysql_jdbc_url": "root:root@tcp(172.1.2.3:3306)/kube_event?charset=utf8"
    }

    sink_cmds, app = enable_kube_eventer_catalog(answners)
    sink_cmd = ""
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_wechat_required():
    answners = {
        "sinktarget": "wechat",
        "sink.wechat.corp_id": "a12389567",
        "sink.wechat.corp_secret": "12389567weqe",
        "sink.wechat.agent_id": "12389567",
        "sink.wechat.to_user": "",
        "sink.wechat.label": "",
        "sink.wechat.level": "",
        "sink.wechat.namespaces": "",
        "sink.wechat.kinds": ""
    }

    sink_cmds,app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=wechat:?corp_id=a12389567&corp_secret=12389567weqe&agent_id=12389567"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def test_sink_wechat_all():
    answners = {
        "sinktarget": "wechat",
        "sink.wechat.corp_id": "a12389567",
        "sink.wechat.corp_secret": "12389567weqe",
        "sink.wechat.agent_id": "12389567",
        "sink.wechat.to_user": "",
        "sink.wechat.label": "",
        "sink.wechat.level": "",
        "sink.wechat.namespaces": "",
        "sink.wechat.kinds": ""
    }

    sink_cmds,app = enable_kube_eventer_catalog(answners)
    sink_cmd = "--sink=wechat:?corp_id=a12389567&corp_secret=12389567weqe&agent_id=12389567"
    assert sink_cmd in sink_cmds

    system = namespace['system']
    system.delete(app)


def enable_kube_eventer_catalog( answers):
    system = namespace['system']
    system_project = namespace['sys_project']
    c_client = namespace["c_client"]
    ns = c_client.create_namespace(name=random_test_name('kube-eventer'),
                                   projectId=system_project.id)

    externalId = "catalog://?catalog=pandaria&template=kube-eventer&version=0.0.1"
    system.create_app(answers=answers, externalId=externalId, name="kube-eventer",
                      projectId=system_project.id,
                      targetNamespace=ns.name)

    time.sleep(3)
    # deployment
    kube_eventer = system.list_workload(name="kube-eventer").data
    assert len(kube_eventer) == 1
    kube_eventer_wl = wait_for_wl_to_active(system, kube_eventer[0])
    assert kube_eventer_wl.state == "active"
    sink_cmds = kube_eventer_wl.containers[0]['entrypoint']
    print(sink_cmds)

    # app
    app = wait_for_app_to_active(system, "kube-eventer")
    assert app.state == "active"

    # configmap
    configmaps = system.list_configMap(namespaceId=ns.name).data
    assert len(configmaps) > 0

    '''
    # cluster role
    cluster_role_cmd = "get clusterrole kube-eventer"
    cluster_role = execute_kubectl_cmd(cluster_role_cmd, json_out=True)
    print("kube_eventer clusterRole: ", cluster_role)
    assert len(cluster_role) > 0

    # service account
    service_account_cmd = "get ServiceAccount kube-eventer -n" + ns.name
    service_account = execute_kubectl_cmd(service_account_cmd)
    print("kube_eventer serviceAccount: ", service_account)
    assert len(service_account) > 0

    # cluster role binding
    role_binding_cmd = "get ClusterRoleBinding kube-eventer"
    role_binding = execute_kubectl_cmd(role_binding_cmd)
    print(role_binding)
    assert role_binding.roleRef['name'] == "kube-eventer"
    result = False
    for subject in role_binding.subjects:
        if subject['name'] == 'kube-eventer':
            assert subject['namespace'] == ns.name
            result = True
    assert result == True
    '''

    return sink_cmds, app


@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    client, cluster = get_admin_client_and_cluster()
    create_kubeconfig(cluster)
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    #p, ns = create_project_and_ns(
    #    ADMIN_TOKEN, cluster, random_test_name("test-gpu"))
    #p_client = get_project_client_for_token(p, ADMIN_TOKEN)
    projects = client.list_project(name="System", clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    sys_client = get_project_client_for_token(project, ADMIN_TOKEN)

    namespace["client"] = client
    #namespace["p_client"] = p_client
    #namespace["ns"] = ns
    namespace["cluster"] = cluster
    #namespace["project"] = p
    namespace["system"] = sys_client
    namespace["sys_project"] = project
    namespace["c_client"] = c_client

    def fin():
        client = namespace["client"]
        client.delete(namespace["project"])
    request.addfinalizer(fin)