from .entfunc import *

headers = {"cookie": "R_SESS="+ADMIN_TOKEN}
CATTLE_HARBOR_CONFIG_URL = (CATTLE_API_URL + '/users?action=saveharborconfig').replace('//v3','/v3')
CATTLE_HARBOR_SERVER_URL = (CATTLE_API_URL + '/settings/harbor-server-url').replace('//v3','/v3')
CATTLE_HARBOR_ADMIN_AUTH = (CATTLE_API_URL + '/settings/harbor-admin-auth').replace('//v3','/v3')
CATTLE_HARBOR_VERSION = (CATTLE_API_URL + '/settings/harbor-version').replace('//v3','/v3')
CATTLE_HARBOR_AUTH_MODE = (CATTLE_API_URL + '/settings/harbor-auth-mode').replace('//v3','/v3')
CATTLE_SYNC_HARBOR_USER = (CATTLE_API_URL + '/users?action=syncharboruser').replace('//v3','/v3')
RANCHER_AUTH_URL = (CATTLE_TEST_URL + "/v3-public/localproviders/local?action=login").replace('//v3','/v3')


def save_harbor_config(username, password, harbor_url, harbor_version, headers = headers):
    harbor_config_json = {"username": username,
                          "serverURL": harbor_url,
                          "password": password,
                          "version": harbor_version,
                          "responseType": "json"}
    r = requests.post(CATTLE_HARBOR_CONFIG_URL,
                      json=harbor_config_json, verify=False, headers=headers)
    return r


def set_harbor_server(harbor_url, headers = headers):
    harbor_server_json = {"value": harbor_url,
                          "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_SERVER_URL,
                     json=harbor_server_json, verify=False, headers=headers)
    return r


def set_harbor_auth(admin, headers = headers):
    harbor_auth_json = {"value": admin,
                        "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_ADMIN_AUTH,
                                 json=harbor_auth_json, verify=False, headers=headers)
    return r


def set_harbor_version(version, headers = headers):
    harbor_version_json = {"value": version,
                        "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_VERSION,
                                 json=harbor_version_json, verify=False, headers=headers)
    return r


def set_harbor_mode(mode, headers = headers):
    harbor_mode_json = {"value": mode,
                        "responseType": "json"}
    r = requests.put(CATTLE_HARBOR_AUTH_MODE,
                                 json=harbor_mode_json, verify=False, headers=headers)
    return r


def  set_harbor_config(username, password, harbor_url, harbor_version, harbor_mode, headers = headers):
    harbor_config_r = save_harbor_config(username, password, harbor_url, harbor_version, headers)
    assert harbor_config_r.status_code == 200

    set_harbor_setting(harbor_url, username, harbor_version, harbor_mode, headers)


def set_harbor_setting(harbor_url, username, harbor_version, harbor_mode, headers = headers):
    harbor_server_r = set_harbor_server(harbor_url, headers)
    assert harbor_server_r.status_code == 200
    assert harbor_server_r.json()['value'] == harbor_url

    harbor_auth_r = set_harbor_auth(username, headers)
    assert harbor_auth_r.status_code == 200
    assert harbor_auth_r.json()['value'] == username

    harbor_version_r = set_harbor_version(harbor_version, headers)
    assert harbor_version_r.status_code == 200
    assert harbor_version_r.json()['value'] == harbor_version

    harbor_mode_r = set_harbor_mode(harbor_mode, headers)
    assert harbor_mode_r.status_code == 200
    assert harbor_mode_r.json()['value'] == harbor_mode


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

    r = requests.post(url, json=json, verify=False, headers=headers)
    return r


def current_harbor_user(harbor_url, version, headers = headers):
    current_url = get_current_url(harbor_url, version)
    r = requests.get(current_url, verify=False, headers=headers)
    return r


def get_current_url(harbor_url, version):
    url = CATTLE_TEST_URL.strip('/') + '/meta/harbor/' + (harbor_url.strip('/')).replace('//','/') + ('/api/' + version + '/users/current').replace('//','/')
    return url

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


def make_user_use_private_image_available(token, harbor_url, harbor_version, setharborauth_url, user, password, project):
    headers = {"cookie": "R_SESS=" + token}
    current_r = current_harbor_user(harbor_url, harbor_version, headers)
    if current_r.status_code != 200:
        setharborauth_r = set_user_harborauth(user, password, setharborauth_url, headers)
        assert setharborauth_r.status_code == 200

        headers = {"cookie": "R_SESS=" + ADMIN_TOKEN, "x-api-harbor-admin-header": "true"}
        r = set_harbor_project_member(harbor_url, harbor_version, project, user, headers)
        assert r == 201


def get_harbor_project_id(harbor_url, version, project_name, headers=headers):
    url = CATTLE_TEST_URL.strip('/') + '/meta/harbor/' + (harbor_url.strip('/')).replace('//','/') + \
          ('/api/' + version + '/projects?name=' + project_name + '&page_size=100&page=1').replace('//','/')
    r = requests.get(url, verify=False, headers=headers)
    for project in r.json():
        if project['name'] == project_name:
            return project['project_id']


def set_harbor_project_member(harbor_url, version, project_name, user_name, headers=headers):
    projectid = get_harbor_project_id(harbor_url, version, project_name, headers)
    url = CATTLE_TEST_URL.strip('/') + '/meta/harbor/' + (harbor_url.strip('/')).replace('//','/') + \
          ('/api/' + version +'/projects/' + str(projectid) +'/members').replace('//','/')
    json = {"member_user": {"username": user_name}, "role_id": 5}
    r = requests.post(url, json=json, verify=False, headers=headers)
    return r.status_code