from nimo.cli.commands import (
    analyse,
    backup,
    behaviours,
    budget,
    cashflow,
    categories,
    dashboard,
    doctor,
    export_data,
    forecast,
    generate,
    goals,
    import_data,
    init,
    invest,
    report,
    users,
)

COMMAND_MODULES = [
    init, users, generate, import_data, analyse, categories, cashflow,
    backup, doctor, export_data,
    behaviours, forecast, budget, goals, invest, report, dashboard,
]

__all__ = ["COMMAND_MODULES"]
