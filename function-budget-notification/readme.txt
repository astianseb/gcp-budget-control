README

This is a GCP function to send budget notification to Google Chat with a chat webhook.
Function should be triggered by HTTP call by GCP Scheduler




Local function development
--------------------------

https://cloud.google.com/functions/docs/functions-framework
https://github.com/GoogleCloudPlatform/functions-framework-python


0. Instal functions framework
pip install functions-framework

1. Start function accepting HTTP calls

functions-framework --target send_notification --debug

2. HTTP Function call

curl localhost:8080