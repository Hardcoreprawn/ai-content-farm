#!/bin/bash
# Cost optimization analysis for AI Content Farm Azure deployment

echo "💰 AI Content Farm - Cost Optimization Analysis"
echo "=" * 50

echo ""
echo "🏗️  Infrastructure Cost Breakdown (Monthly estimates):"
echo ""

echo "📦 Container Apps Environment (Consumption Plan):"
echo "   • Scale-to-zero enabled: \$0 when idle"
echo "   • Only pay for execution time: ~\$0.000024/vCPU-second"
echo "   • Estimated cost: \$5-15/month (depending on usage)"
echo ""

echo "🗄️  Storage Account (Hot tier):"
echo "   • Storage: \$0.0184/GB (first 50TB)"
echo "   • Operations: \$0.0036/10k operations"
echo "   • Estimated cost: \$2-5/month"
echo ""

echo "🤖 Azure OpenAI Service (Pay-per-token):"
echo "   • GPT-4o-mini: \$0.00015/1k input tokens, \$0.0006/1k output tokens"
echo "   • Estimated cost: \$10-30/month (depends on content volume)"
echo ""

echo "🔑 Key Vault:"
echo "   • Standard tier: \$0.03/10k operations"
echo "   • Estimated cost: \$1-2/month"
echo ""

echo "📊 Service Bus (Standard tier - required for Event Grid):"
echo "   • Base: \$0.05/million operations"
echo "   • Estimated cost: \$3-8/month"
echo ""

echo "🏷️  Container Registry (Basic):"
echo "   • Storage: \$0.167/GB/day"
echo "   • Estimated cost: \$2-5/month"
echo ""

echo "=" * 50
echo "💸 TOTAL ESTIMATED MONTHLY COST: \$23-65"
echo "   (Lower end when system is idle, higher during active content generation)"
echo ""

echo "🎯 Cost Optimization Features Enabled:"
echo "   ✅ Scale-to-zero containers (no cost when idle)"
echo "   ✅ Event-driven architecture (no polling overhead)"
echo "   ✅ Basic/Standard SKUs (minimal required tiers)"
echo "   ✅ Short log retention (30 days)"
echo "   ✅ Efficient resource sizing (0.5 CPU, 1Gi memory)"
echo ""

echo "📈 Usage Patterns for Minimal Cost:"
echo "   • Content generation only when new ranked content appears"
echo "   • Containers automatically scale down to 0 when idle"
echo "   • No background processes consuming resources"
echo "   • Pay-per-use model for AI generation"
echo ""

echo "🚨 Cost Monitoring Recommendations:"
echo "   • Set up Azure Cost Alerts at \$50/month"
echo "   • Monitor Azure OpenAI token usage"
echo "   • Review monthly usage reports"
echo "   • Consider reducing retention periods if costs grow"
echo ""

echo "🎉 This architecture is designed for minimal ongoing costs!"
echo "   When there's no content to process, costs approach near-zero."
