import pytest
from .entfunc import *

namespace = {"client": None, "p_client": None, "ns": None, "cluster": None, "project": None}
CATTLE_HARBOR_CONFIG_URL = (CATTLE_API_URL + '/users?action=saveharborconfig').replace('//v3','/v3')
CATTLE_HARBOR_SERVER_URL = (CATTLE_API_URL + '/settings/harbor-server-url').replace('//v3','/v3')
CATTLE_HARBOR_ADMIN_AUTH = (CATTLE_API_URL + '/settings/harbor-admin-auth').replace('//v3','/v3')
CATTLE_HARBOR_AUTH_MODE = (CATTLE_API_URL + '/settings/harbor-auth-mode').replace('//v3','/v3')
RANCHER_HARBOR_URL = os.environ.get('RANCHER_HARBOR_URL', '')
RANCHER_HARBOR_URL_HTTPS = os.environ.get('RANCHER_HARBOR_URL_HTTPS', '')
#RANCHER_HARBOR_HOST = os.environ.get('RANCHER_HARBOR_HOST', RANCHER_HARBOR_URL.split('/')[2].split(':')[0])
RANCHER_HARBOR_HOST = os.environ.get('RANCHER_HARBOR_HOST', '')
RANCHER_HARBOR_ADMIN = os.environ.get('RANCHER_HARBOR_ADMIN', 'admin')
RANCHER_HARBOR_ADMIN_PASSWORD = os.environ.get('RANCHER_HARBOR_ADMIN_PASSWORD', 'Harbor12345')
RANCHER_HARBOR_PUBLIC_IMAGE = os.environ.get('RANCHER_HARBOR_PUBLIC_IMAGE', RANCHER_HARBOR_HOST + '/autotest-public/nginx')
RANCHER_HARBOR_PRIVATE_IMAGE = os.environ.get('RANCHER_HARBOR_PRIVATE_IMAGE', RANCHER_HARBOR_HOST + '/autotest-private/nginx')
RANCHER_USER_TOKEN = os.environ.get('RANCHER_USER_TOKEN', '')
RANCHER_USER = os.environ.get('RANCHER_USER', '')
RANCHER_HARBOR_URL_NEW = os.environ.get('RANCHER_HARBOR_URL_NEW', '')
#RANCHER_HARBOR_HOST_NEW = os.environ.get('RANCHER_HARBOR_HOST_NEW', RANCHER_HARBOR_URL_NEW.split('/')[2].split(':')[0])
RANCHER_HARBOR_HOST_NEW = os.environ.get('RANCHER_HARBOR_HOST_NEW', '')
RANCHER_HARBOR_ADMIN_NEW = os.environ.get('RANCHER_HARBOR_ADMIN_NEW', 'root')
RANCHER_HARBOR_ADMIN_PASSWORD_NEW = os.environ.get('RANCHER_HARBOR_ADMIN_PASSWORD_NEW', 'Harbor12345')
RANCHER_HARBOR_PRIVATE_IMAGE_NEW = os.environ.get('RANCHER_HARBOR_PRIVATE_IMAGE_NEW', RANCHER_HARBOR_HOST_NEW + '/autotest-private/nginx')

headers = {"cookie": "R_SESS="+ADMIN_TOKEN}
registries = {RANCHER_HARBOR_HOST: {}}
harbor_dockercredential_label = {"rancher.cn/registry-harbor-auth":"true",
                                 "rancher.cn/registry-harbor-admin-auth":"true"}

harborcredential = pytest.mark.skipif(not RANCHER_HARBOR_URL,
                                   reason='HARBOR URL Credentials not provided, '
                                          'cannot set harbor')
harborhttpscredential = pytest.mark.skipif(not RANCHER_HARBOR_URL_HTTPS,
                                   reason='HARBOR URL Credentials not provided, '
                                          'cannot set harbor')

