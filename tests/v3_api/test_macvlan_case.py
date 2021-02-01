from .entfunc import *
import pytest
import datetime

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "None")
TEST_RANCHER_GKE_SERVER_IP = os.environ.get('RANCHER_GKE_SERVER_IP', "")
RANCHER_SERVER_URL = os.environ.get('CATTLE_TEST_URL', "https://" + TEST_RANCHER_GKE_SERVER_IP + ":8443/").strip('/')
#RANCHER_SERVER_URL = os.environ.get('CATTLE_TEST_URL', "https://104.154.21.135:8443/").strip('/')
token = os.environ.get('ADMIN_TOKEN', "")
#token = os.environ.get('ADMIN_TOKEN', "token-md7dc:t7cxc97cvc5q2nndd7fddrj2rdqs86r8ws8rt65jpp26f7pjvv5xj9")
DEFAULT_MASTER = os.environ.get('RANCHER_TEST_SUBNET_MASTER', "ens4")
BUSYBOX_IMAGE = os.environ.get('RANCHER_TEST_BUSYBOX_IMAGE', "busybox:musl")
NGINX_IMAGE = os.environ.get('RANCHER_TEST_NGINX_IMAGE', "nginx")
ROUTE_ETH0_GW = os.environ.get('RANCHER_ROUTE_ETH0_GW', '')
#ROUTE_ETH0_GW = os.environ.get('RANCHER_ROUTE_ETH0_GW', '169.254.1.1')
CIDR_PREFIX = os.environ.get('RANCHER_CIDR_PREFIX', '172.20.')
POD_DEFAULT_GATEWAY_CIDR = os.environ.get('RANCHER_CLUSTER_SERVICE_CIDR', '10.43.0.0/16')

RANCHER_AUTH_URL = RANCHER_SERVER_URL + "/v3-public/localproviders/local?action=login"
RANCHER_API_URL = RANCHER_SERVER_URL + "/v3"
headers = {"cookie": "R_SESS=" + token}

namespace = {"client": None, "cluster": None}
password = 'macvlanTest'
IPV6_TEMPLATE = '2002:%s:%s:0:0:0:0:0'
ip_delay_reuse = 60

if_without_rancher = pytest.mark.skipif(not TEST_RANCHER_GKE_SERVER_IP,
                                        reason='GKE SERVER not provided, cannot deploy cluster')
if_without_eth0_gw = pytest.mark.skipif(not ROUTE_ETH0_GW,
                                        reason='ROUTE ETH0 GW not provided, cannot set routes')

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
                    + " --etcd --controlplane --worker --address " + CIDR_PREFIX + "115.7" \
                    + num.__str__() + " --internal-address " + CIDR_PREFIX + "115.7" + num.__str__()
        cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"" +nodeCommand +" \" C-m"
        ssh_cmd= "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        #ssh_cmd= "ssh -o \"ProxyCommand corkscrew 127.0.0.1 7890 %h %p\" -o ServerAliveInterval=50 " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        login_cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"ubuntu\" C-m"
        login_ssh_cmd= "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        #login_ssh_cmd= "ssh -o \"ProxyCommand corkscrew 127.0.0.1 7890 %h %p\" -o ServerAliveInterval=50  " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        result=run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster,project,ns,p_client = validate_macvlan_cluster(client, cluster,token, check_intermediate_state=True,
                                        skipIngresscheck=True,intermediate_state="updating",skipNodecheck=True,flannel_service_check=True)
    namespace['cluster'] = cluster
    #name,project,master,vlan,cidr,gateway,ranges,routes,namespace
    cidr=CIDR_PREFIX + "10.0/24"
    defaultGateway=CIDR_PREFIX + "10.1"
    subnet_name = random_test_name("test-macvlan")
    validate_create_macvlan_subnet(subnet_name, project.id.replace(':', "-"), DEFAULT_MASTER,
                                   0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,NGINX_IMAGE)
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,BUSYBOX_IMAGE)
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


#test create macvlansubnet param
def test_create_subnet_alldefault():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.20.0/24'
    defaultGateway = '172.20.20.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway, headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_name_none():
    cluster = namespace['cluster']
    cidr = '172.20.0.0/24'
    r = create_macvlansubnet(cluster, '', '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0,headers)
    assert r.status_code == 422
    assert 'Invalid' == r.json()['reason']


def test_create_subnet_name_error():
    cluster = namespace['cluster']
    cidr = '172.20.0.0/24'
    r = create_macvlansubnet(cluster, 'abcd@rancher.com', '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, headers)
    assert r.status_code == 422
    assert 'Invalid' == r.json()['reason']


def test_create_subnet_name_dup():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.0.0/24'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, '172.20.0.1',headers)

    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, headers)
    assert r.status_code == 409
    assert 'AlreadyExists' == r.json()['reason']

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_vlan2():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.21.0/24'
    defaultGateway = '172.20.21.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 2, cidr, '', [], [], {}, 0, defaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_vlan_error():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.0.0/24'
    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 'ss', cidr, '', [], [], {}, 0, headers)
    assert r.status_code == 422
    assert 'Invalid' == r.json()['reason']


def test_create_subnet_cidr_none():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 0, '', '', [], [], {}, 0, headers)
    assert r.status_code == 400
    assert 'invalid CIDR address' in r.json()['message']


def test_create_subnet_cidr_error():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 0, '172.22.3e.0/14 ', '', [], [], {}, 0,headers)
    assert r.status_code == 400
    assert 'invalid CIDR address' in r.json()['message']


def test_create_subnet_gateway_in_cidr():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.22.0/24'
    gateway = '172.20.22.99'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], [], {}, 0,'',headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_gateway_default():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.22.0/24'
    gateway = '172.20.22.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], [], {}, 0,'',headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_gateway_not_in_cidr():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.22.0/24'
    gateway = '172.20.0.99'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], [], {}, 0,'',headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_project():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.23.0/24'
    defaultGateway = '172.20.23.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    client.delete(project)


def test_create_subnet_ipDelayReuse():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.24.0/24'
    defaultGateway = '172.20.24.1'
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, ip_delay_reuse, defaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_ipDelayReuse_error():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.0.0/24'
    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 'ss',headers)
    assert r.status_code == 422
    assert 'Invalid' == r.json()['reason']


def test_create_subnet_ranges():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.25.0/24'
    defaultGateway = '172.20.25.1'
    ranges=[{"rangeStart": CIDR_PREFIX + "25.10", "rangeEnd": CIDR_PREFIX + "25.19"},
            {"rangeStart": CIDR_PREFIX + "25.30", "rangeEnd": CIDR_PREFIX + "25.30"}]
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway,headers)

    delete_macvlansubnet(cluster,subnet_name,headers)


def test_create_subnet_routes_eth1_within_cidr():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.26.0/24'
    defaultGateway = '172.20.26.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": CIDR_PREFIX + "26.100", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "31.0/30", "iface": "eth1"}]
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], routes, {}, 0, defaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_routes_eth1_without_cidr():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.0.0/24'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": CIDR_PREFIX + "33.100", "iface": "eth1"}]
    cluster = namespace['cluster']

    r = create_macvlansubnet(cluster, subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], routes, {}, 0, headers)
    assert r.status_code == 400
    assert "invalid gateway ip \\'172.20.33.100\\' is not in network \\'172.20.0.0/24\\'" not in r.json()['message']


def test_create_subnet_routes_eth0():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.27.0/24'
    defaultGateway = '172.20.27.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": CIDR_PREFIX + "26.100", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "31.0/30", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "31.0/30", "gw": CIDR_PREFIX + "27.99", "iface": "eth0"}]
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], routes, {}, 0, defaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_podDefaultGateway():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.28.0/24'
    defaultGateway = '172.20.28.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], podDefaultGateway, 0, defaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_create_subnet_allcustom():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.29.0/24'
    gateway = '172.20.29.100'
    ranges = [{"rangeStart": CIDR_PREFIX + "29.10", "rangeEnd": CIDR_PREFIX + "29.19"},
            {"rangeStart": CIDR_PREFIX + "29.30", "rangeEnd": CIDR_PREFIX + "29.39"}]
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "31.0/30", "gw": CIDR_PREFIX + "29.10", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "32.0/30", "gw": CIDR_PREFIX + "29.11", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "32.0/30", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "32.0/30", "iface": "eth0"}]
    podDefaultGateway =  {"enable": True, "serviceCidr": "10.43.0.0/16"}
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 5, cidr, gateway, ranges, routes, podDefaultGateway, 60, '', headers)

    client.delete(project)


