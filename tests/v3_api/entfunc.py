from .common import *  # NOQA
from time import gmtime
from netaddr import *
import yaml


DEFAULT_NODEPOOL_TIMEOUT = 300
TEST_INTERNAL_IMAGE = os.environ.get('RANCHER_TEST_IMAGE', "busybox:musl")
TEST_INGRESS_TARGET_PORT = os.environ.get('RANCHER_TEST_INGRESS_TARGET_PORT', "8088")
MACVLAN_SERVICE_SUFFIX="-macvlan"

def get_admin_client_byToken(url, token):
    return rancher.Client(url=url, token=token, verify=False)

def validate_internal_cluster(client, cluster, intermediate_state="provisioning",
    check_intermediate_state=True, skipIngresscheck=False,
    nodes_not_in_active_state=[], k8s_version=""):
    cluster = validate_nodedrivers_cluster(
        client, cluster,
        check_intermediate_state=check_intermediate_state,
        intermediate_state=intermediate_state,
        nodes_not_in_active_state=nodes_not_in_active_state)
    # Create Daemon set workload and have an Ingress with Workload
    # rule pointing to this daemonset
    create_kubeconfig(cluster)
    if k8s_version != "":
        check_cluster_version(cluster, k8s_version)
    if hasattr(cluster, 'rancherKubernetesEngineConfig'):
        check_cluster_state(len(get_role_nodes(cluster, "etcd")))
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("default")
    con = [{"name": "test1",
            "image": TEST_INTERNAL_IMAGE, "tty": "true"}]
    print(con)
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        daemonSetConfig={})
    validate_workload(p_client, workload, "daemonSet", ns.name,
                      len(get_schedulable_nodes(cluster)))
    if not skipIngresscheck:
        create_internal_ingress(workload,p_client,name,ns,cluster)
    return cluster


def create_internal_ingress(workload,p_client,name,ns,cluster):
    rule = {"host": "xip.io",
            "paths":
                [{"workloadIds": [workload.id], "targetPort": TEST_INGRESS_TARGET_PORT}]}
    ingress = p_client.create_ingress(name=name,
                                      namespaceId=ns.id,
                                      rules=[rule])
    wait_for_ingress_to_active(p_client, ingress)
    validate_ingress(p_client, cluster, [workload],ingress)


def validate_nodedrivers_cluster(client, cluster,
                               check_intermediate_state=True,
                               intermediate_state="provisioning",
                               nodes_not_in_active_state=[]):
        if check_intermediate_state:
            cluster = wait_for_condition(
                client, cluster,
                lambda x: x.state == intermediate_state,
                lambda x: 'State is: ' + x.state,
                timeout=MACHINE_TIMEOUT)
            assert cluster.state == intermediate_state
        print("check cluster state provisioning success ")
        #nodeDriver state validate
        wait_for_nodes(client, cluster,exception_list=nodes_not_in_active_state)
        #cluster state validate
        cluster = wait_for_condition(
            client, cluster,
            lambda x: x.state == "active",
            lambda x: 'State is: ' + x.state,
            timeout=MACHINE_TIMEOUT)
        assert cluster.state == "active"

        return cluster


def wait_for_nodes(client, cluster, exception_list=[],
                                    retry_count=0):
    nodes = client.list_node(clusterId=cluster.id).data
    print("cluster nodes",nodes)
    node_auto_deleted = False
    for node in nodes:
        if node.requestedHostname not in exception_list:
            node = wait_for_node_status(client,node,"registering")
            print("check node state registering success",nodes)
            time.sleep(5)
            node = wait_for_node_status(client, node, "active")
            print("check node state active success",nodes)
            if node is None:
                print("Need to re-evalauate new node list")
                node_auto_deleted = True
                retry_count += 1
                print("Retry Count:" + str(retry_count))
    if node_auto_deleted and retry_count < 5:
        wait_for_nodes_to_become_active(client, cluster, exception_list,
                                        retry_count)