@harborcredential
def test_set_http_harborconfig():
    harbor_config_r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                                        RANCHER_HARBOR_ADMIN_PASSWORD,
                                        RANCHER_HARBOR_URL)
    assert harbor_config_r.status_code == 200

    harbor_server_r = set_harbor_server(RANCHER_HARBOR_URL)
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == RANCHER_HARBOR_URL

    harbor_auth_r = set_harbor_auth(RANCHER_HARBOR_ADMIN)
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == RANCHER_HARBOR_ADMIN

    harbor_mode_r = set_harbor_mode("db_auth")
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == "db_auth"


@harborhttpscredential
def test_set_https_harborconfig():
    harbor_config_json = {"username": RANCHER_HARBOR_ADMIN,
                          "serverURL": RANCHER_HARBOR_URL_HTTPS,
                          "password": RANCHER_HARBOR_ADMIN_PASSWORD,
                          "responseType": "json"}
    harbor_config_r = requests.post(CATTLE_HARBOR_CONFIG_URL,
                                    json=harbor_config_json, verify=False, headers=headers)
    print(harbor_config_r)
    assert harbor_config_r.status_code == 200

    harbor_server_json = {"value": RANCHER_HARBOR_URL_HTTPS,
                          "responseType": "json"}
    harbor_server_r = requests.put(CATTLE_HARBOR_SERVER_URL,
                                   json=harbor_server_json, verify=False, headers=headers)
    print(harbor_server_r.json())
    assert harbor_server_r.status_code == 200
    assert harbor_config_r['value'] == RANCHER_HARBOR_URL_HTTPS

    harbor_auth_json = {"value": RANCHER_HARBOR_ADMIN,
                        "responseType": "json"}
    harbor_auth_r = requests.put(CATTLE_HARBOR_ADMIN_AUTH,
                                 json=harbor_auth_json, verify=False, headers=headers)
    print(harbor_auth_r.json())
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r['value'] == RANCHER_HARBOR_ADMIN

    harbor_mode_json = {"value": "db_auth",
                        "responseType": "json"}
    harbor_mode_r = requests.put(CATTLE_HARBOR_AUTH_MODE,
                                 json=harbor_mode_json, verify=False, headers=headers)
    print(harbor_mode_r.json())
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r['value'] == "db_auth"


@harborcredential
def test_error_user_password():
    password = random_test_name('Harbor')
    print('Error password: ' + password)

    r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                          RANCHER_HARBOR_URL,
                          password)
    assert r.status_code == 410
    assert r.json()['code'] == "SyncHarborFailed"


@harborcredential
def test_update_password():
    client = namespace['client']
    users = client.list_user(username="admin")
    assert len(users) == 1
    admin_user = users.data[0]

    update_harbor_url = admin_user.actions["updateharborauth"]
    newPassword = random_test_name("Harbor")
    headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                update_harbor_url, headers)
    assert r1.status_code == 200

    assert_r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                                 newPassword,
                                 RANCHER_HARBOR_URL)
    assert assert_r.status_code == 200

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                newPassword,
                                update_harbor_url, headers)
    assert r2.status_code == 200


@harborcredential
def test_user_setharborauth():
    client = namespace['client']
    users = client.list_user(username = RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)

    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}
    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200


@harborcredential
def test_user_update_password():
    client = namespace['client']
    users = client.list_user(username = RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    updateharborauth_url = user.actions["updateharborauth"]
    print(setharborauth_url)
    print(updateharborauth_url)

    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}
    setharborauth_r = set_user_harborauth(RANCHER_USER,
                                          RANCHER_HARBOR_ADMIN_PASSWORD,
                                          setharborauth_url, headers)
    assert setharborauth_r.status_code == 200

    newPassword = random_test_name('Harbor')
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN, "x-api-harbor-admin-header": "false"}
    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                updateharborauth_url, headers)
    assert r1.status_code == 200

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                newPassword, updateharborauth_url, headers)
    assert r2.status_code == 200


@harborcredential
def test_public_image_without_dockercredential():
    client = namespace['client']
    cluster = namespace['cluster']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'
    client.delete(project)


