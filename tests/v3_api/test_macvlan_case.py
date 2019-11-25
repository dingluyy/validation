from .entfunc import *
import pytest

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "None")
TEST_RANCHER_GKE_SERVER_IP = os.environ.get('RANCHER_GKE_SERVER_IP', "")
RANCHER_SERVER_URL = os.environ.get('CATTLE_TEST_URL', "https://" + TEST_RANCHER_GKE_SERVER_IP + ":8443/")
RANCHER_API_URL = RANCHER_SERVER_URL + "/v3"
token = os.environ.get('ADMIN_TOKEN', "")
headers = {"cookie": "R_SESS=" + token}
DEFAULT_MASTER = os.environ.get('RANCHER_TEST_SUBNET_MASTER', "ens4")

if_without_rancher = pytest.mark.skipif(not TEST_RANCHER_GKE_SERVER_IP,
                                     reason='GKE SERVER not provided, cannot deploy cluster')
namespace = {"client": None, "cluster": None}


# flannel macvlan cluster
@if_without_rancher
def test_deploy_rancher_server_flannel_macvlan():
    #node-0
    client = namespace['client']

    rke_config=get_rke_config("v1.17.9-rancher1-1","multus-flannel-macvlan",DEFAULT_MASTER)
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
        #ssh_cmd= "ssh -o \"ProxyCommand corkscrew 127.0.0.1 7890 %h %p\" -o ServerAliveInterval=50 " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        login_cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"ubuntu\" C-m"
        login_ssh_cmd= "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        #login_ssh_cmd= "ssh -o \"ProxyCommand corkscrew 127.0.0.1 7890 %h %p\" -o ServerAliveInterval=50  " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        print(login_ssh_cmd)
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        print(ssh_cmd)
        result=run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster,project,ns,p_client = validate_macvlan_cluster(client, cluster,token, check_intermediate_state=True,
                                        skipIngresscheck=True,intermediate_state="updating",skipNodecheck=True,flannel_service_check=True)
    namespace['cluster'] = cluster
    #name,project,master,vlan,cidr,gateway,ranges,routes,namespace
    cidr="172.20.10.0/24"
    defaultGateway="172.20.10.1"
    subnet_name = random_test_name("test-macvlan")
    validate_create_macvlan_subnet(subnet_name, project.id.replace(':', "-"), DEFAULT_MASTER,
                                   0, cidr, '', [], [], {}, 0, defaultGateway)

    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


def test_macvlan_route():
    print("RANCHER_SERVER_URL : ",RANCHER_SERVER_URL)
    print("token : ",token)
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    validate_create_macvlan_subnet(subnet_name, project.id.replace(":","-"), DEFAULT_MASTER, 2, cidr, "", ranges, [],{},0,"172.20.20.1")


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
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    podDefaultGateway={"enable": True, "serviceCidr": "10.43.0.0/16"}
    validate_create_macvlan_subnet(subnet_name, project.id.replace(":","-"), DEFAULT_MASTER, 3, cidr, "", ranges, [],podDefaultGateway,0,"172.20.20.1")

    c_client = get_cluster_client_for_token(cluster, token)
    ns1 = create_ns(c_client, cluster, project, ns_name=None)
    p_client = get_project_client_for_token(project, token)
    #same subnet/not same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns1,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns1, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


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
    validate_create_macvlan_subnet(subnet_name, project.id, DEFAULT_MASTER, 3, cidr, "", ranges, routes,{})

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


def test_macvlan_iface():
    print("RANCHER_SERVER_URL : ",RANCHER_SERVER_URL)
    print("token : ",token)
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)

    subnet_name = random_test_name("test-macvlan1")
    cidr="172.20.20.0/24"
    ranges=[{"rangeStart":"172.20.20.1","rangeEnd":"172.20.20.10"}]
    routes = [{"dst": "172.20.30.0/30", "gw": "172.20.20.100", "iface": "eth1"}]
    validate_create_macvlan_subnet(subnet_name, project.id.replace(":","-"), DEFAULT_MASTER, 4, cidr, "", ranges, [],{},0,"172.20.20.1")

    c_client = get_cluster_client_for_token(cluster, token)
    ns1 = create_ns(c_client, cluster, project, ns_name=None)
    p_client = get_project_client_for_token(project, token)
    #same subnet/not same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns1,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns1, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


def test_create_subnet_alldefault():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.20.0/24'
    defaultGateway = '172.20.20.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)


def test_create_subnet_vlan2():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.21.0/24'
    defaultGateway = '172.20.21.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 2, cidr, '', [], [], {}, 0, defaultGateway)


