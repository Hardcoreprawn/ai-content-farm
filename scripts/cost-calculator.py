#!/usr/bin/env python3
"""
AI Content Farm Cost Calculator
Estimates monthly Azure costs based on usage patterns
"""


def calculate_function_costs(executions_per_month, avg_duration_seconds, memory_mb):
    """Calculate Azure Functions costs"""
    # Free tier limits
    FREE_EXECUTIONS = 1_000_000
    FREE_GB_SECONDS = 400_000

    # Pricing (USD)
    EXECUTION_PRICE = 0.20 / 1_000_000  # per execution
    GB_SECOND_PRICE = 0.000016  # per GB-second

    # Calculate GB-seconds
    memory_gb = memory_mb / 1024
    gb_seconds = executions_per_month * avg_duration_seconds * memory_gb

    # Calculate costs after free tier
    execution_cost = max(0, executions_per_month - FREE_EXECUTIONS) * EXECUTION_PRICE
    gb_second_cost = max(0, gb_seconds - FREE_GB_SECONDS) * GB_SECOND_PRICE

    return {
        "executions": executions_per_month,
        "gb_seconds": gb_seconds,
        "execution_cost": execution_cost,
        "gb_second_cost": gb_second_cost,
        "total_cost": execution_cost + gb_second_cost,
        "under_free_tier": executions_per_month <= FREE_EXECUTIONS
        and gb_seconds <= FREE_GB_SECONDS,
    }


def calculate_storage_costs(storage_gb, read_ops, write_ops, list_ops):
    """Calculate Azure Storage costs"""
    # Pricing per month (USD)
    STORAGE_PRICE = 0.0196  # per GB
    READ_PRICE = 0.0043  # per 10K operations
    WRITE_PRICE = 0.054  # per 10K operations
    LIST_PRICE = 0.054  # per 10K operations

    storage_cost = storage_gb * STORAGE_PRICE
    read_cost = (read_ops / 10_000) * READ_PRICE
    write_cost = (write_ops / 10_000) * WRITE_PRICE
    list_cost = (list_ops / 10_000) * LIST_PRICE

    return {
        "storage_cost": storage_cost,
        "read_cost": read_cost,
        "write_cost": write_cost,
        "list_cost": list_cost,
        "total_cost": storage_cost + read_cost + write_cost + list_cost,
    }


def calculate_insights_costs(data_gb):
    """Calculate Application Insights costs"""
    FREE_GB = 5
    PRICE_PER_GB = 2.30

    billable_gb = max(0, data_gb - FREE_GB)
    cost = billable_gb * PRICE_PER_GB

    return {
        "data_gb": data_gb,
        "billable_gb": billable_gb,
        "cost": cost,
        "under_free_tier": data_gb <= FREE_GB,
    }


def calculate_logs_costs(data_gb):
    """Calculate Log Analytics costs"""
    FREE_GB = 5
    PRICE_PER_GB = 2.99

    billable_gb = max(0, data_gb - FREE_GB)
    cost = billable_gb * PRICE_PER_GB

    return {
        "data_gb": data_gb,
        "billable_gb": billable_gb,
        "cost": cost,
        "under_free_tier": data_gb <= FREE_GB,
    }


def print_scenario(name, functions, storage, insights, logs):
    """Print cost breakdown for a scenario"""
    print(f"\n{'='*50}")
    print(f"SCENARIO: {name}")
    print(f"{'='*50}")

    print(f"\n📱 Azure Functions:")
    print(f"   Executions: {functions['executions']:,}")
    print(f"   GB-seconds: {functions['gb_seconds']:,.0f}")
    print(f"   Cost: ${functions['total_cost']:.2f}")
    if functions["under_free_tier"]:
        print(f"   ✅ Under free tier!")

    print(f"\n💾 Storage Account:")
    print(f"   Storage Cost: ${storage['storage_cost']:.2f}")
    print(
        f"   Operations: ${storage['read_cost'] + storage['write_cost'] + storage['list_cost']:.2f}"
    )
    print(f"   Total: ${storage['total_cost']:.2f}")

    print(f"\n📊 Application Insights:")
    print(f"   Data: {insights['data_gb']:.1f} GB")
    print(f"   Cost: ${insights['cost']:.2f}")
    if insights["under_free_tier"]:
        print(f"   ✅ Under free tier!")

    print(f"\n📝 Log Analytics:")
    print(f"   Data: {logs['data_gb']:.1f} GB")
    print(f"   Cost: ${logs['cost']:.2f}")
    if logs["under_free_tier"]:
        print(f"   ✅ Under free tier!")

    total_cost = (
        functions["total_cost"]
        + storage["total_cost"]
        + insights["cost"]
        + logs["cost"]
    )

    print(f"\n💰 TOTAL MONTHLY COST: ${total_cost:.2f}")

    return total_cost


def main():
    print("🚀 AI Content Farm - Azure Cost Calculator")
    print("=" * 60)

    # Scenario 1: Current MVP Plan
    functions_mvp = calculate_function_costs(
        executions_per_month=10_800, avg_duration_seconds=15, memory_mb=512
    )
    storage_mvp = calculate_storage_costs(
        storage_gb=25, read_ops=100_000, write_ops=50_000, list_ops=10_000
    )
    insights_mvp = calculate_insights_costs(3.0)
    logs_mvp = calculate_logs_costs(2.0)

    cost_mvp = print_scenario(
        "MVP/Current Plan", functions_mvp, storage_mvp, insights_mvp, logs_mvp
    )

    # Scenario 2: Moderate Growth (5x)
    functions_mod = calculate_function_costs(
        executions_per_month=54_000, avg_duration_seconds=15, memory_mb=512
    )
    storage_mod = calculate_storage_costs(
        storage_gb=125, read_ops=500_000, write_ops=250_000, list_ops=50_000
    )
    insights_mod = calculate_insights_costs(8.0)
    logs_mod = calculate_logs_costs(6.0)

    cost_mod = print_scenario(
        "Moderate Growth (5x)", functions_mod, storage_mod, insights_mod, logs_mod
    )

    # Scenario 3: Heavy Usage
    functions_heavy = calculate_function_costs(
        executions_per_month=1_200_000, avg_duration_seconds=18, memory_mb=512
    )
    storage_heavy = calculate_storage_costs(
        storage_gb=500, read_ops=2_000_000, write_ops=1_000_000, list_ops=200_000
    )
    insights_heavy = calculate_insights_costs(20.0)
    logs_heavy = calculate_logs_costs(15.0)

    cost_heavy = print_scenario(
        "Heavy Usage", functions_heavy, storage_heavy, insights_heavy, logs_heavy
    )

    # Summary
    print(f"\n{'='*60}")
    print("📈 COST SUMMARY")
    print(f"{'='*60}")
    print(f"MVP/Current:     ${cost_mvp:.2f}/month")
    print(f"Moderate Growth: ${cost_mod:.2f}/month")
    print(f"Heavy Usage:     ${cost_heavy:.2f}/month")
    print(f"\n🎯 Recommendation: Start with MVP plan and monitor growth")
    print(f"💡 The serverless architecture scales costs very efficiently!")


if __name__ == "__main__":
    main()