@harborcredential
def test_private_image_without_dockercredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)

    create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    client.delete(project)


@harborcredential
def test_public_image_with_dockercredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    ns1 = create_ns(c_client, cluster, project)
    wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl1.state == 'active'
    client.delete(project)


@harborcredential
def test_private_image_with_dockercredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    ns1 = create_ns(c_client, cluster, project)
    wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl1.state == 'active'
    client.delete(project)


@harborcredential
def test_public_image_with_namespacedDockerCredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    ns1 = create_ns(c_client, cluster, project)
    wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl1.state == 'active'
    client.delete(project)


@harborcredential
def test_private_image_with_namespacedDockerCredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'
    c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
    ns1 = create_ns(c_client, cluster, project)
    create_workload_unavailable(p_client, ns1, RANCHER_HARBOR_PRIVATE_IMAGE)
    client.delete(project)


@harborcredential
def test_update_password_with_dockerCredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    users = client.list_user(username="admin")
    assert len(users) == 1
    admin_user = users.data[0]
    update_harbor_url = admin_user.actions["updateharborauth"]
    newPassword = random_test_name("Harbor")
    headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                update_harbor_url, headers)
    assert r1.status_code == 200

    assert_r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                                 newPassword,
                                 RANCHER_HARBOR_URL)
    assert assert_r.status_code == 200

    wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl2.state == 'active'

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                newPassword,
                                update_harbor_url, headers)
    assert r2.status_code == 200
    client.delete(project)


@harborcredential
def test_update_password_with_namespacedDockerCredential():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    users = client.list_user(username="admin")
    assert len(users) == 1
    admin_user = users.data[0]
    update_harbor_url = admin_user.actions["updateharborauth"]
    newPassword = random_test_name("Harbor")
    headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                update_harbor_url, headers)
    assert r1.status_code == 200

    assert_r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                                 newPassword,
                                 RANCHER_HARBOR_URL)
    assert assert_r.status_code == 200

    wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl2.state == 'active'

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                       newPassword,
                                       update_harbor_url, headers)
    assert r2.status_code == 200
    client.delete(project)


@harborcredential
def test_user_public_image_without_dockercredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username = RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'
    client.delete(project)


@harborcredential
def test_user_private_image_without_dockercredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    client.delete(project)


@harborcredential
def test_user_public_image_with_dockercredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'

    c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
    ns2 = create_ns(c_client, cluster, project)

    wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl2.state == 'active'
    client.delete(project)


@harborcredential
def test_user_private_image_with_dockercredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
    ns2 = create_ns(c_client, cluster, project)

    wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl2.state == 'active'
    client.delete(project)


@harborcredential
def test_user_public_image_with_namespacedDockerCredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl.state == 'active'

    c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
    ns2 = create_ns(c_client, cluster, project)

    wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PUBLIC_IMAGE)
    assert wl2.state == 'active'
    client.delete(project)


@harborcredential
def test_user_private_image_with_namespacedDockerCredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
    ns2 = create_ns(c_client, cluster, project)

    create_workload_unavailable(p_client, ns2, RANCHER_HARBOR_PRIVATE_IMAGE)
    client.delete(project)


@harborcredential
def test_user_update_password_with_dockerCredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    update_harbor_url = user.actions["updateharborauth"]
    newPassword = random_test_name("Harbor")
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN,"x-api-harbor-admin-header": "false"}
    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                update_harbor_url, headers)
    assert r1.status_code == 200

    wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl2.state == "active"

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                newPassword,
                                update_harbor_url, headers)
    assert r2.status_code == 200
    client.delete(project)


