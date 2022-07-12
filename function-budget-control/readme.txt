README

This is a GCP function for automated billing control. Billing data is sourced from PubSub
notification. GCP sends notification to PubSub every 20 minutes. If actual spend is higher
than billing threshold, projects are detached from billing account and notification to Google Chat
is sent through a webhook.



Local function development
--------------------------

https://cloud.google.com/functions/docs/functions-framework
https://github.com/GoogleCloudPlatform/functions-framework-python


0. Instal functions framework
pip install functions-framework

1. Start function with PUBSUB event

functions-framework --target=stop_billing --signature-type=event

2. Function call - generate PUBSUB event call 

curl \
    --header "Content-type: application/json" \
    --request POST \
    --data '@mockPubsub.json' \
    http://localhost:8080