from .entfunc import *
import pytest

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "None")
TEST_RANCHER_GKE_SERVER_IP = os.environ.get('RANCHER_GKE_SERVER_IP', "None")
RANCHER_SERVER_URL = "https://" + TEST_RANCHER_GKE_SERVER_IP + ":8443"
RANCHER_API_URL = RANCHER_SERVER_URL + "/v3"
token = ""

# flannel macvlan cluster
def test_deploy_rancher_server_flannel_macvlan():
    #node-0
    wait_until_active(RANCHER_SERVER_URL)
    global token
    token = get_admin_token(RANCHER_SERVER_URL)
    url = RANCHER_SERVER_URL + "/v3"
    client = get_admin_client_byToken(url, token)
    rke_config=get_rke_config("v1.15.5-rancher1-1","multus-flannel-macvlan",DEFAULT_MASTER)
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

    cluster,project,ns,p_client = validate_macvlan_cluster(client, cluster,token, check_intermediate_state=True,
                                        skipIngresscheck=True,intermediate_state="updating",skipNodecheck=True,flannel_service_check=True)

    #name,project,master,vlan,cidr,gateway,ranges,routes,namespace
    cidr="172.20.10.0/24"
    subnet_name = random_test_name("test-macvlan")
    create_macvlan_subnet(subnet_name,project.id,DEFAULT_MASTER,0,cidr,"",[],[],{})
    result=validate_create_macvlansubnet(subnet_name)
    assert result == 0
    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


def test_macvlan_route():
    print("RANCHER_SERVER_URL : ",RANCHER_SERVER_URL)
    print("token : ",token)
    client , cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    create_macvlan_subnet(subnet_name, project.id, DEFAULT_MASTER, 2, cidr, "", ranges, [],{})
    result = validate_create_macvlansubnet(subnet_name)
    assert result == 0

    c_client = get_cluster_client_for_token(cluster, token)
    ns1 = create_ns(c_client, cluster, project, ns_name=None)
    p_client = get_project_client_for_token(project, token)
    #same subnet/not same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns1,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns1, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)

def test_macvlan_podDefaultGateway():
    print("RANCHER_SERVER_URL : ",RANCHER_SERVER_URL)
    print("token : ",token)
    client , cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    podDefaultGateway={"enable": True, "serviceCidr": "10.43.0.0/16"}
    create_macvlan_subnet(subnet_name, project.id, DEFAULT_MASTER, 2, cidr, "", ranges, [],podDefaultGateway)
    result = validate_create_macvlansubnet(subnet_name)
    assert result == 0

    c_client = get_cluster_client_for_token(cluster, token)
    ns1 = create_ns(c_client, cluster, project, ns_name=None)
    p_client = get_project_client_for_token(project, token)
    #same subnet/not same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns1,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns1, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)
    cluster_cleanup(client, cluster)
    time.sleep(60)

