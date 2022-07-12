import base64
import json
from locale import currency
import os
from httplib2 import Http
from googleapiclient import discovery
PROJECT_ID = os.getenv('GCP_PROJECT')
PROJECT_NAME = f'projects/{PROJECT_ID}'
WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAAAKl2Yltc/messages?key=<KEY>&token=<TOKEN>"


def stop_billing(data, context):
    pubsub_data = base64.b64decode(data['data']).decode('utf-8')
    pubsub_json = json.loads(pubsub_data)
    cost_amount = pubsub_json['costAmount']
    budget_amount = pubsub_json['budgetAmount']
    currency = pubsub_json['currencyCode']

    print(data)
    BILLING_ACCOUNT_ID = data['attributes']['billingAccountId']
    BILLING_ACCOUNT_RESOURCE = f'billingAccounts/{BILLING_ACCOUNT_ID}'

    if cost_amount <= budget_amount:

        print(f'No action necessary. Current cost: {cost_amount}')
        return

    if PROJECT_ID is None:
        print('No project specified with environment variable')
        return

    billing = discovery.build(
        'cloudbilling',
        'v1',
        cache_discovery=False,
    )

    projects_dict = billing.billingAccounts().projects().list(name=BILLING_ACCOUNT_RESOURCE).execute()
    
    projects = billing.projects()

    project_id_list = [  "projects/" + project['projectId'] for project in projects_dict['projectBillingInfo']]
    
    print(project_id_list)

    for project_name in project_id_list:
        billing_enabled = __is_billing_enabled(project_name, projects)
        print("billing_enabled:", billing_enabled)
        
        if billing_enabled:
            print(f'Disabling billing on: {project_name}')
            __webhook_send_message(cost_amount, budget_amount, currency, BILLING_ACCOUNT_ID, project_name)

            __disable_billing_for_project(project_name, projects)
        else:
            print('Billing already disabled')


def __webhook_send_message(cost_amount, budget_amount, currency, billing_account_id, projects):
    url = WEBHOOK
    bot_message = {
        'text' : 'Billing account: {3}\nBudget limit {1} {2} crossed!\nDisablling billing for project {4}\nCurrent cost: {0} {2}\nCurrent budget {1} {2}'.format(cost_amount, budget_amount, currency, billing_account_id, projects)}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=json.dumps(bot_message),
    )

    print(response)
    


def __is_billing_enabled(project_name, projects):
    """
    Determine whether billing is enabled for a project
    @param {string} project_name Name of project to check if billing is enabled
    @return {bool} Whether project has billing enabled or not
    """
    try:
        res = projects.getBillingInfo(name=project_name).execute()
        return res['billingEnabled']
    except KeyError:
        # If billingEnabled isn't part of the return, billing is not enabled
        return False
    except Exception:
        print('Unable to determine if billing is enabled on specified project, assuming billing is enabled')
        return True


def __disable_billing_for_project(project_name, projects):
    """
    Disable billing for a project by removing its billing account
    @param {string} project_name Name of project disable billing on
    """
    body = {'billingAccountName': ''}  # Disable billing
    try:
        res = projects.updateBillingInfo(name=project_name, body=body).execute()
        print(f'Billing disabled: {json.dumps(res)}')
    except Exception:
        print('Failed to disable billing, possibly check permissions')