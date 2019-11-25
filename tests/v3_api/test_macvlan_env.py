from .entfunc import *
import pytest

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "None")
TEST_RANCHER_GKE_SERVER_IP = os.environ.get('RANCHER_GKE_SERVER_IP', "None")
RKE_K8S_VERSION = os.environ.get('RANCHER_RKE_K8S_VERSION', "v1.15.5-rancher1-1")
RANCHER_SERVER_URL = "https://" + TEST_RANCHER_GKE_SERVER_IP + ":8443"
RANCHER_API_URL = RANCHER_SERVER_URL + "/v3"
token = ""

# flannel macvlan cluster
def test_deploy_flannel_macvlan():
    #node-0
    #wait_until_active(RANCHER_SERVER_URL)
    #global token
    #token = get_admin_token(RANCHER_SERVER_URL)
    url = RANCHER_SERVER_URL + "/v3"
    client = get_admin_client_byToken(url, token)
    rke_config=get_rke_config(RKE_K8S_VERSION,"multus-flannel-macvlan",DEFAULT_MASTER)
    cluster = client.create_cluster(
            name=random_name(),
            driver="rancherKubernetesEngine",
            rancherKubernetesEngineConfig=rke_config)
    assert cluster.state == "provisioning"

    clusterregistration={"type":"clusterRegistrationToken","clusterId":cluster.id}
    clusterregistrationtoken=client.create_clusterRegistrationToken(clusterregistration)
    for num in range(0,1):
        nodeCommand=clusterregistrationtoken.nodeCommand \
                    + " --etcd --controlplane --worker --address " + "172.20.115.7" \
                    + num.__str__() + " --internal-address " + "172.20.115.7" + num.__str__()
        cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"" +nodeCommand +" \" C-m"
        ssh_cmd= "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        login_cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"ubuntu\" C-m"
        login_ssh_cmd= "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        print(login_ssh_cmd)
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        print(ssh_cmd)
        result=run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster = wait_for_condition(
        client, cluster,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state,
        timeout=MACHINE_TIMEOUT)
    assert cluster.state == "active"

# canal macvlan cluster
def test_deploy_canal_macvlan():
    #node-2
    url = RANCHER_SERVER_URL + "/v3"
    client = get_admin_client_byToken(url, token)
    rke_config=get_rke_config("v1.15.5-rancher1-1","multus-canal-macvlan",DEFAULT_MASTER)
    cluster = client.create_cluster(
            name=random_name(),
            driver="rancherKubernetesEngine",
            rancherKubernetesEngineConfig=rke_config)
    assert cluster.state == "provisioning"

    clusterregistration={"type":"clusterRegistrationToken","clusterId":cluster.id}
    clusterregistrationtoken=client.create_clusterRegistrationToken(clusterregistration)
    for num in range(1,2):
        nodeCommand=clusterregistrationtoken.nodeCommand \
                    + " --etcd --controlplane --worker --address " + "172.20.115.7" \
                    + num.__str__() + " --internal-address " + "172.20.115.7" + num.__str__()
        cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"" +nodeCommand +" \" C-m"
        ssh_cmd= "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        login_cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"ubuntu\" C-m"
        login_ssh_cmd= "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        print(login_ssh_cmd)
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        print(ssh_cmd)
        result=run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster = wait_for_condition(
        client, cluster,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state,
        timeout=MACHINE_TIMEOUT)
    assert cluster.state == "active"


def get_admin_token(RANCHER_SERVER_URL):
    """Returns a ManagementContext for the default global admin user."""
    CATTLE_AUTH_URL = \
        RANCHER_SERVER_URL + "/v3-public/localproviders/local?action=login"
    r = requests.post(CATTLE_AUTH_URL, json={
        'username': 'admin',
        'password': 'admin',
        'responseType': 'json',
    }, verify=False)
    print(r.json())
    token = r.json()['token']
    print(token)
    # Change admin password
    client = rancher.Client(url=RANCHER_SERVER_URL+"/v3",
                            token=token, verify=False)
    admin_user = client.list_user(username="admin").data
    admin_user[0].setpassword(newPassword=ADMIN_PASSWORD)

    # Set server-url settings
    serverurl = client.list_setting(name="server-url").data
    client.update(serverurl[0], value=RANCHER_SERVER_URL)
    return token


def get_rke_config(k8s_version, network_plugin, master):
    '''
    :param k8s_version:
    :param network_plugin: multus-flannel-macvlan ; multus-canal-macvlan
    :param master:
    :return:master
    '''
    network = get_rke_network(network_plugin, master)
    rke_config = {
        "addonJobTimeout": 30,
        "ignoreDockerVersion": True,
        "sshAgentAuth": False,
        "type": "rancherKubernetesEngineConfig",
        "kubernetesVersion": k8s_version ,
        "authentication": {
            "strategy": "x509",
            "type": "authnConfig"
        },
        "network": network,
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
            }
        }
    }
    return rke_config

def get_rke_network(plugin,iface):
    if plugin == "multus-canal-macvlan" :
        iface_name = "canal_iface"
    if plugin == "multus-flannel-macvlan":
        iface_name = "flannel_iface"
    network = {
            "plugin": plugin,
            "type": "networkConfig",
            "options": {
                "flannel_backend_type": "vxlan",
                iface_name: iface
            }
        }
    return network

@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    wait_until_active(RANCHER_SERVER_URL)
    global token
    token = get_admin_token(RANCHER_SERVER_URL)