@harborcredential
def test_user_update_password_with_namespacedDockerCredential():
    client = namespace['client']
    cluster = namespace['cluster']
    users = client.list_user(username=RANCHER_USER)
    assert len(users) == 1
    user = users.data[0]
    setharborauth_url = user.actions['setharborauth']
    print(setharborauth_url)
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}

    r = set_user_harborauth(RANCHER_USER,
                            RANCHER_HARBOR_ADMIN_PASSWORD,
                            setharborauth_url, headers)
    assert r.status_code == 200

    project, ns = create_project_and_ns(RANCHER_USER_TOKEN, cluster)
    p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
    name = random_test_name("registry")
    p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                               labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    update_harbor_url = user.actions["updateharborauth"]
    newPassword = random_test_name("Harbor")
    headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN, "x-api-harbor-admin-header": "false"}
    r1 = update_harbor_password(newPassword,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                update_harbor_url, headers)
    assert r1.status_code == 200

    wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl2.state == "active"

    r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                newPassword,
                                update_harbor_url, headers)
    assert r2.status_code == 200
    client.delete(project)


@harborcredential
def test_update_harbor_with_old_registries():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    harbor_config_r = set_harbor_config(RANCHER_HARBOR_ADMIN_NEW,
                                        RANCHER_HARBOR_ADMIN_PASSWORD_NEW,
                                        RANCHER_HARBOR_URL_NEW)
    assert harbor_config_r.status_code == 200

    harbor_server_r = set_harbor_server(RANCHER_HARBOR_URL_NEW)
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == RANCHER_HARBOR_URL_NEW

    harbor_auth_r = set_harbor_auth(RANCHER_HARBOR_ADMIN_NEW)
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == RANCHER_HARBOR_ADMIN_NEW

    harbor_mode_r = set_harbor_mode("db_auth")
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == "db_auth"

    create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)

    client.delete(project)

    harbor_config_r = set_harbor_config(RANCHER_HARBOR_ADMIN,
                                        RANCHER_HARBOR_ADMIN_PASSWORD,
                                        RANCHER_HARBOR_URL)
    assert harbor_config_r.status_code == 200

    harbor_server_r = set_harbor_server(RANCHER_HARBOR_URL)
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == RANCHER_HARBOR_URL

    harbor_auth_r = set_harbor_auth(RANCHER_HARBOR_ADMIN)
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == RANCHER_HARBOR_ADMIN

    harbor_mode_r = set_harbor_mode("db_auth")
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == "db_auth"


@harborcredential
def test_update_harbor_with_new_registries():
    cluster = namespace['cluster']
    client = namespace['client']
    project, ns = create_project_and_ns(ADMIN_TOKEN, cluster)
    p_client = get_project_client_for_token(project, ADMIN_TOKEN)
    name = random_test_name("registry")
    p_client.create_dockerCredential(registries=registries, name=name, labels=harbor_dockercredential_label)

    wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
    assert wl.state == 'active'

    harbor_config_r = set_harbor_config(RANCHER_HARBOR_ADMIN_NEW,
                                        RANCHER_HARBOR_ADMIN_PASSWORD_NEW,
                                        RANCHER_HARBOR_URL_NEW)
    assert harbor_config_r.status_code == 200

    harbor_server_r = set_harbor_server(RANCHER_HARBOR_URL_NEW)
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == RANCHER_HARBOR_URL_NEW

    harbor_auth_r = set_harbor_auth(RANCHER_HARBOR_ADMIN_NEW)
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == RANCHER_HARBOR_ADMIN_NEW

    harbor_mode_r = set_harbor_mode("db_auth")
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == "db_auth"

    name2 = random_test_name("registry")
    registries2 = {RANCHER_HARBOR_HOST_NEW:{}}
    p_client.create_dockerCredential(registries=registries2, name=name2, labels=harbor_dockercredential_label)

    wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE_NEW)
    assert wl2.state == 'active'
    client.delete(project)


@harborcredential
def test_delete_harborconfig():
    harbor_server_r = set_harbor_server('')
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == ''

    harbor_auth_r = set_harbor_auth('')
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == ''

    harbor_mode_r = set_harbor_mode('')
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == ''


