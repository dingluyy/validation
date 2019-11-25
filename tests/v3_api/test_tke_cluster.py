from .common import *  # NOQA
import pytest

TKE_ACCESS_KEY = os.environ.get('RANCHER_TKE_ACCESS_KEY', "")
TKE_SECRET_KEY = os.environ.get('RANCHER_TKE_SECRET_KEY', "")
TKE_AMI = os.environ.get('RANCHER_TKE_AMI', "")
TKE_REGION = os.environ.get('RANCHER_TKE_REGION', "ap-guangzhou")
TKE_CONTAINER_CIDR = os.environ.get("RANCHER_TKE_CONTAINER_CIDR","172.16.0.0/16")


tkecredential = pytest.mark.skipif(not (TKE_ACCESS_KEY and TKE_SECRET_KEY),
                                   reason='CCE Credentials not provided, '
                                          'cannot create cluster')

@tkecredential
def test_create_tke_cluster():

    client = get_admin_client()
    tkeConfig = get_tke_config()

    print("Cluster creation")
    cluster = client.create_cluster(tkeConfig)
    print(cluster)
    cluster = validate_cluster(client, cluster, check_intermediate_state=True,
                              skipIngresscheck=True)

    cluster_cleanup(client, cluster)


def get_tke_config():

    name = random_test_name("test-auto-tke")
    tkeConfig =  {
        "bandwidth": 10,
        "bandwidthType": "PayByHour",
        "clusterCidr": TKE_CONTAINER_CIDR,
        "clusterDesc": "",
        "clusterName": name,
        "clusterVersion": "1.10.5",
        "cpu": 0,
        "cvmType": "PayByHour",
        "driverName": "tencentkubernetesengine",
        "ignoreClusterCidrConflict": 0,
        "instanceType": "S2.MEDIUM4",
        "isVpcGateway": 0,
        "keyId": "skey-ge8q9da7",
        "masterSubnetId": "",
        "mem": 0,
        "name": "",
        "nodeCount": 1,
        "osName": "ubuntu16.04.1 LTSx86_64",
        "password": "",
        "period": 0,
        "projectId": 0,
        "region": TKE_REGION,
        "renewFlag": "",
        "rootSize": 25,
        "rootType": "CLOUD_SSD",
        "secretId": TKE_ACCESS_KEY,
        "sgId": "sg-rs3rzezp",
        "storageSize": 20,
        "storageType": "CLOUD_PREMIUM",
        "subnetId": "subnet-82sy1p20",
        "userScript": "",
        "vpcId": "vpc-hdosln5x",
        "wanIp": 1,
        "zoneId": "100003",
        "type": "tencentEngineConfig",
        "secretKey": TKE_SECRET_KEY
    }

    if TKE_AMI is not None:
        tkeConfig.update({"ami": TKE_AMI})

    # Generate the config for CCE cluster
    tkeConfig = {

        "tencentEngineConfig": tkeConfig,
        "name": name,
        "type": "cluster"
    }
    print("\nTKE Configuration")
    print(tkeConfig)

    return tkeConfig