#test update macvlansubnet param
def test_update_subnet_add_range():
    cluster = namespace['cluster']
    subnet_name = random_test_name('vlan')
    cidr = '172.20.30.0/24'
    defaultGateway = '172.20.30.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway, headers)

    ranges = subnet['spec']['ranges']
    range = [{"rangeStart": CIDR_PREFIX + "30.10", "rangeEnd": CIDR_PREFIX + "30.19"}]
    new_ranges = ranges + range
    subnet['spec']['ranges'] = new_ranges
    validate_update_macvlan_subnet(subnet, new_ranges,'','',headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_update_subnet_add_routes():
    cluster = namespace['cluster']

    subnet_name = random_test_name('vlan')
    cidr = '172.20.31.0/24'
    defaultGateway = '172.20.31.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    routes = [{"dst": CIDR_PREFIX + "30.0/30", "iface": "eth1"}]
    subnet['spec']['routes'] = routes
    validate_update_macvlan_subnet(subnet, '', routes,'',headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_update_subnet_modify_routes():
    cluster = namespace['cluster']

    subnet_name = random_test_name('vlan')
    cidr = '172.20.32.0/24'
    gateway = '172.20.32.100'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "31.0/30", "gw": CIDR_PREFIX + "29.100", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway, [], routes, {}, 0, '',headers)

    new_routes = [{"dst": CIDR_PREFIX + "40.0/30", "gw": CIDR_PREFIX + "32.111", "iface": "eth1"}]
    subnet['spec']['routes'] = new_routes
    validate_update_macvlan_subnet(subnet, '', new_routes,{},headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_update_subnet_enable_podDefaultGateway():
    cluster = namespace['cluster']

    subnet_name = random_test_name('vlan')
    cidr = '172.20.33.0/24'
    defaultGateway = '172.20.33.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    new_podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, '', '', new_podDefaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_update_subnet_disable_podDefaultGateway():
    cluster = namespace['cluster']

    subnet_name = random_test_name('vlan')
    cidr = '172.20.34.0/24'
    defaultGateway = '172.20.34.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], podDefaultGateway, 0, defaultGateway,headers)

    new_podDefaultGateway = {}
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, '', '', new_podDefaultGateway,headers)

    delete_macvlansubnet(cluster, subnet_name,headers)


def test_update_subnet_all():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.35.0/24'
    gateway = '172.20.35.100'
    ranges = [{"rangeStart": CIDR_PREFIX + "35.10", "rangeEnd": CIDR_PREFIX + "35.19"},
              {"rangeStart": CIDR_PREFIX + "35.30", "rangeEnd": CIDR_PREFIX + "35.39"}]
    routes = [{"dst": CIDR_PREFIX + "40.0/30", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "41.0/30", "gw": CIDR_PREFIX + "29.100", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 5, cidr, gateway, ranges,
                                   routes, {}, ip_delay_reuse,'',headers)

    range = [{"rangeStart": CIDR_PREFIX + "35.50", "rangeEnd": CIDR_PREFIX + "35.59"},
             {"rangeStart": CIDR_PREFIX + "35.90", "rangeEnd": CIDR_PREFIX + "35.99"}]
    new_ranges = subnet['spec']['ranges'] + range
    new_routes = [{"dst": CIDR_PREFIX + "50.0/30", "iface": "eth1"},
                  {"dst": CIDR_PREFIX + "51.0/30", "gw": CIDR_PREFIX + "35.111", "iface": "eth1"},
                  {"dst": CIDR_PREFIX + "52.0/30", "gw": CIDR_PREFIX + "29.100", "iface": "eth0"}]
    new_podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}

    subnet['spec']['ranges'] = new_ranges
    subnet['spec']['routes'] = new_routes
    subnet['spec']['podDefaultGateway'] = new_podDefaultGateway
    validate_update_macvlan_subnet(subnet, new_ranges, new_routes, new_podDefaultGateway,headers)


    client.delete(project)


#test delete macvlansubnet
def test_delete_subnet():
    subnet_name = random_test_name('vlan')
    cidr = '172.20.36.0/24'
    defaultGateway = '172.20.36.1'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    validate_delete_macvlan_subnet(subnet,headers)


def test_delete_project_subnet():
    client = namespace['client']
    cluster = namespace['cluster']
    project = create_project(client, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.37.0/24'
    gateway = '172.20.37.100'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0, '', headers)

    client.delete(project)
    wait_for_project_delete(client, cluster, project.name)
    detail_r = detail_macvlansubnet(cluster, subnet_name,headers)
    assert detail_r.status_code == 404
    assert detail_r.json()['status'] == 'Failure'

    subnet = get_macvlansubnet(subnet_name, False, False, True)
    assert subnet == 1


#test workload use macvlan
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
                                   [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

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
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_daemonset_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

    nodes = client.list_node(clusterId=cluster.id).data
    validate_use_macvlan(p_client, workload, 'daemonset', ns, subnet, len(nodes))

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
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_statefulset_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

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
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_cronjob_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

    validate_use_macvlan(p_client, workload, 'cronJob', ns, subnet)

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
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_job_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

    validate_use_macvlan(p_client, workload, 'job', ns, subnet)

    client.delete(project)


#test use macvlan param function
def test_macvlan_error_master():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.60.0/30'
    defaultGateway = '172.20.60.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens0p9", 0, cidr, '',
                                            [], [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    unavailable_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_unavailable_macvlan_pod(p_client, unavailable_workload, ns, 'FailedCreatePodSandBox',
                                     'failed to lookup iface \"ens0p9\": Link not found', 30)

    client.delete(project)


def test_macvlan_diff_vlan():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr = '172.20.61.0/24'
    defaultGateway = '172.20.61.1'
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 2, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)
    annotations1 = get_workload_macvlan('172.20.61.10', 'auto', subnet_name1)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    subnet_name2 = random_test_name('vlan')
    subnet2 = validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 3, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)
    annotations2 = get_workload_macvlan('172.20.61.20', 'auto', subnet_name2)
    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations2)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet2)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 1

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 1

    client.delete(project)


def test_macvlan_same_vlan_same_cidr():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr = '172.20.62.0/24'
    defaultGateway = '172.20.62.1'
    ranges1 = [{"rangeStart": CIDR_PREFIX + "62.10", "rangeEnd": CIDR_PREFIX + "62.19"}]
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr, '', ranges1,
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', 'auto', subnet_name1)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    subnet_name2 = random_test_name('vlan')
    ranges2 = [{"rangeStart": CIDR_PREFIX + "62.20", "rangeEnd": CIDR_PREFIX + "62.29"}]
    subnet2 = validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr, '', ranges2,
                                             [], {}, 0, defaultGateway,headers)

    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name2)

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations2)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet2)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_same_vlan_diff_cidr():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr1 = '172.20.63.0/24'
    defaultGateway1 = '172.20.63.1'
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr1, '', [],
                                            [], {}, 0, defaultGateway1,headers)
    annotations1 = get_workload_macvlan('auto', 'auto', subnet_name1)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    subnet_name2 = random_test_name('vlan')
    cidr2 = '172.20.64.0/24'
    defaultGateway2 = '172.20.64.1'
    subnet2 = validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr2, '', [],
                                             [], {}, 0, defaultGateway2,headers)
    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name2)
    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations2)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet2)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 1

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 1

    client.delete(project)


