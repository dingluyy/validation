from .common import *  # NOQA
import pytest

BAIDU_CCE_ACCESS_KEY = os.environ.get('RANCHER_BAIDU_CCE_ACCESS_KEY', "")
BAIDU_CCE_SECRET_KEY = os.environ.get('RANCHER_BAIDU_CCE_SECRET_KEY', "")
BAIDU_CCE_AMI = os.environ.get('RANCHER_BAIDU_CCE_AMI', "")
BAIDU_CCE_REGION = os.environ.get('RANCHER_BAIDU_CCE_REGION', "bj")
BAIDU_CCE_CONTAINER_CIDR = os.environ.get("RANCHER_BAIDU_CCE_CONTAINER_CIDR","172.16.0.0/16")


baiduccecredential = pytest.mark.skipif(not (BAIDU_CCE_ACCESS_KEY and BAIDU_CCE_SECRET_KEY),
                                   reason='BAIDU CCE Credentials not provided, '
                                          'cannot create cluster')

@baiduccecredential
def test_create_baidu_cce_cluster():

    client = get_admin_client()
    baidu_cceConfig = get_baidu_cce_config()

    print("Cluster creation")
    cluster = client.create_cluster(baidu_cceConfig)
    print(cluster)
    cluster = validate_cluster(client, cluster, check_intermediate_state=True,
                               skipIngresscheck=True)
    print(cluster)
    cluster_cleanup(client, cluster)

def get_baidu_cce_config():

    name = random_test_name("test-auto-baidu-cce")
    baidu_cceConfig =  {
        "bandwidthInMbps": 100,
        "clusterName": name,
        "clusterVersion": "1.16.8",
        "containerCidr": BAIDU_CCE_CONTAINER_CIDR,
        "cpu": 4,
        "description": "",
        "diskSize": 0,
        "driverName": "baiducloudcontainerengine",
        "eipName": name,
        "gpuCard": "",
        "gpuCount": 0,
        "ifBuyEip": True,
        "imageId": "m-KX3IaJFg",
        "instanceType": 10,
        "memory": 8,
        "name": "",
        "nodeCount": 1,
        "osType": "",
        "osVersion": "",
        "region": BAIDU_CCE_REGION,
        "securityGroupId": "g-1f9xx3nhcvb2",
        "securityGroupName": "",
        "subProductType": "netraffic",
        "subnetId": "sbn-cvh9kcrz1nfv",
        "zone": "zoneD",
        "type": "baiduEngineConfig",
        "accessKey": BAIDU_CCE_ACCESS_KEY,
        "secretKey": BAIDU_CCE_SECRET_KEY,
        "adminPass": "X%jThoNguS(6rVewI!s!",
        "adminPassConfirm": "X%jThoNguS(6rVewI!s!",
        "cdsConfig": [],
        "vpcId": "vpc-k7gsv7af8857"
    }


    if BAIDU_CCE_AMI is not None:
        baidu_cceConfig.update({"ami": BAIDU_CCE_AMI})

    # Generate the config for CCE cluster
    baidu_cceConfig = {

        "baiduEngineConfig": baidu_cceConfig,
        "name": name,
        "type": "cluster",
        "dockerRootDir": "dockerRootDir",
        "fluentdLogDir": "/var/lib/rancher/fluentd/log"
    }
    print("\nBAIDU CCE Configuration")
    print(baidu_cceConfig)

    return baidu_cceConfig
