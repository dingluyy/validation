from .entfunc import *  # NOQA
import pytest

PINGANYUN_ECS_ACCESS_KEY = os.environ.get('RANCHER_PINGANYUN_ECS_ACCESS_KEY', "")
PINGANYUN_ECS_SECRET_KEY = os.environ.get('RANCHER_PINGANYUN_ECS_SECRET_KEY', "")
PINGANYUN_ECS_REGION = os.environ.get('RANCHER_PINGANYUN_ECS_REGION', "Region-southChina")
PINGANYUN_ECS_ZONE = os.environ.get('RANCHER_PINGANYUN_ECS_ZONE',"Zone-southChinaA")

pinganyunecscredential = pytest.mark.skipif(not (PINGANYUN_ECS_ACCESS_KEY and PINGANYUN_ECS_SECRET_KEY),
                                   reason='PINGANYUN ECS Credentials not provided, '
                                          'cannot create cluster')


@pinganyunecscredential
def test_create_pinganyun_ecs_cluster():

    client = get_admin_client()
    pinganyunecsConfig = get_node_template()
    nodeTemplate = client.create_nodeTemplate(pinganyunecsConfig)
    assert nodeTemplate.state == 'active'

    rancherKubernetesEngineConfig = get_rancherK8sEngine_config()
    print("Cluster creation")
    cluster = client.create_cluster(rancherKubernetesEngineConfig)
    print(cluster)
    print("NodePool creation")
    nodePool = get_node_pool(nodeTemplate,cluster)
    node = client.create_nodePool(nodePool)
    print(node)
    assert node.state == 'active'

    cluster = validate_internal_cluster(client, cluster, check_intermediate_state=True,
                               skipIngresscheck=True)
    cluster_cleanup(client, cluster)

    nodePool_can_delete = wait_for_nodePool_delete(client,nodeTemplate.id)
    print("nodePool_can_delete",nodePool_can_delete)
    assert nodePool_can_delete == []
    client.delete(nodeTemplate)


def get_node_template():
    pinganyunecsConfig = {
        "accessKeyId": PINGANYUN_ECS_ACCESS_KEY,
        "apiEndpoint": "",
        "bandWidthIp": "",
        "bandWidthIpId": "",
        "bandWidthName": "",
        "chargeType": "Hour",
        "createNewSnat": False,
        "diskSize": "0",
        "diskType": "",
        "imageId": "ImageServiceImpl-i9ktsX5Qpl",
        "instanceType": "ecs.c5.1c2m",
        "natId": "Nat-UBGX9W9ZJv",
        "networkId": "Network-IgLTqmjh3E",
        "osTypeId": "ecd95351-bcaf-4817-a441-28ffdce222b2",
        "podId": "Pod-SCA1",
        "privateAddressOnly": False,
        "productSeriesId": "ProductSeries-Ihkus16YfM",
        "region": "Region-southChina",
        "securityGroupId": None,
        "securityGroupName": "rancher-nodes",
        "size": "ecs.c5.1c2m",
        "snatName": "SNAT-TX800062",
        "sshPassword": "",
        "subnetId": "",
        "useType": "PUBLIC",
        "vpcId": "Vpc-vOjx2EUuDt",
        "zone": "Zone-southChinaA",
        "type": "pinganyunecsConfig",
        "accessKeySecret": PINGANYUN_ECS_SECRET_KEY,
        "createNewSNAT": False
    }

    # Generate the config for PINGANYUN ECS cluster
    nodeTemplate = {
        "pinganyunecsConfig": pinganyunecsConfig,
        "name": random_test_name("test-auto-pinganyunecs-nodeTemplate"),
        "type": "nodeTemplate",
        "useInternalIpAddress": True,
        "engineInstallURL": "https://releases.rancher.com/install-docker/18.09.sh"
    }
    print("\nPINGANYUN ECS NodeTemplate")
    print(nodeTemplate)

    return nodeTemplate


def get_rancherK8sEngine_config():
    rancherKubernetesEngineConfig = {
        "addonJobTimeout": 30,
        "ignoreDockerVersion": True,
        "sshAgentAuth": False,
        "type": "rancherKubernetesEngineConfig",
        "kubernetesVersion": "v1.15.5-rancher1-1",
        "authentication": {
            "strategy": "x509",
            "type": "authnConfig"
        },
        "network": {
            "plugin": "canal",
            "type": "networkConfig",
            "options": {
                "flannel_backend_type": "vxlan"
            }
        },
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

    rancherK8sEngineConfig = {
        "rancherKubernetesEngineConfig": rancherKubernetesEngineConfig,
        "name": random_test_name("test-auto-rke-pinganyunecs"),
        "type": "cluster"
    }
    print("\nRKE PINGANYUNECS Configuration")
    print(rancherK8sEngineConfig)

    return rancherK8sEngineConfig


def get_node_pool(nodeTemplate,cluster):
    nodePool = {
        "controlPlane": True,
        "etcd": True,
        "quantity": 1,
        "worker": True,
        "type": "nodePool",
        "nodeTemplateId": nodeTemplate.id,
        "clusterId": cluster.id,
        "hostnamePrefix": random_test_name("test-auto-pinganyunecs-nodepool")
    }
    print(nodePool)
    return nodePool