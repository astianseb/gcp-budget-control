import functions_framework
import json
from httplib2 import Http
from google.api_core import retry
from googleapiclient import discovery
from google.cloud import pubsub_v1
from google.cloud import bigquery
PROJECT_ID = 'sg-budget-control'
PROJECT_NAME = f'projects/{PROJECT_ID}'
WEBHOOK = "https://chat.googleapis.com/v1/spaces/AAAAKl2Yltc/messages?key=<KEY>&token=<TOKEN>"
BILLING_ACCOUNT_ID = '<BILLING_ACCOUNT_ID>'
BILLING_ACCOUNT_RESOURCE = f'billingAccounts/{BILLING_ACCOUNT_ID}'
SUBSCRIPTION_NAME = 'sg-budget-notifications-sub'

@functions_framework.http
def send_notification(request):

    message = __get_message_from_pubsub(PROJECT_ID, SUBSCRIPTION_NAME)[0]

    pubsub_data = message.data
    pubsub_json = json.loads(pubsub_data)
    
    cost_amount = pubsub_json['costAmount']
    budget_amount = pubsub_json['budgetAmount']
    currency = pubsub_json['currencyCode']

    billing_account_id = message.attributes['billingAccountId']

    cost_dict = __get_data_from_bq()
    active_projects_list = __get_active_projects(BILLING_ACCOUNT_RESOURCE)

    message = ""
    for item in cost_dict:
        if item not in active_projects_list:
            message += f'DELETED {item}: {cost_dict[item]} {currency}\n'
        else:
            message += f'------->        *{item}: {cost_dict[item]} {currency}*\n'

    __webhook_send_message(message)

    return f'Finished'

def __get_active_projects(billing_account_resource):
    billing = discovery.build(
        'cloudbilling',
        'v1',
        cache_discovery=False,
    )

    projects_dict = billing.billingAccounts().projects().list(name=billing_account_resource).execute()
    projects_list = []
    for project in projects_dict['projectBillingInfo']:
        projects_list.append(project['projectId'])


    return projects_list


def __get_data_from_bq():
    client = bigquery.Client(project=PROJECT_ID)

    query_string = """SELECT
        project.name as project,
        EXTRACT(MONTH FROM usage_start_time) as month,
        ROUND(SUM(cost), 2) as charges,
        ROUND(SUM((SELECT SUM(amount) FROM UNNEST(credits))),2) as credits
        FROM `sg-budget-control.sg_detailed_usage_cost.gcp_billing_export_resource_v1_01CF89_BC7A7D_004102`
        GROUP BY project, month
        ORDER by project, month"""
    
    query_job = client.query(query_string)

    project_charges = {}
    for row in query_job.result():
        charge = float(row.get('charges'))
        project = row.get('project')
        if charge > float(0):
            project_charges[project] = charge
           
    return dict(sorted(project_charges.items(), key=lambda item: item[1], reverse=True))


def __webhook_send_message(message):
    url = WEBHOOK

    bot_message = {
        'text' : f'{message}'}

    message_headers = {'Content-Type': 'application/json; charset=UTF-8'}

    http_obj = Http()

    response = http_obj.request(
        uri=url,
        method='POST',
        headers=message_headers,
        body=json.dumps(bot_message),
    )

  
def __get_message_from_pubsub(project_id, subscription_id):
   
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_id)

    NUM_MESSAGES = 1

    # Wrap the subscriber in a 'with' block to automatically call close() to
    # close the underlying gRPC channel when done.
    with subscriber:
        # The subscriber pulls a specific number of messages. The actual
        # number of messages pulled may be smaller than max_messages.
        response = subscriber.pull(
            request={"subscription": subscription_path, "max_messages": NUM_MESSAGES},
            retry=retry.Retry(deadline=300),
        )

        if len(response.received_messages) == 0:
            return

        ack_ids = []
        message_list = []
        for received_message in response.received_messages:
            message_list.append(received_message.message)
            ack_ids.append(received_message.ack_id)

        # Acknowledges the received messages so they will not be sent again.
        subscriber.acknowledge(
            request={"subscription": subscription_path, "ack_ids": ack_ids}
        )

        print(
            f"Received and acknowledged {len(response.received_messages)} messages from {subscription_path}."
        )
    return message_list