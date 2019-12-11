from .common import *  # NOQA

k8s_version = "v1.10.1-rancher1"
docker_version = "18.09"
rke_config = {"authentication": {"type": "authnConfig", "strategy": "x509"},
              "ignoreDockerVersion": False,
              "type": "rancherKubernetesEngineConfig"}
RANCHER_CLEANUP_CLUSTER = os.environ.get('RANCHER_CLEANUP_CLUSTER', "True")
NETWORK_PLUGIN = os.environ.get('RANCHER_NETWORK_PLUGIN', "canal,flannel,calico,weave")
DOCKER_INSTALL_CMD = (
    "curl https://releases.rancher.com/install-docker/{0}.sh | sh")

NETWORK_PLUGIN_LIST = NETWORK_PLUGIN.split(",")

def test_rke_custom_k8s_1_15_5():
    assert len(NETWORK_PLUGIN_LIST) > 0
    for plugin in NETWORK_PLUGIN_LIST:
        validate_k8s_version("v1.15.7-rancher1-1", plugin=plugin)


def test_rke_custom_k8s_1_14_8():
    assert len(NETWORK_PLUGIN_LIST) > 0
    for plugin in NETWORK_PLUGIN_LIST:
        validate_k8s_version("v1.16.4-rancher1-1", plugin=plugin)


def test_rke_custom_k8s_1_13_12():
    assert len(NETWORK_PLUGIN_LIST) > 0
    for plugin in NETWORK_PLUGIN_LIST:
        validate_k8s_version("v1.17.0-rancher1-2", plugin=plugin)


def validate_k8s_version(k8s_version, plugin="canal"):
    rke_config["kubernetesVersion"] = k8s_version
    rke_config["network"] = {"type": "networkConfig", "plugin": plugin}
    aws_nodes = \
        AmazonWebServices().create_multiple_nodes(
            3, random_test_name("testcustom"),wait_for_ready=False)

    nodes = AmazonWebServices().wait_for_nodes_state(aws_nodes)
    for node in nodes:
        docker_install_cmd = ("{} && sudo usermod -aG docker {} && sudo systemctl enable docker"
            .format(DOCKER_INSTALL_CMD.format(docker_version),node.ssh_user))
        print(docker_install_cmd)
        command = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                  + node.public_ip_address + " \' " + docker_install_cmd + " \'"
        run_command(command)

    node_roles = [["controlplane"], ["etcd"], ["worker"]]
    client = get_admin_client()
    cluster = client.create_cluster(name=random_name(),
                                    driver="rancherKubernetesEngine",
                                    rancherKubernetesEngineConfig=rke_config)
    assert cluster.state == "provisioning"
    i = 0
    for aws_node in aws_nodes:
        docker_run_cmd = \
            get_custom_host_registration_cmd(client, cluster,
                                             node_roles[i], aws_node)
        command = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/jenkins.pem -l ubuntu " \
                  + aws_node.public_ip_address + " \' " + docker_run_cmd + " \'"
        run_command(command)
        i += 1
    cluster = validate_cluster(client, cluster)
    if RANCHER_CLEANUP_CLUSTER == "True":
        delete_cluster(client, cluster)
        delete_node(aws_nodes)


def delete_node(aws_nodes):
    for node in aws_nodes:
        AmazonWebServices().delete_node(node)