def test_macvlan_cidr_overrun():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.65.0/30'
    defaultGateway = '172.20.65.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '',
                                            [], [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    unavailable_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_unavailable_macvlan_pod(p_client, unavailable_workload, ns, 'MacvlanIPError',
                                     'No enough ip resouce in subnet: ' + subnet_name)

    client.delete(project)


def test_macvlan_notuseip_defaultgateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.66.0/24'
    defaultGateway = '172.20.66.1'
    ranges = [{"rangeStart": CIDR_PREFIX + "66.0", "rangeEnd": CIDR_PREFIX + "66.2"},
              {"rangeStart": CIDR_PREFIX + "66.254", "rangeEnd": CIDR_PREFIX + "66.255"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    ip_list = validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    not_use_ips = ['172.20.66.0', '172.20.66.1', '172.20.66.255']
    for ip in ip_list:
        assert ip not in not_use_ips

    unavailable_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_unavailable_macvlan_pod(p_client, unavailable_workload, ns, 'MacvlanIPError', 'No enough ip resouce in subnet: '+subnet_name)

    client.delete(project)


def test_macvlan_notuseip_gateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.67.0/24'
    gateway = '172.20.67.11'
    ranges = [{"rangeStart": CIDR_PREFIX + "67.10", "rangeEnd": CIDR_PREFIX + "67.12"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, gateway, ranges, [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    ip_list = validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    not_use_ips = ['172.20.67.11']
    for ip in ip_list:
        assert ip not in not_use_ips

    unavailable_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_unavailable_macvlan_pod(p_client, unavailable_workload, ns, 'MacvlanIPError',
                                     'No enough ip resouce in subnet: ' + subnet_name)
    client.delete(project)


def test_macvlan_project_all():
    client = namespace['client']
    cluster = namespace['cluster']
    project1, ns1 = create_project_and_ns_byClient(client, token, cluster)
    p_client1 = get_project_client_for_token(project1, token)

    subnet_name = random_test_name('vlan')
    cidr = '172.20.68.0/24'
    gateway = '172.20.68.11'
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload1 = create_deployment_wl(p_client1, ns1, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client1, workload1, 'deployment', ns1, subnet)

    project2, ns2 = create_project_and_ns_byClient(client, token, cluster)
    p_client2 = get_project_client_for_token(project2, token)

    workload2 = create_deployment_wl(p_client2, ns2, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client2, workload2, 'deployment', ns2, subnet)

    client.delete(project1)
    client.delete(project2)
    delete_macvlansubnet(cluster, subnet_name,headers)


def test_macvlan_project_spec():
    client = namespace['client']
    cluster = namespace['cluster']
    project1, ns1 = create_project_and_ns_byClient(client, token, cluster)
    p_client1 = get_project_client_for_token(project1, token)
    projectId = project1.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.69.0/24'
    gateway = '172.20.69.11'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0,'',headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload1 = create_deployment_wl(p_client1, ns1, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client1, workload1, 'deployment', ns1, subnet)

    project2, ns2 = create_project_and_ns_byClient(client, token, cluster)
    p_client2 = get_project_client_for_token(project2, token)

    unavailable_workload = create_deployment_wl(p_client2, ns2, BUSYBOX_IMAGE, annotations)
    validate_unavailable_macvlan_pod(p_client2, unavailable_workload, ns2, 'MacvlanSubnetError',
                                     '(' + project2.id.replace(":", "-") +') is not own by ' + projectId.replace(":", "-"))
    client.delete(project1)
    client.delete(project2)


def test_macvlan_ipDelayReuse0():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.70.0/24'
    defaultGateway = '172.20.70.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [], [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    pods = p_client.list_pod(workloadId = workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    macvlanip = get_macvlanip(ns, pod)
    assert 'finalizers' not in macvlanip['metadata'].keys()

    p_client.delete(workload)

    pods = wait_for_pod_delete(p_client, workload)
    assert len(pods) == 0

    result = validate_macvlanIP(ns, pod)
    assert result == 1

    client.delete(project)


def test_macvlan_ipDelayReuse_auto():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.71.0/24'
    defaultGateway = '172.20.71.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [], [], {}, ip_delay_reuse, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    pods = p_client.list_pod(workloadId = workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    macvlanip = get_macvlanip(ns, pod)
    check_macvlanip_ipdelayreuse(macvlanip)

    p_client.delete(workload)

    pods = wait_for_pod_delete(p_client, workload)
    assert len(pods) == 0

    to_be_delete_macvlanip = get_macvlanip(ns, pod)
    metadata = to_be_delete_macvlanip['metadata']
    assert 'annotations' in metadata.keys()
    ipDelayReuseTimestamp = metadata['annotations']['macvlan.panda.io/ipDelayReuseTimestamp']
    deletionTimestamp = metadata['deletionTimestamp']
    ipDelayReuseTime = datetime.datetime.strptime(ipDelayReuseTimestamp, '%Y-%m-%dT%H:%M:%SZ')
    deletionTime = datetime.datetime.strptime(deletionTimestamp, '%Y-%m-%dT%H:%M:%SZ')
    assert ip_delay_reuse == (ipDelayReuseTime - deletionTime).seconds

    time.sleep(ip_delay_reuse)
    result = wait_for_macvlanip_delete(ns, pod)
    assert result == 1

    client.delete(project)


def test_macvlan_ipDelayReuse_spec():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.72.0/24'
    defaultGateway = '172.20.72.1'
    ipDelayReuse = 60
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, ipDelayReuse, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.72.11', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    macvlanip = get_macvlanip(ns, pod)
    assert 'finalizers' not in macvlanip['metadata'].keys()

    p_client.delete(workload)

    pods = wait_for_pod_delete(p_client, workload)
    assert len(pods) == 0

    result = validate_macvlanIP(ns, pod)
    assert result == 1

    client.delete(project)


def test_macvlan_iprange1():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.73.0/24'
    defaultGateway = '172.20.73.1'
    ranges = [{"rangeStart": CIDR_PREFIX + "73.15", "rangeEnd": CIDR_PREFIX + "73.16"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet,2)

    client.delete(project)


def test_macvlan_ipranges():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.74.0/24'
    defaultGateway = '172.20.74.1'
    ranges = [{"rangeStart": CIDR_PREFIX + "74.10", "rangeEnd": CIDR_PREFIX + "74.11"},
              {"rangeStart": CIDR_PREFIX + "74.20", "rangeEnd": CIDR_PREFIX + "74.20"},
              {"rangeStart": CIDR_PREFIX + "74.30", "rangeEnd": CIDR_PREFIX + "74.35"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 4)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 4)

    client.delete(project)


def test_macvlan_iprange_overrun():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.75.0/24'
    defaultGateway = '172.20.75.1'
    ranges = [{"rangeStart": CIDR_PREFIX + "75.10", "rangeEnd": CIDR_PREFIX + "75.11"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":","-"), DEFAULT_MASTER, 0, cidr, '', ranges, [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    unavailable_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1)
    validate_unavailable_macvlan_pod(p_client, unavailable_workload, ns, 'MacvlanIPError', 'No enough ip resouce in subnet: '+subnet_name)

    client.delete(project)


def test_macvlan_route_eth1_defaultGW():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.76.0/24'
    defaultGateway = '172.20.76.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "iface": "eth1"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                   [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_route_eth1_customGW():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.77.0/24'
    gateway = '172.20.77.2'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "iface": "eth1"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, gateway,
                                   [], routes, {}, 0, '', headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_route_eth1_routeGW():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.78.0/24'
    defaultGateway = '172.20.78.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": CIDR_PREFIX + "78.100", "iface": "eth1"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                            [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_route_eth0_defaultGW():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.79.0/24'
    defaultGateway = '172.20.79.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                            [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


@if_without_eth0_gw
def test_macvlan_route_eth0_GW_via_default():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.80.0/24'
    defaultGateway = '172.20.80.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "gw": ROUTE_ETH0_GW, "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                            [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


@if_without_eth0_gw
def test_macvlan_route_eth0_eth1():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.81.0/24'
    defaultGateway = '172.20.81.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "gw": ROUTE_ETH0_GW, "iface": "eth0"},
              {"dst": CIDR_PREFIX + "31.0/24", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "32.0/24", "gw": '172.20.81.11', "iface": "eth1"},
              {"dst": CIDR_PREFIX + "33.0/24", "iface": "eth1"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                            [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_route_enable_podDefaultGateway_without_routes():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.82.0/24'
    defaultGateway = '172.20.82.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    routes = [{"dst": "10.42.0.0/16", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": "10.0.2.0/24", "gw": "169.254.1.1", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [], routes, podDefaultGateway, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    ip_route = get_pod_spec_iproute(busybox_pod['name'], ns['name'])
    assert 'default via 172.20.82.1 dev eth1' in ip_route
    assert '10.43.0.0/16 via 169.254.1.1 dev eth0' in ip_route

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_route_enable_podDefaultGateway_with_routes():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.83.0/24'
    gateway = '172.20.83.100'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "31.0/30", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "32.0/30", "gw": CIDR_PREFIX + "83.11", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "33.0/30", "iface": "eth1"},
              {"dst": "10.42.0.0/16", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": "10.0.2.0/24", "gw": "169.254.1.1", "iface": "eth0"}              ]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, gateway, [], routes, podDefaultGateway, 0,'',headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    ip_route = get_pod_spec_iproute(busybox_pod['name'], ns['name'])
    assert 'default via 172.20.83.100 dev eth1' in ip_route
    assert '10.43.0.0/16 via 169.254.1.1 dev eth0' in ip_route

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_service_access_same_subnet_ns():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.84.0/24'
    defaultGateway = '172.20.84.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_service_access_same_subnet_diff_ns():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.85.0/24'
    defaultGateway = '172.20.85.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    c_client = get_cluster_client_for_token(cluster, token)
    nginx_ns = create_ns(c_client, cluster, project)
    nginx_workload = create_deployment_wl(p_client, nginx_ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', nginx_ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, nginx_ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, nginx_ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, nginx_ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, nginx_ns,
                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_service_access_diff_subnet_ns():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr = '172.20.86.0/24'
    defaultGateway = '172.20.86.1'
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', 'auto', subnet_name1)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    c_client = get_cluster_client_for_token(cluster, token)
    nginx_ns = create_ns(c_client, cluster, project)

    subnet_name2 = random_test_name('vlan')
    cidr = '172.20.87.0/24'
    defaultGateway = '172.20.87.1'
    subnet2 = validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)

    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name2)
    nginx_workload = create_deployment_wl(p_client, nginx_ns, NGINX_IMAGE, annotations2)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', nginx_ns, subnet2)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, nginx_ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, nginx_ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, nginx_ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, nginx_ns,
                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 1

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 1

    client.delete(project)


def test_macvlan_service_access_diff_subnet_same_ns():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr = '172.20.88.0/24'
    defaultGateway = '172.20.88.1'
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', 'auto', subnet_name1)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    busybox_pod = busybox_pods[0]

    subnet_name2 = random_test_name('vlan')
    cidr = '172.20.89.0/24'
    defaultGateway = '172.20.89.1'
    subnet2 = validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)

    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name2)
    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations2)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet2)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 1

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 1

    client.delete(project)


#test ip/mac check
def test_check_spec_ip_error_format():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.40.0/24'
    defaultGateway = '172.20.40.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.40.256', 'auto', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'invalid annotation ip list' in workload1.json()['message']

    annotations2 = get_workload_macvlan('172.20.ss.25', 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'invalid annotation ip list' in workload2.json()['message']

    annotations3 = get_workload_macvlan('172.20.40.25;172.20.40.26', 'auto', subnet_name)
    workload3 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations3)
    assert workload3.status_code == 400
    assert 'invalid annotation ip list' in workload3.json()['message']

    client.delete(project)


def test_check_spec_mac_error_format():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.41.0/24'
    defaultGateway = '172.20.41.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', 'abcdef:123:12', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'parse single mac address error' in workload1.json()['message']

    annotations2 = get_workload_macvlan('auto', '0a:00:27:11:00:12;0a:00:27:11:00:0e', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'parse single mac address error' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_not_in_cidr():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.42.0/28'
    defaultGateway = '172.20.42.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.40.5', 'auto', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'ip 172.20.40.5 not in subnet ' + subnet_name + ' hosts' in workload1.json()['message']

    annotations2 = get_workload_macvlan('172.20.42.100', 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip 172.20.42.100 not in subnet ' + subnet_name + ' hosts' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_default():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.43.0/24'
    defaultGateway = '172.20.43.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)


    annotations1 = get_workload_macvlan('172.20.43.0', 'auto', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'ip 172.20.43.0 not in subnet ' + subnet_name + ' hosts' in workload1.json()['message']

    annotations2 = get_workload_macvlan('172.20.43.255', 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip 172.20.43.255 not in subnet ' + subnet_name + ' hosts' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_not_in_ranges():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.44.0/24'
    defaultGateway = '172.20.44.1'
    ranges = [{"rangeStart": CIDR_PREFIX + "44.10", "rangeEnd": CIDR_PREFIX + "44.19"},
              {"rangeStart": CIDR_PREFIX + "44.30", "rangeEnd": CIDR_PREFIX + "44.39"}]
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', ranges,
                                   [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.44.25', 'auto', subnet_name)
    workload = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations)
    assert workload.status_code == 400
    assert 'ip 172.20.44.25 not in subnet ' + subnet_name + ' hosts' in workload.json()['message']

    client.delete(project)


def test_check_spec_ip_duplicate():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.45.0/24'
    defaultGateway = '172.20.45.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.45.25-172.20.45.25', 'auto', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'ip duplicate in list: 172.20.45.25' in workload1.json()['message']

    annotations2 = get_workload_macvlan('172.20.45.25-172.20.45.30-172.20.45.30-172.20.45.26', 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip duplicate in list: 172.20.45.30' in workload2.json()['message']

    client.delete(project)


def test_check_spec_mac_duplicate():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.46.0/24'
    defaultGateway = '172.20.46.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', '0a:00:27:11:00:12-0a:00:27:11:00:12', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'mac duplicate in list: 0a:00:27:11:00:12' in workload1.json()['message']

    annotations2 = get_workload_macvlan('auto', '0a:00:27:11:00:12-0a:00:27:11:00:0e-0a:00:27:11:00:0e', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'mac duplicate in list: 0a:00:27:11:00:0e' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_mac_duplicate():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.47.0/24'
    defaultGateway = '172.20.47.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.47.25-172.20.47.25', '0a:00:27:11:00:12-0a:00:27:11:00:12', subnet_name)
    workload = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations)
    assert workload.status_code == 400
    assert 'ip duplicate in list: 172.20.47.25' in workload.json()['message']

    client.delete(project)


def test_check_spec_ip_reseved_scale1():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.48.0/24'
    defaultGateway = '172.20.48.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.48.5', 'auto', subnet_name)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet)

    annotations2 = get_workload_macvlan('172.20.48.5', 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip has been reseved' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_reseved_scale0():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.49.0/24'
    defaultGateway = '172.20.49.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.49.5', 'auto', subnet_name)
    create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 0)

    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations)
    assert workload2.status_code == 400
    assert 'ip has been reseved' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_used():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.38.0/24'
    defaultGateway = '172.20.38.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', 'auto', subnet_name)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet)
    pods = p_client.list_pod(workloadId=workload1.id).data
    pod = pods[0]

    ip = ''
    annotations = pod["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
    annotations.replace("\n", "")
    annotations = json.loads(annotations)
    for annotation in annotations:
        a = annotation["name"]
        if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
            print(annotation["ips"])
            assert len(annotation["ips"]) == 1
            ip = annotation["ips"][0]

    annotations2 = get_workload_macvlan(ip, 'auto', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip has been used' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_gateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.39.0/24'
    gateway = '172.20.39.11'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, gateway, [],
                                   [], {}, 0,'',headers)

    annotations = get_workload_macvlan(gateway, 'auto', subnet_name)
    workload = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations)
    assert workload.status_code == 400
    assert 'ip use by subnet as gateway' in workload.json()['message']

    client.delete(project)


def test_check_spec_mac_used_same_subnet():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.90.0/24'
    defaultGateway = '172.20.90.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', '0a:00:27:1f:11:0e', subnet_name)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet)

    annotations2 = get_workload_macvlan('auto', '0a:00:27:1f:11:0e', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'mac has been used' in workload2.json()['message']

    client.delete(project)


def test_check_spec_mac_used_diff_subnet():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('vlan')
    cidr = '172.20.91.0/24'
    defaultGateway = '172.20.91.1'
    subnet1 = validate_create_macvlan_subnet(subnet_name1, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('auto', '0a:00:27:1f:11:0e', subnet_name1)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet1)

    subnet_name2 = random_test_name('vlan')
    validate_create_macvlan_subnet(subnet_name2, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr, '', [],
                                             [], {}, 0, defaultGateway,headers)
    annotations2 = get_workload_macvlan('auto', '0a:00:27:1f:11:0e', subnet_name2)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'mac has been used' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip_mac_used():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.92.0/24'
    defaultGateway = '172.20.92.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.92.10', '0a:00:27:1f:11:0e', subnet_name)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet)

    annotations2 = get_workload_macvlan('172.20.92.10', '0a:00:27:1f:11:0e', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'ip has been reseved' in workload2.json()['message']

    client.delete(project)


def test_check_spec_ip1_auto_mac():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.93.0/24'
    defaultGateway = '172.20.93.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.93.10', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    client.delete(project)


def test_check_spec_ipn_auto_mac():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.94.0/24'
    defaultGateway = '172.20.94.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.94.10-172.20.94.12', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    client.delete(project)


def test_check_auto_ip_spec_mac1():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.95.0/24'
    defaultGateway = '172.20.95.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'f2:e6:d8:33:eb:30', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    client.delete(project)


def test_check_auto_ip_spec_macn():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.96.0/24'
    defaultGateway = '172.20.96.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'f2:e6:d8:33:eb:33-f2:e6:d8:36:eb:32', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    client.delete(project)


def test_check_spec_ip1_spec_mac1():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.97.0/24'
    defaultGateway = '172.20.97.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.97.10', 'f2:e6:d8:33:eb:2f', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    client.delete(project)


def test_check_spec_ipn_spec_macn():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.98.0/24'
    defaultGateway = '172.20.98.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.98.20-172.20.98.21', 'f2:e6:d8:33:eb:2a-f2:e6:d8:33:eb:2d', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    client.delete(project)


def test_check_spec_ip_spec_mac_notequal():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.99.0/24'
    defaultGateway = '172.20.99.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.99.20', 'f2:e6:d8:33:eb:2a-f2:e6:d8:33:eb:2d', subnet_name)
    workload1 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations1)
    assert workload1.status_code == 400
    assert 'count of multiple IP and Mac not equal: 1 2' in workload1.json()['message']

    annotations2 = get_workload_macvlan('172.20.99.20-172.20.99.21', 'f2:e6:d8:33:eb:2a', subnet_name)
    workload2 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations2)
    assert workload2.status_code == 400
    assert 'count of IP and Mac not equal: 2 1' in workload2.json()['message']

    annotations3 = get_workload_macvlan('172.20.99.20-172.20.99.21-172.20.99.22', 'f2:e6:d8:33:eb:2a-f2:e6:d8:33:eb:2d', subnet_name)
    workload3 = create_workload_http(projectId, ns, BUSYBOX_IMAGE, annotations3)
    assert workload3.status_code == 400
    assert 'count of multiple IP and Mac not equal: 3 2' in workload3.json()['message']

    client.delete(project)


