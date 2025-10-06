#!/bin/bash
set -e

# Clear Azure Storage Queue
# Removes all messages from a specified queue

STORAGE_ACCOUNT="aicontentprodstkwakpx"
RESOURCE_GROUP="ai-content-prod-rg"
QUEUE_NAME="${1:-content-processing-requests}"

echo "⚠️  WARNING: This will DELETE all messages from queue: $QUEUE_NAME"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 1
fi

echo ""
echo "🔑 Getting storage connection string..."
CONN_STRING=$(az storage account show-connection-string \
    --name "$STORAGE_ACCOUNT" \
    --resource-group "$RESOURCE_GROUP" \
    --query connectionString -o tsv)

echo ""
echo "📊 Checking queue depth..."
MESSAGE_COUNT=$(az storage message peek \
    --queue-name "$QUEUE_NAME" \
    --num-messages 32 \
    --connection-string "$CONN_STRING" \
    --query "length(@)" -o tsv 2>&1 | tail -1)

if [ "$MESSAGE_COUNT" -eq 0 ]; then
    echo "✅ Queue is already empty"
    exit 0
fi

echo "Found $MESSAGE_COUNT+ messages in queue"

echo ""
echo "🗑️  Clearing queue (deleting all messages)..."

# Delete messages in batches until queue is empty
BATCH_COUNT=0
while true; do
    # Get up to 32 messages (max per request)
    MESSAGES=$(az storage message get \
        --queue-name "$QUEUE_NAME" \
        --num-messages 32 \
        --connection-string "$CONN_STRING" \
        --query "[].{id: id, popReceipt: popReceipt}" -o tsv 2>/dev/null)

    if [ -z "$MESSAGES" ]; then
        break
    fi

    # Delete each message
    echo "$MESSAGES" | while IFS=$'\t' read -r MSG_ID POP_RECEIPT; do
        if [ -n "$MSG_ID" ]; then
            az storage message delete \
                --queue-name "$QUEUE_NAME" \
                --id "$MSG_ID" \
                --pop-receipt "$POP_RECEIPT" \
                --connection-string "$CONN_STRING" \
                --output none 2>/dev/null || true
        fi
    done

    BATCH_COUNT=$((BATCH_COUNT + 1))
    echo "  Batch $BATCH_COUNT cleared (32 messages)"
done

echo "✅ Queue cleared! ($BATCH_COUNT batches processed)"
echo ""
echo "Verification:"
REMAINING=$(az storage message peek \
    --queue-name "$QUEUE_NAME" \
    --num-messages 1 \
    --connection-string "$CONN_STRING" \
    --query "length(@)" -o tsv 2>&1 | tail -1)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ Confirmed: Queue is empty"
else
    echo "⚠️  Warning: Queue still has messages (may be in-flight)"
fi