def wait_for_nodePool_delete(client,nodeTemplate,timeout = DEFAULT_NODEPOOL_TIMEOUT):
    start = time.time()
    nodePools = client.list_nodePool(nodeTemplateId=nodeTemplate)
    while nodePools.data != []:
        if time.time() - start > timeout:
            exceptionMsg = 'Timeout waiting for list nodePool : nodeTemplate = ' + nodeTemplate + \
                           ' to satisfy condition: '
            raise Exception(exceptionMsg)
        time.sleep(.5)
        nodePools = client.list_nodePool(nodeTemplateId=nodeTemplate)
    return nodePools.data


def get_status(url):
    r = requests.get(url, allow_redirects = False)
    return r.status_code

# ------ macvlan ------
def get_macvlansubnet(subnet, json_out=True, stderr=False, stderrcode=False):
    cmd = "get macvlansubnet -n kube-system " + subnet
    exec_result = execute_kubectl_cmd_with_code(cmd, json_out, stderr, stderrcode)
    return exec_result

def create_macvlan_workload(client,cluster,p_client,ns,ip,mac,subnet,cidr,img,scale=1,node=None):
    annotations={}
    if ip != "" or mac != "" or subnet != "":
        annotations=get_workload_macvlan(ip,mac,subnet)

    name=random_test_name("test-macvlan-workload")
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
    dnsConfig={"options":[]}
    deploymentConfig={"minReadySeconds":0,"type":"deploymentConfig","revisionHistoryLimit":10,"strategy":"RollingUpdate","maxSurge":0,"maxUnavailable":1}
    scheduling = {"node":{}}
    if node != None:
        scheduling={"node": {"nodeId": node}}
    print("scheduling node : ",scheduling)
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        annotations=annotations,
                                        hostAliases=[],
                                        dnsConfig=dnsConfig,
                                        deploymentConfig=deploymentConfig,
                                        scheduling=scheduling,
                                        scale=scale)

    print(workload)
    pods,kind,ips,macs = validate_macvlan_workload(p_client, workload, "deployment", ns.name,scale,cidr)
    return workload,pods,kind,ips,macs

def get_workload_macvlan(ip,mac,subnet):
    '''
    :param ip: xxx.xxx.xxx.xxx-xxx.xxx.xxx.xxx / auto
    :param mac: xx:xx:xx:xx:xx:xx-xx:xx:xx:xx:xx:xx / auto
    :param subnet: macvlansubnet name
    :return:
    '''
    networks="[{\"name\":\"static-macvlan-cni-attach\",\"interface\":\"eth1\"}]"
    macvlan_annotations={
        "k8s.v1.cni.cncf.io/networks": networks,
        "macvlan.pandaria.cattle.io/ip": ip,
        "macvlan.pandaria.cattle.io/mac": mac,
        "macvlan.pandaria.cattle.io/subnet": subnet,
        "cattle.io/timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ",gmtime())
    }
    return macvlan_annotations

def validate_macvlan_workload(p_client, workload, type, ns_name, pod_count, wait_for_cron_pods=60):
    '''
    step:
        1. check workload status ;
        2. check pod status ;
        3. check macvlanIP create
        4. check pod ip mac
        5. check pod ping
    :return:
    '''
    time.sleep(20)
    workload = wait_for_wl_to_active(p_client, workload)
    assert workload.state == "active"

    ips = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/ip"])
    macs = split_to_list(workload["annotations"]["macvlan.pandaria.cattle.io/mac"])

    validate_macvlan_service(ns_name,workload)
    # For cronjob, wait for the first pod to get created after
    # scheduled wait time
    if type == "cronJob":
        time.sleep(wait_for_cron_pods)
    pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) == pod_count

    kind=get_macvlan_ip_mac_kind(ips,macs)
    if kind in (10, 11, 12, 13, 14):
        for pod in pods:
            wait_for_pod_to_running(p_client, pod)
        wl_result = execute_kubectl_cmd(
            "get " + type + " " + workload.name + " -n " + ns_name)
        if type == "deployment" or type == "statefulSet":
            assert wl_result["status"]["readyReplicas"] == pod_count
        if type == "daemonSet":
            assert wl_result["status"]["currentNumberScheduled"] == pod_count
        if type == "cronJob":
            assert len(wl_result["status"]["active"]) >= pod_count
            return
        if type == "job":
            assert wl_result["status"]["active"] == pod_count
            return

        for key, value in workload.workloadLabels.items():
            label = key + "=" + value
        get_pods = "get pods -l" + label + " -n " + ns_name
        pods_result = execute_kubectl_cmd(get_pods)
        assert len(pods_result["items"]) == pod_count
        return pods_result,kind,ips,macs
     #todo
    if kind == 16:
        for pod in pods:
            events=validate_macvlan_pod_fail(p_client, pod)
            assert len(events["items"]) > 0
            for event in events:
                if event["reason"] == "MacvlanIPError":
                    assert event["reason"] == "MacvlanIPError"
                    return None,kind,ips,macs