def test_create_subnet_gateway():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.22.0/24'
    gateway = '172.20.22.99'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], [], {}, 0)


def test_create_subnet_project():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.23.0/24'
    defaultGateway = '172.20.23.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)


def test_create_subnet_ipDelayReuse():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.24.0/24'
    defaultGateway = '172.20.24.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 5, defaultGateway)


def test_create_subnet_ranges():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges=[{"rangeStart": "172.20.25.10", "rangeEnd": "172.20.25.19"},
            {"rangeStart": "172.20.25.30", "rangeEnd": "172.20.25.39"}]
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway)


def test_create_subnet_routes():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.26.0/24'
    defaultGateway = '172.20.26.1'
    routes = [{"dst": "172.20.30.0/30", "gw": "172.20.26.100", "iface": "eth1"},
              {"dst": "172.20.31.0/30", "iface": "eth0"}]
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], routes, {}, 0, defaultGateway)


def test_create_subnet_podDefaultGateway():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.27.0/24'
    defaultGateway = '172.20.27.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], podDefaultGateway, 0, defaultGateway)


def test_create_subnet_allcustom():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.28.0/24'
    gateway = '172.20.28.100'
    ranges = [{"rangeStart": "172.20.28.10", "rangeEnd": "172.20.28.19"},
            {"rangeStart": "172.20.28.30", "rangeEnd": "172.20.28.39"}]
    routes = [{"dst": "172.20.30.0/30", "iface": "eth1"},
              {"dst": "172.20.31.0/30", "gw": "172.20.29.100", "iface": "eth0"}]
    podDefaultGateway =  {"enable": True, "serviceCidr": "10.43.0.0/16"}
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 5, cidr, gateway, ranges, routes, podDefaultGateway, 10)


def test_update_subnet_add_range():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.30.0/24'
    defaultGateway = '172.20.30.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)

    ranges = subnet['spec']['ranges']
    range = [{"rangeStart": "172.20.30.10", "rangeEnd": "172.20.30.19"}]
    new_ranges = ranges + range
    subnet['spec']['ranges'] = new_ranges
    validate_update_macvlan_subnet(subnet, new_ranges)


def test_update_subnet_add_routes():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.31.0/24'
    defaultGateway = '172.20.31.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)

    routes = [{"dst": "172.20.30.0/30", "iface": "eth1"}]
    subnet['spec']['routes'] = routes
    validate_update_macvlan_subnet(subnet, '', routes)


def test_update_subnet_modify_routes():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.32.0/24'
    gateway = '172.20.32.100'
    routes = [{"dst": "172.20.30.0/30", "iface": "eth1"},
              {"dst": "172.20.31.0/30", "gw": "172.20.29.100", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], routes, {}, 0)

    new_routes = [{"dst": "172.20.40.0/30", "gw": "172.20.32.111", "iface": "eth1"}]
    subnet['spec']['routes'] = new_routes
    validate_update_macvlan_subnet(subnet, '', new_routes)


def test_update_subnet_enable_podDefaultGateway():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.33.0/24'
    defaultGateway = '172.20.33.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)

    new_podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, '', '', new_podDefaultGateway)


def test_update_subnet_disable_podDefaultGateway():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.34.0/24'
    defaultGateway = '172.20.34.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], podDefaultGateway, 0, defaultGateway)

    new_podDefaultGateway = {}
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, '', '', new_podDefaultGateway)


def test_update_subnet_all():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.35.0/24'
    gateway = '172.20.35.100'
    ranges = [{"rangeStart": "172.20.35.10", "rangeEnd": "172.20.35.19"},
              {"rangeStart": "172.20.35.30", "rangeEnd": "172.20.35.39"}]
    routes = [{"dst": "172.20.40.0/30", "iface": "eth1"},
              {"dst": "172.20.41.0/30", "gw": "172.20.29.100", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 5, cidr, gateway, ranges,
                                   routes, {}, 10)

    range = [{"rangeStart": "172.20.35.50", "rangeEnd": "172.20.35.59"},
             {"rangeStart": "172.20.35.90", "rangeEnd": "172.20.35.99"}]
    new_ranges = subnet['spec']['ranges'] + range
    new_routes = [{"dst": "172.20.50.0/30", "iface": "eth1"},
                  {"dst": "172.20.51.0/30", "gw": "172.20.35.111", "iface": "eth1"},
                  {"dst": "172.20.52.0/30", "gw": "172.20.29.100", "iface": "eth0"}]
    new_podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}

    subnet['spec']['ranges'] = new_ranges
    subnet['spec']['routes'] = new_routes
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, new_ranges, new_routes, new_podDefaultGateway)


