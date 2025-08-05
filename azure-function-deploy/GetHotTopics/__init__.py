import logging
import azure.functions as func
import json
import requests
import os
from datetime import datetime


def main(mytimer: func.TimerRequest) -> None:
    logging.info('� Timer trigger started - calling Summary Womble.')

    # Configuration for the scheduled run
    womble_config = {
        "source": "reddit",
        "topics": [
            "technology",
            "programming", 
            "MachineLearning",
            "datascience",
            "computerscience",
            "gadgets",
            "Futurology"
        ],
        "limit": 10,
        "credentials": {
            "source": "keyvault"  # Use default Key Vault setup
        },
        "storage": {
            # Use environment variables (set by Azure Function App settings)
        }
    }

    try:
        # Get the function app URL
        function_app_name = os.environ.get("WEBSITE_SITE_NAME", "hot-topics-func")
        womble_url = f"https://{function_app_name}.azurewebsites.net/api/SummaryWomble"
        
        # Get the function key for authorization
        # In production, you'd get this from Key Vault or app settings
        # For now, we'll make the call without the key (will work within the same function app)
        
        logging.info(f"🔗 Calling Summary Womble at: {womble_url}")
        
        # Make the HTTP request to the womble function
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Summary Wombles Timer/1.0"
        }
        
        response = requests.post(
            womble_url,
            json=womble_config,
            headers=headers,
            timeout=300  # 5 minutes timeout
        )
        
        if response.status_code == 200:
            result_data = response.json()
            total_topics = result_data.get('total_topics', 0)
            total_subreddits = result_data.get('total_subreddits', 0)
            
            logging.info(f"✅ Summary Womble completed successfully: {total_topics} topics from {total_subreddits} subreddits")
            
            # Log individual results
            for result in result_data.get('results', []):
                if result.get('status') == 'success':
                    logging.info(f"  ✅ r/{result['subreddit']}: {result['topics_count']} topics -> {result['blob_name']}")
                else:
                    logging.error(f"  ❌ r/{result['subreddit']}: {result.get('status')} - {result.get('error', 'Unknown error')}")
                    
        else:
            error_text = response.text
            logging.error(f"❌ Summary Womble failed with status {response.status_code}: {error_text}")
            
    except requests.exceptions.Timeout:
        logging.error("❌ Summary Womble request timed out after 5 minutes")
    except Exception as e:
        logging.error(f"❌ Failed to call Summary Womble: {e}")

    if mytimer.past_due:
        logging.info('⚠️ The timer is past due!')

    logging.info('✅ Timer trigger completed.')