def validate_macvlan_service(ns, workload):

    workload_service = workload["name"]
    selector_service = workload["name"] + MACVLAN_SERVICE_SUFFIX

    validate_service(ns, workload_service)
    time.sleep(1)
    validate_service(ns, selector_service)

def get_macvlan_ip_mac_kind(ipList, macList):
    '''
    :param ipList: wl macvlan ips
    :param macList: wl macvlan mac list
    :return: 0 error type; 10 succ; 11 succ; 12 succ; 13 succ; 14 succ; 15 fail
    '''
    kind=0
    ip_type=type(ipList)
    mac_type=type(macList)
    if ip_type is str and mac_type is str and ipList == "auto" and macList == "auto":
        kind = 10
    if ip_type is str and mac_type is list and ipList == "auto" and len(macList) > 0:
        kind = 11
    if ip_type is list and mac_type is str and macList == "auto" and len(ipList) > 0:
        kind = 12
    if ip_type is list and mac_type is list:
        ip_len=len(ipList)
        mac_len=len(macList)
        if ip_len == 1 and mac_len == 1:
            kind = 13
        if ip_len > 1 or mac_len >1:
            if ip_len == mac_len:
                kind = 14
            if ip_len != mac_len:
                kind = 15
    print(kind)
    return kind

def validate_macvlan_pod_fail(client, pod, ns_name, timeout=DEFAULT_TIMEOUT):
    start = time.time()
    pods = client.list_pod(uuid=pod.uuid).data
    assert len(pods) == 1
    p = pods[0]
    while p.state != "running":
        if time.time() - start > timeout:
            get_events(ns_name, pod.name, "Pod")
            raise AssertionError(
                "Timed out waiting for state to get to active")
        time.sleep(.5)
        pods = client.list_pod(uuid=pod.uuid).data
        assert len(pods) == 1
        p = pods[0]
    return p

def validate_service(ns, service):
    '''
    desc: check service exist
    :param ns: namespace
    :param service: service name
    :return: 0 exist ; 1 not exist
    '''
    service_cmd = "get service -n " + ns + " " + service
    result = execute_kubectl_cmd_with_code(service_cmd, json_out=False, stderr=False, stderrcode=True)
    return result

def get_events(ns_name,object_name,object_kind):
    cmd = "get events -n " + ns_name + " --field-selector=involvedObject.name=" + object_name \
          + ",involvedObject.kind=" + object_kind
    exec_result=execute_kubectl_cmd(cmd, json_out=True)
    return exec_result

def validate_nslookup_wget(nginx_kind, busybox_kind,nginx_pods,busybox_pods,nginx_subnet,busybox_subnet,busybox_ns,nginx_ns,nginx_workload,nginx_ips,nginx_macs,busybox_ips,busybox_macs,node=None):
    validate_wl_pod(nginx_pods,nginx_kind,nginx_subnet,nginx_ns,nginx_ips,nginx_macs)
    ping = nginx_subnet == busybox_subnet
    validate_wl_pod(busybox_pods, busybox_kind, busybox_subnet, busybox_ns, busybox_ips, busybox_macs, nginx_ns, nginx_workload,ping,nginx_pods)

