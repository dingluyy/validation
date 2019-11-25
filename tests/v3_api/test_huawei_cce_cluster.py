from .common import *  # NOQA
import pytest

HUAWEI_CCE_ACCESS_KEY = os.environ.get('RANCHER_HUAWEI_CCE_ACCESS_KEY', "")
HUAWEI_CCE_SECRET_KEY = os.environ.get('RANCHER_HUAWEI_CCE_SECRET_KEY', "")
HUAWEI_CCE_PROJECT = os.environ.get('RANCHER_HUAWEI_CCE_PROJECT', "")
HUAWEI_CCE_AMI = os.environ.get('RANCHER_HUAWEI_CCE_AMI', "")
HUAWEI_CCE_REGION = os.environ.get('RANCHER_HUAWEI_CCE_REGION', "bj")
HUAWEI_CCE_CONTAINER_CIDR = os.environ.get("RANCHER_HUAWEI_CCE_CONTAINER_CIDR","172.20.0.0/16")


huaweiccecredential = pytest.mark.skipif(not (HUAWEI_CCE_ACCESS_KEY and HUAWEI_CCE_SECRET_KEY and HUAWEI_CCE_PROJECT),
                                   reason='HUAWEI CCE Credentials not provided, '
                                          'cannot create cluster')

@huaweiccecredential
def test_create_huawei_cce_cluster():

    client = get_admin_client()
    huawei_cceConfig = get_huawei_cce_config()

    print("Cluster creation")
    cluster = client.create_cluster(huawei_cceConfig)
    print(cluster)
    cluster = validate_cluster(client, cluster, check_intermediate_state=True,
                               skipIngresscheck=True)
    print(cluster)
    cluster_cleanup(client, cluster)

def get_huawei_cce_config():

    name = random_test_name("test-auto-huawei-cce")
    huawei_cceConfig =  {
        "accessKey": HUAWEI_CCE_ACCESS_KEY,
        "apiServerElbId": "",
        "authentiactionMode": "rbac",
        "authenticatingProxyCa":None,
        "availableZone": "cn-north-1a",
        "billingMode": 0,
        "bmsIsAutoRenew": "false",
        "bmsPeriodNum": 1,
        "bmsPeriodType": "month",
        "clusterBillingMode": 0,
        "clusterEipId": "",
        "clusterFlavor": "cce.s1.small",
        "clusterType": "VirtualMachine",
        "containerNetworkCidr": HUAWEI_CCE_CONTAINER_CIDR,
        "containerNetworkMode": "overlay_l2",
        "dataVolumeSize": 100,
        "dataVolumeType": "SATA",
        "description": "",
        "displayName": "",
        "driverName": "huaweicontainercloudengine",
        "eipBandwidthSize": 0,
        "eipChargeMode": "traffic",
        "eipCount": 0,
        "eipShareType": "PER",
        "eipType": "5-bgp",
        "externalServerEnabled": False,
        "highwaySubnet": "",
        "masterVersion": "v1.11.3",
        "nodeCount": 1,
        "nodeFlavor": "s2.large.2",
        "nodeOperationSystem": "CentOS 7.4",
        "password": "",
        "projectId": HUAWEI_CCE_PROJECT,
        "region": "cn-north-1",
        "rootVolumeSize": 40,
        "rootVolumeType": "SATA",
        "secretKey": HUAWEI_CCE_SECRET_KEY,
        "sshKey": "201712-hwcloud-nancy",
        "subnetId": "d4bad3d3-c421-4801-8b68-3f622e4c8434",
        "userName": "root",
        "vpcId": "db7e2f63-20b2-4e26-838d-96d253d4ee87",
        "type": "huaweiEngineConfig",
        "labels": {},
        "keypairs": "cn-north-1a",
        "nodeLabels": {}
    }
    if HUAWEI_CCE_AMI is not None:
        huawei_cceConfig.update({"ami": HUAWEI_CCE_AMI})

    # Generate the config for CCE cluster
    huawei_cceConfig = {

        "huaweiEngineConfig": huawei_cceConfig,
        "name": name,
        "type": "cluster"
    }
    print("\nHUAWEI CCE Configuration")
    print(huawei_cceConfig)

    return huawei_cceConfig
