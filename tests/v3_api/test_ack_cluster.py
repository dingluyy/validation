from .entfunc import *  # NOQA
import pytest

ACK_ACCESS_KEY = os.environ.get('RANCHER_ACK_ACCESS_KEY', "")
ACK_SECRET_KEY = os.environ.get('RANCHER_ACK_SECRET_KEY', "")
ACK_AMI = os.environ.get('RANCHER_ACK_AMI', "")
ACK_REGION = os.environ.get('RANCHER_ACK_REGION', "cn-beijing-a")
ACK_CONTAINER_CIDR = os.environ.get("RANCHER_ACK_CONTAINER_CIDR","172.16.0.0/16")


ackcredential = pytest.mark.skipif(not (ACK_ACCESS_KEY and ACK_SECRET_KEY),
                                   reason='ACK Credentials not provided, '
                                          'cannot create cluster')

@ackcredential
def test_create_ack_cluster():

    client = get_admin_client()
    ackConfig = get_ack_config()

    print("Cluster creation")
    cluster = client.create_cluster(ackConfig)
    print(cluster)
    cluster = validate_cluster(client, cluster, check_intermediate_state=True,
                               skipIngresscheck=True)

    cluster_cleanup(client, cluster)


def get_ack_config():

    name = random_test_name("test-auto-ack")
    ackConfig =  {
        "clusterType": "Kubernetes",
        "containerCidr": "",
        "displayName": "ack",
        "driverName": "aliyunkubernetescontainerservice",
        "keyPair": "hailong",
        "kubernetesVersion": "1.11.5",
        "masterAutoRenewPeriod": 0,
        "masterDataDiskCategory": "",
        "masterDataDiskSize": 0,
        "masterInstanceChargeType": "",
        "masterInstanceType": "ecs.n1.large",
        "masterInstanceTypeA": "",
        "masterInstanceTypeB": "",
        "masterInstanceTypeC": "",
        "masterPeriod": 0,
        "masterPeriodUnit": "",
        "masterSystemDiskCategory": "cloud_efficiency",
        "masterSystemDiskSize": 120,
        "multiAz": "false",
        "name": "ack",
        "numOfNodes": 1,
        "numOfNodesA": 0,
        "numOfNodesB": 0,
        "numOfNodesC": 0,
        "regionId": "cn-beijing",
        "serviceCidr": "",
        "timeoutMins": 0,
        "vpcId": "",
        "vswitchId": "",
        "vswitchIdA": "",
        "vswitchIdB": "",
        "vswitchIdC": "",
        "workerAutoRenewPeriod": 0,
        "workerDataDiskCategory": "cloud_efficiency",
        "workerDataDiskSize": 120,
        "workerInstanceChargeType": "PostPaid",
        "workerInstanceType": "ecs.n1.large",
        "workerInstanceTypeA": "",
        "workerInstanceTypeB": "",
        "workerInstanceTypeC": "",
        "workerPeriod": 0,
        "workerPeriodUnit": "",
        "workerSystemDiskCategory": "cloud_efficiency",
        "workerSystemDiskSize": 120,
        "zoneId": ACK_REGION,
        "type": "aliyunEngineConfig",
        "accessKeyId": ACK_ACCESS_KEY,
        "accessKeySecret": ACK_SECRET_KEY
    }

    if ACK_AMI is not None:
        ackConfig.update({"ami": ACK_AMI})

    # Generate the config for CCE cluster
    ackConfig = {

        "aliyunEngineConfig": ackConfig,
        "name": name,
        "type": "cluster"
    }
    print("\nACK Configuration")
    print(ackConfig)

    return ackConfig
