from .entfunc import *  # NOQA
import pytest


ALIYUN_ECS_ACCESS_KEY = os.environ.get('RANCHER_ALIYUN_ECS_ACCESS_KEY', "")
ALIYUN_ECS_SECRET_KEY = os.environ.get('RANCHER_ALIYUN_ECS_SECRET_KEY', "")
ALIYUN_ECS_REGION = os.environ.get('RANCHER_ALIYUN_ECS_REGION', "cn-shenzhen")

aliyunecscredential = pytest.mark.skipif(not (ALIYUN_ECS_ACCESS_KEY and ALIYUN_ECS_SECRET_KEY),
                                   reason='ALIYUN ECS Credentials not provided, '
                                          'cannot create cluster')


@aliyunecscredential
def test_create_aliyun_ecs_cluster():

    client = get_admin_client()
    aliyunecsConfig = get_node_template()
    nodeTemplate = client.create_nodeTemplate(aliyunecsConfig)
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
    time.sleep(5)
    nodePool_can_delete = wait_for_nodePool_delete(client, nodeTemplate.id)
    assert nodePool_can_delete == []
    client.delete(nodeTemplate)


def get_node_template():
    aliyunecsConfig =  {
        "accessKeyId": ALIYUN_ECS_ACCESS_KEY,
        "apiEndpoint": "",
        "description": "",
        "diskCategory": "cloud_efficiency",
        "diskFs": "ext4",
        "diskSize": "0",
        "imageId": "ubuntu_16_04_64_20G_alibase_20190620.vhd",
        "instanceType": "ecs.g5.large",
        "internetMaxBandwidth": "1",
        "ioOptimized": "optimized",
        "privateAddressOnly": False,
        "privateIp": "",
        "region": ALIYUN_ECS_REGION,
        "routeCidr": "",
        "securityGroup": "sg-wz974bqip62ylkx5aq6r",
        "slbId": "",
        "sshKeyContents": "",
        "sshKeypair": "",
        "sshPassword": "",
        "systemDiskCategory": "cloud_efficiency",
        "systemDiskSize": "40",
        "upgradeKernel": False,
        "vpcId": "vpc-d9b73rns0",
        "vswitchId": "vsw-wz9h0eyi4yyewa0rio9vy",
        "zone": "cn-shenzhen-e",
        "type": "aliyunecsConfig",
        "accessKeySecret": ALIYUN_ECS_SECRET_KEY
    }

    # Generate the config for ALIYUN ECS cluster
    nodeTemplate = {
        "aliyunecsConfig": aliyunecsConfig,
        "name": random_test_name("test-auto-aliyunecs-nodeTemplate"),
        "type": "nodeTemplate"
    }
    print("\nALIYUN ECS NodeTemplate")
    print(nodeTemplate)

    return nodeTemplate


def get_rancherK8sEngine_config():
    rancherKubernetesEngineConfig = {
        "addonJobTimeout": 30,
        "ignoreDockerVersion": True,
        "sshAgentAuth": False,
        "type": "rancherKubernetesEngineConfig",
        "kubernetesVersion": "v1.14.6-rancher1-1",
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
        "name": random_test_name("test-auto-rke-aliyunecs"),
        "type": "cluster"
    }
    print("\nRKE ALIYUNECS Configuration")
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
        "hostnamePrefix": random_test_name("test-auto-aliyunecs-nodepool")
    }
    print(nodePool)
    return nodePool