#test network-controller 0.5.x
def test_network_controller_loglevel():
    client = namespace['client']
    cluster = namespace['cluster']

    projects = client.list_project(name="System",clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, token)

    workloads = p_client.list_workload(name='network-controller').data
    assert len(workloads) == 1
    workload = workloads[0]

    p_client.update(workload, scale=0)
    p_client.update(workload, scale=1)
    pods = wait_for_pods_in_workload(p_client, workload, 1)
    assert len(pods) == 1
    pod = pods[0]
    wait_for_pod_to_running(p_client, pod)

    cmd = 'exec -n kube-system ' + pod.name + ' -- loglevel'
    result = execute_kubectl_cmd(cmd, json_out=False, stderr=True)
    assert b'info\n' == result

    cmd = 'exec -n kube-system ' + pod.name + ' -- loglevel --set debug'
    result = execute_kubectl_cmd(cmd, json_out=False, stderr=True)
    assert b'OK\n' == result

    cmd = 'exec -n kube-system ' + pod.name + ' -- loglevel'
    result = execute_kubectl_cmd(cmd, json_out=False, stderr=True)
    assert b'debug\n' == result


def test_pod_macvlanip_delete_logo():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.100.0/24'
    defaultGateway = '172.20.100.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    assert 'removed' not in pod.keys()
    assert 'removedTS' not in pod.keys()

    p_client.delete(workload)

    time.sleep(1)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    assert 'removed' in pod.keys()
    assert 'removedTS' in pod.keys()

    client.delete(project)


def test_not_enough_ip_used():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.101.0/30'
    defaultGateway = '172.20.101.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.101.2', 'auto', subnet_name)
    workload1 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1)
    validate_use_macvlan(p_client, workload1, 'deployment', ns, subnet)

    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name)
    workload2 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations2)
    validate_use_macvlan(p_client, workload2, 'deployment', ns, subnet)

    annotations3 = get_workload_macvlan('auto', 'auto', subnet_name)
    workload3 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations3)

    validate_unavailable_macvlan_pod(p_client, workload3, ns, 'MacvlanIPError', 'No enough ip resouce in subnet')

    client.delete(project)


def test_not_enough_ip_reseved():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.102.0/30'
    defaultGateway = '172.20.102.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations1 = get_workload_macvlan('172.20.102.2', 'auto', subnet_name)
    create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations1, 0)

    annotations2 = get_workload_macvlan('auto', 'auto', subnet_name)
    workload2 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations2)
    validate_use_macvlan(p_client, workload2, 'deployment', ns, subnet)

    annotations3 = get_workload_macvlan('auto', 'auto', subnet_name)
    workload3 = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations3)

    validate_unavailable_macvlan_pod(p_client, workload3, ns, 'MacvlanIPError', 'No enough ip resouce in subnet')

    client.delete(project)


def test_auto_ip_spec_mac_scale_up():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.103.0/24'
    defaultGateway = '172.20.103.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', '7e:11:0a:00:50:55-7e:11:0a:00:50:15', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 2
    pods_name = []
    for pod in pods:
        pods_name = pods_name + [pod.name]

    p_client.update(workload, scale=3)

    time.sleep(1)
    new_pods = p_client.list_pod(workloadId=workload.id).data
    assert len(new_pods) == 3

    pod = {}
    for new_pod in new_pods:
        if new_pod.name not in pods_name:
            pod = new_pod

    diff_unavailable_macvlan_pod(p_client, ns, pod, 'MacvlanIPError', 'not enough mac resouce in annotations')

    client.delete(project)


def test_spec_ip_auto_mac_scale_up():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.104.0/24'
    defaultGateway = '172.20.104.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.104.2-172.20.104.20', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 2
    pods_name = []
    for pod in pods:
        pods_name = pods_name + [pod.name]

    p_client.update(workload, scale=3)

    new_pods = p_client.list_pod(workloadId=workload.id).data
    assert len(new_pods) == 3

    pod = {}
    for new_pod in new_pods:
        if new_pod.name not in pods_name:
            pod = new_pod

    diff_unavailable_macvlan_pod(p_client, ns, pod, 'MacvlanIPError', 'No enough ip resouce in subnet: 172.20.104.2-172.20.104.20')

    client.delete(project)


def test_macvlanIptype_lable_autoip():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.105.0/24'
    defaultGateway = '172.20.105.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    time.sleep(1)

    cmd = 'get deployment -n ' + ns.name + ' ' + workload.name + ' -o yaml'
    result = execute_kubectl_cmd(cmd, True, False)
    assert result['metadata']['labels']['macvlan.panda.io/macvlanIpType'] == 'auto'

    client.delete(project)