@pytest.mark.skip
def test_macvlan_multi_nodes():
    #node-0,node-1
    client , cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)

    clusterregistration = {"type": "clusterRegistrationToken", "clusterId": cluster.id}
    clusterregistrationtoken = client.create_clusterRegistrationToken(clusterregistration)
    for num in range(1, 2):
        nodeCommand = clusterregistrationtoken.nodeCommand \
                      + " --etcd --controlplane --worker --address " + "172.20.115.7" \
                      + num.__str__() + " --internal-address " + "172.20.115.7" + num.__str__()
        cmd = "sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() + " \"" + nodeCommand + " \" C-m"
        ssh_cmd = "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + \
                  RANCHER_SERVER_URL.split(":", 2)[1][2:] + " \' " + cmd + " \'"
        login_cmd = "sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() + " \"ubuntu\" C-m"
        login_ssh_cmd = "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + \
                        RANCHER_SERVER_URL.split(":", 2)[1][2:] + " \' " + login_cmd + " \'"
        print(login_ssh_cmd)
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        print(ssh_cmd)
        result = run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster = wait_for_condition(
        client, cluster,
        lambda x: x.state == "active",
        lambda x: 'State is: ' + x.state,
        timeout=MACHINE_TIMEOUT)
    assert cluster.state == "active"
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)

    subnet_name = random_test_name("test-macvlan2")
    cidr = "172.20.0.0/16"
    ranges = [{"rangeStart": "172.20.30.10", "rangeEnd": "172.20.30.20"},{"rangeStart": "172.20.30.5", "rangeEnd": "172.20.30.10"}]
    routes = [{"dst": "172.20.30.0/30", "gw": "172.20.30.1"}]
    create_macvlan_subnet(subnet_name, project.id, DEFAULT_MASTER, 3, cidr, "", ranges, routes,{})
    result = validate_create_macvlansubnet(subnet_name)
    assert result == 0
    nodes = client.list_node(clusterId=cluster.id).data
    print("nodes : ",nodes)
    schedulable_nodes = []
    for node in nodes:
        if node.worker:
            schedulable_nodes.append(node)
    assert len(schedulable_nodes) == 2
    nginx_wl, nginx_pods, nginx_kind, nginx_ips, nginx_macs = create_macvlan_workload(client, cluster, p_client, ns,
                                                                                      "auto", "auto", subnet_name, cidr,
                                                                                      "nginx",1,schedulable_nodes[0].id)
    busybox_wl, busybox_pods, busybox_kind, busybox_ips, busybox_macs = create_macvlan_workload(client, cluster,
                                                                                                p_client, ns, "auto",
                                                                                                "auto", subnet_name,
                                                                                                cidr, "busybox:musl",1,schedulable_nodes[1].id)
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                               ns, ns, nginx_wl, nginx_ips, nginx_macs, busybox_ips, busybox_macs)
    cluster_cleanup(client, cluster)
    time.sleep(60)

# canal macvlan cluster
def test_deploy_case_canal_macvlan():
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
    for num in range(2,3):
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

    cluster,project,ns,p_client = validate_macvlan_cluster(client, cluster,token, check_intermediate_state=True,
                                        skipIngresscheck=True,intermediate_state="updating",skipNodecheck=True)

    #name,project,master,vlan,cidr,gateway,ranges,routes,namespace
    cidr="172.20.10.0/24"
    subnet_name = random_test_name("test-macvlan")
    create_macvlan_subnet(subnet_name,project.id,DEFAULT_MASTER,0,cidr,"",[],[],{})
    result=validate_create_macvlansubnet(subnet_name)
    assert result == 0
    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)

def test_macvlan_iface():
    print("RANCHER_SERVER_URL : ",RANCHER_SERVER_URL)
    print("token : ",token)
    client , cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    routes = [{"dst": "172.20.30.0/30", "gw": "172.20.20.100", "iface": "eth1"}]
    create_macvlan_subnet(subnet_name, project.id, DEFAULT_MASTER, 2, cidr, "", ranges, [],{})
    result = validate_create_macvlansubnet(subnet_name)
    assert result == 0

    c_client = get_cluster_client_for_token(cluster, token)
    ns1 = create_ns(c_client, cluster, project, ns_name=None)
    p_client = get_project_client_for_token(project, token)
    #same subnet/not same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns1,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns1, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)

    cluster_cleanup(client, cluster)



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

def create_macvlan_subnet(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway):
    '''
    :param name:
    :param project:
    :param master:
    :param vlan: 0,2-4095
    :param cidr: xxx.xxx.xxx.xxx/xx
    :param gateway:
    :param ranges: [{"rangeStart":"xxx.xxx.xxx.xxx","rangeEnd":"xxx.xxx.xxx.xxx"}] 或 []
    :param routes: [{"dst": "xxx.xxx.xxx.xxx/xx", "gw": "xxx.xxx.xxx.xxx", "iface": "eth1/eth0"}] 或 []
    :param podDefaultGateway: {enable: true, serviceCidr: "xxx.xxx.xxx.xxx/xx"} 或 {}
    :return:
    '''
    project=project.replace(":","-")
    yaml_fname=create_macvlan_subnet_yaml(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway)
    create_cmd = " create -f " + yaml_fname
    execute_kubectl_cmd(create_cmd)
    return name