def validate_wl_pod(pods,kind,subnet,busybox_ns,ips,macs,nginx_ns=None,nginx_workload=None,ping=False,nginx_pods=None,node=None):
    print("validate_wl_pod busybox_ns",busybox_ns)
    spec = get_macvlansubnet_info(subnet)
    print("subnet spec:",spec)
    for pod in pods["items"]:
        print("validate_wl_pod pod", pod)
        assert pod["status"]["phase"] == "Running"
        annotations = pod["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
        annotations.replace("\n","")
        annotations=json.loads(annotations)
        for annotation in annotations:
            print("annotation for",annotation)
            a=annotation["name"]
            print(a)
            if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
                print(annotation["ips"])
                assert len(annotation["ips"]) == 1
                ip = annotation["ips"][0]
                ips, macs = validate_ip_mac_by_kind(ip, annotation["mac"], ips, macs, kind, spec["cidr"])
                if len(spec["ranges"]) != 0 :
                    result = check_ip_in_ranges(ip,spec["ranges"])
                    assert result
        ip_result=validate_macvlanIP(busybox_ns,pod['metadata'])
        assert ip_result == 0
        if (nginx_ns != None) and (nginx_workload != None):
            nslookup=validate_macvlan_service_nslookup(pod,busybox_ns,nginx_ns,nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
            if ping:
                assert nslookup == 0
            else:
                assert nslookup == 1
            wget=validate_macvlan_service_wget(pod,busybox_ns,nginx_ns,nginx_workload.name+MACVLAN_SERVICE_SUFFIX)
            if ping:
                assert wget == 0
            else:
                assert wget == 1
                # check Custom Route
            if 'routes' in spec:
                check_pod_route(pod["metadata"]["name"], busybox_ns["name"], spec["routes"])
        if nginx_pods != None:
            print("validate_wl_pod nginx_pods",nginx_pods)
            for nginx_pod in nginx_pods["items"]:
                ip_ping = validate_macvlan_pods_ping(pod,nginx_pod,busybox_ns)
                if ping:
                    assert ip_ping == 0
                else:
                    assert ip_ping == 1
        if node != None:
            cmd = " -- ping -w 5 " + ip
            result = get_kubectl_execCmd_result(pod["metadata"]["name"], busybox_ns["name"], cmd)
            return result

def get_macvlansubnet_info(subnet):
    cmd = "get  macvlansubnet -n kube-system " + subnet
    exec_result = execute_kubectl_cmd_with_code(cmd, json_out=True, stderr=False, stderrcode=False)
    print(exec_result["spec"])
    return exec_result["spec"]

def validate_ip_mac_by_kind(podip, podmac, ipList, macList, kind, cidr):
    '''
    desc : check pod ip in subnet, check ip mac spec
    :param podip:
    :param podmac:
    :param ipList:
    :param macList:
    :param kind: 10 not validate_in_list;11,12,13,14;all validate_ip_in_cidr
    :param cidr:
    :return:
    '''
    validate_ip_in_subnet(podip, cidr)
    if kind == 11 :
        macList=validate_in_list(podmac,macList)
    if kind == 12 :
        ipList=validate_in_list(podip, ipList)
    if kind in (13, 14) :
        ipList=validate_in_list(podip, ipList)
        macList=validate_in_list(podmac,macList)

    return ipList, macList

def check_ip_in_ranges(ip, ip_ranges):
    print("check_ip_in_ranges ip : ",ip)
    print("check_ip_in_ranges ip_ranges : ",ip_ranges)
    result = False
    ip_int=int(ipToBinary(ip), 2)
    for range in ip_ranges:
        start = int(ipToBinary(range["rangeStart"]),2)
        end = int(ipToBinary(range["rangeEnd"]),2)
        if ip_int >= start and ip_int <= end:
            result = True
            return result
    return result

def validate_macvlanIP(ns, pod):
    '''
    desc: check subnet macvlanIP exist
    :param ns: namespace
    :param pod: wl pod
    :return: 0 exist ; 1 not exist
    '''
    print("validate_macvlanIP pod",pod)
    print("validate_macvlanIP ns",ns)
    cmd = "get MacvlanIP -n " + ns["name"] + " " + pod["name"]
    exec_result = execute_kubectl_cmd_with_code(cmd, json_out=False, stderr=False, stderrcode=True)
    return exec_result

def check_pod_route(pod, ns, routes):
    for route in routes:
        dst=route["dst"]
        gw=route["gw"]
        results = get_pod_spec_route(pod,ns,dst)
        print("get_pod_spec_route results : ",results)
        if gw != "" :
            assert gw == results[1]
        mask = exchange_maskint(dst.split("/")[1])
        assert mask == results[2]

def get_pod_spec_route(pod, ns, dst):
    destination = dst.split("/")[0]
    cmd = "exec " + pod + " -n " + ns +" -- route -n | grep " + destination + " | tr -s [:space:]"
    result = execute_kubectl_cmd_with_code(cmd, json_out=False, stderr=False, stderrcode=False)
    result = result.split(" ")
    return result

def validate_macvlan_service_nslookup(pod, busybox_ns, nginx_ns, service):
    '''
    desc: check macvlan service request nslookup
    :param pod: pod
    :param ns: ns
    :param service: wl.name
    :return: 0 success ; 1 fail
    '''
    cmd = " -- nslookup " + service + "." + nginx_ns["name"] +".svc.cluster.local"
    result = get_kubectl_execCmd_result(pod["metadata"]["name"], busybox_ns["name"], cmd)
    return result

def get_kubectl_execCmd_result(type, ns, cmd):
    exec_cmd = "exec " + type + " -n " + ns + cmd
    print("kubectl exec cmd : ", exec_cmd)
    result = execute_kubectl_cmd_with_code(exec_cmd, json_out=False, stderr=False, stderrcode=True)
    print("kubectl exec result : ", result)
    return result

def validate_macvlan_service_wget(pod, busybox_ns, nginx_ns, service):
    '''
    desc: check macvlan service request wget
    :param pod: pod
    :param ns: ns
    :param service: wl.name
    :return: 0 success ; 1 fail
    '''
    cmd = " -- wget --spider --timeout=10 " + service + "." + nginx_ns["name"]
    result = get_kubectl_execCmd_result(pod["metadata"]["name"], busybox_ns["name"], cmd)
    return result

def validate_macvlan_pods_ping(busybox_pod, nginx_pod, ns):
    '''
    desc: check macvlan pod ping
    :param busybox_pod: busybox macvlan pod
    :param nginx_pod:  nginx macvlan pod
    :param ns: namespace
    :return: 0 ping success ; 1 ping fail
    '''
    print("validate_macvlan_pods_ping nginx_pod : ",nginx_pod)
    annotations = nginx_pod["metadata"]["annotations"]["k8s.v1.cni.cncf.io/networks-status"]
    annotations.replace("\n", "")
    annotations = json.loads(annotations)
    for annotation in annotations:
        print("annotation for", annotation)
        a = annotation["name"]
        print(a)
        if (annotation["name"] == "static-macvlan-cni-attach") and (annotation["interface"] == "eth1"):
            print(annotation["ips"])
            assert len(annotation["ips"]) == 1
            ip = annotation["ips"][0]
            cmd = " -- ping -w 5 " + ip
            result = get_kubectl_execCmd_result(busybox_pod["metadata"]["name"], ns["name"], cmd)
            return result

def validate_ip_in_subnet(ip, subnet):
    subnet_list = subnet.split('/')

    networt_add = subnet_list[0]
    network_mask = subnet_list[1]

    ip_num = int(ipToBinary(ip), 2)
    subnet_num = int(ipToBinary(networt_add), 2)
    mask_bin = int(maskToBinary(network_mask), 2)

    assert (ip_num & mask_bin) == (subnet_num & mask_bin)


def validate_macvlan_cluster(client, cluster, token,intermediate_state="provisioning",
    check_intermediate_state=True, skipIngresscheck=False,
    nodes_not_in_active_state=[], k8s_version="",skipNodecheck=False,flannel_service_check=False):
    if skipNodecheck == False:
        cluster = validate_nodedrivers_cluster(
            client, cluster,
            check_intermediate_state=check_intermediate_state,
            intermediate_state=intermediate_state,
            nodes_not_in_active_state=nodes_not_in_active_state)
    else:
        cluster = wait_for_condition(
            client, cluster,
            lambda x: x.state == "active",
            lambda x: 'State is: ' + x.state,
            timeout=MACHINE_TIMEOUT)
        assert cluster.state == "active"
    nodes = client.list_node(clusterId=cluster.id).data
    print("cluster nodes", nodes)
    for node in nodes:
        wait_for_node_status(client, node, "active")
    # Create Daemon set workload and have an Ingress with Workload
    # rule pointing to this daemonset
    create_kubeconfig(cluster)
    projects = client.list_project(name="System",clusterId=cluster.id).data
    assert len(projects) == 1
    project = projects[0]
    p_client = get_project_client_for_token(project, token)

    ###kube-multus-ds-amd64/network-cni-ds-amd64/ network-controller
    validate_wl_byName(p_client, "kube-multus-ds-amd64", "kube-system", "daemonSet")
    validate_wl_byName(p_client, "network-cni-ds-amd64", "kube-system", "daemonSet")
    validate_wl_byName(p_client, "network-controller", "kube-system", "deployment")

    support = validate_support_macvlansubnet()
    assert support == 0
    time.sleep(10)
    if flannel_service_check:
        yaml = validate_macvlan_yaml("kube-flannel-ds-amd64", "ens4")
        assert yaml
    if k8s_version != "":
        check_cluster_version(cluster, k8s_version)
    if hasattr(cluster, 'rancherKubernetesEngineConfig'):
        check_cluster_state(len(get_role_nodes_byClient(client, cluster, "etcd")))
    project, ns = create_project_and_ns_byClient(client, token, cluster)
    p_client = get_project_client_for_token(project, token)
    name = random_test_name("default")
    con = [{"name": "test1",
            "image": TEST_INTERNAL_IMAGE, "tty": "true"}]
    workload = p_client.create_workload(name=name,
                                        containers=con,
                                        namespaceId=ns.id,
                                        daemonSetConfig={})
    validate_workload(p_client, workload, "daemonSet", ns.name,
                      len(get_schedulable_nodes_byClient(client, cluster)))
    if not skipIngresscheck:
        create_internal_ingress(workload,p_client,name,ns,cluster)
    return cluster,project,ns,p_client

def validate_wl_byName(p_client, wl_name, ns_name, type, wait_for_cron_pods=60):
    wl = p_client.list_workload(name=wl_name).data
    assert len(wl) == 1
    wl = wl[0]
    workload = wait_for_wl_to_active(p_client, wl)
    assert workload.state == "active"
    if type == "cronJob":
        time.sleep(wait_for_cron_pods)
    pods = p_client.list_pod(workloadId=workload.id).data
    pod_count = len(pods)
    assert pod_count > 0
    for pod in pods:
        wait_for_pod_to_running(p_client, pod)
    wl_result = execute_kubectl_cmd(
        "get " + type + " " + workload.name + " -n " + ns_name)
    if type == "deployment" or type == "statefulSet":
        assert wl_result["status"]["readyReplicas"] == pod_count
    if type == "daemonSet":
        assert wl_result["status"]["currentNumberScheduled"] == pod_count
    if type == "cronJob":
        assert len(wl_result["status"]["active"]) >= pod_count
        return
    label = ""
    for key, value in workload.workloadLabels.items():
        label = label + key + "=" + value + ","
    get_pods = "get pods -l" + label[:-1] + " -n " + ns_name
    pods_result = execute_kubectl_cmd(get_pods)
    assert len(pods_result["items"]) == pod_count
    for pod in pods_result["items"]:
        assert pod["status"]["phase"] == "Running"
    return pods_result["items"]


def validate_macvlan_yaml(ds, master):
    '''
    desc: check macvlan yaml with iface
    :param ds: flannel / canal wl name
    :param master: subnet master
    :return: bollean
    '''
    str="--iface="+master
    result=get_macvlan_yaml(ds)
    if type(result) is int :
        return False
    return str in result

def get_macvlan_yaml(ds):
    cmd = "get ds " + ds + " -n kube-system -o yaml"
    code=execute_kubectl_cmd_with_code(cmd, json_out=False, stderr=False, stderrcode=True)
    if code == 1 :
        return code
    else:
        result=execute_kubectl_cmd(cmd, json_out=False)
        return result

def validate_support_macvlansubnet():
    '''
    desc: check cluster support macvlan
    :return: 0 support ; 1 not support
    '''
    exec_result=get_macvlansubnet("", False, False, True)
    return exec_result

def get_role_nodes_byClient(client, cluster, role):
    etcd_nodes = []
    control_nodes = []
    worker_nodes = []
    node_list = []
    nodes = client.list_node(clusterId=cluster.id).data
    for node in nodes:
        if node.etcd:
            etcd_nodes.append(node)
        if node.controlPlane:
            control_nodes.append(node)
        if node.worker:
            worker_nodes.append(node)
    if role == "etcd":
        node_list = etcd_nodes
    if role == "control":
        node_list = control_nodes
    if role == "worker":
        node_list = worker_nodes
    return node_list

def create_project_and_ns_byClient(client,token, cluster, project_name=None, ns_name=None):
    p = create_project(client, cluster, project_name)
    c_client = get_cluster_client_for_token(cluster, token)
    ns = create_ns(c_client, cluster, p, ns_name)
    return p, ns

def get_schedulable_nodes_byClient(client, cluster):
    nodes = client.list_node(clusterId=cluster.id).data
    schedulable_nodes = []
    for node in nodes:
        if node.worker:
            schedulable_nodes.append(node)
    return schedulable_nodes

def get_admin_client_and_cluster_byUrlToken(url, token):
    client = get_admin_client_byToken(url, token)
    if CLUSTER_NAME == "":
        clusters = client.list_cluster().data
    else:
        clusters = client.list_cluster(name=CLUSTER_NAME).data
    assert len(clusters) > 0
    cluster = clusters[0]
    return client, cluster

# ------ tools ------
def split_to_list(str):
    # des : split wl network ip/mac
    if str == "auto":
        return str
    return str.split("-")

def validate_in_list(str,list):
    # des : remove pod exist ip/mac
    assert str in list
    list.remove(str)
    return list

def exchange_mask(mask):
    count_bit = lambda bin_str: len([i for i in bin_str if i=='1'])
    mask_splited = mask.split(".")
    mask_count = [count_bit(bin((int(i)))) for i in mask_splited]
    return sum(mask_count)

def exchange_maskint(mask_int):
    bin_arr = ['0' for i in range(32)]
    for i in range(mask_int):
        bin_arr[i] = '1'
    tmpmask = [''.join(bin_arr[i * 8:i * 8 + 8]) for i in range(4)]
    tmpmask = [str(int(tmpstr, 2)) for tmpstr in tmpmask]
    return '.'.join(tmpmask)

def ipToBinary(ip):
    ip_num = ip.split('.')
    x = 0
    for i in range(len(ip_num)):
        num = int(ip_num[i]) << (24 - i * 8)
        x = x | num
    brnary = str(bin(x).replace('0b', ''))
    return brnary

def maskToBinary(mask):
    mask_list = str(mask).split('.')

    if len(mask_list) == 1:
        binary32 = []
        for i in range(32):
            binary32.append('0')
        for i in range(int(mask)):
            binary32[i] = '1'

        binary = ''.join(binary32)

    elif len(mask_list) == 4:
        binary = ipToBinary(mask)

    print(binary)
    return binary

# ------ run cmd ------
def execute_kubectl_cmd_with_code(cmd, json_out=True, stderr=False, stderrcode=False):
    command = 'kubectl --kubeconfig {0} {1}'.format(
        kube_fname, cmd)
    print(command)
    result = ""
    if json_out:
        command += ' -o json'
    if stderr:
        result = run_command_with_stderr(command)
    if stderrcode:
        result = run_command_with_stderr_code(command)
    else:
        result = run_command(command)
    if json_out:
        result = json.loads(result)
    print(result)
    return result

def run_command_with_stderr_code(command):
    try:
        output = subprocess.check_output(command, shell=True,
                                         stderr=subprocess.PIPE)
        returncode = 0
    except subprocess.CalledProcessError as e:
        output = e.output
        returncode = e.returncode
    print(returncode)
    return returncode

# ------ deprecated ------
def create_macvlan_subnet_yaml(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway):
    yaml_fname=macvlan_subnet_fname
    macvlan_subnet_yaml=get_macvlan_subnet_template(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway)
    print(macvlan_subnet_yaml)
    with open(yaml_fname, 'w') as fp:
        yaml.dump(macvlan_subnet_yaml,fp,default_flow_style=False)
    return yaml_fname

def get_macvlan_subnet_template(name,project,master,vlan,cidr,gateway,ranges,routes,podDefaultGateway):
    maxvlan_subnet_template = {
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
            "podDefaultGateway": podDefaultGateway
        }
    }
    return maxvlan_subnet_template
    return returncode