def test_macvlanIptype_lable_specip():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.106.0/24'
    defaultGateway = '172.20.106.1'
    validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                   [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('172.20.106.11', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    time.sleep(1)

    cmd = 'get deployment -n ' + ns.name + ' ' + workload.name + ' -o yaml'
    result = execute_kubectl_cmd(cmd, True, False)
    assert result['metadata']['labels']['macvlan.panda.io/macvlanIpType'] == 'specific'

    client.delete(project)


def test_macvlan_selectip_with_useip():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.107.0/24'
    defaultGateway = '172.20.107.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 2)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 2)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 2

    for pod in pods:
        ip = ''
        assert pod["status"]["phase"] == "Running"
        annotations = pod["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
        annotations.replace("\n","")
        annotations=json.loads(annotations)
        for annotation in annotations:
            if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
                assert len(annotation["ips"]) == 1
                ip = annotation["ips"][0]
        assert pod['labels']['macvlan.pandaria.cattle.io/selectedIp'] == ip

    client.delete(project)


#test macvlan ingress
def test_tcpdump_wget_svc():
    client = namespace['client']
    cluster = namespace['cluster']

    nodeId = get_workload_nodeId(client, cluster)

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.115.0/24'
    defaultGateway = '172.20.115.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    apt_update = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get update'
    execute_kubectl_cmd(apt_update, False, True)
    time.sleep(1)
    apt_install = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt install -y tcpdump'
    execute_kubectl_cmd(apt_install, False, True)

    busybox_cmd = 'exec ' + busybox_pod['name'] + ' -n ' + ns.name + ' -- wget --spider --timeout=5 ' + nginx_workload['name']
    busybox_command = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, busybox_cmd)

    nginx_cmd0 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth0'
    nginx_command0 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd0)

    cmd0 = busybox_command + ' | ' + nginx_command0

    result0 = run_command_error_with_stderr(cmd0)
    list0 = str(result0).split('\\n')
    captured0 = list0[-5].split(' ')[0]
    received0 = list0[-4].split(' ')[0]
    dropped0 = list0[-3].split(' ')[0]

    assert int(captured0) != 0 or int(received0) !=0 or int(dropped0) !=0

    nginx_cmd1 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth1'
    nginx_command1 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd1)

    cmd1 = busybox_command + ' | ' + nginx_command1

    result1 = run_command_error_with_stderr(cmd1)
    list1 = str(result1).split('\\n')
    captured1 = list1[-5].split(' ')[0]
    received1 = list1[-4].split(' ')[0]
    dropped1 = list1[-3].split(' ')[0]

    assert int(captured1) == 0 and int(received1) == 0 and int(dropped1) == 0
    client.delete(project)


def test_tcpdump_wget_macvlan_svc():
    client = namespace['client']
    cluster = namespace['cluster']

    nodeId = get_workload_nodeId(client, cluster)

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.115.0/24'
    defaultGateway = '172.20.115.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    apt_update = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get update'
    execute_kubectl_cmd(apt_update, False, False)
    apt_install = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get install -y tcpdump'
    execute_kubectl_cmd(apt_install, False, True)

    time.sleep(1)
    busybox_cmd = 'exec ' + busybox_pod['name'] + ' -n ' + ns.name + ' -- wget --spider --timeout=5 ' + nginx_workload['name'] + MACVLAN_SERVICE_SUFFIX
    busybox_command = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, busybox_cmd)

    nginx_cmd0 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth0'
    nginx_command0 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd0)

    cmd0 = busybox_command + ' | ' + nginx_command0

    result0 = run_command_error_with_stderr(cmd0)
    list0 = str(result0).split('\\n')
    captured0 = list0[-5].split(' ')[0]
    received0 = list0[-4].split(' ')[0]
    dropped0 = list0[-3].split(' ')[0]
    assert int(captured0) == 0 and int(received0) == 0 and int(dropped0) == 0

    nginx_cmd1 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth1'
    nginx_command1 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd1)

    cmd1 = busybox_command + ' | ' + nginx_command1

    result1 = run_command_error_with_stderr(cmd1)
    list1 = str(result1).split('\\n')
    captured1 = list1[-5].split(' ')[0]
    received1 = list1[-4].split(' ')[0]
    dropped1 = list1[-3].split(' ')[0]
    assert int(captured1) != 0 or int(received1) !=0 or int(dropped1) !=0
    client.delete(project)


def test_tcpdump_wget_ingress_wl():
    client = namespace['client']
    cluster = namespace['cluster']

    nodeId = get_workload_nodeId(client, cluster)

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.109.0/24'
    defaultGateway = '172.20.109.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    annotations = {"macvlan.panda.io/ingress": "true"}
    rule = get_wl_ingress_rule(nginx_workload.id)
    ingress_name = random_test_name('ingress-wl')
    ingress = p_client.create_ingress(name=ingress_name,
                                      namespaceId=ns.id,
                                      rules=[rule],
                                      annotations=annotations)
    ingress = wait_for_ingress_to_active(p_client, ingress)
    publicEndpoints = ingress.publicEndpoints
    assert len(publicEndpoints) == 1
    publicEndpoint = publicEndpoints[0]
    ingress_service = publicEndpoint.protocol.lower() + "://" + publicEndpoint.hostname

    apt_update = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get update'
    execute_kubectl_cmd(apt_update, False, False)
    apt_install = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get install -y tcpdump'
    execute_kubectl_cmd(apt_install, False, True)

    busybox_cmd = 'exec ' + busybox_pod['name'] + ' -n ' + ns.name + ' -- wget --spider --timeout=5 ' + ingress_service
    busybox_command = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, busybox_cmd)

    nginx_cmd0 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth0'
    nginx_command0 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd0)

    cmd0 = busybox_command + ' | ' + nginx_command0
    result0 = run_command_error_with_stderr(cmd0)
    list0 = str(result0).split('\\n')
    captured0 = list0[-5].split(' ')[0]
    received0 = list0[-4].split(' ')[0]
    dropped0 = list0[-3].split(' ')[0]

    assert int(captured0) == 0 and int(received0) == 0 and int(dropped0) == 0

    nginx_cmd1 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth1'
    nginx_command1 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd1)

    cmd1 = busybox_command + ' | ' + nginx_command1
    result1 = run_command_error_with_stderr(cmd1)
    list1 = str(result1).split('\\n')
    captured1 = list1[-5].split(' ')[0]
    received1 = list1[-4].split(' ')[0]
    dropped1 = list1[-3].split(' ')[0]

    assert int(captured1) != 0 or int(received1) !=0 or int(dropped1) !=0
    client.delete(project)


def test_tcpdump_wget_ingress_svc():
    client = namespace['client']
    cluster = namespace['cluster']

    nodeId = get_workload_nodeId(client, cluster)

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.109.0/24'
    defaultGateway = '172.20.109.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    annotations = {"macvlan.panda.io/ingress": "true"}
    rule = get_svc_ingress_rule(ns.name + ":" + nginx_workload.name, 42)
    ingress_name = random_test_name('ingress-svc')
    ingress = p_client.create_ingress(name=ingress_name,
                                      namespaceId=ns.id,
                                      rules=[rule],
                                      annotations=annotations)
    ingress = wait_for_ingress_to_active(p_client, ingress)
    publicEndpoints = ingress.publicEndpoints
    assert len(publicEndpoints) == 1
    publicEndpoint = publicEndpoints[0]
    ingress_service = publicEndpoint.protocol.lower() + "://" + publicEndpoint.hostname

    apt_update = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get update'
    execute_kubectl_cmd(apt_update, False, False)
    apt_install = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get install -y tcpdump'
    execute_kubectl_cmd(apt_install, False, True)

    busybox_cmd = 'exec ' + busybox_pod['name'] + ' -n ' + ns.name + ' -- wget --spider --timeout=5 ' + ingress_service
    busybox_command = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, busybox_cmd)

    nginx_cmd0 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth0'
    nginx_command0 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd0)

    cmd0 = busybox_command + ' | ' + nginx_command0
    result0 = run_command_error_with_stderr(cmd0)
    list0 = str(result0).split('\\n')
    captured0 = list0[-5].split(' ')[0]
    received0 = list0[-4].split(' ')[0]
    dropped0 = list0[-3].split(' ')[0]

    assert int(captured0) != 0 or int(received0) != 0 or int(dropped0) != 0

    nginx_cmd1 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth1'
    nginx_command1 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd1)

    cmd1 = busybox_command + ' | ' + nginx_command1
    result1 = run_command_error_with_stderr(cmd1)
    list1 = str(result1).split('\\n')
    captured1 = list1[-5].split(' ')[0]
    received1 = list1[-4].split(' ')[0]
    dropped1 = list1[-3].split(' ')[0]

    assert int(captured1) == 0 and int(received1) ==0 and int(dropped1) ==0
    client.delete(project)


def test_tcpdump_wget_ingress_macvlan_svc():
    client = namespace['client']
    cluster = namespace['cluster']

    nodeId = get_workload_nodeId(client, cluster)

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.115.0/24'
    defaultGateway = '172.20.115.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 5, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations, 1, nodeId)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    annotations = {"macvlan.panda.io/ingress": "true"}
    rule = get_svc_ingress_rule(ns.name + ":" + nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    ingress_name = random_test_name('ingress-svc')
    ingress = p_client.create_ingress(name=ingress_name,
                                      namespaceId=ns.id,
                                      rules=[rule],
                                      annotations=annotations)
    ingress = wait_for_ingress_to_active(p_client, ingress)
    publicEndpoints = ingress.publicEndpoints
    assert len(publicEndpoints) == 1
    publicEndpoint = publicEndpoints[0]
    ingress_service = publicEndpoint.protocol.lower() + "://" + publicEndpoint.hostname

    apt_update = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get update'
    execute_kubectl_cmd(apt_update, False, False)
    apt_install = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- apt-get install -y tcpdump'
    execute_kubectl_cmd(apt_install, False, True)

    busybox_cmd = 'exec ' + busybox_pod['name'] + ' -n ' + ns.name + ' -- wget --spider --timeout=5 ' + ingress_service
    busybox_command = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, busybox_cmd)

    nginx_cmd0 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth0'
    nginx_command0 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd0)

    cmd0 = busybox_command + ' | ' + nginx_command0
    result0 = run_command_error_with_stderr(cmd0)
    list0 = str(result0).split('\\n')
    captured0 = list0[-5].split(' ')[0]
    received0 = list0[-4].split(' ')[0]
    dropped0 = list0[-3].split(' ')[0]

    assert int(captured0) == 0 and int(received0) == 0 and int(dropped0) == 0

    nginx_cmd1 = 'exec ' + nginx_pod['name'] + ' -n ' + ns.name + ' -- timeout 20 tcpdump -i eth1'
    nginx_command1 = 'kubectl --kubeconfig {0} {1}'.format(kube_fname, nginx_cmd1)

    cmd1 = busybox_command + ' | ' + nginx_command1
    result1 = run_command_error_with_stderr(cmd1)
    list1 = str(result1).split('\\n')
    captured1 = list1[-5].split(' ')[0]
    received1 = list1[-4].split(' ')[0]
    dropped1 = list1[-3].split(' ')[0]

    assert int(captured1) != 0 or int(received1) !=0 or int(dropped1) !=0
    client.delete(project)