def test_delete_subnet():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.40.0/24'
    defaultGateway = '172.20.40.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway)

    validate_delete_macvlan_subnet(subnet)


def test_delete_project_subnet():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    print(project)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.41.0/24'
    gateway = '172.20.41.100'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0)

    client.delete(project)
    wait_for_project_delete(client, cluster, project.name)
    detail_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    detail_r = requests.get(detail_url, verify=False, headers=headers)
    assert detail_r.status_code == 404
    assert detail_r.json()['status'] == 'Failure'

    subnet = get_macvlansubnet(subnet_name, False, False, True)
    assert subnet == 1


def test_use_macvlan_deployment():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.50.0/24'
    gateway = '172.20.50.100'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                   [], [], {}, 0)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    client.delete(project)


def test_use_macvlan_daemonset():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.51.0/24'
    gateway = '172.20.51.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_daemonset_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'daemonset', ns, subnet)

    client.delete(project)


def test_use_macvlan_statefulset():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.52.0/24'
    gateway = '172.20.52.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_statefulset_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'statefulset', ns, subnet)

    client.delete(project)


def test_use_macvlan_cronjob():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.53.0/24'
    gateway = '172.20.53.99'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_cronjob_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'cronjob', ns, subnet)

    client.delete(project)


def test_use_macvlan_job():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.54.0/24'
    gateway = '172.20.54.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)


