from __future__ import annotations

from dataclasses import dataclass

from nimo.application.container import ApplicationContainer


@dataclass(frozen=True, slots=True)
class DashboardServices:
    container: ApplicationContainer

    @property
    def analysis(self):
        return self.container.analysis

    @property
    def ingestion(self):
        return self.container.ingestion

    @property
    def generation(self):
        return self.container.generation

    @property
    def categorisation(self):
        return self.container.categorisation

    @property
    def layouts(self):
        return self.container.layouts

    @property
    def behaviours(self):
        return self.container.behaviours

    @property
    def forecasting(self):
        return self.container.forecasting

    @property
    def planning(self):
        return self.container.planning

    @property
    def investing(self):
        return self.container.investing

    @property
    def reporting(self):
        return self.container.reporting

    @property
    def backups(self):
        return self.container.backups