def test_macvlan_wl_with_portmapping():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.110.0/24'
    defaultGateway = '172.20.110.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    ports = [{"containerPort": 80, "hostPort": 0, "type": "containerPort", "kind": "NodePort", "protocol": "TCP"}]
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1, None, ports)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations, 1, None, ports)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    nslookup_nodeport_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + '-nodeport')
    assert nslookup_nodeport_result == 0

    wget_nodeport_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + '-nodeport')
    assert wget_nodeport_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    service_cmd = "get service -n " + ns['name'] + " " + busybox_workload.name + MACVLAN_SERVICE_SUFFIX
    result = execute_kubectl_cmd_with_code(service_cmd, json_out=True, stderr=False, stderrcode=False)
    ports = result['spec']['ports']
    assert len(ports) == 1
    port = ports[0]
    assert port['port'] == 80
    assert port['targetPort'] == 80

    client.delete(project)


def test_macvlan_wl_update_portmapping():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.111.0/24'
    defaultGateway = '172.20.111.1'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway,headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    ports1 = [{"containerPort": 80, "hostPort": 0, "type": "containerPort", "kind": "NodePort", "protocol": "TCP"}]
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations, 1, None, ports1)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    service_cmd = "get service -n " + ns['name'] + " " + workload.name + MACVLAN_SERVICE_SUFFIX
    result = execute_kubectl_cmd_with_code(service_cmd, json_out=True, stderr=False, stderrcode=False)
    ports = result['spec']['ports']
    assert len(ports) == 1
    port = ports[0]
    assert port['port'] == 80
    assert port['targetPort'] == 80

    cons = workload.containers
    assert len(cons) > 0
    assert len(cons[0].ports) > 0
    cons[0].ports[0].containerPort = 8088
    p_client.update(workload, containers=cons, annotations=annotations)
    time.sleep(1)
    wait_for_pods_in_workload(p_client,workload,1)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    result = execute_kubectl_cmd_with_code(service_cmd, json_out=True, stderr=False, stderrcode=False)
    ports = result['spec']['ports']
    assert len(ports) == 1
    port = ports[0]
    assert port['port'] == 8088
    assert port['targetPort'] == 8088

    client.delete(project)


#test macvlan rbac
def test_cluster_owner():
    client = namespace['client']
    cluster = namespace['cluster']

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    cluster_owner_user, cluster_owner_token = create_user(RANCHER_AUTH_URL, client, random_test_name('cluster-owner'), password,
                                                          'user')
    cluster_owner_headers = {"cookie": "R_SESS=" + cluster_owner_token}
    assign_members_to_cluster(client, cluster_owner_user, cluster, 'cluster-owner')
    p_client = get_project_client_for_token(project, cluster_owner_token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.150.0/24'
    defaultGateway = '172.20.150.1'
    create_subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '', [],
                                            [], {}, 0, defaultGateway, cluster_owner_headers)

    list_subnet = list_macvlansubnets(cluster, projectId.replace(":", "-"), cluster_owner_headers)
    assert list_subnet.status_code == 200
    assert len(list_subnet.json()['items']) == 1
    assert list_subnet.json()['items'][0]['metadata']['name'] == subnet_name

    ranges = [{"rangeStart": CIDR_PREFIX + "150.10", "rangeEnd": CIDR_PREFIX + "150.19"}]
    create_subnet['spec']['ranges'] = ranges
    update_subnet = validate_update_macvlan_subnet(create_subnet, ranges, '', '', cluster_owner_headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, update_subnet)

    validate_delete_macvlan_subnet(update_subnet, cluster_owner_headers)

    client.delete(project)


def test_cluster_member():
    client = namespace['client']
    cluster = namespace['cluster']

    cluster_member_user, cluster_member_token = create_user(RANCHER_AUTH_URL, client, random_test_name('cluster-member'), password,
                                                            'user')
    cluster_member_headers = {"cookie": "R_SESS=" + cluster_member_token}

    assign_members_to_cluster(client, cluster_member_user, cluster, 'cluster-member')

    cidr = '172.20.151.0/24'
    defaultGateway = '172.20.151.1'
    create_r = create_macvlansubnet(cluster, random_test_name('vlan'), '', DEFAULT_MASTER, 0, cidr, '',
                                                   [], [], {}, 0, cluster_member_headers)
    assert create_r.status_code == 403

    subnet_name = random_test_name('vlan')
    subnet = validate_create_macvlan_subnet(subnet_name, '', DEFAULT_MASTER, 0, cidr, '',
                                            [], [], {}, 0, defaultGateway,headers)

    list_subnet = list_macvlansubnets(cluster, '%2C', cluster_member_headers)
    assert list_subnet.status_code == 200
    assert len(list_subnet.json()['items']) > 0


    routes = [{"dst": CIDR_PREFIX + "199.0/30", "iface": "eth1"}]
    subnet['spec']['routes'] = routes
    update_r = update_macvlansubnet(cluster, subnet, cluster_member_headers)
    assert update_r.status_code == 403

    delete_r = delete_macvlansubnet(cluster, subnet['metadata']['name'], cluster_member_headers)
    assert delete_r.status_code == 403

    delete_macvlansubnet(cluster,subnet_name,headers)


def test_project_owner():
    client = namespace['client']
    cluster = namespace['cluster']

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    project_owner_user, project_owner_token = create_user(RANCHER_AUTH_URL, client, random_test_name('project-owner'), password,
                                                            'user')
    project_owner_headers = {"cookie": "R_SESS=" + project_owner_token}
    assign_members_to_project(client, project_owner_user, project, 'project-owner')
    p_client = get_project_client_for_token(project, project_owner_token)

    cidr = '172.20.152.0/24'
    defaultGateway = '172.20.152.1'
    create_r = create_macvlansubnet(cluster, random_test_name('vlan'), '', DEFAULT_MASTER, 0, cidr, '',
                                    [], [], {}, 0, project_owner_headers)
    assert create_r.status_code == 403

    subnet = validate_create_macvlan_subnet(random_test_name('vlan'), project.id.replace(":","-"), DEFAULT_MASTER, 0, cidr, '',
                                    [], [], {}, 0, defaultGateway,headers)

    list_subnet = list_macvlansubnets(cluster, project.id.replace(":","-"), project_owner_headers)
    assert list_subnet.status_code == 200
    assert len(list_subnet.json()['items']) > 0

    annotations = get_workload_macvlan('auto', 'auto', subnet['metadata']['name'])
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)
    p_client.delete(workload)

    routes = [{"dst": CIDR_PREFIX + "199.0/30", "iface": "eth1"}]
    subnet['spec']['routes'] = routes
    update_r =  update_macvlansubnet(cluster, subnet, project_owner_headers)
    assert update_r.status_code == 403

    delete_r = delete_macvlansubnet(cluster, subnet['metadata']['name'], project_owner_headers)
    assert delete_r.status_code == 403

    client.delete(project)


def test_project_member():
    client = namespace['client']
    cluster = namespace['cluster']

    project, ns = create_project_and_ns_byClient(client, token, cluster)
    project_member_user, project_member_token = create_user(RANCHER_AUTH_URL, client, random_test_name('project-memter'), password, 'user')
    project_member_headers = {"cookie": "R_SESS=" + project_member_token}
    assign_members_to_project(client, project_member_user, project, 'project-member')
    p_client = get_project_client_for_token(project, project_member_token)

    cidr = '172.20.153.0/24'
    defaultGateway = '172.20.153.1'
    create_r = create_macvlansubnet(cluster, random_test_name('vlan'), '', DEFAULT_MASTER, 0, cidr, '',
                                    [], [], {}, 0,  project_member_headers)
    assert create_r.status_code == 403
    subnet = validate_create_macvlan_subnet(random_test_name('vlan'), project.id.replace(":", "-"), DEFAULT_MASTER, 0, cidr, '',
                                            [], [], {}, 0, defaultGateway,headers)

    list_subnet = list_macvlansubnets(cluster, project.id.replace(":", "-"), project_member_headers)
    assert list_subnet.status_code == 200
    assert len(list_subnet.json()['items']) > 0

    annotations = get_workload_macvlan('auto', 'auto', subnet['metadata']['name'])
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)
    p_client.delete(workload)

    routes = [{"dst": CIDR_PREFIX + "199.0/30", "iface": "eth1"}]
    subnet['spec']['routes'] = routes
    update_r = update_macvlansubnet(cluster, subnet, project_member_headers)
    assert update_r.status_code == 403

    delete_r = delete_macvlansubnet(cluster, subnet['metadata']['name'], project_member_headers)
    assert delete_r.status_code == 403

    client.delete(project)


#test macvlan ipv6
def test_macvlan_ipv6_pod():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.150.0/24'
    gateway = '172.20.150.10'
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 1, 2)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    validate_macvlan_pod_support_ipv6(pod, ns, cidr)

    client.delete(project)
    os.remove(yaml)


def test_macvlan_ipv6_ping_default():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.151.0/24'
    gateway = '172.20.151.1'
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet, 1, 2)

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet, 1, 2)

    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns, 2)
    assert ping_result == 0

    client.delete(project)
    os.remove(yaml)


