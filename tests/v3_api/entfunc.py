from .common import *  # NOQA

DEFAULT_NODEPOOL_TIMEOUT = 300
TEST_INTERNAL_IMAGE = os.environ.get('RANCHER_TEST_IMAGE', "busybox:musl")
TEST_INGRESS_TARGET_PORT = os.environ.get('RANCHER_TEST_INGRESS_TARGET_PORT', "8088")


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