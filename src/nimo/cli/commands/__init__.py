from nimo.cli.commands import analyse, cashflow, categories, dashboard, generate, import_data, init, users

COMMAND_MODULES = [init, users, generate, import_data, analyse, categories, cashflow, dashboard]

__all__ = ["COMMAND_MODULES"]