def test_macvlan_ipv6_ping_routes():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.152.0/24'
    gateway = '172.20.152.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/30", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "31.0/30", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "32.0/30", "gw": CIDR_PREFIX + "152.11", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "33.0/30", "iface": "eth1"}]
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway, [], routes)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet, 1, 2)

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet, 1, 2)

    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns, 2)
    assert ping_result == 0

    client.delete(project)
    os.remove(yaml)


def test_macvlan_ipv6_ping_podDefaultGateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.153.0/24'
    gateway = '172.20.153.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    routes =  [{"dst": "10.42.0.0/16", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": "10.0.2.0/24", "gw": "169.254.1.1", "iface": "eth0"}]
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway, [], routes, podDefaultGateway)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet, 1, 2)

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet, 1, 2)

    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns, 2)
    assert ping_result == 0

    client.delete(project)
    os.remove(yaml)


def test_macvlan_ipv6_ping_route_podDefaultGateway():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.154.0/24'
    gateway = '172.20.154.1'
    podDefaultGateway = {"enable": True, "serviceCidr": "10.43.0.0/16"}
    routes = [{"dst": "10.42.0.0/16", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": "10.0.2.0/24", "gw": "169.254.1.1", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "10.0/24", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "11.0/24", "gw": CIDR_PREFIX + "154.11", "iface": "eth1"},
              {"dst": CIDR_PREFIX + "12.0/24", "iface": "eth0"},
              {"dst": CIDR_PREFIX + "13.0/24", "gw": "169.254.1.1", "iface": "eth0"}]
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway, [], routes, podDefaultGateway)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet, 1, 2)

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet, 1, 2)

    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns, 2)
    assert ping_result == 0

    client.delete(project)
    os.remove(yaml)


def test_macvlan_ipv6_ping_vlan():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name1 = random_test_name('busybox')
    subnet_name2 = random_test_name('nginx')
    cidr = '172.20.155.0/24'
    gateway = '172.20.155.1'
    yaml1 = create_macvlan_subnet_ipv6_yaml(subnet_name1, projectId.replace(":", "-"), 'ens4', cidr, 2, gateway)
    cmd1 = 'apply -f ' + yaml1
    execute_kubectl_cmd(cmd1, False, False)
    time.sleep(.5)
    subnet1 = get_macvlansubnet(subnet_name1)

    yaml2 = create_macvlan_subnet_ipv6_yaml(subnet_name2, projectId.replace(":", "-"), 'ens4', cidr, 3, gateway)
    cmd2 = 'apply -f ' + yaml2
    execute_kubectl_cmd(cmd2, False, False)
    time.sleep(.5)
    subnet2 = get_macvlansubnet(subnet_name2)

    busybox_annotations = get_workload_macvlan('172.20.155.10', 'auto', subnet_name1)
    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, busybox_annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet1, 1, 2)

    nginx_annotations = get_workload_macvlan('172.20.155.20', 'auto', subnet_name2)
    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, nginx_annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet2, 1, 2)

    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]

    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 1

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns, 2)
    assert ping_result == 1

    client.delete(project)
    os.remove(yaml1)
    os.remove(yaml2)


def test_delete_subnet_with_pod():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.156.0/24'
    gateway = '172.20.156.100'
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(':', "-"), DEFAULT_MASTER, 0, cidr, gateway,
                                            [], [], {}, 0, '', headers)

    annotations = get_workload_macvlan('auto', 'auto', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)

    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet)

    validate_delete_macvlan_subnet(subnet)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    assert pods[0]["status"]["phase"] == "Running"

    cmd = 'get macvlanip -n ' + ns.name + ' -l workload.user.cattle.io/workloadselector=deployment-' + ns.name + '-' +workload['name']
    result = execute_kubectl_cmd_with_code(cmd, json_out=False, stderr=False, stderrcode=True)
    assert result == 0

    client.delete(project)


@pytest.mark.skip
def test_macvlan_route_eth0_gw_in_cidr():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = CIDR_PREFIX + '157.0/24'
    defaultGateway = CIDR_PREFIX + '157.1'
    routes = [{"dst": CIDR_PREFIX + "30.0/24", "gw": CIDR_PREFIX + "157.99", "iface": "eth0"}]
    subnet = validate_create_macvlan_subnet(subnet_name, projectId.replace(":", "-"), "ens4", 0, cidr, '',
                                            [], routes, {}, 0, defaultGateway,headers)
    annotations = get_workload_macvlan('auto', 'auto', subnet_name)

    busybox_workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, busybox_workload, 'deployment', ns, subnet)
    busybox_pods = p_client.list_pod(workloadId=busybox_workload.id).data
    assert len(busybox_pods) == 1
    busybox_pod = busybox_pods[0]
    check_pod_route(busybox_pod['name'], ns['name'], subnet['spec'])

    nginx_workload = create_deployment_wl(p_client, ns, NGINX_IMAGE, annotations)
    validate_use_macvlan(p_client, nginx_workload, 'deployment', ns, subnet)
    nginx_pods = p_client.list_pod(workloadId=nginx_workload.id).data
    assert len(nginx_pods) == 1
    nginx_pod = nginx_pods[0]

    nslookup_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name)
    assert nslookup_result == 0

    wget_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                nginx_workload.name)
    assert wget_result == 0

    nslookup_macvlan_result = validate_macvlan_service_nslookup(busybox_pod['name'], ns, ns,
                                                                nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert nslookup_macvlan_result == 0

    wget_macvlan_result = validate_macvlan_service_wget(busybox_pod['name'], ns, ns,
                                                        nginx_workload.name + MACVLAN_SERVICE_SUFFIX)
    assert wget_macvlan_result == 0

    ping_result = validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns)
    assert ping_result == 0

    client.delete(project)


def test_macvlan_ipv6_spec():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    projectId = project.id

    subnet_name = random_test_name('vlan')
    cidr = '172.20.158.0/24'
    gateway = '172.20.158.10'
    yaml = create_macvlan_subnet_ipv6_yaml(subnet_name, projectId.replace(":", "-"), 'ens4', cidr, 0, gateway)
    cmd = 'apply -f ' + yaml
    execute_kubectl_cmd(cmd, False, False)
    time.sleep(.5)
    subnet = get_macvlansubnet(subnet_name)

    annotations = get_workload_macvlan('172.20.158.21', '0a:10:11:0f:1a:1b', subnet_name)
    workload = create_deployment_wl(p_client, ns, BUSYBOX_IMAGE, annotations)
    validate_use_macvlan(p_client, workload, 'deployment', ns, subnet, 1, 2)

    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == 1
    pod = pods[0]

    validate_macvlan_pod_support_ipv6(pod, ns, cidr)

    client.delete(project)
    os.remove(yaml)


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
                    + " --etcd --controlplane --worker --address " + CIDR_PREFIX + "115.7" \
                    + num.__str__() + " --internal-address " + CIDR_PREFIX + "115.7" + num.__str__()
        cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"" +nodeCommand +" \" C-m"
        ssh_cmd= "ssh -o StrictHostKeyChecking=no -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + cmd + " \'"
        login_cmd="sudo tmux send-keys -t " + "kvm:" + num.__radd__(1).__str__() +" \"ubuntu\" C-m"
        login_ssh_cmd= "ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=20 -i /src/rancher-validation/.ssh/id_rsa -l jenkins " + RANCHER_SERVER_URL.split(":",2)[1][2:]  + " \' " + login_cmd + " \'"
        run_command(login_ssh_cmd)
        run_command(login_ssh_cmd)
        result=run_command(ssh_cmd)
        wait_for_nodes_to_become_active(client, cluster, exception_list=[])
        time.sleep(10)

    cluster,project,ns,p_client = validate_macvlan_cluster(client, cluster,token, check_intermediate_state=True,
                                        skipIngresscheck=True,intermediate_state="updating",skipNodecheck=True)

    #name,project,master,vlan,cidr,gateway,ranges,routes,namespace
    cidr = CIDR_PREFIX + "10.0/24"
    defaultGateway = CIDR_PREFIX + "10.1"
    subnet_name = random_test_name("test-macvlan")
    validate_create_macvlan_subnet(subnet_name,project.id,DEFAULT_MASTER,0,cidr,"",[],[],{},0,defaultGateway,headers)

    # same subnet/same ns
    nginx_wl,nginx_pods,nginx_kind,nginx_ips,nginx_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,NGINX_IMAGE)
    busybox_wl,busybox_pods,busybox_kind,busybox_ips,busybox_macs = create_macvlan_workload(client,cluster,p_client,ns,"auto","auto",subnet_name,cidr,BUSYBOX_IMAGE)
    if (nginx_pods != None) and (busybox_pods != None):
        validate_nslookup_wget(nginx_kind, busybox_kind, nginx_pods, busybox_pods, subnet_name, subnet_name,
                                   ns, ns, nginx_wl,nginx_ips,nginx_macs,busybox_ips,busybox_macs)


def get_admin_token(RANCHER_SERVER_URL):
    """Returns a ManagementContext for the default global admin user."""
    CATTLE_AUTH_URL = \
        RANCHER_SERVER_URL + "/v3-public/localproviders/local?action=login"
    r = requests.post(CATTLE_AUTH_URL, json={
        'username': 'admin',
        'password': 'admin',
        'responseType': 'json',
    }, verify=False)
    token = r.json()['token']
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


def validate_create_macvlan_subnet(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway='', headers=headers):
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

    create_r = create_macvlansubnet(cluster,name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,headers)
    assert create_r.status_code == 201

    time.sleep(2)

    detail_r = detail_macvlansubnet(cluster, name,headers)
    assert detail_r.status_code == 200
    diff_create_subnet(detail_r.json(), project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway)

    subnet = get_macvlansubnet(name)
    diff_create_subnet(subnet, project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse,defaultGateway)
    return subnet


def create_macvlansubnet(cluster,name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway,ipDelayReuse, headers=headers):

    create_url = RANCHER_SERVER_URL + '/k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets'

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
    return create_r


