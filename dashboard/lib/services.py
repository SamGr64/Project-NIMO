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