@pytest.fixture(scope='module', autouse="True")
def create_project_client(request):
    client, cluster = get_admin_client_and_cluster()
    create_kubeconfig(cluster)
    p, ns = create_project_and_ns(
        ADMIN_TOKEN, cluster, random_test_name("testharbor"))
    p_client = get_project_client_for_token(p, ADMIN_TOKEN)
    namespace["client"] = client
    namespace["p_client"] = p_client
    namespace["ns"] = ns
    namespace["cluster"] = cluster
    namespace["project"] = p

    def fin():
        client = get_admin_client()
        time.sleep(30)
        client.delete(namespace["project"])
    request.addfinalizer(fin)


def create_workload(p_client, ns, image):
    workload_name = random_test_name("harbor")
    con = [{"name": "test",
            "image": image,
            "runAsNonRoot": False,
            "stdin": True,
            "imagePullPolicy": "Always",
            }]
    workload = p_client.create_workload(name=workload_name,
                                        containers=con,
                                        namespaceId=ns.id)
    workload = wait_for_wl_to_active(p_client, workload, timeout=90)
    return workload


def create_workload_unavailable(p_client, ns, image):
    workload_name = random_test_name("harbor")
    con = [{"name": "test",
            "image": image,
            "runAsNonRoot": False,
            "stdin": True,
            "imagePullPolicy": "Always",
            }]
    workload = p_client.create_workload(name=workload_name,
                                        containers=con,
                                        namespaceId=ns.id)

    events = wait_for_wl_unavailable(p_client, workload, ['ImagePullBackOff', 'ErrImagePull'], timeout=60)
    return events


def wait_for_wl_unavailable(p_client, workload, reasons, timeout):
    pods = p_client.list_pod(workloadId=workload.id).data
    start = time.time()
    while len(pods) == 0 and (time.time() - start) < 30 :
        pods = p_client.list_pod(workloadId=workload.id).data
    assert len(pods) > 0
    p = pods[0]
    start = time.time()
    while p.state != "running":
        if time.time() - start > timeout:
            containerStatuses = p.status.containerStatuses[0]
            print(containerStatuses)
            assert containerStatuses.ready == False
            assert containerStatuses.started == False
            reason = containerStatuses.state.waiting.reason
            exist = False
            for r in reasons:
                if r == reason:
                    exist = True
            assert exist == True
            break
        time.sleep(.5)
        pods = p_client.list_pod(uuid=p.uuid).data
        assert len(pods) == 1
        p = pods[0]

    assert p.state != "running"


def set_harbor_config(username, password, harbor_url, headers = headers):
    harbor_config_json = {"username": username,
                          "serverURL": harbor_url,
                          "password": password,
                          "responseType": "json"}
    r = requests.post(CATTLE_HARBOR_CONFIG_URL,
                      json=harbor_config_json, verify=False, headers=headers)
    print(r)
    return r


def set_harbor_server(harbor_url, headers = headers):
    harbor_server_json = {"value": harbor_url,
                          "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_SERVER_URL,
                     json=harbor_server_json, verify=False, headers=headers)
    print(r.json())
    return r


def set_harbor_auth(admin, headers = headers):
    harbor_auth_json = {"value": admin,
                        "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_ADMIN_AUTH,
                                 json=harbor_auth_json, verify=False, headers=headers)
    print(r.json())
    return r


def set_harbor_mode(mode, headers = headers):
    harbor_mode_json = {"value": mode,
                        "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_AUTH_MODE,
                                 json=harbor_mode_json, verify=False, headers=headers)
    print(r.json())
    return r


def update_harbor_password(newPassword, oldPassword, url, headers):
    update_json = {"newPassword": newPassword,
                    "oldPassword": oldPassword,
                    "responseType": "json"}
    r = requests.post(url, json=update_json, verify=False, headers=headers)

    return r

def set_user_harborauth(username, password, url, headers):
    json = {"username": username,
            "password": password,
            "email": random_name() + "@rancher.com",
            "responseType": "json"}

    r = requests.post(url,
                      json=json, verify=False, headers=headers)
    return r