def delete_macvlansubnet(cluster, subnet_name, headers=headers):
    delete_url = RANCHER_SERVER_URL + '/k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    delete_r = requests.delete(delete_url, verify=False, headers=headers)
    return delete_r


def update_macvlansubnet(cluster, subnet, headers=headers):
    update_url = RANCHER_SERVER_URL + '/k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet['metadata']['name']
    update_r = requests.put(update_url, json.dumps(subnet), verify=False, headers=headers)
    return update_r


def detail_macvlansubnet(cluster, subnet_name, headers=headers):
    detail_url = RANCHER_SERVER_URL + '/k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets/' + subnet_name
    detail_r = requests.get(detail_url, verify=False, headers=headers)
    return detail_r


def list_macvlansubnets(cluster, projects, headers=headers):
    list_url = RANCHER_SERVER_URL + '/k8s/clusters/' + cluster.id + '/apis/macvlan.cluster.cattle.io/v1/namespaces/kube-system/macvlansubnets?limit=50&labelSelector=project%20in%20(' + projects + ')'
    list_r = requests.get(list_url, verify=False, headers=headers)
    return list_r


def validate_update_macvlan_subnet(subnet, ranges='', routes='', podDefaultGateway='', headers=headers):
    cluster = namespace['cluster']
    subnet_name = subnet['metadata']['name']
    update_r = update_macvlansubnet(cluster, subnet, headers)
    assert update_r.status_code == 200

    detail_r = detail_macvlansubnet(cluster, subnet_name, headers)
    assert detail_r.status_code == 200
    diff_update_subnet(detail_r.json(), ranges, routes, podDefaultGateway)

    subnet = get_macvlansubnet(subnet_name)
    diff_update_subnet(subnet, ranges, routes, podDefaultGateway)
    return subnet


def validate_delete_macvlan_subnet(subnet, headers=headers):
    cluster = namespace['cluster']
    subnet_name = subnet['metadata']['name']

    delete_r = delete_macvlansubnet(cluster, subnet_name, headers)
    assert delete_r.status_code == 200

    detail_r = detail_macvlansubnet(cluster, subnet_name, headers)
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


def validate_use_macvlan(p_client, workload, type, ns, subnet, pod_count=1, ip_count=1):
    validate_workload(p_client, workload, type, ns.name, pod_count)

    ips = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/ip"])
    macs = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/mac"])

    kind=get_macvlan_ip_mac_kind(ips,macs)

    pods = p_client.list_pod(workloadId=workload.id).data

    if type != 'cronJob' and type != 'job':
        validate_macvlan_service(ns.name, workload)

    ip_list = validate_macvlan_pods(pods, ns, subnet, kind, ips, macs, ip_count)

    return ip_list


def validate_unavailable_macvlan_pod(p_client, workload, ns, reason, msg, timeout=10):
    pods = p_client.list_pod(workloadId=workload.id).data
    for pod in pods:
        diff_unavailable_macvlan_pod(p_client, ns, pod, reason, msg, timeout)


def diff_unavailable_macvlan_pod(p_client, ns, pod, reason, msg, timeout=10):
    assert pod["status"]["phase"] != "running"
    start = time.time()
    pods = p_client.list_pod(uuid=pod.uuid).data
    assert len(pods) == 1
    p = pods[0]
    events = []
    while p.state != "running":
        if time.time() - start > timeout:
            events = get_events(ns['name'], pod.name, 'Pod')
            break
        pods = p_client.list_pod(uuid=pod.uuid).data
        assert len(pods) == 1
        p = pods[0]
    has = 1
    for event in events['items']:
        if event["reason"] == reason:
            assert msg in event["message"]
            has = 0
            break
    assert has == 0


def validate_macvlan_pods(pods, ns, subnet, kind, ips, macs, ip_count=1):
    ip_list = []
    for pod in pods:
        assert pod["status"]["phase"] == "Running"
        annotations = pod["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
        annotations.replace("\n","")
        annotations=json.loads(annotations)
        for annotation in annotations:
            if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
                assert len(annotation["ips"]) == ip_count
                ip = annotation["ips"][0]
                ips, macs = validate_ip_mac_by_kind(ip, annotation["mac"], ips, macs, kind, subnet['spec']["cidr"])
                if len(subnet['spec']["ranges"]) != 0 :
                    result = check_ip_in_ranges(ip,subnet['spec']["ranges"])
                    assert result
                ip_list.append(ip)
        ip_result=validate_macvlanIP(ns, pod)
        assert ip_result == 0
    return ip_list


def wait_for_macvlanip_delete(ns, pod, timeout=DEFAULT_TIMEOUT):
    result = validate_macvlanIP(ns, pod)
    start = time.time()
    while result != 1:
        if time.time() - start > timeout:
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        result = validate_macvlanIP(ns, pod)
    return result


def create_workload_http(project, ns, img, annotations={}, scale=1, node=None):
    name = random_test_name("http")
    con = [{
        "initContainer": False,
        "restartCount": 0,
        "stdin": True,
        "stdinOnce": False,
        "tty": True,
        "type": "container",
        "privileged": False,
        "allowPrivilegeEscalation": False,
        "readOnly": False,
        "runAsNonRoot": False,
        "namespaceId": ns.name,
        "imagePullPolicy": "Always",
        "environmentFrom": [],
        "resources": {
            "requests": {},
            "limits": {}
        },
        "capAdd": [],
        "capDrop": [],
        "image": img,
        "livenessProbe": None,
        "name": name,
        "volumeMounts": []
    }]
    dnsConfig = {"options": []}
    deploymentConfig = {"minReadySeconds": 0, "type": "deploymentConfig", "revisionHistoryLimit": 10,
                        "strategy": "RollingUpdate", "maxSurge": 0, "maxUnavailable": 1}
    scheduling = {"node": {}}
    if node != None:
        scheduling = {"node": {"nodeId": node}}

    url = RANCHER_API_URL.replace('//v3','/v3') + '/projects/' + project + '/workload'
    json = {
        "hostIPC": False,
        "hostNetwork": False,
        "hostPID": False,
        "paused": False,
        "type": "workload",
        "namespaceId": ns.name,
        "scale": 1,
        "dnsPolicy": "ClusterFirst",
        "restartPolicy": "Always",
        "labels": {},
        "containers": con,
        "scheduling": scheduling,
        "deploymentConfig": deploymentConfig,
        "hostAliases": [],
        "dnsConfig": dnsConfig,
        "annotations": annotations,
        "name": name,
        "volumes": []
    }
    r = requests.post(url, json=json, verify=False, headers=headers)
    return r


def get_wl_ingress_rule(workloadId, port=80):
    rule = {
            "host": "xip.io",
            "new": True,
            "paths": [
                {
                    "path": "",
                    "workloadIds": [ workloadId ],
                    "targetPort": port
                }
            ]
        }

    return rule


def get_svc_ingress_rule(serviceId, port=43):
    rule = {
            "host": "xip.io",
            "new": True,
            "paths": [
                {
                    "path": "",
                    "serviceId": serviceId,
                    "targetPort": port
                }
            ]
        }
    return rule


def validate_macvlan_pod_support_ipv6(pod, ns, cidr):

    #test pod enable ipv6
    lo_ipv6_cmd = 'exec ' + pod['name'] + ' -n ' + ns.name + ' -- sysctl net.ipv6.conf.lo.disable_ipv6'
    lo_ipv6_result = execute_kubectl_cmd(lo_ipv6_cmd, False, False)
    assert 'net.ipv6.conf.lo.disable_ipv6 = 0' == lo_ipv6_result.strip('\n')

    eth1_ipv6_cmd = 'exec ' + pod['name'] + ' -n ' + ns.name + ' -- sysctl net.ipv6.conf.eth1.disable_ipv6'
    eth1_ipv6_result = execute_kubectl_cmd(eth1_ipv6_cmd, False, False)
    assert 'net.ipv6.conf.eth1.disable_ipv6 = 0' == eth1_ipv6_result.strip('\n')

    #test pod annotations ipv4/ipv6
    annotations = pod['annotations']['k8s.v1.cni.cncf.io/networks-status']
    annotations.replace("\n", "")
    annotations = json.loads(annotations)
    ips = []
    for annotation in annotations:
        if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
            ips = annotation["ips"]
    assert len(ips) == 2

    ipv6 = v4_to_v6(ips[0], cidr)
    assert str(ipv6.ipv6().ip) == ips[1]

    #test pod ip settings
    ipv6_addr_cmd = 'exec ' + pod['name'] + ' -n ' + ns.name + ' -- ip -6 addr show dev eth1'
    ipv6_addr_result = execute_kubectl_cmd(ipv6_addr_cmd, False, False)
    assert 'inet6 ' + str(ipv6.ipv6()) + ' scope global' in ipv6_addr_result

    ipv6_route_cmd = 'exec ' + pod['name'] + ' -n ' + ns.name + ' -- ip -6 route'
    ipv6_route_result = execute_kubectl_cmd(ipv6_route_cmd, False, False)
    assert str(ipv6.cidr) + ' dev eth1  metric 256' in ipv6_route_result


def get_workload_nodeId(client, cluster):
    nodes = client.list_node(clusterId=cluster.id).data
    try:
        assert len(nodes) >= 2
    except AssertionError as aeeor:
        print("cluster node less than 2, can't verify macvlan ingress", aeeor.__str__())
        return

    systems = client.list_project(name="System", clusterId=cluster.id).data
    assert len(systems) == 1
    system = systems[0]
    p_client = get_project_client_for_token(system, token)

    controllers = p_client.list_workload(name='nginx-ingress-controller').data
    assert len(controllers) == 1
    controller = controllers[0]
    ingress_nodeId = controller.scheduling.node.nodeId
    try:
        assert ingress_nodeId != None
    except AssertionError:
        print("nginx ingress controller pod 1 per node, can't verify macvlan ingress")
        return

    nodeId = ""
    for node in nodes:
        if node.id != ingress_nodeId:
            nodeId = node.id
            break
    assert nodeId != ""

    return nodeId


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


