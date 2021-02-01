import pytest
from .harbor import *

namespace = {"client": None, "p_client": None, "ns": None, "cluster": None, "project": None}
admin = {"setharborauth":None, "updateharborauth":None}
user = {"setharborauth":None, "updateharborauth":None, "self":None}
admin_harbor_dockercredential_label = {"rancher.cn/registry-harbor-auth":"true",
                                       "rancher.cn/registry-harbor-admin-auth":"true"}
user_harbor_dockercredential_label = {"rancher.cn/registry-harbor-auth": "true"}
i = 0

params = json.loads(os.environ.get('RANCHER_HARBOR2_PARAMS','[]'))

class Test_Harbor():
    def setup_class(self):
        global RANCHER_HARBOR_URL
        global RANCHER_HARBOR_VERSION
        global RANCHER_HARBOR_ADMIN
        global RANCHER_HARBOR_ADMIN_PASSWORD
        RANCHER_HARBOR_URL = params[i]['harbor_url'].strip('/')
        RANCHER_HARBOR_VERSION = params[i]['harbor_version']
        RANCHER_HARBOR_ADMIN = params[i]['harbor_admin'] if params[i]['harbor_admin']!= '' else 'admin'
        RANCHER_HARBOR_ADMIN_PASSWORD = params[i]['harbor_password'] if params[i]['harbor_password']!= '' else 'Harbor12345'

        RANCHER_HARBOR_HOST = RANCHER_HARBOR_URL.split('/')[2]
        global registries
        registries = {RANCHER_HARBOR_HOST: {}}
        global RANCHER_HARBOR_PUBLIC_IMAGE
        RANCHER_HARBOR_PUBLIC_IMAGE = params[i]['public_image'] if params[i]['public_image'] != '' else RANCHER_HARBOR_HOST + '/autotest-public/nginx'
        global RANCHER_HARBOR_PRIVATE_IMAGE
        RANCHER_HARBOR_PRIVATE_IMAGE = params[i]['private_image'] if params[i]['private_image'] != '' else RANCHER_HARBOR_HOST + '/autotest-private/nginx'

        global RANCHER_HARBOR_URL_NEW
        global RANCHER_HARBOR_VERSION_NEW
        global RANCHER_HARBOR_ADMIN_NEW
        global RANCHER_HARBOR_ADMIN_PASSWORD_NEW
        global RANCHER_HARBOR_PRIVATE_IMAGE_NEW
        global RANCHER_HARBOR_HOST_NEW
        RANCHER_HARBOR_URL_NEW = params[i]['harbor_url_new'].strip('/')
        RANCHER_HARBOR_VERSION_NEW = params[i]['harbor_version_new']
        RANCHER_HARBOR_HOST_NEW = RANCHER_HARBOR_URL_NEW.split('/')[2]
        RANCHER_HARBOR_ADMIN_NEW = params[i]['harbor_admin_new']
        RANCHER_HARBOR_ADMIN_PASSWORD_NEW = params[i]['harbor_password_new'] if params[i]['harbor_password_new']!= '' else 'Harbor12345'
        RANCHER_HARBOR_PRIVATE_IMAGE_NEW = params[i]['private_image_new'] if params[i]['private_image_new'] != '' else RANCHER_HARBOR_HOST_NEW + '/autotest-private/nginx'

        print('RANCHER_HARBOR_URL', RANCHER_HARBOR_URL)
        print('RANCHER_HARBOR_VERSION', RANCHER_HARBOR_VERSION)
        print('RANCHER_HARBOR_ADMIN', RANCHER_HARBOR_ADMIN)
        print('RANCHER_HARBOR_ADMIN_PASSWORD', RANCHER_HARBOR_ADMIN_PASSWORD)
        print('registries', registries)
        print('RANCHER_HARBOR_PUBLIC_IMAGE', RANCHER_HARBOR_PUBLIC_IMAGE)
        print('RANCHER_HARBOR_PRIVATE_IMAGE', RANCHER_HARBOR_PRIVATE_IMAGE)
        print('RANCHER_HARBOR_URL_NEW', RANCHER_HARBOR_URL_NEW)
        print('RANCHER_HARBOR_VERSION_NEW', RANCHER_HARBOR_VERSION_NEW)
        print('RANCHER_HARBOR_ADMIN_NEW', RANCHER_HARBOR_ADMIN_NEW)
        print('RANCHER_HARBOR_ADMIN_PASSWORD_NEW', RANCHER_HARBOR_ADMIN_PASSWORD_NEW)
        print('RANCHER_HARBOR_PRIVATE_IMAGE_NEW', RANCHER_HARBOR_PRIVATE_IMAGE_NEW)


    def teardown_method(self):
        time.sleep(.5)


    def test_set_http_harborconfig(self):
        set_harbor_config(RANCHER_HARBOR_ADMIN,
                          RANCHER_HARBOR_ADMIN_PASSWORD,
                          RANCHER_HARBOR_URL,
                          RANCHER_HARBOR_VERSION, 'db_auth')


    def test_error_user_password(self):
        password = random_test_name('Harbor')
        print('Error password: ' + password)

        r = save_harbor_config(RANCHER_HARBOR_ADMIN,
                              password,
                              RANCHER_HARBOR_URL,
                              RANCHER_HARBOR_VERSION)
        assert r.status_code == 410
        assert r.json()['code'] == "SyncHarborFailed"


    def test_update_password(self):
        update_harbor_url = admin["updateharborauth"]
        newPassword = random_test_name("Harbor")
        print(newPassword)
        headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

        r1 = update_harbor_password(newPassword,
                                    RANCHER_HARBOR_ADMIN_PASSWORD,
                                    update_harbor_url, headers)
        assert r1.status_code == 200

        r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                    newPassword,
                                    update_harbor_url, headers)
        assert r2.status_code == 200


    def test_user_setharborauth(self):
        setharborauth_url = user["setharborauth"]

        headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN}
        r = set_user_harborauth(RANCHER_USER,
                                RANCHER_HARBOR_ADMIN_PASSWORD,
                                setharborauth_url, headers)
        assert r.status_code == 200

        current_r = current_harbor_user(RANCHER_HARBOR_URL, RANCHER_HARBOR_VERSION, headers)
        assert current_r.status_code == 200
        assert current_r.json()['username'] == RANCHER_USER

        headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}
        r = set_harbor_project_member(RANCHER_HARBOR_URL, RANCHER_HARBOR_VERSION,
                                      RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1],RANCHER_USER, headers)
        assert r == 201


    def test_user_update_password(self):
        updateharborauth_url = user["updateharborauth"]
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        newPassword = random_test_name('Harbor')
        print(newPassword)
        headers = {"cookie": "R_SESS=" + RANCHER_USER_TOKEN, "x-api-harbor-admin-header": "false"}
        r1 = update_harbor_password(newPassword,
                                    RANCHER_HARBOR_ADMIN_PASSWORD,
                                    updateharborauth_url, headers)
        assert r1.status_code == 200

        r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                    newPassword, updateharborauth_url, headers)
        assert r2.status_code == 200


    def test_public_image_without_dockercredential(self):
        p_client = namespace['p_client']
        ns = namespace['ns']

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'


    def test_private_image_without_dockercredential(self):
        p_client = namespace['p_client']
        ns = namespace['ns']
        create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)


    def test_public_image_with_dockercredential(self):
        cluster = namespace['cluster']
        project = namespace['project']
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'
        c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
        ns1 = create_ns(c_client, cluster, project)
        wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl1.state == 'active'

        p_client.delete(dockerCredential)


    def test_private_image_with_dockercredential(self):
        cluster = namespace['cluster']
        project = namespace['project']
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'
        c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
        ns1 = create_ns(c_client, cluster, project)
        wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl1.state == 'active'

        p_client.delete(dockerCredential)


    def test_public_image_with_namespacedDockerCredential(self):
        cluster = namespace['cluster']
        project = namespace['project']
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'
        c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
        ns1 = create_ns(c_client, cluster, project)
        wl1 = create_workload(p_client, ns1, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl1.state == 'active'

        p_client.delete(namespacedDockerCredential)


    def test_private_image_with_namespacedDockerCredential(self):
        cluster = namespace['cluster']
        project = namespace['project']
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'
        c_client = get_cluster_client_for_token(cluster, ADMIN_TOKEN)
        ns1 = create_ns(c_client, cluster, project)
        create_workload_unavailable(p_client, ns1, RANCHER_HARBOR_PRIVATE_IMAGE)

        p_client.delete(namespacedDockerCredential)


    def test_update_password_with_dockerCredential(self):
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        update_harbor_url = admin["updateharborauth"]
        newPassword = random_test_name("Harbor")
        print(newPassword)
        headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

        r1 = update_harbor_password(newPassword,
                                    RANCHER_HARBOR_ADMIN_PASSWORD,
                                    update_harbor_url, headers)
        assert r1.status_code == 200
        time.sleep(5)

        wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl2.state == 'active'

        r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                    newPassword,
                                    update_harbor_url, headers)
        assert r2.status_code == 200

        p_client.delete(dockerCredential)


    def test_update_password_with_namespacedDockerCredential(self):
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        update_harbor_url = admin["updateharborauth"]
        newPassword = random_test_name("Harbor")
        print(newPassword)
        headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}

        r1 = update_harbor_password(newPassword,
                                    RANCHER_HARBOR_ADMIN_PASSWORD,
                                    update_harbor_url, headers)
        assert r1.status_code == 200
        time.sleep(5)

        wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl2.state == 'active'

        r2 = update_harbor_password(RANCHER_HARBOR_ADMIN_PASSWORD,
                                           newPassword,
                                           update_harbor_url, headers)
        assert r2.status_code == 200

        p_client.delete(namespacedDockerCredential)


    def test_user_public_image_without_dockercredential(self):
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'


    def test_user_private_image_without_dockercredential(self):
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)


    def test_user_public_image_with_dockercredential(self):
        cluster = namespace['cluster']
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'

        c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
        ns2 = create_ns(c_client, cluster, project)

        wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl2.state == 'active'
        p_client.delete(dockerCredential)


    def test_user_private_image_with_dockercredential(self):
        cluster = namespace['cluster']
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION,user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
        ns2 = create_ns(c_client, cluster, project)

        wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl2.state == 'active'
        p_client.delete(dockerCredential)


    def test_user_public_image_with_namespacedDockerCredential(self):
        cluster = namespace['cluster']
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl.state == 'active'

        c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
        ns2 = create_ns(c_client, cluster, project)

        wl2 = create_workload(p_client, ns2, RANCHER_HARBOR_PUBLIC_IMAGE)
        assert wl2.state == 'active'
        p_client.delete(namespacedDockerCredential)


    def test_user_private_image_with_namespacedDockerCredential(self):
        cluster = namespace['cluster']
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        c_client = get_cluster_client_for_token(cluster, RANCHER_USER_TOKEN)
        ns2 = create_ns(c_client, cluster, project)

        create_workload_unavailable(p_client, ns2, RANCHER_HARBOR_PRIVATE_IMAGE)
        p_client.delete(namespacedDockerCredential)


    def test_user_update_password_with_dockerCredential(self):
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name,
                                                   labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        update_harbor_url = user["updateharborauth"]
        newPassword = random_test_name("Harbor")
        print(newPassword)
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
        p_client.delete(dockerCredential)


    def test_user_update_password_with_namespacedDockerCredential(self):
        ns = namespace['ns']
        project = namespace['project']
        p_client = get_project_client_for_token(project, RANCHER_USER_TOKEN)
        make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                              RANCHER_HARBOR_VERSION, user['setharborauth'],
                                              RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                              RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])

        name = random_test_name("registry")
        namespacedDockerCredential = p_client.create_namespacedDockerCredential(registries=registries, name=name, namespaceId=ns.id,
                                                   labels=user_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        update_harbor_url = user["updateharborauth"]
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
        p_client.delete(namespacedDockerCredential)


    def test_update_harbor_with_old_registries(self):
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        dockerCredential = p_client.create_dockerCredential(registries=registries, name=name, labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        set_harbor_config(RANCHER_HARBOR_ADMIN_NEW,
                          RANCHER_HARBOR_ADMIN_PASSWORD_NEW,
                          RANCHER_HARBOR_URL_NEW,
                          RANCHER_HARBOR_VERSION_NEW, 'db_auth')

        create_workload_unavailable(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)

        set_harbor_config(RANCHER_HARBOR_ADMIN,
                          RANCHER_HARBOR_ADMIN_PASSWORD,
                          RANCHER_HARBOR_URL,
                          RANCHER_HARBOR_VERSION, 'db_auth')
        p_client.delete(dockerCredential)


    def test_update_harbor_with_new_registries(self):
        ns = namespace['ns']
        p_client = namespace['p_client']

        name = random_test_name("registry")
        dockerCredential1 = p_client.create_dockerCredential(registries=registries, name=name, labels=admin_harbor_dockercredential_label)

        wl = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE)
        assert wl.state == 'active'

        set_harbor_config(RANCHER_HARBOR_ADMIN_NEW,
                          RANCHER_HARBOR_ADMIN_PASSWORD_NEW,
                          RANCHER_HARBOR_URL_NEW,
                          RANCHER_HARBOR_VERSION_NEW, 'db_auth')

        name2 = random_test_name("registry")
        registries2 = {RANCHER_HARBOR_HOST_NEW:{}}
        dockerCredential2 = p_client.create_dockerCredential(registries=registries2, name=name2, labels=admin_harbor_dockercredential_label)

        wl2 = create_workload(p_client, ns, RANCHER_HARBOR_PRIVATE_IMAGE_NEW)
        assert wl2.state == 'active'
        p_client.delete(dockerCredential1)
        p_client.delete(dockerCredential2)


    def teardown_class(self):
        global i
        i = i + 1
        time.sleep(3)


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

    users = client.list_user(username=RANCHER_HARBOR_ADMIN)
    assert len(users) == 1
    admin_user = users.data[0]
    admin["setharborauth"] = admin_user.actions["setharborauth"]
    admin["updateharborauth"] = admin_user.actions["updateharborauth"]

    username = random_test_name('harbor-user')
    standard_user, standard_user_token = create_user(
        RANCHER_AUTH_URL, client, username,
        RANCHER_HARBOR_ADMIN_PASSWORD, 'user')

    global RANCHER_USER
    RANCHER_USER = username
    global RANCHER_USER_TOKEN
    RANCHER_USER_TOKEN = standard_user_token

    user["setharborauth"] = standard_user.actions['setharborauth']
    user["updateharborauth"] = standard_user.actions["updateharborauth"]
    user["self"] = standard_user.links["self"]

    assign_members_to_project(client, standard_user, p, 'project-member')

    def fin():
        client = namespace["client"]
        client.delete(namespace["project"])
        users = client.list_user(username=RANCHER_USER)
        assert len(users) == 1
        user = users.data[0]
        client.delete(user)
    request.addfinalizer(fin)


def test_delete_harborconfig():
    make_user_use_private_image_available(RANCHER_USER_TOKEN, RANCHER_HARBOR_URL,
                                          RANCHER_HARBOR_VERSION, user['setharborauth'],
                                          RANCHER_USER, RANCHER_HARBOR_ADMIN_PASSWORD,
                                          RANCHER_HARBOR_PRIVATE_IMAGE.split('/')[1])
    time.sleep(.5)
    set_harbor_setting('', '', '', '')

    r = requests.get(user['self'], verify=False, headers=headers)
    assert 'authz.management.cattle.io.cn/harboremail' not in r.json()['annotations']
    assert 'management.harbor.pandaria.io/synccomplete' not in r.json()['annotations']