def test_macvlan_iprange():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges = [{"rangeStart": "172.20.25.10", "rangeEnd": "172.20.25.19"},
              {"rangeStart": "172.20.25.30", "rangeEnd": "172.20.25.39"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)


def test_macvlan_ipranges():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges = [{"rangeStart": "172.20.25.10", "rangeEnd": "172.20.25.19"},
              {"rangeStart": "172.20.25.30", "rangeEnd": "172.20.25.39"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)

def test_macvlan_notuseip_defaultgateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges = [{"rangeStart": "172.20.25.10", "rangeEnd": "172.20.25.19"},
              {"rangeStart": "172.20.25.30", "rangeEnd": "172.20.25.39"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)


def test_macvlan_notuseip_gateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges = [{"rangeStart": "172.20.25.10", "rangeEnd": "172.20.25.19"},
              {"rangeStart": "172.20.25.30", "rangeEnd": "172.20.25.39"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, "busybox:musl", annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)


# canal macvlan cluster
@if_without_rancher
def test_deploy_case_canal_macvlan():
    #node-2
    client = namespace['client']
    rke_config=get_rke_config("v1.17.9-rancher1-1","multus-canal-macvlan",DEFAULT_MASTER)
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
    validate_create_macvlan_subnet(subnet_name,project.id,DEFAULT_MASTER,0,cidr,"",[],[],{})

    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"nginx")
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,"busybox:musl")
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


def get_admin_token(RANCHER_SERVER_URL):
    """Returns a ManagementContext for the default global admin user."""
    CATTLE_AUTH_URL = \
        RANCHER_SERVER_URL + "v3-public/localproviders/local?action=login"
    r = requests.post(CATTLE_AUTH_URL, json={
        'username': 'admin',
        'password': 'admin',
        'responseType': 'json',
    }, verify=False)
    print(r.json())
    token = r.json()['token']
    print(token)
    # Change admin password
    client = rancher.Client(url=RANCHER_SERVER_URL+"v3",
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


def validate_create_macvlan_subnet(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway=''):
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

    cluster = namespace['cluster']

    create_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets'

    json = {
        "apiVersion": "macvlan.cluster.cattle.io/v1",
        "kind": "MacvlanSubnet",
        "metadata": {
            "name": name,
            "namespace": "kube-system",
            "labels": {
                "project": project
            }
        },
        "spec": {
            "master": master,
            "vlan": vlan,
            "cidr": cidr,
            "mode": "bridge",
            "gateway": gateway,
            "ranges": ranges,
            "routes": routes,
            "podDefaultGateway": podDefaultGateway,
            "ipDelayReuse": ipDelayReuse
        }
    }

    create_r = requests.post(create_url, json=json, verify=False, headers=headers)
    assert create_r.status_code == 201

    time.sleep(2)

    detail_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + name
    detail_r = requests.get(detail_url, verify=False, headers=headers)
    assert detail_r.status_code == 200
    diff_create_subnet(detail_r.json(), project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway)

    subnet = get_macvlansubnet(name)
    diff_create_subnet(subnet, project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway)
    return subnet


def validate_update_macvlan_subnet(subnet, ranges='', routes='', podDefaultGateway=''):
    cluster = namespace['cluster']
    subnet_name = subnet['metadata']['name']
    update_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    update_r = requests.put(update_url, json.dumps(subnet), verify=False, headers=headers)
    assert update_r.status_code == 200

    detail_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    detail_r = requests.get(detail_url, verify=False, headers=headers)
    assert detail_r.status_code == 200
    diff_update_subnet(detail_r.json(), ranges, routes, podDefaultGateway)

    subnet = get_macvlansubnet(subnet_name)
    diff_update_subnet(subnet, ranges, routes, podDefaultGateway)
    return subnet


def validate_delete_macvlan_subnet(subnet):
    cluster = namespace['cluster']
    subnet_name = subnet['metadata']['name']

    delete_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    delete_r = requests.delete(delete_url, verify=False, headers=headers)
    assert delete_r.status_code == 200

    detail_url = RANCHER_SERVER_URL + 'k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    detail_r = requests.get(detail_url, verify=False, headers=headers)
    assert detail_r.status_code == 404
    assert detail_r.json()['status'] == 'Failure'

    subnet = get_macvlansubnet(subnet_name, False, False, True)
    assert subnet == 1


def diff_create_subnet(subnet, project, master, vlan, cidr, gateway, ranges, routes, podDefaultGateway, ipDelayReuse, defaultGateway):

    assert subnet['metadata']['labels']['project'] == project
    assert subnet['spec']['master'] == master
    assert subnet['spec']['vlan'] == vlan
    assert subnet['spec']['cidr'] == cidr
    if not defaultGateway:
        assert subnet['spec']['gateway'] == gateway
    else:
        assert subnet['spec']['gateway'] == defaultGateway
    assert subnet['spec']['ranges'] == ranges
    if routes != []:
        assert subnet['spec']['routes'] == routes
    assert subnet['spec']['podDefaultGateway'] == podDefaultGateway
    if ipDelayReuse != 0:
        assert subnet['spec']['ipDelayReuse'] == ipDelayReuse


def diff_update_subnet(subnet, ranges, routes, podDefaultGateway):
    if ranges != '':
        assert subnet['spec']['ranges'] == ranges
    if routes != '' and routes != []:
        assert subnet['spec']['routes'] == routes
    if podDefaultGateway != '':
        assert subnet['spec']['podDefaultGateway'] == podDefaultGateway


def validate_use_macvlan(p_client, workload, type, ns, subnet):

    validate_workload(p_client, workload, type, ns.name)

    ips = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/ip"])
    macs = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/mac"])

    kind=get_macvlan_ip_mac_kind(ips,macs)

    pods = p_client.list_pod(workloadId=workload.id).data

    validate_macvlan_service(ns.name, workload)

    validate_macvlan_pods(pods, ns, subnet, kind, ips, macs)


def validate_macvlan_pods(pods, ns, subnet, kind, ips, macs):
    for pod in pods:
        assert pod["status"]["phase"] == "Running"
        annotations = pod["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
        annotations.replace("\n","")
        annotations=json.loads(annotations)
        for annotation in annotations:
            print("annotation for",annotation)
            a=annotation["name"]
            if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
                assert len(annotation["ips"]) == 1
                ip = annotation["ips"][0]
                ips, macs = validate_ip_mac_by_kind(ip, annotation["mac"], ips, macs, kind, subnet['spec']["cidr"])
                if len(subnet['spec']["ranges"]) != 0 :
                    result = check_ip_in_ranges(ip,subnet['spec']["ranges"])
                    assert result
        ip_result=validate_macvlanIP(ns, pod)
        assert ip_result == 0


@pytest.fixture(scope='module', autouse="True")
def create_project_client():
    if TEST_RANCHER_GKE_SERVER_IP != "":
        wait_until_active(RANCHER_SERVER_URL)
        global token
        token = get_admin_token(RANCHER_SERVER_URL)
        client = get_admin_client_byToken(RANCHER_API_URL, token)
        namespace["client"] = client
        global headers
        headers = {"cookie": "R_SESS=" + token}
    elif token != "" and RANCHER_SERVER_URL != "https://:8443":
        client, cluster = get_admin_client_and_cluster_byUrlToken(RANCHER_API_URL, token)
        create_kubeconfig(cluster)
        namespace["client"] = client
        namespace["cluster"] = cluster


def wait_for_project_delete(client, cluster, project, timeout=DEFAULT_TIMEOUT):
    projects = client.list_project(name=project,clusterId=cluster.id)
    print(projects)
    start = time.time()
    while len(projects) != 0:
        if time.time() - start > timeout:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        projects = client.list_project(name=project, clusterId=cluster.id)
    return projects