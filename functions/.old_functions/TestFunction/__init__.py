import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Test function processed a request.')
    
    return func.HttpResponse(
        "Hello World from Test Function",
        status_code=200,
        headers={"Content-Type": "text/plain"}
    )
